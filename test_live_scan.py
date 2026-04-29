"""
test_live_scan.py
Query swap events langsung dari Agni via RPC (bypass subgraph)
Feed ke detector.py untuk lihat score real pertama.
"""

import asyncio
import logging
from web3 import Web3
from detector import run_detection
from scorer import compute_final_score, get_alert_level

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(name)s — %(message)s")
logger = logging.getLogger("test_live_scan")

RPC_URL = "https://rpc.mantle.xyz"
AGNI_FACTORY = "0x25780dc8Fc3cfBD75F33bFDAB65e969b603b2035"

# Agni Factory — PoolCreated event to get pool addresses
FACTORY_ABI = [
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "token0", "type": "address"},
            {"indexed": True, "name": "token1", "type": "address"},
            {"indexed": True, "name": "fee", "type": "uint24"},
            {"indexed": False, "name": "tickSpacing", "type": "int24"},
            {"indexed": False, "name": "pool", "type": "address"},
        ],
        "name": "PoolCreated",
        "type": "event",
    }
]

# Agni Pool — Swap event
POOL_ABI = [
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True,  "name": "sender",       "type": "address"},
            {"indexed": True,  "name": "recipient",    "type": "address"},
            {"indexed": False, "name": "amount0",      "type": "int256"},
            {"indexed": False, "name": "amount1",      "type": "int256"},
            {"indexed": False, "name": "sqrtPriceX96", "type": "uint160"},
            {"indexed": False, "name": "liquidity",    "type": "uint128"},
            {"indexed": False, "name": "tick",         "type": "int24"},
            {"indexed": False, "name": "protocolFees0","type": "uint128"},
            {"indexed": False, "name": "protocolFees1","type": "uint128"},
        ],
        "name": "Swap",
        "type": "event",
    }
]

# Known active Agni pools (WMNT/USDT, WMNT/USDC, WETH/USDT)
KNOWN_POOLS = [
    "0xeAfc4D6d4c3391Cd4Fc10c85D2f5f972d58C0dD5",  # Agni WMNT/USDe $173K/day
]


def get_recent_swaps(pool_address: str, w3: Web3, blocks: int = 1000) -> list[dict]:
    try:
        latest = w3.eth.block_number
        from_block = latest - blocks

        # Normalize address
        pool_address = w3.to_checksum_address(pool_address.lower())

        contract = w3.eth.contract(
            address=pool_address,
            abi=POOL_ABI
        )

        events = contract.events.Swap.get_logs(
            from_block=from_block,
            to_block=latest
        )

        swaps = []
        for e in events:
            args = e["args"]
            amount0 = abs(args["amount0"])
            amount1 = abs(args["amount1"])
            amount_usd = float(w3.from_wei(max(amount0, amount1), "ether")) * 0.5

            swaps.append({
                "id":        e["transactionHash"].hex(),
                "sender":    args["sender"].lower(),
                "amountUSD": amount_usd,
                "amount0":   float(args["amount0"]),
                "amount1":   float(args["amount1"]),
                "timestamp": str(w3.eth.get_block(e["blockNumber"])["timestamp"]),
                "pool":      {"id": pool_address.lower()},
                "block":     e["blockNumber"],
            })

        logger.info(f"[pool {pool_address[:10]}...] {len(swaps)} swaps in last {blocks} blocks")
        return swaps

    except Exception as e:
        logger.error(f"get_recent_swaps failed for {pool_address[:10]}: {e}")
        return []

async def main():
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    if not w3.is_connected():
        logger.error("Cannot connect to Mantle RPC")
        return

    logger.info(f"Connected — block #{w3.eth.block_number}")

    all_swaps = []
    for pool in KNOWN_POOLS:
        swaps = get_recent_swaps(pool, w3, blocks=5000)
        all_swaps.extend(swaps)

    if not all_swaps:
        logger.warning("No swaps found — try increasing blocks range")
        return
    logger.info(f"Total swaps fetched: {len(all_swaps)}")

    # Group by pool for detection
    from collections import defaultdict
    pools: dict[str, list] = defaultdict(list)
    for s in all_swaps:
        pool_id = s["pool"]["id"]
        pools[pool_id].append(s)

    # Run detection per pool
    for pool_id, swaps in pools.items():
        logger.info(f"\n{'='*50}")
        logger.info(f"Pool: {pool_id[:20]}... | {len(swaps)} swaps")

        try:
            # Build minimal buckets dan daily_snapshots dari swaps
            from collections import defaultdict
            bucket: dict[str, float] = defaultdict(float)
            for s in swaps:
                bucket["volumeUSD"] += s["amountUSD"]
                bucket["txCount"] = bucket.get("txCount", 0) + 1
            buckets = [dict(bucket)]
            daily_snapshots = [{"volumeUSD": bucket["volumeUSD"], "txCount": bucket["txCount"]}]
            agent_map = {}  # empty for now

            result = await run_detection(
                dex             = "agni",
                pool_id         = pool_id,
                swaps           = swaps,
                buckets         = buckets,
                daily_snapshots = daily_snapshots,
                agent_map       = agent_map,
            )

            dex_results = [{"dex": "agni", "pool": pool_id, **result}]
            score_data = compute_final_score(dex_results)

            s_final = score_data.get("s_final", 0)
            level   = score_data.get("alert_level", "none")
            emoji   = "🔴" if level in ("ALERT","HIGH_CONF") else "🟡" if level == "WATCHING" else "🟢"

            logger.info(f"{emoji} Score: {s_final:.1f}/100 | Level: {level.upper()}")
            logger.info(f"   L1={score_data.get('l1_score',0):.1f} | L2={score_data.get('l2_score',0):.1f} | L3={score_data.get('l3_score',0):.1f}")
            logger.info(f"   wash_ratio={result.get('wash_ratio',0):.2f}x | cycle_count={result.get('cycle_count',0)}")

            wallet_vols: dict[str, float] = defaultdict(float)
            for s in swaps:
                wallet_vols[s["sender"]] += s["amountUSD"]
            top = sorted(wallet_vols.items(), key=lambda x: x[1], reverse=True)[:3]
            for w, vol in top:
                logger.info(f"   wallet {w[:12]}... | vol=${vol:,.0f}")

        except Exception as e:
            logger.error(f"Detection failed: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main())
