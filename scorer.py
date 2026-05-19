# scorer.py — Dynamic Weighting + Final Score + Alert Level
# Corroboration modifier: signal confirmed across multiple DEXes = higher confidence
# DexScreener: real-time vol_24h for dynamic weight adjustment

import logging
import requests
from config import (
    DEX_WEIGHTS,
    DEXSCREENER_BASE,
    DEXSCREENER_WEIGHT_FLOOR,
    FALLBACK_DISCOUNT,
    CORROBORATION_MODIFIER,
    THRESHOLD_WATCHING,
    THRESHOLD_ALERT,
    THRESHOLD_HIGH_CONF,
    THRESHOLD_PHASE1,
    PHASE1_DAYS,
    L1_MAX, L2_MAX, L3_MAX,
    AAVE_ALPHA, # v3.0
    AAVE_HARD_GATE_THRESHOLD, # v3.0
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
    local_swap_counts: dict[str, int] = None,
) -> dict[str, float]:
    """
    Adjust DEX weights based on real vol_24h from DexScreener.
    If a DEX pool vol < DEXSCREENER_WEIGHT_FLOOR (5%) of total → weight = 0.
    Renormalize remaining weights to sum = 1.0.
    """
    # Start with baseline weights
    weights = dict(DEX_WEIGHTS)
    local_swap_counts = local_swap_counts or {}

    # Map dex → pool vol from DexScreener
    dex_vols: dict[str, float] = {}
    for r in dex_results:
        pool_id = r.get("pool_id", "").lower()
        dex = r.get("dex", "")
        vol = ds_volumes.get(pool_id, 0.0)
        dex_vols[dex] = dex_vols.get(dex, 0.0) + vol

    total_vol = sum(dex_vols.values())

    if total_vol > 0:
        for dex in list(weights.keys()):
            local_active = local_swap_counts.get(dex, 0) > 0

            # Case 1: DexScreener no coverage — fallback to discounted prior
            if dex not in dex_vols:
                logger.warning(f"[scorer] {dex}: no DexScreener coverage — mode=fallback local_active={local_active}")
                weights[dex] = DEX_WEIGHTS.get(dex, 0.0) * FALLBACK_DISCOUNT
                continue

            vol_share = dex_vols[dex] / total_vol

            # Case 2: DexScreener low/zero but MAD sees local activity — observability mismatch
            if vol_share < DEXSCREENER_WEIGHT_FLOOR and local_active:
                logger.warning(f"[scorer] {dex}: vol_share={vol_share:.2%} < floor but local swaps detected — mode=fallback")
                weights[dex] = DEX_WEIGHTS.get(dex, 0.0) * FALLBACK_DISCOUNT
                continue

            # Case 3: genuinely inactive
            if vol_share < DEXSCREENER_WEIGHT_FLOOR:
                logger.info(f"[scorer] {dex}: vol_share={vol_share:.2%} — mode=inactive")
                weights[dex] = 0.0
            else:
                # Case 4: observed data — full trust
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


# ── Aave Integration (v3.0) ───────────────────────────────

