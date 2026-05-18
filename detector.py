# detector.py — RealClaw Detection Engine
# L1 (Statistical) + L2 (Behavioral) + L3 (Structural)
# L3 only executes if L1+L2 combined > L3_TRIGGER_THRESHOLD

import logging
import asyncio
import numpy as np
from scipy import stats
from collections import Counter
from config import (
    # L1
    ZSCORE_PRIMARY_WINDOW_MIN,
    ZSCORE_SECONDARY_WINDOW_MIN,
    ZSCORE_ROLLING_BASELINE_DAYS,
    BOLLINGER_PERIOD,
    BOLLINGER_SIGMA_BASELINE,
    BOLLINGER_SIGMA_ADAPTIVE,
    BOLLINGER_ADAPTIVE_TRIGGER,
    POISSON_BASELINE_DAYS,
    RATE_OF_CHANGE_MULTIPLIER,
    # L2
    WASH_RATIO_EPSILON,
    SENDER_CONCENTRATION_TOP_N,
    WASH_RATIO_HIGH_THRESHOLD,
    WASH_RATIO_MID_THRESHOLD,
    ERC8004_HIGH_RISK_THRESHOLD,
    # L3
    L3_TRIGGER_THRESHOLD,
    CYCLE_WINDOW_MIN,
    CYCLE_MAX_HOPS,
    BENFORD_PVALUE_THRESHOLD,
    # Scoring
    L1_MAX, L2_MAX, L3_MAX,
)

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════
# L1 — STATISTICAL DETECTION (max 60 pts)
# ══════════════════════════════════════════════════════════

def l1_zscore(buckets: list[dict], window: str = "primary") -> tuple[float, dict]:
    """
    Z-Score deviation on volumeUSD buckets.
    primary = 15-min window, secondary = 1h window (slow accumulation)
    Max 40 pts combined (20 primary + 20 secondary).
    """
    if len(buckets) < 3:
        return 0.0, {"method": "zscore", "reason": "insufficient data"}

    volumes = [float(b["volumeUSD"]) for b in buckets]
    current = volumes[-1]
    baseline = volumes[:-1]

    if not baseline or np.std(baseline) == 0:
        return 0.0, {"method": "zscore", "reason": "zero std"}

    z = (current - np.mean(baseline)) / np.std(baseline)
    max_pts = 20.0

    if z >= 4.0:
        pts = max_pts
    elif z >= 3.0:
        pts = max_pts * 0.75
    elif z >= 2.5:
        pts = max_pts * 0.5
    elif z >= 2.0:
        pts = max_pts * 0.25
    else:
        pts = 0.0

    return pts, {
        "method": f"zscore_{window}",
        "z_score": round(z, 3),
        "current_vol": current,
        "baseline_mean": round(np.mean(baseline), 2),
        "pts": pts,
    }


def l1_bollinger(daily_snapshots: list[dict], current_vol: float) -> tuple[float, dict]:
    """
    Bollinger Band breach on daily volume.
    Adaptive sigma: 2.5 if daily range > 3× 7d avg range.
    Max 20 pts.
    """
    if len(daily_snapshots) < BOLLINGER_PERIOD:
        return 0.0, {"method": "bollinger", "reason": "insufficient data"}
    volumes = [float(s["volumeUSD"]) for s in daily_snapshots]
    mean = np.mean(volumes)
    std = np.std(volumes)

    # Adaptive sigma check
    ranges = []
    for s in daily_snapshots:
        high = float(s.get("highVolumeUSD") or 0)
        low = float(s.get("lowVolumeUSD") or 0)
        if high and low:
            ranges.append(high - low)

    sigma = BOLLINGER_SIGMA_BASELINE
    if ranges:
        avg_range = np.mean(ranges)
        current_range = ranges[-1] if ranges else 0
        if avg_range > 0 and current_range > BOLLINGER_ADAPTIVE_TRIGGER * avg_range:
            sigma = BOLLINGER_SIGMA_ADAPTIVE

    upper = mean + (sigma * std)
    breach = current_vol - upper

    if breach <= 0:
        return 0.0, {"method": "bollinger", "reason": "no breach", "upper": round(upper, 2)}

    # Score proportional to breach magnitude
    breach_ratio = breach / upper if upper > 0 else 0
    pts = min(20.0, 20.0 * (breach_ratio / 0.5))  # 50% above upper = full pts

    return pts, {
        "method": "bollinger",
        "upper_band": round(upper, 2),
        "current_vol": round(current_vol, 2),
        "sigma_used": sigma,
        "breach_pct": round(breach_ratio * 100, 1),
        "pts": round(pts, 2),
    }


