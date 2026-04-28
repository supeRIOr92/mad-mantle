# data_sources/mantlescan.py — MantleScan API
# Wallet enrichment + ROI calculation
# Etherscan V2 API (free key)

import logging
import requests
from datetime import datetime, timedelta
from config import MANTLESCAN_API_KEY, MANTLE_CHAIN_ID

logger = logging.getLogger(__name__)
BASE_URL = "https://api.etherscan.io/v2/api"


def _get(params: dict) -> dict:
    params["apikey"] = MANTLESCAN_API_KEY
    params["chainid"] = MANTLE_CHAIN_ID
    try:
        resp = requests.get(BASE_URL, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") == "0":
            logger.warning(f"[mantlescan] API error: {data.get('message')} — {data.get('result')}")
            return {}
        return data
    except Exception as e:
        logger.error(f"[mantlescan] request failed: {e}")
        return {}


def fetch_wallet_balance(address: str) -> float:
    data = _get({
        "module": "account",
        "action": "balance",
        "address": address,
        "tag": "latest",
    })
    try:
        return int(data.get("result", "0")) / 1e18
    except Exception:
        return 0.0


def fetch_wallet_tx_list(address: str, limit: int = 100) -> list:
    data = _get({
        "module": "account",
        "action": "txlist",
        "address": address,
        "startblock": 0,
        "endblock": 99999999,
        "page": 1,
        "offset": limit,
        "sort": "desc",
    })
    return data.get("result", [])


def fetch_wallet_token_transfers(address: str, limit: int = 200) -> list:
    data = _get({
        "module": "account",
        "action": "tokentx",
        "address": address,
        "page": 1,
        "offset": limit,
        "sort": "desc",
    })
    return data.get("result", [])


def calc_roi_7d(address: str) -> float | None:
    """
    Approximate 7-day ROI proxy based on token transfer inflow/outflow.
    Not price-adjusted — used as relative signal only.
    """
    try:
        transfers = fetch_wallet_token_transfers(address)
        if not transfers:
            return None

        cutoff = datetime.utcnow() - timedelta(days=7)
        inflow = 0.0
        outflow = 0.0

        for tx in transfers:
            ts = datetime.utcfromtimestamp(int(tx.get("timeStamp", 0)))
            if ts < cutoff:
                continue
            decimals = int(tx.get("tokenDecimal", 18))
            value = int(tx.get("value", 0)) / (10 ** decimals)
            if tx.get("to", "").lower() == address.lower():
                inflow += value
            else:
                outflow += value

        if outflow == 0:
            return None
        return round((inflow - outflow) / outflow, 4)
    except Exception as e:
        logger.error(f"[mantlescan] calc_roi_7d failed for {address}: {e}")
        return None


def enrich_wallet(address: str) -> dict:
    """Full wallet enrichment — returns dict ready for upsert_wallet()."""
    address = address.lower()
    txs = fetch_wallet_tx_list(address, limit=50)
    roi = calc_roi_7d(address)
    balance = fetch_wallet_balance(address)
    return {
        "address": address,
        "tx_count": len(txs),
        "roi_7d": roi,
        "mnt_balance": balance,
    }

# ── Alias for wallet_profiler.py compatibility ────────────
def get_wallet_roi(address: str, days: int = 7) -> float | None:
    """Alias for calc_roi_7d. days param reserved for future use."""
    return calc_roi_7d(address)