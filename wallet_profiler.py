"""
wallet_profiler.py
Per-wallet behavioral profiling: agent classification, smart money scoring,
ROI tracking, Aave exposure, and archetype assignment.
"""

import logging
import time
import math
from typing import Optional
from config import (
    AGENT_HIGH_FREQ_TX_MIN,
    AGENT_ROUND_AMOUNT_PCT,
    AGENT_EXEC_TIME_MAX_SEC,
    AGENT_CV_MAX,
    SMART_MONEY_HEURISTIC_MIN,
    SMART_MONEY_ROI_MIN,
    SMART_MONEY_WASH_MAX,
    WASH_RATIO_HIGH_THRESHOLD,
    WASH_NET_FLOW_CIRCULAR,
    WASH_NET_FLOW_DIRECTIONAL,
    WASH_CONCENTRATION_THRESHOLD,
    ERC8004_HIGH_RISK_THRESHOLD,
    AAVE_OPEN_BORROW_FRESH_MIN,
)
from data_sources.agents import get_agent_identity, get_agent_reputation
from data_sources.mantlescan import get_wallet_roi
from data_sources.aave import get_wallet_aave_summary

logger = logging.getLogger(__name__)

# ── Labels ────────────────────────────────────────────────────────────────────

AGENT_TYPE_CONFIRMED   = "CONFIRMED AGENT"
AGENT_TYPE_PROBABLE    = "PROBABLE AGENT"
AGENT_TYPE_MANIPULATOR = "MANIPULATOR"
AGENT_TYPE_SMART_MONEY = "SMART MONEY"
AGENT_TYPE_UNKNOWN     = "UNKNOWN WALLET"

ARCHETYPE_FLASH_WASH = "FLASH_WASH"
ARCHETYPE_COORD_WASH = "COORDINATED_WASH"
ARCHETYPE_PUMP_DUMP  = "PUMP_DUMP"
ARCHETYPE_MULTI_DEX  = "COMPLEX_MULTI_DEX"
ARCHETYPE_ARB        = "ARB_PATTERN"
ARCHETYPE_UNKNOWN    = "UNKNOWN"

WASH_LABEL_HIGH  = "HIGH_CONFIDENCE_WASH"
WASH_LABEL_BOT   = "POSSIBLE_BOT"
WASH_LABEL_MON   = "MONITORING"
WASH_LABEL_CLEAN = "CLEAN"


# ── SECTION 1 — Agent heuristics ─────────────────────────────────────────────

def _check_heuristics(swaps: list[dict]) -> int:
    """
    Returns count of heuristics matched (0-4).
      1. High frequency  — >= AGENT_HIGH_FREQ_TX_MIN swaps in window
      2. Round amounts   — > AGENT_ROUND_AMOUNT_PCT of amounts are round numbers
      3. Fast execution  — avg time between swaps < AGENT_EXEC_TIME_MAX_SEC
      4. Low variance    — coefficient of variation (CV) < AGENT_CV_MAX
    """
    if not swaps:
        return 0

    score = 0

    # 1. High frequency
    if len(swaps) >= AGENT_HIGH_FREQ_TX_MIN:
        score += 1

    # 2. Round amounts
    amounts = [s.get("amount_usd", 0) for s in swaps if s.get("amount_usd", 0) > 0]
    if amounts:
        round_count = sum(
            1 for a in amounts if a >= 10 and round(a, 0) == round(a, 2)
        )
        if (round_count / len(amounts)) > AGENT_ROUND_AMOUNT_PCT:
            score += 1

    # 3. Fast execution
    timestamps = sorted([s.get("timestamp", 0) for s in swaps])
    if len(timestamps) >= 2:
        deltas = [timestamps[i+1] - timestamps[i] for i in range(len(timestamps) - 1)]
        avg_delta = sum(deltas) / len(deltas)
        if avg_delta < AGENT_EXEC_TIME_MAX_SEC:
            score += 1

    # 4. Low CV
    if len(amounts) >= 3:
        mean = sum(amounts) / len(amounts)
        if mean > 0:
            std = math.sqrt(sum((a - mean) ** 2 for a in amounts) / len(amounts))
            cv = std / mean
            if cv < AGENT_CV_MAX:
                score += 1

    return score


# ── SECTION 2 — Agent type classification ────────────────────────────────────

