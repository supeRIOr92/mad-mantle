"""
predictor.py
Risk Prediction Engine — MAD v2.0
6-dim feature vector + cosine similarity + top-k nearest neighbors.
Predicts: rug_prob, dump_window_min, price_drop_pct, confidence.
"""

import math
import logging
import time
from typing import Optional
from config import (
    PREDICTOR_TOP_K,
    PREDICTOR_MIN_EVENTS,
    PREDICTOR_CONFIDENCE_SCALE,
    FEATURE_CYCLE_NORM,
    FEATURE_AAVE_NORM_OFFSET,
    FEATURE_AAVE_NORM_SCALE,
    FEATURE_TX_DENSITY_NORM,
)

logger = logging.getLogger(__name__)


# ── Historical Event Store ────────────────────────────────────────────────────
# In-memory store. Seeded with archetype priors, grows as MAD runs.
# Schema per event:
#   features: list[float]  — 6-dim normalized vector
#   archetype: str
#   outcome: dict          — rug_prob, dump_window_min, price_drop_pct
#   timestamp: float

_event_store: list[dict] = []

# Archetype priors — seed data so predictor works on Day 1
_ARCHETYPE_PRIORS = [
    # FLASH_WASH — high rug, fast dump
    {"archetype": "FLASH_WASH",        "features": [1.0, 1.0, 1.0, 0.9, 0.8, 1.0], "outcome": {"rug_prob": 0.85, "dump_window_min": 10,  "price_drop_pct": 35.0}},
    {"archetype": "FLASH_WASH",        "features": [0.9, 1.0, 0.9, 1.0, 0.7, 1.0], "outcome": {"rug_prob": 0.80, "dump_window_min": 8,   "price_drop_pct": 30.0}},
    {"archetype": "FLASH_WASH",        "features": [1.0, 0.9, 1.0, 0.8, 0.9, 0.9], "outcome": {"rug_prob": 0.90, "dump_window_min": 5,   "price_drop_pct": 40.0}},

    # COORDINATED_WASH — medium rug, slower dump
    {"archetype": "COORDINATED_WASH",  "features": [0.8, 0.7, 0.6, 0.9, 0.5, 0.7], "outcome": {"rug_prob": 0.65, "dump_window_min": 30,  "price_drop_pct": 20.0}},
    {"archetype": "COORDINATED_WASH",  "features": [0.7, 0.8, 0.7, 0.8, 0.6, 0.6], "outcome": {"rug_prob": 0.60, "dump_window_min": 45,  "price_drop_pct": 18.0}},
    {"archetype": "COORDINATED_WASH",  "features": [0.9, 0.6, 0.8, 0.7, 0.7, 0.5], "outcome": {"rug_prob": 0.70, "dump_window_min": 25,  "price_drop_pct": 22.0}},

    # PUMP_DUMP — very high rug, medium window
    {"archetype": "PUMP_DUMP",         "features": [0.6, 0.3, 0.2, 1.0, 0.9, 0.4], "outcome": {"rug_prob": 0.90, "dump_window_min": 20,  "price_drop_pct": 55.0}},
    {"archetype": "PUMP_DUMP",         "features": [0.5, 0.2, 0.3, 0.9, 1.0, 0.3], "outcome": {"rug_prob": 0.88, "dump_window_min": 15,  "price_drop_pct": 50.0}},
    {"archetype": "PUMP_DUMP",         "features": [0.7, 0.4, 0.1, 1.0, 0.8, 0.5], "outcome": {"rug_prob": 0.92, "dump_window_min": 25,  "price_drop_pct": 60.0}},

    # COMPLEX_MULTI_DEX — medium rug, wide window
    {"archetype": "COMPLEX_MULTI_DEX", "features": [0.8, 0.8, 0.7, 0.6, 0.5, 0.9], "outcome": {"rug_prob": 0.55, "dump_window_min": 60,  "price_drop_pct": 15.0}},
    {"archetype": "COMPLEX_MULTI_DEX", "features": [0.7, 0.9, 0.8, 0.5, 0.4, 1.0], "outcome": {"rug_prob": 0.50, "dump_window_min": 90,  "price_drop_pct": 12.0}},

    # ARB_PATTERN — low rug (not manipulation)
    {"archetype": "ARB_PATTERN",       "features": [0.9, 0.1, 0.1, 0.3, 0.2, 0.2], "outcome": {"rug_prob": 0.10, "dump_window_min": 0,   "price_drop_pct": 2.0}},
    {"archetype": "ARB_PATTERN",       "features": [1.0, 0.2, 0.0, 0.2, 0.1, 0.1], "outcome": {"rug_prob": 0.08, "dump_window_min": 0,   "price_drop_pct": 1.0}},

    # UNKNOWN — baseline
    {"archetype": "UNKNOWN",           "features": [0.5, 0.5, 0.5, 0.5, 0.5, 0.5], "outcome": {"rug_prob": 0.40, "dump_window_min": 30,  "price_drop_pct": 10.0}},
]

