# data_sources/moe.py — Merchant Moe LB 2.2 data source
# Queries unified custom subgraph for Moe swap data
# Moe uses discrete bin model (LB 2.2) — Poisson + RoC detection

import logging
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport
from config import SUBGRAPH_URL

logger = logging.getLogger(__name__)


def get_client() -> Client:
    transport = RequestsHTTPTransport(url=SUBGRAPH_URL, timeout=30)
    return Client(transport=transport, fetch_schema_from_transport=False)


# ── Queries ───────────────────────────────────────────────
QUERY_RECENT_SWAPS = gql("""
    query MoeRecentSwaps($since: BigInt!, $first: Int!) {
        swaps(
            where:          { dex: "moe", timestamp_gte: $since }
            orderBy:        timestamp
            orderDirection: desc
            first:          $first
        ) {
            id
            timestamp
            pool      { id token0Symbol token1Symbol txCount }
            sender    { id txCount isAgent agentTokenId }
            recipient { id }
            amountUSD
            txHash
        }
    }
""")

QUERY_TX_COUNT_BUCKETS = gql("""
    query MoeTxBuckets($poolId: String!, $since: BigInt!) {
        volumeBuckets(
            where:          { pool: $poolId, dex: "moe", bucketStart_gte: $since }
            orderBy:        bucketStart
            orderDirection: asc
        ) {
            bucketStart
            txCount
            volumeUSD
            uniqueSenders
        }
    }
""")

QUERY_DAILY_SNAPSHOTS = gql("""
    query MoeDailySnapshots($poolId: String!, $days: Int!) {
        dailyPoolSnapshots(
            where:          { pool: $poolId, dex: "moe" }
            orderBy:        date
            orderDirection: desc
            first:          $days
        ) {
            date
            txCount
            volumeUSD
        }
    }
""")

QUERY_TOP_POOLS = gql("""
    query MoeTopPools($first: Int!) {
        pools(
            where:          { dex: "moe" }
            orderBy:        txCount
            orderDirection: desc
            first:          $first
        ) {
            id
            token0Symbol
            token1Symbol
            txCount
            totalVolumeUSD
            lastSwapAt
        }
    }
""")


# ── Fetchers ──────────────────────────────────────────────
def fetch_recent_swaps(since_ts: int, limit: int = 500) -> list:
    """Fetch recent Moe swaps since timestamp."""
    try:
        client = get_client()
        result = client.execute(QUERY_RECENT_SWAPS, variable_values={
            "since": str(since_ts),
            "first": limit,
        })
        return result.get("swaps", [])
    except Exception as e:
        logger.error(f"[moe] fetch_recent_swaps failed: {e}")
        return []


def fetch_tx_count_buckets(pool_id: str, since_ts: int) -> list:
    """Fetch 15-min tx count buckets — used for Poisson + RoC detection."""
    try:
        client = get_client()
        result = client.execute(QUERY_TX_COUNT_BUCKETS, variable_values={
            "poolId": pool_id.lower(),
            "since": str(since_ts),
        })
        return result.get("volumeBuckets", [])
    except Exception as e:
        logger.error(f"[moe] fetch_tx_count_buckets failed: {e}")
        return []


def fetch_daily_snapshots(pool_id: str, days: int = 7) -> list:
    """Fetch daily snapshots for Poisson lambda baseline."""
    try:
        client = get_client()
        result = client.execute(QUERY_DAILY_SNAPSHOTS, variable_values={
            "poolId": pool_id.lower(),
            "days":   days,
        })
        return result.get("dailyPoolSnapshots", [])
    except Exception as e:
        logger.error(f"[moe] fetch_daily_snapshots failed: {e}")
        return []


def fetch_top_pools(limit: int = 20) -> list:
    """Fetch top Moe pools by tx count."""
    try:
        client = get_client()
        result = client.execute(QUERY_TOP_POOLS, variable_values={"first": limit})
        return result.get("pools", [])
    except Exception as e:
        logger.error(f"[moe] fetch_top_pools failed: {e}")
        return []