def classify_agent_type(
    wallet: str,
    swaps: list[dict],
    anomaly_score: float,
    wash_ratio: float,
    cycle_detected: bool,
    roi_7d: Optional[float] = None,
) -> str:
    """
    Classify wallet into one of 5 agent types.
    Priority order (deterministic):
      1. MANIPULATOR    — (confirmed or probable) + manipulation signals
      2. SMART MONEY    — (confirmed or probable) + clean ROI >= 15%
      3. CONFIRMED AGENT — ERC-8004 registry match
      4. PROBABLE AGENT  — >= 2 heuristics matched
      5. UNKNOWN WALLET
    """
    identity     = get_agent_identity(wallet)
    is_confirmed = identity is not None

    heuristic_count = _check_heuristics(swaps)
    is_probable = (not is_confirmed) and (heuristic_count >= SMART_MONEY_HEURISTIC_MIN)

    is_agent = is_confirmed or is_probable

    manipulation = (
        wash_ratio > WASH_RATIO_HIGH_THRESHOLD or
        cycle_detected or
        anomaly_score >= 71
    )

    if is_agent and manipulation:
        return AGENT_TYPE_MANIPULATOR

    if is_agent and roi_7d is not None:
        if roi_7d >= SMART_MONEY_ROI_MIN and wash_ratio <= SMART_MONEY_WASH_MAX:
            return AGENT_TYPE_SMART_MONEY

    if is_confirmed:
        return AGENT_TYPE_CONFIRMED

    if is_probable:
        return AGENT_TYPE_PROBABLE

    return AGENT_TYPE_UNKNOWN


# ── SECTION 3 — Wash label ────────────────────────────────────────────────────

def compute_wash_label(
    wash_ratio: float,
    inflow: float,
    outflow: float,
    total_volume: float,
    concentration: float,
) -> str:
    """
    3-way wash confidence gate (v2.0 Fix #13 + #14).

    HIGH_CONFIDENCE_WASH — ratio >10x + net_flow <0.05 + concentration >0.60
    POSSIBLE_BOT         — ratio >10x + net_flow >0.30 (directional = likely arb)
    MONITORING           — elevated but not confirmed
    CLEAN                — ratio < 3x
    """
    if wash_ratio < 3.0:
        return WASH_LABEL_CLEAN

    net_flow = abs(inflow - outflow) / (total_volume + 1e-9)

    if (wash_ratio > WASH_RATIO_HIGH_THRESHOLD
            and net_flow < WASH_NET_FLOW_CIRCULAR
            and concentration > WASH_CONCENTRATION_THRESHOLD):
        return WASH_LABEL_HIGH

    if wash_ratio > WASH_RATIO_HIGH_THRESHOLD and net_flow > WASH_NET_FLOW_DIRECTIONAL:
        return WASH_LABEL_BOT

    return WASH_LABEL_MON


# ── SECTION 4 — Smart Money Score ─────────────────────────────────────────────

def compute_smart_score(
    roi_7d: float,
    wash_ratio: float,
    reputation_score: float,
) -> float:
    """
    Smart Money Score v9.0.
    smart_score = (1 + max(roi_7d/100, -1.0))
                x (1 - clamp(wash_ratio/20, 0.0, 1.0))
                x (reputation_score / 100)

    Range: 0.0 to ~2.0
    """
    roi_factor   = 1.0 + max(roi_7d / 100.0, -1.0)
    wash_penalty = min(max(wash_ratio / 20.0, 0.0), 1.0)
    rep_factor   = reputation_score / 100.0

    return round(roi_factor * (1.0 - wash_penalty) * rep_factor, 4)


# ── SECTION 5 — Archetype assignment ─────────────────────────────────────────

def classify_archetype(
    aave_modifier: float,
    wash_ratio: float,
    cycle_count: int,
    volume_spike_x: float,
    corroboration: int,
    tx_per_minute: float,
) -> str:
    """
    Deterministic priority-order archetype (v2.0 Fix #11).
      1. FLASH_WASH        — flash loan (aave x1.5) + wash ratio >10x
      2. COORDINATED_WASH  — cycle_count >= 3
      3. PUMP_DUMP         — volume spike >15x + no wash cycle
      4. COMPLEX_MULTI_DEX — all 3 DEXes flagged (corroboration == 3)
      5. ARB_PATTERN       — high freq + low wash (NOT flagged as manipulation)
      6. UNKNOWN
    """
    if aave_modifier >= 1.5 and wash_ratio > WASH_RATIO_HIGH_THRESHOLD:
        return ARCHETYPE_FLASH_WASH

    if cycle_count >= 3:
        return ARCHETYPE_COORD_WASH

    if volume_spike_x > 15 and cycle_count == 0:
        return ARCHETYPE_PUMP_DUMP

    if corroboration == 3:
        return ARCHETYPE_MULTI_DEX

    if tx_per_minute > 10 and wash_ratio < 3.0:
        return ARCHETYPE_ARB

    return ARCHETYPE_UNKNOWN