# Seed store with priors
for _p in _ARCHETYPE_PRIORS:
    _event_store.append({**_p, "timestamp": 0.0})


# ── Feature Vector ────────────────────────────────────────────────────────────

def build_feature_vector(
    anomaly_score: float,
    wash_ratio: float,
    cycle_count: int,
    aave_modifier: float,
    tx_per_minute: float,
    volume_spike_x: float,
) -> list[float]:
    """
    6-dim normalized feature vector (v2.0 Fix #10).
    All dims clamped to [0.0,1.0].

Dim 0 — anomaly_score   / 100
    Dim 1 — wash_ratio      / 20       (>20 = max)
    Dim 2 — cycle_count     / FEATURE_CYCLE_NORM
    Dim 3 — volume_spike_x  / 20       (>20 = max)
    Dim 4 — tx_per_minute   / FEATURE_TX_DENSITY_NORM
    Dim 5 — aave_modifier   normalized (1.0→0.0, 1.5→1.0)
    """
    def clamp(v: float) -> float:
        return max(0.0, min(1.0, v))

    f0 = clamp(anomaly_score / 100.0)
    f1 = clamp(wash_ratio / 20.0)
    f2 = clamp(cycle_count / FEATURE_CYCLE_NORM)
    f3 = clamp(volume_spike_x / 20.0)
    f4 = clamp(tx_per_minute / FEATURE_TX_DENSITY_NORM)
    f5 = clamp((aave_modifier - FEATURE_AAVE_NORM_OFFSET) / FEATURE_AAVE_NORM_SCALE)

    return [f0, f1, f2, f3, f4, f5]


# ── Cosine Similarity ─────────────────────────────────────────────────────────

def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot   = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


# ── Top-K Retrieval ───────────────────────────────────────────────────────────

def _get_top_k(query: list[float], k: int = PREDICTOR_TOP_K) -> list[dict]:
    """Return top-k most similar historical events (cosine similarity)."""
    scored = []
    for event in _event_store:
        sim = _cosine_similarity(query, event["features"])
        scored.append((sim, event))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [e for _, e in scored[:k]]


# ── Accuracy Tracking ─────────────────────────────────────────────────────────

_accuracy_log: list[dict] = []  # {predicted_archetype, actual_archetype, timestamp}

def log_prediction_outcome(predicted_archetype: str, actual_archetype: str):
    """Call this when a prediction can be verified (e.g. post-event)."""
    _accuracy_log.append({
        "predicted": predicted_archetype,
        "actual":    actual_archetype,
        "timestamp": time.time(),
    })

