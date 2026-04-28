"""
data_sources/aave.py
Aave v3 Mantle — Flash loan, collateral dump, open borrow detection.
"""

from web3 import Web3
from web3.exceptions import ContractLogicError
import time
import logging
from config import (
    MANTLE_RPC_URL,
    AAVE_POOL_ADDRESS,
    AAVE_FLASH_LOAN_WINDOW_BLOCKS,
    AAVE_COLLATERAL_DUMP_WINDOW_MIN,
    AAVE_OPEN_BORROW_MIN_USD,
    AAVE_OPEN_BORROW_FRESH_MIN,
    AAVE_MODIFIER_CAP,
)

logger = logging.getLogger(__name__)

# ── ABI fragments ─────────────────────────────────────────────────────────────

AAVE_POOL_ABI = [
    # FlashLoan(address initiator, address target, address asset, uint256 amount,
    #           uint8 interestRateMode, uint256 premium, uint16 referralCode)
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
    # LiquidationCall(address collateralAsset, address debtAsset, address user,
    #                 uint256 debtToCover, uint256 liquidatedCollateralAmount,
    #                 address liquidator, bool receiveAToken)
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True,  "name": "collateralAsset",            "type": "address"},
            {"indexed": True,  "name": "debtAsset",                  "type": "address"},
            {"indexed": True,  "name": "user",                       "type": "address"},
            {"indexed": False, "name": "debtToCover",                "type": "uint256"},
            {"indexed": False, "name": "liquidatedCollateralAmount", "type": "uint256"},
            {"indexed": False, "name": "liquidator",                 "type": "address"},
            {"indexed": False, "name": "receiveAToken",              "type": "bool"},
        ],
        "name": "LiquidationCall",
        "type": "event",
    },
    # Borrow(address reserve, address user, address onBehalfOf, uint256 amount,
    #        uint8 interestRateMode, uint256 borrowRate, uint16 referralCode)
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
    # getUserAccountData(address user) view returns (...)
    {
        "inputs": [{"name": "user", "type": "address"}],
        "name": "getUserAccountData",
        "outputs": [
            {"name": "totalCollateralBase",     "type": "uint256"},
            {"name": "totalDebtBase",           "type": "uint256"},
            {"name": "availableBorrowsBase",    "type": "uint256"},
            {"name": "currentLiquidationThreshold", "type": "uint256"},
            {"name": "ltv",                     "type": "uint256"},
            {"name": "healthFactor",            "type": "uint256"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
]

# ── Web3 setup ────────────────────────────────────────────────────────────────
_w3: Web3 | None = None
_pool = None

def _get_w3() -> Web3:
    global _w3
    if _w3 is None or not _w3.is_connected():
        _w3 = Web3(Web3.HTTPProvider(MANTLE_RPC_URL, request_kwargs={"timeout": 10}))
    return _w3

def _get_pool():
    global _pool
    if _pool is None:
        w3 = _get_w3()
        _pool = w3.eth.contract(
            address=Web3.to_checksum_address(AAVE_POOL_ADDRESS),
            abi=AAVE_POOL_ABI,
        )
    return _pool

# ── Recent event cache (in-memory, TTL 60s) ───────────────────────────────────

_flash_cache: dict[str, int] = {}   # wallet -> block number of last flash loan
_borrow_cache: dict[str, dict] = {} # wallet -> {block, timestamp, amount_usd}
_cache_ts: float = 0.0
CACHE_TTL = 60  # seconds

def _refresh_cache_if_needed():
    global _cache_ts
    if time.time() - _cache_ts < CACHE_TTL:
        return
    _fetch_recent_events()
    _cache_ts = time.time()

def _fetch_recent_events():
    """Fetch FlashLoan + Borrow events from last ~30 blocks (~60s on Mantle ~2s/block)."""
    global _flash_cache, _borrow_cache
    try:
        w3   = _get_w3()
        pool = _get_pool()
        latest = w3.eth.block_number
        from_block = max(0, latest - 30)

        # FlashLoan events
        flash_events = pool.events.FlashLoan.get_logs(fromBlock=from_block, toBlock=latest)
        _flash_cache = {}
        for ev in flash_events:
            initiator = ev["args"]["initiator"].lower()
            _flash_cache[initiator] = ev["blockNumber"]

        # Borrow events — store latest borrow per wallet
        borrow_events = pool.events.Borrow.get_logs(fromBlock=from_block, toBlock=latest)
        _borrow_cache = {}
        for ev in borrow_events:
            wallet = ev["args"]["onBehalfOf"].lower()
            block_info = w3.eth.get_block(ev["blockNumber"])
            _borrow_cache[wallet] = {
                "block":     ev["blockNumber"],
                "timestamp": block_info["timestamp"],
                "amount":    ev["args"]["amount"],
                "reserve":   ev["args"]["reserve"].lower(),
            }

    except Exception as e:
        logger.warning("aave._fetch_recent_events failed: %s", e)

# ── Detection functions ───────────────────────────────────────────────────────

def flash_loan_detected(wallet: str, current_block: int) -> bool:
    """
    Returns True if wallet initiated a flash loan in the same block
    as the current DEX swap (or within AAVE_FLASH_LOAN_WINDOW_BLOCKS).
    """
    _refresh_cache_if_needed()
    wallet = wallet.lower()
    flash_block = _flash_cache.get(wallet)
    if flash_block is None:
        return False
    return abs(current_block - flash_block) <= AAVE_FLASH_LOAN_WINDOW_BLOCKS


def collateral_dump_detected(wallet: str, swap_timestamp: int) -> bool:
    """
    Returns True if wallet borrowed from Aave (stablecoin) AND then
    sold collateral on DEX within AAVE_COLLATERAL_DUMP_WINDOW_MIN minutes.

    Logic: borrow_timestamp < swap_timestamp < borrow_timestamp + window
    """
    _refresh_cache_if_needed()
    wallet = wallet.lower()
    borrow = _borrow_cache.get(wallet)
    if borrow is None:
        return False

    window_sec = AAVE_COLLATERAL_DUMP_WINDOW_MIN * 60
    delta = swap_timestamp - borrow["timestamp"]
    return 0 <= delta <= window_sec


def open_borrow_gte(wallet: str, min_usd: float, fresh_min: int) -> bool:
    """
    Returns True if wallet has an open Aave borrow >= min_usd USD
    AND the borrow is fresh (< fresh_min minutes old).

    Uses getUserAccountData for live debt position + cache for freshness.
    """
    wallet = wallet.lower()

    # Freshness check from borrow cache
    borrow = _borrow_cache.get(wallet)
    if borrow is None:
        return False  # no recent borrow on record

    age_min = (time.time() - borrow["timestamp"]) / 60
    if age_min >= fresh_min:
        return False  # borrow too old

    # Debt position check via getUserAccountData
    try:
        pool = _get_pool()
        data = pool.functions.getUserAccountData(
            Web3.to_checksum_address(wallet)
        ).call()
        # totalDebtBase is in USD with 8 decimals (Aave v3 standard)
        total_debt_usd = data[1] / 1e8
        return total_debt_usd >= min_usd
    except ContractLogicError as e:
        logger.debug("getUserAccountData ContractLogicError for %s: %s", wallet, e)
        return False
    except Exception as e:
        logger.warning("open_borrow_gte failed for %s: %s", wallet, e)
        return False


def collateral_dump_from_liquidation(wallet: str, window_min: int = 60) -> bool:
    """
    Supplementary: check if wallet was recently liquidated (LiquidationCall).
    Liquidated positions often precede panic selling on DEX.
    Not used in main modifier — available for future L3 signal.
    """
    try:
        w3   = _get_w3()
        pool = _get_pool()
        latest    = w3.eth.block_number
        from_block = max(0, latest - (window_min * 30))  # ~30 blocks/min on Mantle

        events = pool.events.LiquidationCall.get_logs(
            fromBlock=from_block,
            toBlock=latest,
            argument_filters={"user": Web3.to_checksum_address(wallet)},
        )
        return len(events) > 0
    except Exception as e:
        logger.warning("collateral_dump_from_liquidation failed for %s: %s", wallet, e)
        return False


# ── Main interface ────────────────────────────────────────────────────────────

def get_aave_modifier(wallet: str, current_block: int, swap_timestamp: int) -> float:
    """
    Returns the Aave cross-protocol modifier for scoring.

    Priority max selection (not stacking):
        flash loan same block  -> 1.5 (hard cap)
        collateral dump <15min -> max(current, 1.3)
        open borrow fresh      -> max(current, 1.2)
        nothing                -> 1.0

    Returns: float in [1.0, 1.5]
    """
    modifier = 1.0

    try:
        if flash_loan_detected(wallet, current_block):
            return AAVE_MODIFIER_CAP  # 1.5 — short-circuit, no need to check further

        if collateral_dump_detected(wallet, swap_timestamp):
            modifier = max(modifier, 1.3)

        if open_borrow_gte(wallet, AAVE_OPEN_BORROW_MIN_USD, AAVE_OPEN_BORROW_FRESH_MIN):
            modifier = max(modifier, 1.2)

    except Exception as e:
        logger.warning("get_aave_modifier failed for %s: %s", wallet, e)

    return modifier


def get_wallet_aave_summary(wallet: str) -> dict:
    """
    Returns a summary dict for wallet_profiler + alerter use.
    {
        "has_open_borrow": bool,
        "total_debt_usd": float,
        "health_factor": float,   # < 1.0 = liquidatable
        "recent_flash_loan": bool,
        "recent_borrow_fresh": bool,
    }
    """
    result = {
        "has_open_borrow":     False,
        "total_debt_usd":      0.0,
        "health_factor":       999.0,
        "recent_flash_loan":   False,
        "recent_borrow_fresh": False,
    }
    try:
        _refresh_cache_if_needed()
        w3 = _get_w3()
        pool = _get_pool()

        data = pool.functions.getUserAccountData(
            Web3.to_checksum_address(wallet)
        ).call()
        total_debt_usd = data[1] / 1e8
        health_factor  = data[5] / 1e18

        result["has_open_borrow"] = total_debt_usd > 0
        result["total_debt_usd"]  = round(total_debt_usd, 2)
        result["health_factor"]   = round(health_factor, 4)

        wallet_lc = wallet.lower()
        result["recent_flash_loan"]   = wallet_lc in _flash_cache
        result["recent_borrow_fresh"] = (
            wallet_lc in _borrow_cache and
            (time.time() - _borrow_cache[wallet_lc]["timestamp"]) / 60 < AAVE_OPEN_BORROW_FRESH_MIN
        )

    except Exception as e:
        logger.warning("get_wallet_aave_summary failed for %s: %s", wallet, e)

    return result