def apply_aave_signal(s_moe: float, aave_signal: float) -> tuple[float, float]:
    """
    Apply Aave signal to risk score with hard gate.

    Hard gate: s_moe < AAVE_HARD_GATE_THRESHOLD → aave_signal_effective = 0
    Rationale: Aave is a conditional amplifier, not a standalone detector.
               S_moe < 20 = noise band, Aave is not relevant.

    Formula:
        risk_score = s_moe * (1 + ALPHA * aave_signal_effective)

    Returns:
        (risk_score, aave_signal_effective)
    """
    aave_signal_effective = aave_signal if s_moe >= AAVE_HARD_GATE_THRESHOLD else 0.0
    risk_score = s_moe * (1 + AAVE_ALPHA * aave_signal_effective)
    return round(min(max(risk_score, 0.0), 100.0), 2), round(aave_signal_effective, 4)


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
    aave_signal: float = 0.0,
    aave_label: str = "NO_ACTIVITY",
    local_swap_counts: dict[str, int] = None,
) -> dict:
    """
    Compute weighted S_final from per-DEX S_DEX scores,
    then apply Aave signal amplification (v3.0).

    Pipeline:
        1. Dynamic weights from DexScreener vol
        2. Weighted sum → s_moe (single active DEX)
        3. Corroboration modifier
        4. Aave hard gate + amplification
        5. Clamp → s_final

    Returns full scoring breakdown dict.
    """
    if not dex_results:
        return {
            "s_final": 0.0,
            "alert_level": "none",
            "weights_used": {},
            "corroboration": 1,
            "dex_scores": [],
            "aave_signal": 0.0,
            "aave_signal_effective": 0.0,
            "aave_label": "NO_ACTIVITY",
            "source_factor": 0.6,
        }

    ds_volumes = ds_volumes or {}

    # Dynamic weights
    weights = compute_dynamic_weights(dex_results, ds_volumes, local_swap_counts)

    # Aggregate per DEX: Top-K=2 with outlier dampening
    dex_pool_scores: dict[str, list[float]] = {}
    for r in dex_results:
        dex = r.get("dex", "")
        s_dex = r.get("s_dex", 0.0)
        if dex not in dex_pool_scores:
            dex_pool_scores[dex] = []
        dex_pool_scores[dex].append(s_dex)

    def aggregate_dex_score(scores: list[float]) -> float:
        sorted_scores = sorted(scores, reverse=True)
        top1 = sorted_scores[0]
        top2 = sorted_scores[1] if len(sorted_scores) > 1 else top1
        if top2 < 0.3 * top1:
            return top1 * 0.7  # outlier — dampen score
        return (top1 + top2) / 2

    # Weighted sum — one contribution per DEX
    s_weighted = 0.0
    dex_scores = []
    seen_dex: set[str] = set()

    for r in dex_results:
        dex = r.get("dex", "")
        s_dex = r.get("s_dex", 0.0)
        w = weights.get(dex, 0.0)

        if dex not in seen_dex:
            seen_dex.add(dex)
            s_dex_agg = aggregate_dex_score(dex_pool_scores[dex])
            contribution = w * s_dex_agg
            s_weighted += contribution
            dex_scores.append({
                "dex": dex,
                "s_dex": round(s_dex_agg, 2),
                "weight": round(w, 4),
                "contribution": round(contribution, 2),
            })
        else:
            dex_scores.append({
                "dex": dex,
                "s_dex": round(s_dex, 2),
                "weight": 0.0,
                "contribution": 0.0,
            })

    # Corroboration modifier
    corroboration = compute_corroboration(dex_results)
    modifier = CORROBORATION_MODIFIER.get(corroboration, 0.3)
    s_moe = s_weighted * modifier if corroboration > 1 else s_weighted

    # v3.0 — Aave amplification with hard gate
    s_final, aave_signal_effective = apply_aave_signal(s_moe, aave_signal)

    # Source factor — confidence cap
    # Moe only → 0.6 | Moe + Aave active → 1.0
    source_factor = 1.0 if aave_signal > 0.0 else 0.6
    s_final = round(s_final * source_factor, 2)

    alert_level = get_alert_level(s_final, phase1=phase1)

    return {
        "s_final": s_final,
        "s_weighted": round(s_moe, 2),
        "alert_level": alert_level,
        "weights_used": {k: round(v, 4) for k, v in weights.items()},
        "corroboration": corroboration,
        "corroboration_modifier": modifier,
        "dex_scores": dex_scores,
        "phase1_active": phase1,
        # v3.0
        "aave_signal": round(aave_signal, 4),
        "aave_signal_effective": aave_signal_effective,
        "aave_label": aave_label,
        "source_factor": source_factor,
    }


# ── Persist + Return ──────────────────────────────────────

def score_and_persist(
    dex_results: list[dict],
    tx_hashes: list[str],
    ds_volumes: dict[str, float] = None,
    phase1: bool = False,
    aave_signal: float = 0.0,        # v3.0
    aave_label: str = "NO_ACTIVITY", # v3.0
) -> dict:
    """
    Compute final score and persist to signal_log.
    Returns full result dict including DB row id.
    """
    result = compute_final_score(
        dex_results, ds_volumes, phase1,
        aave_signal=aave_signal,
        aave_label=aave_label,
    )

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
        # v3.0
        aave_signal=result["aave_signal"],
        aave_label=result["aave_label"],
    )

    result["db_row_id"] = row_id

    logger.info(
        "[scorer] Signal persisted — id=%s s_final=%s level=%s "
        "aave_signal=%.2f aave_effective=%.2f source_factor=%.1f",
        row_id, result["s_final"], result["alert_level"],
        result["aave_signal"], result["aave_signal_effective"],
        result["source_factor"],
    )

    return result