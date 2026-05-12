# data_sources/moe.py — Merchant Moe LB 2.2 data source
# MIGRATED: subgraph → direct RPC via web3.py
# Detection: Poisson + Rate-of-Change (same as before)
#
# Verified onchain:
#   Swap topic: 0xad7d6f97abf51ce18e17a38f4d70e975be9c0708474987bb3e26ad21bd93ca70
#   Signature:  Swap(address sender, address to, uint24 id,
#                    bytes32 amountsIn, bytes32 amountsOut,
#                    uint24 volatilityAccumulator,
#                    bytes32 totalFees, bytes32 protocolFees)
#   Factory:    0xa6630671775c4EA2743840F9A5016dCf2A104054
#
# Decode bytes32 amounts (Moe LB specific):
#   upper 128 bits = token1 (tokenY) amount
#   lower 128 bits = token0 (tokenX) amount

import logging
import time
from collections import defaultdict
from datetime import datetime, timezone

from web3 import Web3
from eth_abi import decode as abi_decode

from config import MANTLE_RPC_URL, RPC_BLOCK_LOOKBACK

logger = logging.getLogger(__name__)

SWAP_TOPIC      = "0xad7d6f97abf51ce18e17a38f4d70e975be9c0708474987bb3e26ad21bd93ca70"
FACTORY_ADDRESS = Web3.to_checksum_address("0xa6630671775c4EA2743840F9A5016dCf2A104054")
BUCKET_SIZE     = 15 * 60
MANTLE_BLOCK_TIME = 2

LB_FACTORY_ABI = [
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True,  "name": "tokenX",  "type": "address"},
            {"indexed": True,  "name": "tokenY",  "type": "address"},
            {"indexed": True,  "name": "binStep", "type": "uint256"},
            {"indexed": False, "name": "LBPair",  "type": "address"},
            {"indexed": False, "name": "pid",     "type": "uint256"},
        ],
        "name": "LBPairCreated",
        "type": "event",
    }
]

