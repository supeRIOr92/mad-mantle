# scheduler.py — APScheduler: 15-min default, 5-min watch, 1-hr digest
# Orchestrates full scan pipeline per interval
# Watch mode: auto-escalate when S_final > POLL_WATCH_TRIGGER

import logging
import asyncio
from datetime import datetime, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
import database as db

from config import (
    POLL_DEFAULT_MIN,
    POLL_WATCH_MIN,
    POLL_WATCH_TRIGGER,
    POLL_WATCH_DEESCALATE,
    DIGEST_HOUR_UTC,
)
from data_sources import moe, fluxion
from data_sources.aave import fetch_pool_signal
from data_sources.agents import fetch_all_agents, build_agent_map
from detector import run_detection
from scorer import score_and_persist, fetch_dexscreener_volumes
from wallet_profiler import profile_top_wallets, flag_capital_flows
from alerter import broadcast_signal, broadcast_digest
from database import init_db

logger = logging.getLogger(__name__)


# ── State ─────────────────────────────────────────────────

class ScanState:
    def __init__(self):
        self.watch_mode: bool = False
        self.watch_deescalate_count: int = 0
        self.last_scan_ts: datetime | None = None
        self.agent_map: dict = {}
        self.agent_map_refreshed_at: datetime | None = None
        self.start_date: str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self.scan_count: int = 0

state = ScanState()


# ── Agent Map Refresh ─────────────────────────────────────

async def refresh_agent_map():
    """Refresh ERC-8004 agent map every hour."""
    try:
        loop = asyncio.get_event_loop()
        agents = await loop.run_in_executor(None, fetch_all_agents)
        state.agent_map = build_agent_map(agents)
        state.agent_map_refreshed_at = datetime.now(timezone.utc)
        logger.info(f"[scheduler] Agent map refreshed — {len(state.agent_map)} agents")
        
        for a in agents:
            db.upsert_agent(
                token_id=a["token_id"],
                owner_address=a["owner_address"],
                reputation_score=a["reputation_score"],
                metadata={"token_uri": a.get("token_uri", ""), "is_high_risk": a.get("is_high_risk", False)},
            )
        logger.info(f"[scheduler] Agent registry synced — {len(agents)} agents")
    except Exception as e:
        logger.error(f"[scheduler] Agent map refresh failed: {e}")


# ── Pool Discovery ────────────────────────────────────────

async def discover_pools() -> dict[str, list]:
    """
    Fetch top pools from all DEXes.
    Returns { "agni": [...], "moe": [...], "fluxion": [...] }
    """
    loop = asyncio.get_event_loop()

    try:
        moe_pools = await loop.run_in_executor(None, moe.fetch_top_pools, 10)
    except Exception as e:
        logger.error(f"[scheduler] Moe pool discovery failed: {e}")
        moe_pools = []

    try:
        fluxion_pools = await loop.run_in_executor(None, fluxion.fetch_top_pools, 10)
    except Exception as e:
        logger.error(f"[scheduler] Fluxion pool discovery failed: {e}")
        fluxion_pools = []

    return {
        "moe": moe_pools,
        "fluxion": fluxion_pools,
    }


# ── Per-Pool Scan ─────────────────────────────────────────

async def scan_pool(
    dex: str,
    pool_id: str,
    since_ts: int,
) -> dict | None:
    """Run full detection pipeline for a single pool."""
    loop = asyncio.get_event_loop()

    try:
        # Fetch data
        if dex == "agni":
            swaps = await loop.run_in_executor(None, agni.fetch_recent_swaps, since_ts)
            buckets = await loop.run_in_executor(None, agni.fetch_volume_buckets, pool_id, since_ts)
            daily = await loop.run_in_executor(None, agni.fetch_daily_snapshots, pool_id, 7)
        elif dex == "moe":
            swaps = await loop.run_in_executor(None, moe.fetch_recent_swaps, since_ts)
            buckets = await loop.run_in_executor(None, moe.fetch_tx_count_buckets, pool_id, since_ts)
            daily = await loop.run_in_executor(None, moe.fetch_daily_snapshots, pool_id, 7)
        elif dex == "fluxion":
            swaps = await loop.run_in_executor(None, fluxion.fetch_recent_swaps, since_ts)
            buckets = await loop.run_in_executor(None, fluxion.fetch_volume_buckets, pool_id, since_ts)
            daily = await loop.run_in_executor(None, fluxion.fetch_daily_snapshots, pool_id, 7)
        else:
            return None

        if not swaps:
            return None

        # Run detection
        result = await run_detection(
            dex=dex,
            pool_id=pool_id,
            swaps=swaps,
            buckets=buckets,
            daily_snapshots=daily,
            agent_map=state.agent_map,
        )
        result["swaps"] = swaps
        return result
    except Exception as e:
        logger.error(f"[scheduler] scan_pool failed — {dex}/{pool_id}: {e}")
        return None


# ── Main Scan Cycle ───────────────────────────────────────

