# data_sources/moe_v2.py — Merchant Moe AMM (UniV2-style) data source
# REPLACES: moe.py (LB 2.2) — active pools are UniV2 format, not LB 2.2
#
# Verified onchain:
#   Swap topic: 0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822
#   Signature:  Swap(address sender, uint256 amount0In, uint256 amount1In,
#                    uint256 amount0Out, uint256 amount1Out, address to)
#   Active pool: 0x763868612858358f62b05691dB82Ad35a9b3E110 (MOE/WMNT)
#
# Detection: Z-Score + Bollinger (matching Fluxion — UniV2 microstructure)
# DEX name:  "moe" (unchanged — scorer weight 0.45 preserved)

import logging
import time
from collections import defaultdict
from datetime import datetime, timezone

from web3 import Web3
from eth_abi import decode as abi_decode

from config import MANTLE_RPC_URL, RPC_BLOCK_LOOKBACK

logger = logging.getLogger(__name__)

SWAP_TOPIC    = "0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822"
BUCKET_SIZE   = 15 * 60
MANTLE_BLOCK_TIME = 2

# UniV2 factory for Merchant Moe AMM
# Pools discovered via DexScreener + on-chain verification
FACTORY_ADDRESS = Web3.to_checksum_address("0x5757371414417b8C6CAad45bAeF941aBc7d3Ab32")

FACTORY_ABI = [
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True,  "name": "token0", "type": "address"},
            {"indexed": True,  "name": "token1", "type": "address"},
            {"indexed": False, "name": "pair",   "type": "address"},
            {"indexed": False, "name": "",        "type": "uint256"},
        ],
        "name": "PairCreated",
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
        factory = w3.eth.contract(address=FACTORY_ADDRESS, abi=FACTORY_ABI)
        events  = factory.events.PairCreated.get_logs(
            from_block=max(0, latest - 500_000), to_block=latest
        )
        for ev in events:
            pool_addr = ev["args"]["pair"].lower()
            m0 = _get_token_meta(ev["args"]["token0"])
            m1 = _get_token_meta(ev["args"]["token1"])
            _pool_registry[pool_addr] = {
                "id": pool_addr, "dex": "moe",
                "token0": ev["args"]["token0"].lower(),
                "token1": ev["args"]["token1"].lower(),
                "token0Symbol": m0["symbol"], "token1Symbol": m1["symbol"],
                "decimals0": m0["decimals"],  "decimals1": m1["decimals"],
                "feeTier": None, "txCount": 0, "totalVolumeUSD": 0.0, "lastSwapAt": None,
            }
        _registry_fetched_at = time.time()
        logger.info("[moe] registry loaded — %d pools", len(_pool_registry))
    except Exception as e:
        logger.error("[moe] registry fetch failed: %s", e)
        # Fallback: hardcode known active pool if factory discovery fails
        _seed_known_pools()
        _registry_fetched_at = time.time()


def _seed_known_pools():
    """Fallback: seed known active Moe AMM pools directly."""
    known = [
        {
            "address": "0x763868612858358f62b05691db82ad35a9b3e110",
            "token0":  "0x4515A45337F461A11Ff0FE8aBF3c606AE5dC00c9",  # MOE
            "token1":  "0x78c1b0C915c4FAA5FffA6CAbf0219DA63d7f4cb8",  # WMNT
        }
    ]
    for p in known:
        addr = p["address"].lower()
        if addr not in _pool_registry:
            m0 = _get_token_meta(p["token0"])
            m1 = _get_token_meta(p["token1"])
            _pool_registry[addr] = {
                "id": addr, "dex": "moe",
                "token0": p["token0"].lower(), "token1": p["token1"].lower(),
                "token0Symbol": m0["symbol"],  "token1Symbol": m1["symbol"],
                "decimals0": m0["decimals"],   "decimals1": m1["decimals"],
                "feeTier": None, "txCount": 0, "totalVolumeUSD": 0.0, "lastSwapAt": None,
            }
    logger.info("[moe] seeded %d known pools", len(_pool_registry))


def _decode_swap_log(log: dict) -> dict | None:
    """Decode UniV2-style Swap event."""
    try:
        pool_addr = log["address"].lower()
        meta = _pool_registry.get(pool_addr, {})

        raw_data = log["data"]
        if isinstance(raw_data, (bytes, bytearray)):
            data_bytes = bytes(raw_data)
        else:
            data_bytes = bytes.fromhex(str(raw_data).removeprefix("0x"))

        # UniV2 Swap: (uint256 amount0In, uint256 amount1In, uint256 amount0Out, uint256 amount1Out)
        amount0In, amount1In, amount0Out, amount1Out = abi_decode(
            ["uint256", "uint256", "uint256", "uint256"],
            data_bytes,
        )

        def topic_to_hex(t) -> str:
            if isinstance(t, (bytes, bytearray)):
                return t.hex()
            return str(t).removeprefix("0x")

        sender    = "0x" + topic_to_hex(log["topics"][1])[24:]
        recipient = "0x" + topic_to_hex(log["topics"][2])[24:]

        dec0, dec1 = meta.get("decimals0", 18), meta.get("decimals1", 18)

        # Volume = larger of in/out amounts (avoid double-counting)
        vol0 = max(amount0In, amount0Out) / (10 ** dec0)
        vol1 = max(amount1In, amount1Out) / (10 ** dec1)
        amount_usd = vol0 if vol0 > 0 else vol1

        # Timestamp
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
            "sender":    {"id": sender,    "txCount": 0, "isAgent": False, "agentTokenId": None},
            "recipient": {"id": recipient},
            "amountUSD": round(amount_usd, 6),
            "amount0In":  amount0In  / (10 ** dec0),
            "amount1In":  amount1In  / (10 ** dec1),
            "amount0Out": amount0Out / (10 ** dec0),
            "amount1Out": amount1Out / (10 ** dec1),
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
        from_b = max(0, latest - RPC_BLOCK_LOOKBACK)
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


def fetch_volume_buckets(pool_id: str, since_ts: int) -> list:
    _ensure_pool_registry()
    try:
        w3     = _get_w3()
        latest = w3.eth.block_number
        from_b = max(0, latest - RPC_BLOCK_LOOKBACK)
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
        return [{"bucketStart": bk, "volumeUSD": round(b["volumeUSD"], 6),
                 "txCount": b["txCount"], "uniqueSenders": len(b["senders"])}
                for bk, b in sorted(buckets.items())]
    except Exception as e:
        logger.error("[moe] fetch_volume_buckets failed %s: %s", pool_id, e)
        return []


def fetch_daily_snapshots(pool_id: str, days: int = 7) -> list:
    _ensure_pool_registry()
    try:
        w3       = _get_w3()
        latest   = w3.eth.block_number
        now_ts   = int(time.time())
        since_ts = now_ts - (days * 86400)
        from_b   = max(0, latest - RPC_BLOCK_LOOKBACK)
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
