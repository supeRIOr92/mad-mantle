"""
mcp_server.py
MAD — Mantle Anomaly Detector
Read-only MCP (Model Context Protocol) intelligence API.
Exposes: recent signals, wallet profiles, pool stats, predictor.
"""

import logging
import json
from typing import Any
from database import get_recent_signals, get_connection
from predictor import predict, build_feature_vector

logger = logging.getLogger(__name__)


# ── MCP Tool Registry ─────────────────────────────────────────────────────────

TOOLS = {
    "get_recent_signals": {
        "description": "Get recent anomaly signals from MAD signal_log.",
        "params": {
            "limit":       {"type": "int",    "default": 10,   "description": "Max signals to return (1-50)"},
            "alert_level": {"type": "string", "default": None, "description": "Filter: watching | alert | high_conf"},
        },
    },
    "get_wallet_profile": {
        "description": "Get behavioral profile for a wallet address.",
        "params": {
            "address": {"type": "string", "required": True, "description": "Wallet address (0x...)"},
        },
    },
    "get_pool_stats": {
        "description": "Get signal stats for a specific pool address.",
        "params": {
            "pool_address": {"type": "string", "required": True, "description": "Pool contract address"},
            "limit":        {"type": "int",    "default": 20,   "description": "Max records"},
        },
    },
    "run_prediction": {
        "description": "Run risk prediction for a given anomaly feature set.",
        "params": {
            "anomaly_score":  {"type": "float", "required": True},
            "wash_ratio":     {"type": "float", "default": 0.0},
            "cycle_count":    {"type": "int",   "default": 0},
            "aave_modifier":  {"type": "float", "default": 1.0},
            "tx_per_minute":  {"type": "float", "default": 0.0},
            "volume_spike_x": {"type": "float", "default": 1.0},
            "archetype":      {"type": "string","default": "UNKNOWN"},
        },
    },
    "get_top_wallets": {
        "description": "Get top wallets by ROI or risk label.",
        "params": {
            "order_by": {"type": "string", "default": "roi_7d", "description": "roi_7d | wash_ratio | reputation_score"},
            "limit":    {"type": "int",    "default": 10},
        },
    },
    "get_digest_stats": {
        "description": "Get today's digest stats: scan count, alert count, top pools.",
        "params": {},
    },
    "list_tools": {
        "description": "List all available MCP tools.",
        "params": {},
    },
}


# ── Tool Handlers ─────────────────────────────────────────────────────────────

def _handle_get_recent_signals(params: dict) -> dict:
    limit = min(int(params.get("limit", 10)), 50)
    alert_level = params.get("alert_level")
    signals = get_recent_signals(limit=limit, alert_level=alert_level)
    return {"count": len(signals), "signals": signals}


def _handle_get_wallet_profile(params: dict) -> dict:
    address = params.get("address", "").lower()
    if not address:
        return {"error": "address is required"}

with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM wallet_profile WHERE address = ?", (address,)
        ).fetchone()

    if not row:
        return {"error": f"wallet {address} not found"}

    return {"wallet": dict(row)}