def l1_poisson(tx_buckets: list[dict], baseline_daily: list[dict]) -> tuple[float, dict]:
    """
    Poisson probability for Moe (discrete event model).
    λ from 7-day rolling average of tx count per 15-min bucket.
    Max 20 pts.
    """
    if not baseline_daily or not tx_buckets:
        return 0.0, {"method": "poisson", "reason": "no data"}

    # Compute λ: avg tx per 15-min window from daily data
    daily_tx = [float(d["txCount"]) for d in baseline_daily]
    buckets_per_day = 96  # 24h / 15min
    lam = np.mean(daily_tx) / buckets_per_day

    if lam == 0:
        return 0.0, {"method": "poisson", "reason": "lambda=0"}

    current_tx = float(tx_buckets[-1]["txCount"]) if tx_buckets else 0

    # P(X >= current_tx) — probability of observing this or more under null
    p_value = 1 - stats.poisson.cdf(int(current_tx) - 1, lam)

    if p_value < 0.001:
        pts = 20.0
    elif p_value < 0.01:
        pts = 15.0
    elif p_value < 0.05:
        pts = 10.0
    else:
        pts = 0.0

    return pts, {
        "method": "poisson",
        "lambda": round(lam, 3),
        "current_tx": current_tx,
        "p_value": round(p_value, 5),
        "pts": pts,
    }


def l1_rate_of_change(tx_buckets: list[dict], baseline_daily: list[dict]) -> tuple[float, dict]:
    """
    Rate-of-change: current 15-min tx count > 5× 7d avg.
    Max 20 pts.
    """
    if not baseline_daily or not tx_buckets:
        return 0.0, {"method": "roc", "reason": "no data"}

    daily_tx = [float(d["txCount"]) for d in baseline_daily]
    buckets_per_day = 96
    avg_per_bucket = np.mean(daily_tx) / buckets_per_day

    if avg_per_bucket == 0:
        return 0.0, {"method": "roc", "reason": "avg=0"}

    current_tx = float(tx_buckets[-1]["txCount"])
    ratio = current_tx / avg_per_bucket

    if ratio >= RATE_OF_CHANGE_MULTIPLIER:
        pts = 20.0
    elif ratio >= RATE_OF_CHANGE_MULTIPLIER * 0.75:
        pts = 15.0
    elif ratio >= RATE_OF_CHANGE_MULTIPLIER * 0.5:
        pts = 10.0
    else:
        pts = 0.0

    return pts, {
        "method": "rate_of_change",
        "ratio": round(ratio, 2),
        "threshold": RATE_OF_CHANGE_MULTIPLIER,
        "pts": pts,
    }


def run_l1(dex: str, buckets: list, daily_snapshots: list, current_vol: float) -> tuple[float, list]:
    """
    Run L1 for a given DEX. Returns (total_l1_score, methods_triggered).
    Agni + Fluxion: Z-Score + Bollinger
    Moe: Poisson + Rate-of-Change
    """
    total = 0.0
    methods = []

    if dex in ("agni", "fluxion"):
        # Primary Z-Score (15-min)
        pts, info = l1_zscore(buckets, window="primary")
        total += pts
        if pts > 0:
            methods.append(info)

        # Secondary Z-Score (1h — use last 4 buckets as 1h proxy)
        if len(buckets) >= 4:
            pts2, info2 = l1_zscore(buckets[-4:], window="secondary")
            total += pts2
            if pts2 > 0:
                methods.append(info2)

        # Bollinger
        pts3, info3 = l1_bollinger(daily_snapshots, current_vol)
        total += pts3
        if pts3 > 0:
            methods.append(info3)

    elif dex == "moe":
        # Poisson
        pts, info = l1_poisson(buckets, daily_snapshots)
        total += pts
        if pts > 0:
            methods.append(info)

        # Rate-of-Change
        pts2, info2 = l1_rate_of_change(buckets, daily_snapshots)
        total += pts2
        if pts2 > 0:
            methods.append(info2)

    return min(total, float(L1_MAX)), methods


