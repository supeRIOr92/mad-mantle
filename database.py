"""
database.py
MAD — Mantle Anomaly Detector
Supabase backend: signal_log + wallet_profile + agent_registry + pool_baseline
"""

import logging
import json
from datetime import date, datetime, timezone
from typing import Optional
from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_KEY

logger = logging.getLogger(__name__)

# ── Client ────────────────────────────────────────────────────────────────────
_client: Optional[Client] = None

def get_client() -> Client:
    global _client
    if _client is None:
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise RuntimeError("SUPABASE_URL or SUPABASE_KEY not set")
        from supabase.lib.client_options import ClientOptions
        _client = create_client(SUPABASE_URL, SUPABASE_KEY, options=ClientOptions(httpx_client_args={"http2": False}))
    return _client

def init_db():
    """Verify Supabase connection. Tables created via SQL migration."""
    try:
        client = get_client()
        client.table("signal_log").select("id").limit(1).execute()
        logger.info("[db] Supabase connection OK")
    except Exception as e:
        logger.error("[db] Supabase connection failed: %s", e)
        raise


# ── Signal Log ────────────────────────────────────────────────────────────────

def log_signal(
    dex: str,
    pool_address: str,
    tx_hashes: list,
    l1_score: float,
    l2_score: float,
    l3_score: float,
    s_dex: float,
    s_final: float,
    alert_level: str,
    environment: str = "live",
    is_simulated: bool = False,
    **kwargs,
) -> Optional[int]:
    """Insert a new signal. Returns inserted row id."""
    try:
        row = {
            "dex": dex,
            "pool_address": pool_address.lower(),
            "tx_hashes": tx_hashes,
            "l1_score": round(l1_score, 2),
            "l2_score": round(l2_score, 2),
            "l3_score": round(l3_score, 2),
            "s_dex": round(s_dex, 2),
            "s_final": round(s_final, 2),
            "alert_level": alert_level,
            "environment": environment,
            "is_simulated": is_simulated,
            "l1_methods": kwargs.get("l1_methods", []),
            "l2_methods": kwargs.get("l2_methods", []),
            "l3_methods": kwargs.get("l3_methods", []),
            "top_wallets": kwargs.get("top_wallets", []),
            "volume_usd": kwargs.get("volume_usd"),
            "corroboration": kwargs.get("corroboration", 1),
            "phase1_active": bool(kwargs.get("phase1_active", False)),
            "notes": kwargs.get("notes"),
            # v3.0 — Aave context signal (context only, bukan alert trigger)
            "aave_signal": round(float(kwargs.get("aave_signal", 0.0)), 4),
            "aave_label": kwargs.get("aave_label", "NO_DATA"),
        }
        res = get_client().table("signal_log").insert(row).execute()
        row_id = res.data[0]["id"] if res.data else None
        logger.info("[db] signal_log insert id=%s level=%s s_final=%.1f", row_id, alert_level, s_final)
        return row_id
    except Exception as e:
        logger.error("[db] log_signal failed: %s", e)
        return None


def get_recent_signals(limit: int = 50, alert_level: Optional[str] = None, environment: str = "live") -> list:
    """Fetch recent signals, optionally filtered by alert_level."""
    try:
        q = get_client().table("signal_log").select("*").order("created_at", desc=True).limit(limit).eq("environment", environment)
        if alert_level:
            q = q.eq("alert_level", alert_level)
        res = q.execute()
        return res.data or []
    except Exception as e:
        logger.error("[db] get_recent_signals failed: %s", e)
        return []


# ── Wallet Profile ────────────────────────────────────────────────────────────

def upsert_wallet(address: str, **kwargs):
    """Upsert wallet profile."""
    try:
        row = {"address": address.lower(), **kwargs}
        row["last_updated"] = datetime.now(timezone.utc).isoformat()
        get_client().table("wallet_profile").upsert(row, on_conflict="address").execute()
    except Exception as e:
        logger.error("[db] upsert_wallet failed for %s: %s", address, e)


def get_wallet(address: str) -> Optional[dict]:
    """Fetch wallet profile by address."""
    try:
        res = get_client().table("wallet_profile").select("*").eq("address", address.lower()).limit(1).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        logger.error("[db] get_wallet failed for %s: %s", address, e)
        return None