async def run_scan():
    """
    Full scan cycle across all DEXes + pools.
    Called every POLL_DEFAULT_MIN or POLL_WATCH_MIN.
    """
    state.scan_count += 1
    now = datetime.now(timezone.utc)
    since_ts = int(now.timestamp()) - (POLL_DEFAULT_MIN * 60)

    logger.info(
        f"[scheduler] Scan #{state.scan_count} started — "
        f"{'WATCH MODE' if state.watch_mode else 'normal'} — {now.strftime('%H:%M:%S')} UTC"
    )

    # Refresh agent map if stale (>1h)
    if (
        not state.agent_map_refreshed_at
        or (now - state.agent_map_refreshed_at).seconds > 3600
    ):
        await refresh_agent_map()

    # Discover pools
    pools = await discover_pools()
    all_results = []
    all_pool_ids = []

    # Scan each pool
    for dex, pool_list in pools.items():
        for pool in pool_list:
            pool_id = pool.get("id", "").lower()
            if not pool_id:
                continue

            result = await scan_pool(dex, pool_id, since_ts)
            if result:
                all_results.append(result)
                all_pool_ids.append(pool_id)

    if not all_results:
        logger.info("[scheduler] Scan complete — no data")
        return

    # Build local swap counts per DEX for observability check
    local_swap_counts: dict[str, int] = {}
    for r in all_results:
        dex = r.get("dex", "")
        local_swap_counts[dex] = local_swap_counts.get(dex, 0) + len(r.get("swaps", []))

    # Fetch DexScreener volumes for dynamic weighting
    loop = asyncio.get_event_loop()
    try:
        ds_volumes = await loop.run_in_executor(
            None,
            fetch_dexscreener_volumes,
            all_pool_ids,
        )
    except Exception:
        ds_volumes = {}

    # Fetch Aave pool-level signal (v3.0)
    loop = asyncio.get_event_loop()
    try:
        current_block = await loop.run_in_executor(
            None,
            lambda: __import__("web3").Web3(
                __import__("web3").Web3.HTTPProvider(__import__("config").MANTLE_RPC_URL)
            ).eth.block_number
        )
        aave_data = await loop.run_in_executor(None, fetch_pool_signal, current_block)
    except Exception as e:
        logger.warning(f"[scheduler] Aave signal fetch failed: {e}")
        aave_data = {"aave_signal": 0.0, "aave_label": "NO_DATA"}

    # Compute final score (v3.0 — dengan Aave amplification)
    from scorer import compute_final_score, is_phase1
    phase1 = is_phase1(state.start_date)
    final = compute_final_score(
        all_results, ds_volumes, phase1=phase1,
        aave_signal=aave_data["aave_signal"],
        aave_label=aave_data["aave_label"],
        local_swap_counts=local_swap_counts,
    )
    s_final = final["s_final"]
    alert_level = final["alert_level"]

    logger.info(
        f"[scheduler] Scan #{state.scan_count} complete — "
        f"s_final={s_final:.1f} level={alert_level} "
        f"pools={len(all_results)}"
    )

    # Pick best result by s_dex score
    best_result = max(all_results, key=lambda r: r.get("s_dex", 0))

    # Profile top wallets / capital flow flags (non-blocking, best effort)
    try:
        cap_flags = flag_capital_flows(best_result.get("swaps", []))
        if cap_flags["total_flags"] > 0:
            logger.info(f"[scheduler] Capital flow flags: {cap_flags['total_flags']}")
    except Exception:
        pass
    
    logger.info(f"[scheduler] Profiling wallets — swap count: {len(best_result.get('swaps', []))}")
    # Profile top wallets unconditional — populate wallet_profile table
    try:
        profiles = profile_top_wallets(
            swaps=best_result.get("swaps", []),
            anomaly_score=best_result.get("s_dex", 0),
            wash_ratio=best_result.get("l2_score", 0) / 25.0,
            total_volume=best_result.get("volume_usd", 0),
        )
        for p in profiles:
            db.upsert_wallet(
                address=p["wallet"],
                total_volume_usd=p.get("total_volume", 0),
                tx_count=len([s for s in best_result.get("swaps", []) if (s.get("sender", {}) or {}).get("id", "") == p["wallet"]]),
                wash_ratio=p.get("wash_ratio", 0),
                wash_label=p.get("wash_label", "CLEAN"),
                agent_type=p.get("agent_type", "UNKNOWN WALLET"),
                archetype=p.get("archetype", "UNKNOWN"),
                is_probable_agent=p.get("agent_type") in ("PROBABLE AGENT", "CONFIRMED AGENT"),
                agent_token_id=p.get("erc8004_token_id"),
                reputation_score=p.get("rep_score", 50.0),
                roi_7d=p.get("roi_7d"),
                smart_score=p.get("smart_score", 0),
                aave_modifier=p.get("aave_modifier", 1.0),
                aave_debt_usd=p.get("aave_debt_usd", 0),
                aave_health_factor=p.get("aave_health_factor", 999.0),
                aave_flash_loan=p.get("aave_flash_loan", False),
                aave_fresh_borrow=p.get("aave_fresh_borrow", False),
                risk_label=p.get("wash_label", "CLEAN"),
                environment="live",
            )
        if profiles:
            logger.info(f"[scheduler] Wallet profiles upserted — {len(profiles)} wallets")
    except Exception as e:
        logger.warning(f"[scheduler] Wallet profiling failed: {e}")

    # Persist + broadcast only when there's a signal
    signal_record = {
        **final,
        "dex": best_result.get("dex"),
        "pool_address": best_result.get("pool_id"),
        "l1_score": best_result.get("l1_score", 0),
        "l2_score": best_result.get("l2_score", 0),
        "l3_score": best_result.get("l3_score", 0),
        "s_dex": best_result.get("s_dex", 0),
        "volume_usd": best_result.get("volume_usd", 0),
        "l1_methods": best_result.get("l1_methods", []),
        "l2_methods": best_result.get("l2_methods", []),
        "l3_methods": best_result.get("l3_methods", []),
        "top_wallets": best_result.get("top_wallets", []),
        "corroboration": final.get("corroboration", 1),
        "phase1_active": phase1,
        "created_at": now.strftime("%Y-%m-%d %H:%M:%S"),
    }

    try:
        row_id = db.log_signal(
            dex=signal_record["dex"] or "unknown",
            pool_address=signal_record["pool_address"] or "",
            tx_hashes=best_result.get("tx_hashes", []),
            l1_score=signal_record["l1_score"],
            l2_score=signal_record["l2_score"],
            l3_score=signal_record["l3_score"],
            s_dex=signal_record["s_dex"],
            s_final=s_final,
            alert_level=alert_level,
            l1_methods=signal_record["l1_methods"],
            l2_methods=signal_record["l2_methods"],
            l3_methods=signal_record["l3_methods"],
            top_wallets=signal_record["top_wallets"],
            volume_usd=signal_record["volume_usd"],
            corroboration=signal_record["corroboration"],
            phase1_active=phase1,
            aave_signal=aave_data["aave_signal"],
            aave_label=aave_data["aave_label"],
        )
        logger.info(f"[scheduler] Signal persisted — row_id={row_id}")
    except Exception as e:
        logger.error(f"[scheduler] Failed to persist signal: {e}")

    if alert_level != "none":
        verbose = alert_level == "high_conf"
        await broadcast_signal(signal_record, verbose=verbose)

    # Watch mode management
    _update_watch_mode(s_final, scheduler)

    state.last_scan_ts = now