# ══════════════════════════════════════════════════════════
# L2 — BEHAVIORAL DETECTION (max 55 pts)
# ══════════════════════════════════════════════════════════

def l2_wash_ratio(swaps: list[dict]) -> tuple[float, dict]:
    """
    Wash Ratio: total_vol / (|net_position_change| + ε)
    High ratio = circular trading signal.
    Max 25 pts.
    """
    if not swaps:
        return 0.0, {"method": "wash_ratio", "reason": "no swaps"}

    total_vol = sum(float(s.get("amountUSD", 0)) for s in swaps)

    # Net position: sum of signed amounts per wallet
    wallet_net: dict[str, float] = {}
    for s in swaps:
        sender = s.get("sender", {}).get("id", "") if isinstance(s.get("sender"), dict) else s.get("sender", "")
        amount = float(s.get("amountUSD", 0))
        wallet_net[sender] = wallet_net.get(sender, 0) + amount

        recipient = s.get("recipient", {}).get("id", "") if isinstance(s.get("recipient"), dict) else s.get("recipient", "")
        wallet_net[recipient] = wallet_net.get(recipient, 0) - amount

    net_position_change = sum(abs(v) for v in wallet_net.values())
    ratio = total_vol / (net_position_change + WASH_RATIO_EPSILON)

    if ratio >= WASH_RATIO_HIGH_THRESHOLD:
        pts = 25.0
    elif ratio >= WASH_RATIO_MID_THRESHOLD:
        pts = 25.0 * ((ratio - WASH_RATIO_MID_THRESHOLD) / (WASH_RATIO_HIGH_THRESHOLD - WASH_RATIO_MID_THRESHOLD))
    else:
        pts = 0.0

    return pts, {
        "method": "wash_ratio",
        "ratio": round(ratio, 3),
        "total_vol": round(total_vol, 2),
        "net_position": round(net_position_change, 2),
        "pts": round(pts, 2),
    }


def l2_sender_concentration(swaps: list[dict]) -> tuple[float, dict]:
    """
    Top-N sender concentration: top-5 wallets % of total txns.
    Max 15 pts.
    """
    if not swaps:
        return 0.0, {"method": "sender_concentration", "reason": "no swaps"}

    senders = []
    for s in swaps:
        sender = s.get("sender", {}).get("id", "") if isinstance(s.get("sender"), dict) else s.get("sender", "")
        if sender:
            senders.append(sender)

    if not senders:
        return 0.0, {"method": "sender_concentration", "reason": "no senders"}

    counter = Counter(senders)
    top_n = counter.most_common(SENDER_CONCENTRATION_TOP_N)
    top_n_count = sum(c for _, c in top_n)
    concentration = top_n_count / len(senders)

    if concentration >= 0.9:
        pts = 15.0
    elif concentration >= 0.7:
        pts = 10.0
    elif concentration >= 0.5:
        pts = 5.0
    else:
        pts = 0.0

    return pts, {
        "method": "sender_concentration",
        "top_wallets": [w for w, _ in top_n],
        "concentration_pct": round(concentration * 100, 1),
        "pts": pts,
    }


def l2_agent_reputation(swaps: list[dict], agent_map: dict) -> tuple[float, dict]:
    """
    ERC-8004 agent reputation cross-reference.
    Score < 30 = high risk multiplier applied.
    Max 15 pts.
    """
    if not swaps or not agent_map:
        return 0.0, {"method": "agent_reputation", "reason": "no data"}

    high_risk_agents = []
    for s in swaps:
        sender = s.get("sender", {}).get("id", "") if isinstance(s.get("sender"), dict) else s.get("sender", "")
        if sender and sender.lower() in agent_map:
            agent = agent_map[sender.lower()]
            if agent["reputation_score"] < ERC8004_HIGH_RISK_THRESHOLD:
                high_risk_agents.append({
                    "wallet": sender,
                    "token_id": agent["token_id"],
                    "reputation_score": agent["reputation_score"],
                })

    if not high_risk_agents:
        return 0.0, {"method": "agent_reputation", "reason": "no high-risk agents"}

    # More high-risk agents = higher score
    ratio = min(len(high_risk_agents) / max(len(swaps), 1), 1.0)
    pts = 15.0 * ratio

    return pts, {
        "method": "agent_reputation",
        "high_risk_count": len(high_risk_agents),
        "agents": high_risk_agents[:5],  # top 5
        "pts": round(pts, 2),
    }