def get_accuracy_30d() -> float:
    """Returns prediction accuracy over last 30 days."""
    cutoff = time.time() - (30 * 86400)
    recent = [x for x in _accuracy_log if x["timestamp"] >= cutoff]
    if not recent:
        return 0.75  # default prior — no data yet
    correct = sum(1 for x in recent if x["predicted"] == x["actual"])
    return round(correct / len(recent), 4)


# ── Main Prediction ───────────────────────────────────────────────────────────

def predict(
    anomaly_score: float,
    wash_ratio: float,
    cycle_count: int,
    aave_modifier: float,
    tx_per_minute: float,
    volume_spike_x: float,
    archetype: str,
) -> dict:
    """
    Run risk prediction for a detected anomaly.

    Returns:
        rug_prob        float   0-1
        dump_window_min int     estimated minutes until dump
        price_drop_pct  float   estimated price drop %
        confidence      float   0-1 (based on similar_count)
        similar_count   int     number of historical matches
        accuracy_30d    float   30-day prediction accuracy
        archetype       str     confirmed/refined archetype
    """
    features = build_feature_vector(
        anomaly_score, wash_ratio, cycle_count,
        aave_modifier, tx_per_minute, volume_spike_x,
    )

    top_k = _get_top_k(features, k=PREDICTOR_TOP_K)
    similar_count = len(top_k)

    if similar_count < PREDICTOR_MIN_EVENTS:
        confidence = 0.2
    else:
        confidence = min(similar_count / PREDICTOR_CONFIDENCE_SCALE, 1.0)

    # Weighted average of outcomes (weight = cosine similarity)
    sims = [_cosine_similarity(features, e["features"]) for e in top_k]
    total_sim = sum(sims) or 1.0

    rug_prob       = sum(s * e["outcome"]["rug_prob"]        for s, e in zip(sims, top_k)) / total_sim
    dump_window    = sum(s * e["outcome"]["dump_window_min"] for s, e in zip(sims, top_k)) / total_sim
    price_drop     = sum(s * e["outcome"]["price_drop_pct"]  for s, e in zip(sims, top_k)) / total_sim

    # Archetype majority vote from top-k
    arch_votes: dict[str, float] = {}
    for s, e in zip(sims, top_k):
        a = e["archetype"]
        arch_votes[a] = arch_votes.get(a, 0.0) + s
    predicted_archetype = max(arch_votes, key=arch_votes.get)

    # If input archetype is explicit (not UNKNOWN), trust it over prediction
    final_archetype = archetype if archetype != "UNKNOWN" else predicted_archetype

    accuracy_30d = get_accuracy_30d()

    logger.info(
        "[predictor] archetype=%s rug=%.2f dump=%dmin drop=%.1f%% conf=%.2f similar=%d",
        final_archetype, rug_prob, int(dump_window), price_drop, confidence, similar_count,
    )

    return {
        "rug_prob":        round(rug_prob, 4),
        "dump_window_min": int(dump_window),
        "price_drop_pct":  round(price_drop, 2),
        "confidence":      round(confidence, 4),
        "similar_count":   similar_count,
        "accuracy_30d":    accuracy_30d,
        "archetype":       final_archetype,
    }


# ── Store New Event ───────────────────────────────────────────────────────────

def store_event(
    anomaly_score: float,
    wash_ratio: float,
    cycle_count: int,
    aave_modifier: float,
    tx_per_minute: float,
    volume_spike_x: float,
    archetype: str,
    outcome: dict,
):
    """
    Store a confirmed event into the historical store.
    outcome: { rug_prob, dump_window_min, price_drop_pct }
    Call this after an anomaly is confirmed (e.g. post-dump verification).
    """
    features = build_feature_vector(
        anomaly_score, wash_ratio, cycle_count,
        aave_modifier, tx_per_minute, volume_spike_x,
    )
    _event_store.append({
        "features":  features,
        "archetype": archetype,
        "outcome":   outcome,
        "timestamp": time.time(),
    })
    logger.debug("[predictor] event stored — store size=%d", len(_event_store))