# ── SECTION 6 — Full wallet profile ──────────────────────────────────────────

def build_wallet_profile(
    wallet: str,
    swaps: list[dict],
    anomaly_score: float,
    wash_ratio: float,
    inflow: float,
    outflow: float,
    total_volume: float,
    concentration: float,
    cycle_count: int,
    volume_spike_x: float,
    corroboration: int,
    aave_modifier: float,
    tx_per_minute: float,
) -> dict:
    """
    Build full wallet profile dict.
    Called by scorer.py after scoring pipeline.
    Persisted to Supabase wallet_profiles table.
    """
    # ROI from MantleScan
    roi_7d = None
    try:
        roi_7d = get_wallet_roi(wallet, days=7)
    except Exception as e:
        logger.debug("get_wallet_roi failed for %s: %s", wallet, e)

    # ERC-8004
    identity  = get_agent_identity(wallet)
    rep_score = 50.0
    try:
        reputation = get_agent_reputation(wallet)
        rep_score  = reputation.get("score", 50.0) if reputation else 50.0
    except Exception as e:
        logger.debug("get_agent_reputation failed for %s: %s", wallet, e)

    # Aave summary
    aave_summary = {}
    try:
        aave_summary = get_wallet_aave_summary(wallet)
    except Exception as e:
        logger.debug("get_wallet_aave_summary failed for %s: %s", wallet, e)

    # Derived
    wash_label  = compute_wash_label(
        wash_ratio, inflow, outflow, total_volume, concentration
    )
    archetype   = classify_archetype(
        aave_modifier, wash_ratio, cycle_count,
        volume_spike_x, corroboration, tx_per_minute
    )
    agent_type  = classify_agent_type(
        wallet, swaps, anomaly_score, wash_ratio,
        cycle_count >= 1, roi_7d
    )
    smart_score = compute_smart_score(
        roi_7d if roi_7d is not None else 0.0,
        wash_ratio,
        rep_score,
    )

    return {
        # Identity
        "wallet":           wallet.lower(),
        "agent_type":       agent_type,
        "erc8004_token_id": identity.get("token_id") if identity else None,
        "rep_score":        round(rep_score, 1),

        # Scoring
        "anomaly_score":  round(anomaly_score, 2),
        "wash_ratio":     round(wash_ratio, 4),
        "wash_label":     wash_label,
        "archetype":      archetype,
        "aave_modifier":  aave_modifier,
        "corroboration":  corroboration,
        "cycle_count":    cycle_count,
        "volume_spike_x": round(volume_spike_x, 2),
        "tx_per_minute":  round(tx_per_minute, 4),
        "concentration":  round(concentration, 4),

        # Capital flow
        "inflow":       round(inflow, 2),
        "outflow":      round(outflow, 2),
        "total_volume": round(total_volume, 2),
        "net_flow":     round(abs(inflow - outflow) / (total_volume + 1e-9), 4),

        # Smart money
        "roi_7d":      round(roi_7d, 4) if roi_7d is not None else None,
        "smart_score": smart_score,

        # Aave
        "aave_debt_usd":      aave_summary.get("total_debt_usd", 0.0),
        "aave_health_factor": aave_summary.get("health_factor", 999.0),
        "aave_flash_loan":    aave_summary.get("recent_flash_loan", False),
        "aave_fresh_borrow":  aave_summary.get("recent_borrow_fresh", False),

        # Meta
        "updated_at": int(time.time()),
    }


# ── SECTION 7 — Alert-ready summary ──────────────────────────────────────────