# ── Watch Mode ────────────────────────────────────────────

def _update_watch_mode(s_final: float, scheduler: AsyncIOScheduler):
    """Auto-escalate/de-escalate watch mode based on S_final."""
    if s_final >= POLL_WATCH_TRIGGER and not state.watch_mode:
        state.watch_mode = True
        state.watch_deescalate_count = 0
        _set_interval(scheduler, POLL_WATCH_MIN)
        logger.info(f"[scheduler] ⚡ Watch mode ON — interval={POLL_WATCH_MIN}min")

    elif s_final < POLL_WATCH_DEESCALATE and state.watch_mode:
        state.watch_deescalate_count += 1
        if state.watch_deescalate_count >= 2:
            state.watch_mode = False
            state.watch_deescalate_count = 0
            _set_interval(scheduler, POLL_DEFAULT_MIN)
            logger.info(f"[scheduler] Watch mode OFF — back to {POLL_DEFAULT_MIN}min")
    else:
        state.watch_deescalate_count = 0


def _set_interval(scheduler: AsyncIOScheduler, minutes: int):
    """Update scan job interval dynamically."""
    try:
        scheduler.reschedule_job(
            "scan_job",
            trigger=IntervalTrigger(minutes=minutes),
        )
    except Exception as e:
        logger.warning(f"[scheduler] reschedule failed: {e}")

# ── Scheduler Setup ───────────────────────────────────────

scheduler = AsyncIOScheduler(timezone="UTC")

def setup_scheduler():
    """Register all jobs."""

    # Main scan job — default 15 min
    scheduler.add_job(
        run_scan,
        trigger=IntervalTrigger(minutes=POLL_DEFAULT_MIN),
        id="scan_job",
        name="AMD Main Scan",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=60,
    )

    # Hourly digest
    scheduler.add_job(
        broadcast_digest,
        trigger=CronTrigger(hour=DIGEST_HOUR_UTC, minute=0, timezone="UTC"),
        id="digest_job",
        name="MAD Hourly Digest",
        max_instances=1,
    )

    # Agent map refresh — every hour
    scheduler.add_job(
        refresh_agent_map,
        trigger=IntervalTrigger(hours=1),
        id="agent_refresh_job",
        name="ERC-8004 Agent Map Refresh",
        max_instances=1,
    )

    logger.info(
        f"[scheduler] Jobs registered — "
        f"scan={POLL_DEFAULT_MIN}min | "
        f"digest=00:{DIGEST_HOUR_UTC:02d} UTC | "
        f"agent_refresh=1h"
    )


def start_scheduler():
    """Start scheduler (non-blocking)."""
    init_db()
    setup_scheduler()
    scheduler.start()
    logger.info("[scheduler] Scheduler started ✅")