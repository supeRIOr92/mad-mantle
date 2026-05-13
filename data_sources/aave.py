"""
data_sources/aave.py — Aave v3 Mantle
Pool-level signal untuk scorer amplification.

CHANGES:
- BUG FIX: decimal hardcoded 1e6 → lookup per asset via ERC20
- REMOVED: get_aave_modifier() — dead code, tidak dipanggil di scheduler.py
- fetch_pool_signal() = single source of truth untuk scorer.py
- get_wallet_aave_summary() tetap untuk wallet_profiler.py
"""

from web3 import Web3
from web3.exceptions import ContractLogicError
import time
import logging
from config import (
    MANTLE_RPC_URL,
    AAVE_POOL_ADDRESS,
    AAVE_OPEN_BORROW_FRESH_MIN,
    AAVE_SIGNAL_WINDOW_BLOCKS,
)

logger = logging.getLogger(__name__)

AAVE_POOL_ABI = [
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True,  "name": "target",           "type": "address"},
            {"indexed": True,  "name": "initiator",        "type": "address"},
            {"indexed": True,  "name": "asset",            "type": "address"},
            {"indexed": False, "name": "amount",           "type": "uint256"},
            {"indexed": False, "name": "interestRateMode", "type": "uint8"},
            {"indexed": False, "name": "premium",          "type": "uint256"},
            {"indexed": False, "name": "referralCode",     "type": "uint16"},
        ],
        "name": "FlashLoan",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True,  "name": "reserve",          "type": "address"},
            {"indexed": True,  "name": "user",             "type": "address"},
            {"indexed": True,  "name": "onBehalfOf",       "type": "address"},
            {"indexed": False, "name": "amount",           "type": "uint256"},
            {"indexed": False, "name": "interestRateMode", "type": "uint8"},
            {"indexed": False, "name": "borrowRate",       "type": "uint256"},
            {"indexed": False, "name": "referralCode",     "type": "uint16"},
        ],
        "name": "Borrow",
        "type": "event",
    },
    {
        "inputs": [{"name": "user", "type": "address"}],
        "name": "getUserAccountData",
        "outputs": [
            {"name": "totalCollateralBase",         "type": "uint256"},
            {"name": "totalDebtBase",               "type": "uint256"},
            {"name": "availableBorrowsBase",        "type": "uint256"},
            {"name": "currentLiquidationThreshold", "type": "uint256"},
            {"name": "ltv",                         "type": "uint256"},
            {"name": "healthFactor",                "type": "uint256"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
]

ERC20_DECIMALS_ABI = [
    {"inputs": [], "name": "decimals", "outputs": [{"type": "uint8"}], "stateMutability": "view", "type": "function"},
]

_w3 = None
_pool = None
_decimals_cache: dict = {}
_borrow_cache: dict = {}
_cache_ts: float = 0.0
CACHE_TTL = 60


def _get_w3() -> Web3:
    global _w3
    if _w3 is None or not _w3.is_connected():
        _w3 = Web3(Web3.HTTPProvider(MANTLE_RPC_URL, request_kwargs={"timeout": 10}))
    return _w3


def _get_pool():
    global _pool
    if _pool is None:
        _pool = _get_w3().eth.contract(
            address=Web3.to_checksum_address(AAVE_POOL_ADDRESS),
            abi=AAVE_POOL_ABI,
        )
    return _pool


def _get_asset_decimals(asset: str) -> int:
    """FIX: lookup decimals per asset, bukan hardcoded 1e6."""
    addr = asset.lower()
    if addr in _decimals_cache:
        return _decimals_cache[addr]
    try:
        token = _get_w3().eth.contract(
            address=Web3.to_checksum_address(asset), abi=ERC20_DECIMALS_ABI
        )
        dec = token.functions.decimals().call()
        _decimals_cache[addr] = dec
        return dec
    except Exception as e:
        logger.debug("[aave] decimals lookup failed %s: %s — default 18", asset, e)
        _decimals_cache[addr] = 18
        return 18


def _refresh_cache_if_needed():
    global _cache_ts
    if time.time() - _cache_ts < CACHE_TTL:
        return
    try:
        w3     = _get_w3()
        pool   = _get_pool()
        latest = w3.eth.block_number
        from_b = max(0, latest - 30)
        global _borrow_cache
        _borrow_cache = {}
        for ev in pool.events.Borrow.get_logs(from_block=from_b, to_block=latest):
            wallet = ev["args"]["onBehalfOf"].lower()
            asset  = ev["args"]["reserve"].lower()
            dec    = _get_asset_decimals(asset)
            block_info = w3.eth.get_block(ev["blockNumber"])
            _borrow_cache[wallet] = {
                "block":      ev["blockNumber"],
                "timestamp":  block_info["timestamp"],
                "amount_usd": ev["args"]["amount"] / (10 ** dec),
                "reserve":    asset,
            }
        _cache_ts = time.time()
    except Exception as e:
        logger.warning("[aave] cache refresh failed: %s", e)


def _signal_label(signal: float) -> str:
    if signal >= 1.0: return "FLASH_LOAN_LARGE"
    if signal >= 0.7: return "FLASH_LOAN"
    if signal >= 0.6: return "BORROW_LARGE"
    if signal >= 0.4: return "BORROW_MID"
    if signal >= 0.2: return "BORROW_SMALL"
    return "NO_ACTIVITY"


def compute_aave_signal(events: list) -> float:
    signal = 0.0
    for e in events:
        t   = e.get("type", "")
        usd = float(e.get("amount_usd", 0))
        if t == "FLASH_LOAN":
            signal = max(signal, 1.0 if usd > 500_000 else 0.7)
        elif t == "BORROW":
            if usd > 1_000_000: signal = max(signal, 0.6)
            elif usd > 100_000: signal = max(signal, 0.4)
            elif usd > 10_000:  signal = max(signal, 0.2)
    return round(signal, 4)


def fetch_pool_signal(current_block: int) -> dict:
    """
    Single source of truth untuk scorer.py.
    Fetch FlashLoan + Borrow dari Aave dalam AAVE_SIGNAL_WINDOW_BLOCKS terakhir.
    """
    result = {"aave_signal": 0.0, "aave_label": "NO_ACTIVITY", "events": []}
    try:
        pool    = _get_pool()
        from_b  = max(0, current_block - AAVE_SIGNAL_WINDOW_BLOCKS)
        events  = []

        for ev in pool.events.FlashLoan.get_logs(from_block=from_b, to_block=current_block):
            asset = ev["args"]["asset"].lower()
            dec   = _get_asset_decimals(asset)  # FIX
            events.append({
                "type":       "FLASH_LOAN",
                "amount_usd": ev["args"]["amount"] / (10 ** dec),
                "block":      ev["blockNumber"],
                "initiator":  ev["args"]["initiator"].lower(),
                "asset":      asset,
            })

        for ev in pool.events.Borrow.get_logs(from_block=from_b, to_block=current_block):
            asset = ev["args"]["reserve"].lower()
            dec   = _get_asset_decimals(asset)  # FIX
            events.append({
                "type":       "BORROW",
                "amount_usd": ev["args"]["amount"] / (10 ** dec),
                "block":      ev["blockNumber"],
                "wallet":     ev["args"]["onBehalfOf"].lower(),
                "asset":      asset,
            })

        signal = compute_aave_signal(events)
        result["aave_signal"] = signal
        result["aave_label"]  = _signal_label(signal)
        result["events"]      = events
        logger.info("[aave] blocks=%d–%d events=%d signal=%.2f label=%s",
                    from_b, current_block, len(events), signal, result["aave_label"])
    except Exception as e:
        logger.warning("[aave.fetch_pool_signal] failed: %s", e)
    return result


def get_wallet_aave_summary(wallet: str) -> dict:
    """Untuk wallet_profiler.py dan alerter.py."""
    result = {"has_open_borrow": False, "total_debt_usd": 0.0,
               "health_factor": 999.0, "recent_borrow_fresh": False}
    try:
        _refresh_cache_if_needed()
        data  = _get_pool().functions.getUserAccountData(
            Web3.to_checksum_address(wallet)
        ).call()
        result["has_open_borrow"] = data[1] > 0
        result["total_debt_usd"]  = round(data[1] / 1e8, 2)
        result["health_factor"]   = round(data[5] / 1e18, 4)
        borrow = _borrow_cache.get(wallet.lower())
        if borrow:
            result["recent_borrow_fresh"] = (time.time() - borrow["timestamp"]) / 60 < AAVE_OPEN_BORROW_FRESH_MIN
    except Exception as e:
        logger.debug("[aave] getUserAccountData skip %s: %s", wallet, e)
    return result