def format_wallet_line(profile: dict) -> str:
    """
    Compact single-line summary for Telegram alerts.
    Example:
      0xA91f..cc #47 | Rep: 23/100 | MANIPULATOR | COORDINATED_WASH | Aave x1.5
    """
    w    = profile["wallet"]
    ws   = w[:6] + ".." + w[-2:] if len(w) > 8 else w
    tid  = f"#{profile['erc8004_token_id']}" if profile.get("erc8004_token_id") else ""
    rep  = f"Rep: {profile['rep_score']}/100"
    amod = profile.get("aave_modifier", 1.0)
    aave = f"Aave x{amod}" if amod > 1.0 else ""

    parts = [f"{ws} {tid}".strip(), rep, profile["agent_type"], profile["wash_label"]]
    if aave:
        parts.append(aave)

    return " | ".join(parts)

# ── SECTION 8 — Batch helpers (called by scheduler.py) ───────────────────

def profile_top_wallets(swaps: list[dict], anomaly_score: float, **score_kwargs) -> list[dict]:
    """
    Profile top N wallets from swap list.
    Returns list of profile dicts sorted by anomaly_score desc.
    """
    if not swaps:
        return []

    wallet_swaps: dict[str, list] = {}
    for s in swaps:
        w = s.get("sender", "") or s.get("wallet", "")
        if isinstance(w, dict):
            w = w.get("id", "")
        if w:
            wallet_swaps.setdefault(w.lower(), []).append(s)

    profiles = []
    for wallet, wswaps in list(wallet_swaps.items())[:10]:
        try:
            vol     = sum(s.get("amountUSD", 0) or s.get("amount_usd", 0) for s in wswaps)
            inflow  = sum(s.get("amountUSD", 0) or s.get("amount_usd", 0) for s in wswaps if s.get("direction") == "in")
            outflow = vol - inflow
            conc    = vol / (score_kwargs.get("total_volume", vol) + 1e-9)

            profile = build_wallet_profile(
                wallet        = wallet,
                swaps         = wswaps,
                anomaly_score = anomaly_score,
                wash_ratio    = score_kwargs.get("wash_ratio", 0.0),
                inflow        = inflow,
                outflow       = outflow,
                total_volume  = vol,
                concentration = conc,
                cycle_count   = score_kwargs.get("cycle_count", 0),
                volume_spike_x = score_kwargs.get("volume_spike_x", 1.0),
                corroboration = score_kwargs.get("corroboration", 1),
                aave_modifier = score_kwargs.get("aave_modifier", 1.0),
                tx_per_minute = len(wswaps) / max(score_kwargs.get("window_min", 15), 1),
            )
            profiles.append(profile)
        except Exception as e:
            logger.debug("profile_top_wallets skip %s: %s", wallet, e)

    profiles.sort(key=lambda p: p.get("anomaly_score", 0), reverse=True)
    return profiles


def flag_capital_flows(swaps: list[dict]) -> dict:
    """
    Detect coordinated capital flow patterns.
    Returns { total_flags, large_single, coordinated_wallets, details }
    """
    from config import (
        CAPITAL_FLOW_SINGLE_MULTIPLIER,
        CAPITAL_FLOW_COORDINATED_USD,
        CAPITAL_FLOW_COORDINATED_WALLETS,
    )

    if not swaps:
        return {"total_flags": 0, "large_single": False, "coordinated_wallets": 0, "details": []}

    amounts = [s.get("amountUSD", 0) or s.get("amount_usd", 0) for s in swaps]
    amounts = [a for a in amounts if a > 0]
    if not amounts:
        return {"total_flags": 0, "large_single": False, "coordinated_wallets": 0, "details": []}

    avg    = sum(amounts) / len(amounts)
    flags  = 0
    details = []

    large_single = any(a > avg * CAPITAL_FLOW_SINGLE_MULTIPLIER for a in amounts)
    if large_single:
        flags += 1
        details.append("large_single_tx")

    wallets_large = set(
        (s.get("sender") or s.get("wallet", "")).lower()
        if not isinstance(s.get("sender"), dict)
        else s["sender"].get("id", "").lower()
        for s in swaps
        if (s.get("amountUSD", 0) or s.get("amount_usd", 0)) >= CAPITAL_FLOW_COORDINATED_USD
    )
    coordinated_wallets = len(wallets_large)
    if coordinated_wallets >= CAPITAL_FLOW_COORDINATED_WALLETS:
        flags += 1
        details.append(f"coordinated_{coordinated_wallets}_wallets")

    return {
        "total_flags":         flags,
        "large_single":        large_single,
        "coordinated_wallets": coordinated_wallets,
        "details":             details,
    }