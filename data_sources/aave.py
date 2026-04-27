# data_sources/aave.py — Aave V3 Mantle integration
# Detects: flash loans, collateral dumps, open large borrows
# AAVE_POOL: 0x458F293454fE0d67EC0655f3672301301DD51422

import logging
import time
from web3 import Web3
from config import MANTLE_RPC_URL, AAVE_POOL_ADDRESS

logger = logging.getLogger(__name__)

# ── ABI (minimal — only events/functions we need) ─────────────────────────

AAVE_POOL_ABI = [
    # FlashLoan event
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
    # LiquidationCall event (collateral dump signal)
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
    # Borrow event
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True,  "name": "reserve",          "type": "address"},
            {"indexed": False, "name": "user",             "type": "address"},
            {"indexed": True,  "name": "onBehalfOf",       "type": "address"},
            {"indexed": False, "name": "amount",           "type": "uint256"},
            {"indexed": False, "name": "interestRateMode", "type": "uint8"},
            {"indexed": False, "name": "borrowRate",       "type": "uint256"},
            {"indexed": True,  "name": "referralCode",     "type": "uint16"},
        ],
        "name": "Borrow",
        "type": "event",
    },
    # getUserAccountData — for open position check
    {
        "inputs": [{"name": "user", "type": "address"}],
        "name": "getUserAccountData",
        "outputs": [
            {"name": "totalCollateralBase",          "type": "uint256"},
            {"name": "totalDebtBase",                "type": "uint256"},
            {"name": "availableBorrowsBase",         "type": "uint256"},
            {"name": "currentLiquidationThreshold", "type": "uint256"},
            {"name": "ltv",                          "type": "uint256"},
            {"name": "healthFactor",                 "type": "uint256"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
]

# ── Web3 Client ───────────────────────────────────────────────────────────

_w3 = None
_pool = None

def get_pool():
    global _w3, _pool
    if _pool is None:
        _w3 = Web3(Web3.HTTPProvider(MANTLE_RPC_URL, request_kwargs={"timeout": 10}))
        _pool = _w3.eth.contract(
            address=Web3.to_checksum_address(AAVE_POOL_ADDRESS),
            abi=AAVE_POOL_ABI,
        )
    return _pool

# ── Flash Loan Detection ──────────────────────────────────────────────────

def flash_loan_detected(wallet: str, block_number: int) -> bool:
    """
    Returns True if wallet was initiator of a FlashLoan in the given block.
    """
    try:
        pool = get_pool()
        logs = pool.events.FlashLoan.get_logs(
            from_block=block_number,
            to_block=block_number,
            argument_filters={"initiator": Web3.to_checksum_address(wallet)},
        )
        return len(logs) > 0
    except Exception as e:
        logger.warning(f"[aave] flash_loan_detected error for {wallet}: {e}")
        return False

# ── Collateral Dump Detection ─────────────────────────────────────────────

def collateral_dump_detected(wallet: str, window_min: int = 15) -> bool:
    """
    Returns True if wallet was liquidated (collateral dump) within the last `window_min` minutes.
    Uses LiquidationCall event — wallet is the `user` field.
    """
    try:
        pool = get_pool()
        w3 = _w3
        latest_block = w3.eth.block_number
        # Estimate blocks for window (Mantle ~2s block time → 30 blocks/min)
        blocks_back = window_min * 30
        from_block = max(0, latest_block - blocks_back)

        logs = pool.events.LiquidationCall.get_logs(
            from_block=from_block,
            to_block=latest_block,
            argument_filters={"user": Web3.to_checksum_address(wallet)},
        )
        return len(logs) > 0
    except Exception as e:
        logger.warning(f"[aave] collateral_dump_detected error for {wallet}: {e}")
        return False

# ── Open Borrow Detection ─────────────────────────────────────────────────

def open_borrow_gte(wallet: str, min_usd: float = 10_000, max_age_min: int = 15) -> bool:
    """
    Returns True if wallet has an open borrow >= min_usd AND the borrow is fresh (< max_age_min).
    Uses getUserAccountData for current debt + Borrow event for recency check.
    min_usd in USD (Aave reports in USD base unit 1e8).
    """
    try:
        pool = get_pool()
        w3 = _w3
        checksum = Web3.to_checksum_address(wallet)

        # Check current debt
        data = pool.functions.getUserAccountData(checksum).call()
        total_debt_usd = data[1] / 1e8  # totalDebtBase in USD (8 decimals)

        if total_debt_usd < min_usd:
            return False

        # Check if borrow is fresh (within max_age_min)
        latest_block = w3.eth.block_number
        blocks_back = max_age_min * 30
        from_block = max(0, latest_block - blocks_back)

        logs = pool.events.Borrow.get_logs(
            from_block=from_block,
            to_block=latest_block,
            argument_filters={"onBehalfOf": checksum},
        )
        return len(logs) > 0

    except Exception as e:
        logger.warning(f"[aave] open_borrow_gte error for {wallet}: {e}")
        return False

# ── Aave Modifier (main entry point for scorer.py) ────────────────────────

def get_aave_modifier(wallet: str, block_number: int) -> float:
    """
    Returns Aave modifier for S_final calculation.
    Priority (max selection, no stacking):
        1.5x — flash loan same block
        1.3x — collateral dump within 15 min
        1.2x — open borrow >= $10K, fresh < 15 min
        1.0x — no signal

    Usage in scorer.py:
        aave_mod = get_aave_modifier(wallet, block_number)
        S_final = S_weighted * corr_modifier * min(aave_mod, 1.5)
    """
    try:
        if flash_loan_detected(wallet, block_number):
            logger.info(f"[aave] {wallet[:10]}... FLASH LOAN @ block {block_number}")
            return 1.5

        if collateral_dump_detected(wallet, window_min=15):
            logger.info(f"[aave] {wallet[:10]}... COLLATERAL DUMP")
            return 1.3

        if open_borrow_gte(wallet, min_usd=10_000, max_age_min=15):
            logger.info(f"[aave] {wallet[:10]}... OPEN BORROW fresh")
            return 1.2

        return 1.0

    except Exception as e:
        logger.warning(f"[aave] get_aave_modifier error for {wallet}: {e}")
        return 1.0  # fail-safe: no modifier on error