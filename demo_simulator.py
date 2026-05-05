"""
demo_simulator.py
MAD Demo Mode — Async Scenario Simulation Engine
"""

import asyncio
import random
import logging
from datetime import datetime, timezone
from typing import Optional

from config import THRESHOLD_WATCHING, THRESHOLD_ALERT, DEMO_MODE
from predictor import predict
from scorer import compute_final_score
from database import log_signal, upsert_wallet
from alerter import broadcast_signal

logger = logging.getLogger(__name__)

# ── Demo addresses ──────────────────────────────────────
DEMO_POOLS = {
    "FLASH_WASH":     "0xdemo1111111111111111111111111111111111a1",
    "PUMP_DUMP":      "0xdemo2222222222222222222222222222222222b2",
    "CLEAN_MARKET":   "0xdemo3333333333333333333333333333333333c3",
    "FALSE_POSITIVE": "0xdemo4444444444444444444444444444444444d4",
}

DEMO_WALLETS = {
    "FLASH_WASH":     "0xdemowalletaaaaaaaaaaaaaaaaaaaaaaaaaaaa01",
    "PUMP_DUMP":      "0xdemowalletbbbbbbbbbbbbbbbbbbbbbbbbbbbb02",
    "CLEAN_MARKET":   "0xdemowalletcccccccccccccccccccccccccccc03",
    "FALSE_POSITIVE": "0xdemowalletdddddddddddddddddddddddddddd04",
}

# ── Scenario timelines ──────────────────────────────────
SCENARIOS = {
    "FLASH_WASH": [
        {"wash_ratio": 2,  "volume_spike_x": 1.2, "aave_modifier": 1.0, "anomaly_score": 18, "cycle_count": 0, "tx_per_minute": 2,  "corroboration": 1},
        {"wash_ratio": 15, "volume_spike_x": 5,   "aave_modifier": 1.3, "anomaly_score": 52, "cycle_count": 1, "tx_per_minute": 5,  "corroboration": 1},
        {"wash_ratio": 35, "volume_spike_x": 12,  "aave_modifier": 1.5, "anomaly_score": 78, "cycle_count": 2, "tx_per_minute": 8,  "corroboration": 1},
        {"wash_ratio": 42, "volume_spike_x": 18,  "aave_modifier": 1.5, "anomaly_score": 91, "cycle_count": 2, "tx_per_minute": 9,  "corroboration": 1},
    ],
    "PUMP_DUMP": [
        {"wash_ratio": 1, "volume_spike_x": 2,  "aave_modifier": 1.0, "anomaly_score": 15, "cycle_count": 0, "tx_per_minute": 3, "corroboration": 1},
        {"wash_ratio": 3, "volume_spike_x": 8,  "aave_modifier": 1.0, "anomaly_score": 38, "cycle_count": 0, "tx_per_minute": 5, "corroboration": 1},
        {"wash_ratio": 5, "volume_spike_x": 16, "aave_modifier": 1.0, "anomaly_score": 68, "cycle_count": 0, "tx_per_minute": 7, "corroboration": 1},
        {"wash_ratio": 6, "volume_spike_x": 20, "aave_modifier": 1.0, "anomaly_score": 85, "cycle_count": 0, "tx_per_minute": 8, "corroboration": 1},
    ],
    "CLEAN_MARKET": [
        {"wash_ratio": 1.0, "volume_spike_x": 1.1, "aave_modifier": 1.0, "anomaly_score": 12, "cycle_count": 0, "tx_per_minute": 1.5, "corroboration": 1},
        {"wash_ratio": 1.5, "volume_spike_x": 1.3, "aave_modifier": 1.0, "anomaly_score": 18, "cycle_count": 0, "tx_per_minute": 2.0, "corroboration": 1},
        {"wash_ratio": 1.2, "volume_spike_x": 1.2, "aave_modifier": 1.0, "anomaly_score": 14, "cycle_count": 0, "tx_per_minute": 1.8, "corroboration": 1},
        {"wash_ratio": 2.0, "volume_spike_x": 1.5, "aave_modifier": 1.0, "anomaly_score": 22, "cycle_count": 0, "tx_per_minute": 2.5, "corroboration": 1},
        {"wash_ratio": 1.3, "volume_spike_x": 1.1, "aave_modifier": 1.0, "anomaly_score": 16, "cycle_count": 0, "tx_per_minute": 1.5, "corroboration": 1},
    ],
    "FALSE_POSITIVE": [
        {"wash_ratio": 4, "volume_spike_x": 3, "aave_modifier": 1.0, "anomaly_score": 25, "cycle_count": 0, "tx_per_minute": 3, "corroboration": 1},
        {"wash_ratio": 8, "volume_spike_x": 5, "aave_modifier": 1.0, "anomaly_score": 42, "cycle_count": 0, "tx_per_minute": 5, "corroboration": 1},
        {"wash_ratio": 6, "volume_spike_x": 4, "aave_modifier": 1.0, "anomaly_score": 38, "cycle_count": 0, "tx_per_minute": 4, "corroboration": 1},
    ],
}