ERC20_ABI = [
    {"inputs": [], "name": "symbol",   "outputs": [{"type": "string"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "decimals", "outputs": [{"type": "uint8"}],  "stateMutability": "view", "type": "function"},
]

_w3 = None
_token_cache: dict = {}
_pool_registry: dict = {}
_registry_fetched_at: float = 0.0
REGISTRY_TTL = 3600


def _get_w3() -> Web3:
    global _w3
    if _w3 is None or not _w3.is_connected():
        _w3 = Web3(Web3.HTTPProvider(MANTLE_RPC_URL, request_kwargs={"timeout": 15}))
    return _w3


def _get_token_meta(address: str) -> dict:
    addr = address.lower()
    if addr in _token_cache:
        return _token_cache[addr]
    try:
        w3 = _get_w3()
        c  = w3.eth.contract(address=Web3.to_checksum_address(address), abi=ERC20_ABI)
        _token_cache[addr] = {"symbol": c.functions.symbol().call(), "decimals": c.functions.decimals().call()}
    except Exception as e:
        logger.debug("[moe] token meta failed %s: %s", address, e)
        _token_cache[addr] = {"symbol": addr[:8] + "...", "decimals": 18}
    return _token_cache[addr]


def _ensure_pool_registry():
    global _registry_fetched_at
    if time.time() - _registry_fetched_at < REGISTRY_TTL and _pool_registry:
        return
    try:
        w3      = _get_w3()
        latest  = w3.eth.block_number
        factory = w3.eth.contract(address=FACTORY_ADDRESS, abi=LB_FACTORY_ABI)
        events  = factory.events.LBPairCreated.get_logs(
            from_block=max(0, latest - 500_000), to_block=latest
        )
        for ev in events:
            pool_addr = ev["args"]["LBPair"].lower()
            mx = _get_token_meta(ev["args"]["tokenX"])
            my = _get_token_meta(ev["args"]["tokenY"])
            _pool_registry[pool_addr] = {
                "id": pool_addr, "dex": "moe",
                "token0": ev["args"]["tokenX"].lower(),
                "token1": ev["args"]["tokenY"].lower(),
                "token0Symbol": mx["symbol"], "token1Symbol": my["symbol"],
                "decimals0": mx["decimals"],  "decimals1": my["decimals"],
                "feeTier": None, "txCount": 0, "totalVolumeUSD": 0.0, "lastSwapAt": None,
            }
        _registry_fetched_at = time.time()
        logger.info("[moe] registry loaded — %d pools", len(_pool_registry))
    except Exception as e:
        logger.error("[moe] registry fetch failed: %s", e)


def _decode_amounts(b32: bytes) -> tuple:
    v = int.from_bytes(b32, "big")
    return v & ((1 << 128) - 1), v >> 128  # amount0, amount1


def _decode_swap_log(log: dict) -> dict | None:
    try:
        pool_addr = log["address"].lower()
        meta = _pool_registry.get(pool_addr, {})
        # Handle HexBytes or str for data
        raw_data = log["data"]
        if isinstance(raw_data, (bytes, bytearray)):
            data_bytes = bytes(raw_data)
        else:
            data_bytes = bytes.fromhex(str(raw_data).removeprefix("0x"))
        id_, amounts_in, amounts_out, vol_acc, total_fees, protocol_fees = abi_decode(
            ["uint24", "bytes32", "bytes32", "uint24", "bytes32", "bytes32"],
            data_bytes,
        )
        # Handle HexBytes for topics
        def topic_to_hex(t) -> str:
            if isinstance(t, (bytes, bytearray)):
                return t.hex()
            return str(t).removeprefix("0x")

        sender = "0x" + topic_to_hex(log["topics"][1])[24:]
        recipient = "0x" + topic_to_hex(log["topics"][2])[24:]
        in0, in1 = _decode_amounts(amounts_in)
        dec0, dec1 = meta.get("decimals0", 18), meta.get("decimals1", 18)
        amount_usd = (in0 / (10 ** dec0)) if in0 > 0 else (in1 / (10 ** dec1)) if in1 > 0 else 0.0
        # Get timestamp
        ts = 0
        raw_ts = log.get("blockTimestamp")
        if raw_ts:
            try:
                ts = int(raw_ts, 16) if isinstance(raw_ts, str) else int(raw_ts)
            except Exception:
                ts = 0
        if ts == 0:
            w3 = _get_w3()
            block_num = log["blockNumber"]
            if isinstance(block_num, (bytes, bytearray)):
                block_num = int.from_bytes(block_num, "big")
            ts = w3.eth.get_block(block_num)["timestamp"]
        # Handle HexBytes for transactionHash and logIndex
        tx_h = log["transactionHash"]
        if isinstance(tx_h, (bytes, bytearray)):
            tx_h = "0x" + tx_h.hex()
        else:
            tx_h = str(tx_h)
        log_idx = log["logIndex"]
        if isinstance(log_idx, (bytes, bytearray)):
            log_idx = int.from_bytes(log_idx, "big")
        elif isinstance(log_idx, str):
            log_idx = int(log_idx, 16)
        else:
            log_idx = int(log_idx)
        return {
            "id": f"{tx_h}-{log_idx}",
            "timestamp": ts,
            "txHash": tx_h,
            "pool": {
                "id": pool_addr,
                "token0Symbol": meta.get("token0Symbol", "?"),
                "token1Symbol": meta.get("token1Symbol", "?"),
                "txCount": 0,
            },
            "sender": {"id": sender, "txCount": 0, "isAgent": False, "agentTokenId": None},
            "recipient": {"id": recipient},
            "amountUSD": round(amount_usd, 6),
            "bin_id": id_,
            "dex": "moe",
        }
    except Exception as e:
        logger.debug("[moe] decode failed: %s", e)
        return None

def fetch_recent_swaps(since_ts: int, limit: int = 500) -> list:
    _ensure_pool_registry()
    if not _pool_registry:
        return []
    try:
        w3     = _get_w3()
        latest = w3.eth.block_number
        now_ts = int(time.time())
        from_b = max(0, latest - min(delta, RPC_BLOCK_LOOKBACK))
        swaps  = []
        for pool_addr in list(_pool_registry.keys()):
            logs = w3.eth.get_logs({
                "fromBlock": from_b, "toBlock": latest,
                "address": Web3.to_checksum_address(pool_addr),
                "topics": [SWAP_TOPIC],
            })
            for log in logs:
                s = _decode_swap_log(dict(log))
                if s and s["timestamp"] >= since_ts:
                    swaps.append(s)
            if len(swaps) >= limit:
                break
        swaps.sort(key=lambda s: s["timestamp"], reverse=True)
        return swaps[:limit]
    except Exception as e:
        logger.error("[moe] fetch_recent_swaps failed: %s", e)
        return []


def fetch_tx_count_buckets(pool_id: str, since_ts: int) -> list:
    _ensure_pool_registry()
    try:
        w3     = _get_w3()
        latest = w3.eth.block_number
        now_ts = int(time.time())
        delta  = (max(0, now_ts - since_ts) // MANTLE_BLOCK_TIME) + 10
        from_b = max(0, latest - min(delta, RPC_BLOCK_LOOKBACK))
        logs   = w3.eth.get_logs({
            "fromBlock": from_b, "toBlock": latest,
            "address": Web3.to_checksum_address(pool_id),
            "topics": [SWAP_TOPIC],
        })
        buckets: dict = defaultdict(lambda: {"volumeUSD": 0.0, "txCount": 0, "senders": set()})
        for log in logs:
            s = _decode_swap_log(dict(log))
            if not s or s["timestamp"] < since_ts:
                continue
            bk = (s["timestamp"] // BUCKET_SIZE) * BUCKET_SIZE
            buckets[bk]["volumeUSD"] += s["amountUSD"]
            buckets[bk]["txCount"]   += 1
            buckets[bk]["senders"].add(s["sender"]["id"])
        return [{"bucketStart": bk, "txCount": b["txCount"],
                 "volumeUSD": round(b["volumeUSD"], 6), "uniqueSenders": len(b["senders"])}
                for bk, b in sorted(buckets.items())]
    except Exception as e:
        logger.error("[moe] fetch_tx_count_buckets failed %s: %s", pool_id, e)
        return []


def fetch_daily_snapshots(pool_id: str, days: int = 7) -> list:
    _ensure_pool_registry()
    try:
        w3       = _get_w3()
        latest   = w3.eth.block_number
        now_ts   = int(time.time())
        since_ts = now_ts - (days * 86400)
        from_b = max(0, latest - RPC_BLOCK_LOOKBACK)
        logs     = w3.eth.get_logs({
            "fromBlock": from_b, "toBlock": latest,
            "address": Web3.to_checksum_address(pool_id),
            "topics": [SWAP_TOPIC],
        })
        daily: dict = defaultdict(lambda: {"volumeUSD": 0.0, "txCount": 0})
        for log in logs:
            s = _decode_swap_log(dict(log))
            if not s or s["timestamp"] < since_ts:
                continue
            day = datetime.fromtimestamp(s["timestamp"], tz=timezone.utc).strftime("%Y-%m-%d")
            daily[day]["volumeUSD"] += s["amountUSD"]
            daily[day]["txCount"]   += 1
        return [{"date": day, "txCount": d["txCount"], "volumeUSD": round(d["volumeUSD"], 6)}
                for day in sorted(daily.keys(), reverse=True)[:days]]
    except Exception as e:
        logger.error("[moe] fetch_daily_snapshots failed %s: %s", pool_id, e)
        return []


def fetch_top_pools(limit: int = 20) -> list:
    _ensure_pool_registry()
    pools = list(_pool_registry.values())
    try:
        w3      = _get_w3()
        latest  = w3.eth.block_number
        since_b = max(0, latest - 4320)
        activity: dict = defaultdict(int)
        for addr in list(_pool_registry.keys())[:50]:
            logs = w3.eth.get_logs({
                "fromBlock": since_b, "toBlock": latest,
                "address": Web3.to_checksum_address(addr),
                "topics": [SWAP_TOPIC],
            })
            activity[addr] = len(logs)
        pools.sort(key=lambda p: activity.get(p["id"], 0), reverse=True)
    except Exception as e:
        logger.warning("[moe] fetch_top_pools sort failed: %s", e)
    return pools[:limit]
