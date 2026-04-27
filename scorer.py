# scorer.py — Dynamic Weighting + Final Score + Alert Level
# Corroboration modifier: signal confirmed across multiple DEXes = higher confidence
# DexScreener: real-time vol_24h for dynamic weight adjustment

import logging
import requests
from config import (
    DEX_WEIGHTS,
    DEXSCREENER_BASE,
    DEXSCREENER_WEIGHT_FLOOR,
    CORROBORATION_MODIFIER,
    THRESHOLD_WATCHING,
    THRESHOLD_ALERT,
    THRESHOLD_HIGH_CONF,
    THRESHOLD_PHASE1,
    PHASE1_DAYS,
    L1_MAX, L2_MAX, L3_MAX,
)
from database import log_signal

logger = logging.getLogger(__name__)


# ── DexScreener ───────────────────────────────────────────

def fetch_dexscreener_volumes(pool_addresses: list[str]) -> dict[str, float]:
    """
    Fetch vol_24h for each pool from DexScreener.
    Returns { pool_address: vol_24h_usd }
    Falls back to subgraph totalVolumeUSD if DexScreener fails.
    """
    volumes = {}
    try:
        # DexScreener supports up to 30 addresses per call
        chunk = ",".join(pool_addresses[:30])
        url = f"{DEXSCREENER_BASE}/pairs/mantle/{chunk}"
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        for pair in data.get("pairs", []):
            addr = pair.get("pairAddress", "").lower()
            vol = float(pair.get("volume", {}).get("h24", 0))
            volumes[addr] = vol

    except Exception as e:
        logger.warning(f"[scorer] DexScreener fetch failed: {e} — using baseline weights")

    return volumes


def compute_dynamic_weights(
    dex_results: list[dict],
    ds_volumes: dict[str, float],
) -> dict[str, float]:
    """
    Adjust DEX weights based on real vol_24h from DexScreener.
    If a DEX pool vol < DEXSCREENER_WEIGHT_FLOOR (5%) of total → weight = 0.
    Renormalize remaining weights to sum = 1.0.
    """
    # Start with baseline weights
    weights = dict(DEX_WEIGHTS)

    # Map dex → pool vol from DexScreener
    dex_vols: dict[str, float] = {}
    for r in dex_results:
        pool_id = r.get("pool_id", "").lower()
        dex = r.get("dex", "")
        vol = ds_volumes.get(pool_id, 0.0)
        dex_vols[dex] = dex_vols.get(dex, 0.0) + vol

    total_vol = sum(dex_vols.values())

    if total_vol > 0:
        for dex in weights:
            vol_share = dex_vols.get(dex, 0.0) / total_vol
            if vol_share < DEXSCREENER_WEIGHT_FLOOR:
                logger.info(f"[scorer] {dex} vol share {vol_share:.2%} < floor — zeroing weight")
                weights[dex] = 0.0
            else:
                weights[dex] = vol_share

    # Renormalize
    total_w = sum(weights.values())
    if total_w > 0:
        weights = {k: v / total_w for k, v in weights.items()}
    else:
        # All zeroed — fall back to baseline
        weights = dict(DEX_WEIGHTS)

    return weights


# ── Corroboration ─────────────────────────────────────────

def compute_corroboration(dex_results: list[dict], threshold: float = 40.0) -> int:
    """
    Count how many DEXes flagged a signal above threshold.
    1 DEX = modifier 1.0, 2 DEX = 0.6, 3 DEX = 0.3
    (Corroboration reduces false positive weight — same anomaly on multiple DEXes
    may indicate market-wide event, not manipulation.)
    """
    flagged = sum(1 for r in dex_results if r.get("s_dex", 0) >= threshold)
    return max(flagged, 1)


# ── Phase 1 Conservative Mode ─────────────────────────────

def is_phase1(start_date: str) -> bool:
    """
    Returns True if we're within PHASE1_DAYS of system start.
    start_date: ISO format string (YYYY-MM-DD)
    """
    from datetime import datetime, date
    try:
        start = date.fromisoformat(start_date)
        delta = (date.today() - start).days
        return delta < PHASE1_DAYS
    except Exception:
        return False