BASE_INTERVAL = 2.0  # seconds

# ── State ───────────────────────────────────────────────
_sim_state: dict = {
    "running":  False,
    "paused":   False,
    "scenario": None,
    "step":     0,
    "speed":    1.0,
    "task":     None,
    "pool_address": None,
}

def _noise(base: float, pct: float = 0.08) -> float:
    """Add ±pct noise to base value."""
    return max(0.0, base * (1 + random.uniform(-pct, pct)))

async def _run_scenario(scenario: str, speed: float) -> None:
    steps = SCENARIOS[scenario]
    pool_address = DEMO_POOLS[scenario]
    wallet_address = DEMO_WALLETS[scenario]

    _sim_state["running"] = True
    _sim_state["paused"] = False
    _sim_state["scenario"] = scenario
    _sim_state["speed"] = speed
    _sim_state["pool_address"] = pool_address

    logger.info("[demo] Starting scenario=%s speed=%.1fx steps=%d", scenario, speed, len(steps))

    for i, step in enumerate(steps):
        _sim_state["step"] = i

        # Respect pause
        while _sim_state["paused"]:
            await asyncio.sleep(0.5)

        # Apply noise
        data = {
            "wash_ratio":     _noise(step["wash_ratio"]),
            "volume_spike_x": _noise(step["volume_spike_x"]),
            "aave_modifier":  step["aave_modifier"],
            "anomaly_score":  min(100.0, _noise(step["anomaly_score"])),
            "cycle_count":    step["cycle_count"],
            "tx_per_minute":  _noise(step["tx_per_minute"]),
            "corroboration":  step["corroboration"],
        }

        # Clamp CLEAN_MARKET score
        if scenario == "CLEAN_MARKET":
            data["anomaly_score"] = min(data["anomaly_score"], 28.0)

        # Clamp FALSE_POSITIVE score 
        if scenario == "FALSE_POSITIVE":
            data["anomaly_score"] = max(24.0, min(data["anomaly_score"], 46.0))

        try:
            # Step 1: predict
            prediction = predict(**data)
            archetype = prediction.get("predicted_archetype", "UNKNOWN")
            s_dex = prediction.get("rug_prob", 0) * 100  # approximate

            # Step 2: build mock dex_results
            dex_results = [{
                "dex":          "agni",
                "pool_id":      pool_address,
                "s_dex":        data["anomaly_score"],
                "l1_score":     data["anomaly_score"] * 0.4,
                "l2_score":     data["wash_ratio"] * 1.5,
                "l3_score":     data["cycle_count"] * 10.0,
                "volume_usd":   50000 * _noise(1.0),
                "top_wallets":  [wallet_address],
                "l1_methods":   [],
                "l2_methods":   [],
                "l3_methods":   [],
            }]

            # Step 3: score
            score_result = compute_final_score(dex_results)
            s_final = score_result.get("s_final", data["anomaly_score"])
            alert_level = score_result.get("alert_level", "none")

            # Force s_final dari anomaly_score untuk scenario attack
            if scenario in ("FLASH_WASH", "PUMP_DUMP"):
                s_final = data["anomaly_score"]
            if s_final >= THRESHOLD_ALERT:
                alert_level = "alert"
            elif s_final >= THRESHOLD_WATCHING:
                alert_level = "watching"
            else:
                alert_level = "none"

            # Override alert for CLEAN_MARKET / FALSE_POSITIVE
            if scenario == "CLEAN_MARKET":
                alert_level = "none"
                s_final = min(s_final, 30.0)
            if scenario == "FALSE_POSITIVE" and s_final >= THRESHOLD_WATCHING:
                alert_level = "watching"
                s_final = min(s_final, 44.0)

            # Step 4: persist to signal_log (demo environment)
            log_signal(
                dex="agni",
                pool_address=pool_address,
                tx_hashes=[f"0xdemotx{i:04d}{random.randint(1000,9999)}"],
                l1_score=dex_results[0]["l1_score"],
                l2_score=dex_results[0]["l2_score"],
                l3_score=dex_results[0]["l3_score"],
                s_dex=data["anomaly_score"],
                s_final=s_final,
                alert_level=alert_level,
                environment="demo",
                is_simulated=True,
                volume_usd=dex_results[0]["volume_usd"],
                corroboration=data["corroboration"],
                top_wallets=[{
                    "wallet":       wallet_address,
                    "agent_type":   "MANIPULATOR" if scenario in ("FLASH_WASH", "PUMP_DUMP") else "UNKNOWN WALLET",
                    "archetype":    archetype,
                    "wash_ratio":   data["wash_ratio"],
                    "aave_modifier": data["aave_modifier"],
                    "cycle_count":  data["cycle_count"],
                    "is_simulated": True,
                aave_signal=0.0,
                aave_label="NO_DATA",
                }],
            )

            # Step 5: upsert wallet_profile jika score cukup
            if s_final >= THRESHOLD_WATCHING:
                upsert_wallet(
                    address=wallet_address,
                    agent_type="MANIPULATOR" if scenario in ("FLASH_WASH", "PUMP_DUMP") else "UNKNOWN WALLET",
                    archetype=archetype,
                    wash_ratio=data["wash_ratio"],
                    wash_label=archetype,
                    roi_7d=None,
                    smart_score=0.0,
                    risk_label="HIGH" if s_final >= THRESHOLD_ALERT else "MEDIUM",
                    total_volume_usd=dex_results[0]["volume_usd"],
                    tx_count=i + 1,
                    environment="demo",
                    is_simulated=True,
                )

            # Step 6: broadcast jika alert
            if alert_level in ("alert", "high_conf"):
                signal_payload = {
                    "alert_level":   alert_level,
                    "s_final":       s_final,
                    "dex":           "agni",
                    "pool_address":  pool_address,
                    "l1_score":      dex_results[0]["l1_score"],
                    "l2_score":      dex_results[0]["l2_score"],
                    "l3_score":      dex_results[0]["l3_score"],
                    "l1_methods":    [],
                    "tx_hashes":     [],
                    "top_wallets":   [{
                        "wallet":       wallet_address,
                        "agent_type":   "MANIPULATOR",
                        "archetype":    archetype,
                        "wash_ratio":   data["wash_ratio"],
                        "aave_modifier": data["aave_modifier"],
                        "cycle_count":  data["cycle_count"],
                        "corroboration": data["corroboration"],
                    }],
                    "corroboration": data["corroboration"],
                    "volume_usd":    dex_results[0]["volume_usd"],
                }
                await broadcast_signal(signal_payload)

            logger.info(
                "[demo] step=%d/%d scenario=%s score=%.1f level=%s archetype=%s",
                i + 1, len(steps), scenario, s_final, alert_level, archetype
            )

        except Exception as e:
            logger.error("[demo] step %d error: %s", i, e)

        # Interval
        interval = BASE_INTERVAL / speed + random.uniform(-0.4, 0.4)
        await asyncio.sleep(max(0.5, interval))

    _sim_state["running"] = False
    _sim_state["step"] = len(steps)
    logger.info("[demo] Scenario %s complete.", scenario)