def run_l2(swaps: list[dict], agent_map: dict) -> tuple[float, list]:
    """Run all L2 methods. Returns (total_l2_score, methods_triggered)."""
    total = 0.0
    methods = []

    pts, info = l2_wash_ratio(swaps)
    total += pts
    if pts > 0:
        methods.append(info)

    pts2, info2 = l2_sender_concentration(swaps)
    total += pts2
    if pts2 > 0:
        methods.append(info2)

    pts3, info3 = l2_agent_reputation(swaps, agent_map)
    total += pts3
    if pts3 > 0:
        methods.append(info3)

    return min(total, float(L2_MAX)), methods


# ══════════════════════════════════════════════════════════
# L3 — STRUCTURAL DETECTION (max 50 pts)
# Async — only runs if L1+L2 > L3_TRIGGER_THRESHOLD
# ══════════════════════════════════════════════════════════

def l3_benfords_law(amounts: list[float]) -> tuple[float, dict]:
    """
    Benford's Law chi-square on amountUSD distribution.
    Supporting signal only — DEX amounts tend power-law.
    Max 20 pts.
    """
    if len(amounts) < 50:
        return 0.0, {"method": "benfords", "reason": "insufficient samples"}

    # Extract leading digits
    leading_digits = []
    for a in amounts:
        if a > 0:
            s = str(float(a)).lstrip("0").replace(".", "")
            if s:
                leading_digits.append(int(s[0]))

    if len(leading_digits) < 30:
        return 0.0, {"method": "benfords", "reason": "insufficient leading digits"}

    # Expected Benford distribution
    expected_freq = np.array([np.log10(1 + 1/d) for d in range(1, 10)])
    observed_counts = np.array([leading_digits.count(d) for d in range(1, 10)])
    expected_counts = expected_freq * len(leading_digits)

    chi2, p_value = stats.chisquare(observed_counts, expected_counts)

    if p_value < BENFORD_PVALUE_THRESHOLD:
        pts = 20.0 * (1 - p_value / BENFORD_PVALUE_THRESHOLD)
        pts = min(pts, 20.0)
    else:
        pts = 0.0

    return pts, {
        "method": "benfords_law",
        "chi2": round(chi2, 3),
        "p_value": round(p_value, 5),
        "sample_size": len(leading_digits),
        "pts": round(pts, 2),
    }