def get_top_wallets(order_by: str = "roi_7d", limit: int = 10) -> list:
    """Get top wallets sorted by field."""
    allowed = {"roi_7d", "wash_ratio", "reputation_score", "smart_score"}
    if order_by not in allowed:
        order_by = "roi_7d"
    try:
        res = (
            get_client()
            .table("wallet_profile")
            .select("address,roi_7d,wash_ratio,reputation_score,smart_score,agent_type,archetype,risk_label")
            .order(order_by, desc=True)
            .limit(limit)
            .execute()
        )
        return res.data or []
    except Exception as e:
        logger.error("[db] get_top_wallets failed: %s", e)
        return []


# ── Digest Stats ──────────────────────────────────────────────────────────────

def get_digest_stats() -> dict:
    """Pull today's stats for daily digest."""
    today = date.today().isoformat()

    try:
        client = get_client()

        # All signals today
        signals_res = (
            client.table("signal_log")
            .select("id,alert_level,s_final,volume_usd,pool_address,dex")
            .gte("created_at", today)
            .eq("environment", "live")
            .execute()
        )
        signals = signals_res.data or []
        scan_count     = len(signals)
        alert_count    = sum(1 for s in signals if s["alert_level"] in ("alert", "high_conf"))
        watching_count = sum(1 for s in signals if s["alert_level"] == "watching")
        total_volume   = sum(s.get("volume_usd") or 0 for s in signals)

        # Top pools by max s_final
        pool_scores: dict[str, dict] = {}
        for s in signals:
            key = s["pool_address"]
            if key not in pool_scores or s["s_final"] > pool_scores[key]["s_dex"]:
                pool_scores[key] = {
                    "pool_name":  s["pool_address"],
                    "dex":        s["dex"],
                    "s_dex":      s["s_final"],
                    "volume_usd": s.get("volume_usd") or 0,
                }
        top_pools = sorted(pool_scores.values(), key=lambda x: x["s_dex"], reverse=True)[:5]

        # Top smart money wallets
        top_wallets = get_top_wallets(order_by="roi_7d", limit=5)

        return {
            "scan_count":       scan_count,
            "alert_count":      alert_count,
            "watching_count":   watching_count,
            "total_volume_usd": round(total_volume, 2),
            "top_pools":        top_pools,
            "top_wallets":      top_wallets,
            "phase1_active":    False,
            "start_date":       today,
        }

    except Exception as e:
        logger.error("[db] get_digest_stats failed: %s", e)
        return {
            "scan_count": 0, "alert_count": 0, "watching_count": 0,
            "total_volume_usd": 0, "top_pools": [], "top_wallets": [],
            "phase1_active": False, "start_date": today,
        }


# ── Pool Baseline ─────────────────────────────────────────────────────────────

def upsert_pool_baseline(pool_address: str, dex: str, window_start: str, window_end: str, **kwargs):
    """Upsert pool baseline stats."""
    try:
        row = {
            "pool_address": pool_address.lower(),
            "dex":          dex,
            "window_start": window_start,
            "window_end":   window_end,
            **kwargs,
        }
        get_client().table("pool_baseline").upsert(
            row, on_conflict="pool_address,dex,window_start"
        ).execute()
    except Exception as e:
        logger.error("[db] upsert_pool_baseline failed: %s", e)


def get_pool_baseline(pool_address: str, dex: str) -> Optional[dict]:
    """Get latest baseline for a pool."""
    try:
        res = (
            get_client()
            .table("pool_baseline")
            .select("*")
            .eq("pool_address", pool_address.lower())
            .eq("dex", dex)
            .order("window_start", desc=True)
            .limit(1)
            .execute()
        )
        return res.data[0] if res.data else None
    except Exception as e:
        logger.error("[db] get_pool_baseline failed: %s", e)
        return None


# ── Agent Registry ────────────────────────────────────────────────────────────

def upsert_agent(token_id: str, owner_address: str, reputation_score: float, metadata: dict = None):
    """Cache ERC-8004 agent data."""
    try:
        row = {
            "token_id":         token_id,
            "owner_address":    owner_address.lower(),
            "reputation_score": reputation_score,
            "last_synced":      datetime.now(timezone.utc).isoformat(),
            "metadata":         metadata or {},
        }
        get_client().table("agent_registry").upsert(row, on_conflict="token_id").execute()
    except Exception as e:
        logger.error("[db] upsert_agent failed for %s: %s", token_id, e)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    init_db()
    print("✅ Supabase connection verified")