# ── Public API ──────────────────────────────────────────

async def start_simulation(scenario: str, speed: float = 1.0) -> dict:
    if scenario not in SCENARIOS:
        return {"ok": False, "error": f"Unknown scenario: {scenario}. Valid: {list(SCENARIOS.keys())}"}

    if _sim_state["running"]:
        await reset_simulation()

    task = asyncio.create_task(_run_scenario(scenario, speed))
    _sim_state["task"] = task
    return {"ok": True, "scenario": scenario, "speed": speed, "steps": len(SCENARIOS[scenario])}

async def pause_simulation() -> dict:
    if not _sim_state["running"]:
        return {"ok": False, "error": "No simulation running"}
    _sim_state["paused"] = not _sim_state["paused"]
    state = "paused" if _sim_state["paused"] else "resumed"
    return {"ok": True, "state": state}

async def reset_simulation() -> dict:
    task = _sim_state.get("task")
    if task and not task.done():
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    _sim_state.update({
        "running": False,
        "paused": False,
        "scenario": None,
        "step": 0,
        "speed": 1.0,
        "task": None,
        "pool_address": None,
    })
    return {"ok": True, "state": "reset"}

def get_status() -> dict:
    scenario = _sim_state["scenario"]
    total_steps = len(SCENARIOS[scenario]) if scenario else 0
    return {
        "running": _sim_state["running"],
        "paused": _sim_state["paused"],
        "scenario": scenario,
        "step": _sim_state["step"],
        "total_steps": total_steps,
        "speed": _sim_state["speed"],
        "pool_address": _sim_state["pool_address"],
    }