def _handle_get_pool_stats(params: dict) -> dict:
    pool_address = params.get("pool_address", "").lower()
    limit = min(int(params.get("limit", 20)), 100)

    if not pool_address:
        return {"error": "pool_address is required"}

    with get_connection() as conn:
        rows = conn.execute("""
            SELECT dex, pool_address, s_final, alert_level, volume_usd,
                   l1_score, l2_score, l3_score, corroboration, created_at
            FROM signal_log
            WHERE pool_address = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (pool_address, limit)).fetchall()

        if not rows:
            return {"error": f"no signals for pool {pool_address}"}

        records = [dict(r) for r in rows]
        avg_score = sum(r["s_final"] for r in records) / len(records)
        max_score = max(r["s_final"] for r in records)

    return {
        "pool_address": pool_address,
        "total_signals": len(records),
        "avg_score":     round(avg_score, 2),
        "max_score":     round(max_score, 2),
        "signals":       records,
    }


def _handle_run_prediction(params: dict) -> dict:
    try:
        result = predict(
            anomaly_score  = float(params.get("anomaly_score", 0)),
            wash_ratio     = float(params.get("wash_ratio", 0.0)),
            cycle_count    = int(params.get("cycle_count", 0)),
            aave_modifier  = float(params.get("aave_modifier", 1.0)),
            tx_per_minute  = float(params.get("tx_per_minute", 0.0)),
            volume_spike_x = float(params.get("volume_spike_x", 1.0)),
            archetype      = str(params.get("archetype", "UNKNOWN")),
        )
        return result
    except Exception as e:
        return {"error": str(e)}


def _handle_get_top_wallets(params: dict) -> dict:
    order_by = params.get("order_by", "roi_7d")
    allowed  = {"roi_7d", "wash_ratio", "reputation_score"}
    if order_by not in allowed:
        order_by = "roi_7d"

    limit = min(int(params.get("limit", 10)), 50)

    with get_connection() as conn:
        rows = conn.execute(f"""
            SELECT address, roi_7d, wash_ratio, reputation_score,
                   risk_label, is_probable_agent, agent_token_id
            FROM wallet_profile
            WHERE {order_by} IS NOT NULL
            ORDER BY {order_by} DESC
            LIMIT ?
        """, (limit,)).fetchall()

    return {"count": len(rows), "wallets": [dict(r) for r in rows]}


def _handle_get_digest_stats(params: dict) -> dict:
    from database import get_digest_stats
    return get_digest_stats()


def _handle_list_tools(params: dict) -> dict:
    return {
        "tools": [
            {"name": k, "description": v["description"]}
            for k, v in TOOLS.items()
        ]
    }


# ── Dispatcher ────────────────────────────────────────────────────────────────

_HANDLERS = {
    "get_recent_signals": _handle_get_recent_signals,
    "get_wallet_profile": _handle_get_wallet_profile,
    "get_pool_stats":     _handle_get_pool_stats,
    "run_prediction":     _handle_run_prediction,
    "get_top_wallets":    _handle_get_top_wallets,
    "get_digest_stats":   _handle_get_digest_stats,
    "list_tools":         _handle_list_tools,
}


def handle_request(tool_name: str, params: dict) -> dict:
    """
    Main MCP request handler.
    Returns JSON-serializable dict.
    Read-only — no write operations exposed.
    """
    if tool_name not in _HANDLERS:
        return {
            "error":            f"unknown tool: {tool_name}",
            "available_tools":  list(TOOLS.keys()),
        }

    try:
        result = _HANDLERS[tool_name](params)
        logger.info("[mcp] tool=%s params=%s", tool_name, params)
        return result
    except Exception as e:
        logger.error("[mcp] tool=%s error: %s", tool_name, e)
        return {"error": str(e)}


def handle_mcp_json(raw: str) -> str:
    """
    Parse MCP JSON request and return JSON response.
    Expected input: {"tool": "...", "params": {...}}
    """
    try:
        req = json.loads(raw)
        tool   = req.get("tool", "")
        params = req.get("params", {})
        result = handle_request(tool, params)
    except json.JSONDecodeError as e:
        result = {"error": f"invalid JSON: {e}"}

    return json.dumps(result, default=str, indent=2)


# ── Stdio MCP Runner (for Claude Desktop / MCP clients) ──────────────────────

def run_stdio():
    """
    Run MCP server in stdio mode.
    Reads newline-delimited JSON from stdin, writes JSON to stdout.
    Compatible with MCP protocol (Claude Desktop, etc.)
    """
    import sys
    logger.info("[mcp] MAD MCP Server started — stdio mode")

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        response = handle_mcp_json(line)
        sys.stdout.write(response + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    run_stdio()