def apply_phase1_threshold(s_final: float) -> float:
    """
    During Phase 1: use conservative threshold.
    Scores below THRESHOLD_PHASE1 are treated as THRESHOLD_WATCHING max.
    """
    if s_final >= THRESHOLD_PHASE1:
        return s_final
    return min(s_final, float(THRESHOLD_WATCHING))


# ── Alert Level ───────────────────────────────────────────

def get_alert_level(s_final: float, phase1: bool = False) -> str:
    """
    Map final score to alert level.
    Phase 1: conservative — cap at 'alert' (no high_conf for first 7 days).
    """
    if phase1:
        s_final = apply_phase1_threshold(s_final)

    if s_final >= THRESHOLD_HIGH_CONF and not phase1:
        return "high_conf"
    elif s_final >= THRESHOLD_ALERT:
        return "alert"
    elif s_final >= THRESHOLD_WATCHING:
        return "watching"
    else:
        return "none"


# ── Final Score ───────────────────────────────────────────

def compute_final_score(
    dex_results: list[dict],
    ds_volumes: dict[str, float] = None,
    phase1: bool = False,
) -> dict:
    """
    Compute weighted S_final from per-DEX S_DEX scores.

    S_final = Σ (w_dex × S_DEX) × corroboration_modifier

    Returns full scoring breakdown dict.
    """
    if not dex_results:
        return {
            "s_final": 0.0,
            "alert_level": "none",
            "weights_used": {},
            "corroboration": 1,
            "dex_scores": [],
        }

    ds_volumes = ds_volumes or {}

    # Dynamic weights
    weights = compute_dynamic_weights(dex_results, ds_volumes)

    # Weighted sum
    s_weighted = 0.0
    dex_scores = []
    for r in dex_results:
        dex = r.get("dex", "")
        s_dex = r.get("s_dex", 0.0)
        w = weights.get(dex, 0.0)
        contribution = w * s_dex
        s_weighted += contribution
        dex_scores.append({
            "dex": dex,
            "s_dex": round(s_dex, 2),
            "weight": round(w, 4),
            "contribution": round(contribution, 2),
        })

    # Corroboration modifier
    corroboration = compute_corroboration(dex_results)
    modifier = CORROBORATION_MODIFIER.get(corroboration, 0.3)
    s_final = s_weighted * modifier if corroboration > 1 else s_weighted

    # Clamp
    s_final = min(max(s_final, 0.0), 100.0)

    alert_level = get_alert_level(s_final, phase1=phase1)

    return {
        "s_final": round(s_final, 2),
        "s_weighted": round(s_weighted, 2),
        "alert_level": alert_level,
        "weights_used": {k: round(v, 4) for k, v in weights.items()},
        "corroboration": corroboration,
        "corroboration_modifier": modifier,
        "dex_scores": dex_scores,
        "phase1_active": phase1,
    }


# ── Persist + Return ──────────────────────────────────────

def score_and_persist(
    dex_results: list[dict],
    tx_hashes: list[str],
    ds_volumes: dict[str, float] = None,
    phase1: bool = False,
) -> dict:
    """
    Compute final score and persist to signal_log.
    Returns full result dict including DB row id.
    """
    result = compute_final_score(dex_results, ds_volumes, phase1)

    if result["alert_level"] == "none":
        return result  # Don't persist non-events

    # Use highest-scoring DEX result for per-layer scores
    best = max(dex_results, key=lambda r: r.get("s_dex", 0))

    row_id = log_signal(
        dex=best.get("dex", "multi"),
        pool_address=best.get("pool_id", ""),
        tx_hashes=tx_hashes,
        l1_score=best.get("l1_score", 0),
        l2_score=best.get("l2_score", 0),
        l3_score=best.get("l3_score", 0),
        s_dex=best.get("s_dex", 0),
        s_final=result["s_final"],
        alert_level=result["alert_level"],
        l1_methods=best.get("l1_methods", []),
        l2_methods=best.get("l2_methods", []),
        l3_methods=best.get("l3_methods", []),
        top_wallets=best.get("top_wallets", []),
        volume_usd=best.get("volume_usd", 0),
        corroboration=result["corroboration"],
        phase1_active=phase1,
    )

    result["db_row_id"] = row_id
    logger.info(
        f"[scorer] Signal persisted — id={row_id} "
        f"s_final={result['s_final']} level={result['alert_level']} "
        f"corroboration={result['corroboration']}"
    )

    return result