def l3_cycle_detection(swaps: list[dict]) -> tuple[float, dict]:
    """
    Wallet graph cycle detection: A→B→A within 5–60 min.
    Uses networkx for graph traversal.
    Max 30 pts.
    """
    try:
        import networkx as nx
    except ImportError:
        logger.warning("[L3] networkx not installed — skipping cycle detection")
        return 0.0, {"method": "cycle_detection", "reason": "networkx missing"}

    if not swaps:
        return 0.0, {"method": "cycle_detection", "reason": "no swaps"}

    G = nx.DiGraph()
    min_window = CYCLE_WINDOW_MIN[0] * 60  # seconds
    max_window = CYCLE_WINDOW_MIN[1] * 60

    # Build graph with timestamps
    swap_list = sorted(swaps, key=lambda s: int(s.get("timestamp", 0)))

    for i, s in enumerate(swap_list):
        sender = s.get("sender", {}).get("id", "") if isinstance(s.get("sender"), dict) else s.get("sender", "")
        recipient = s.get("recipient", {}).get("id", "") if isinstance(s.get("recipient"), dict) else s.get("recipient", "")
        ts = int(s.get("timestamp", 0))

        if sender and recipient and sender != recipient:
            G.add_edge(sender, recipient, timestamp=ts, tx=s.get("txHash", ""))

    # Detect simple cycles (A→B→A)
    cycles_found = []
    try:
        for cycle in nx.simple_cycles(G):
            if len(cycle) <= CYCLE_MAX_HOPS:
                # Check timing constraint
                edges = [(cycle[i], cycle[(i+1) % len(cycle)]) for i in range(len(cycle))]
                timestamps = []
                for u, v in edges:
                    if G.has_edge(u, v):
                        timestamps.append(G[u][v].get("timestamp", 0))
                if timestamps:
                    time_span = max(timestamps) - min(timestamps)
                    if min_window <= time_span <= max_window:
                        cycles_found.append({
                            "cycle": cycle,
                            "time_span_sec": time_span,
                        })
    except Exception as e:
        logger.warning(f"[L3] cycle detection error: {e}")

    if not cycles_found:
        return 0.0, {"method": "cycle_detection", "cycles": 0}

    pts = min(30.0, 10.0 * len(cycles_found))

    return pts, {
        "method": "cycle_detection",
        "cycles_found": len(cycles_found),
        "examples": cycles_found[:3],
        "pts": pts,
    }


async def run_l3_async(swaps: list[dict]) -> tuple[float, list]:
    """
    Async L3 execution — does not block real-time pipeline.
    Returns (total_l3_score, methods_triggered).
    """
    loop = asyncio.get_event_loop()
    methods = []
    total = 0.0

    amounts = [float(s.get("amountUSD", 0)) for s in swaps if float(s.get("amountUSD", 0)) > 0]

    # Run CPU-bound tasks in thread pool
    benford_pts, benford_info = await loop.run_in_executor(None, l3_benfords_law, amounts)
    total += benford_pts
    if benford_pts > 0:
        methods.append(benford_info)

    cycle_pts, cycle_info = await loop.run_in_executor(None, l3_cycle_detection, swaps)
    total += cycle_pts
    if cycle_pts > 0:
        methods.append(cycle_info)

    return min(total, float(L3_MAX)), methods


# ══════════════════════════════════════════════════════════
# MAIN ENTRY
# ══════════════════════════════════════════════════════════

async def run_detection(
    dex: str,
    pool_id: str,
    swaps: list[dict],
    buckets: list[dict],
    daily_snapshots: list[dict],
    agent_map: dict,
) -> dict:
    """
    Full detection pipeline for one DEX pool.
    Returns detection result dict.
    """
    current_vol = float(buckets[-1]["volumeUSD"]) if buckets else 0.0

    l1_score, l1_methods = run_l1(dex, buckets, daily_snapshots, current_vol)
    l2_score, l2_methods = run_l2(swaps, agent_map)

    l3_score = 0.0
    l3_methods = []

    if (l1_score + l2_score) > L3_TRIGGER_THRESHOLD:
        logger.info(f"[detector] L1+L2={l1_score+l2_score:.1f} > {L3_TRIGGER_THRESHOLD} — running L3 async")
        l3_score, l3_methods = await run_l3_async(swaps)

    # Normalize per-DEX: S_DEX = ((L1+L2+L3) / 165) × 100
    raw = l1_score + l2_score + l3_score
    s_dex = min((raw / (L1_MAX + L2_MAX + L3_MAX)) * 100, 100.0)

    # Top flagged wallets (from L2 sender concentration)
    top_wallets = []
    for m in l2_methods:
        if m.get("method") == "sender_concentration":
            top_wallets = m.get("top_wallets", [])

    return {
        "dex": dex,
        "pool_id": pool_id,
        "l1_score": round(l1_score, 2),
        "l2_score": round(l2_score, 2),
        "l3_score": round(l3_score, 2),
        "s_dex": round(s_dex, 2),
        "l1_methods": l1_methods,
        "l2_methods": l2_methods,
        "l3_methods": l3_methods,
        "top_wallets": top_wallets,
        "volume_usd": current_vol,
        "l3_triggered": (l1_score + l2_score) > L3_TRIGGER_THRESHOLD,
    }