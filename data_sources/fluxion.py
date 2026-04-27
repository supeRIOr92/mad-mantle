# data_sources/fluxion.py — Fluxion (UniV3 fork) data source
# Queries unified custom subgraph
# Same detection as Agni: Z-Score + Bollinger

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
    query FluxionRecentSwaps($since: BigInt!, $first: Int!) {
        swaps(
            where:          { dex: "fluxion", timestamp_gte: $since }
            orderBy:        timestamp
            orderDirection: desc
            first:          $first
        ) {
            id
            timestamp
            pool      { id token0Symbol token1Symbol totalVolumeUSD txCount }
            sender    { id totalVolumeUSD txCount isAgent agentTokenId }
            recipient { id }
            amountUSD
            amount0
            amount1
            sqrtPriceX96
            tick
            txHash
        }
    }
""")

QUERY_VOLUME_BUCKETS = gql("""
    query FluxionBuckets($poolId: String!, $since: BigInt!) {
        volumeBuckets(
            where:          { pool: $poolId, dex: "fluxion", bucketStart_gte: $since }
            orderBy:        bucketStart
            orderDirection: asc
        ) {
            bucketStart
            volumeUSD
            txCount
            uniqueSenders
        }
    }
""")

QUERY_DAILY_SNAPSHOTS = gql("""
    query FluxionDailySnapshots($poolId: String!, $days: Int!) {
        dailyPoolSnapshots(
            where:          { pool: $poolId, dex: "fluxion" }
            orderBy:        date
            orderDirection: desc
            first:          $days
        ) {
            date
            volumeUSD
            txCount
            highVolumeUSD
            lowVolumeUSD
        }
    }
""")

QUERY_TOP_POOLS = gql("""
    query FluxionTopPools($first: Int!) {
        pools(
            where:          { dex: "fluxion" }
            orderBy:        totalVolumeUSD
            orderDirection: desc
            first:          $first
        ) {
            id
            token0Symbol
            token1Symbol
            feeTier
            totalVolumeUSD
            txCount
            lastSwapAt
        }
    }
""")


# ── Fetchers ──────────────────────────────────────────────
def fetch_recent_swaps(since_ts: int, limit: int = 500) -> list:
    """Fetch recent Fluxion swaps since timestamp."""
    try:
        client = get_client()
        result = client.execute(QUERY_RECENT_SWAPS, variable_values={
            "since": str(since_ts),
            "first": limit,
        })
        return result.get("swaps", [])
    except Exception as e:
        logger.error(f"[fluxion] fetch_recent_swaps failed: {e}")
        return []


def fetch_volume_buckets(pool_id: str, since_ts: int) -> list:
    """Fetch 15-min volume buckets for a pool."""
    try:
        client = get_client()
        result = client.execute(QUERY_VOLUME_BUCKETS, variable_values={
            "poolId": pool_id.lower(),
            "since": str(since_ts),
        })
        return result.get("volumeBuckets", [])
    except Exception as e:
        logger.error(f"[fluxion] fetch_volume_buckets failed: {e}")
        return []


def fetch_daily_snapshots(pool_id: str, days: int = 7) -> list:
    """Fetch daily snapshots for Bollinger baseline calculation."""
    try:
        client = get_client()
        result = client.execute(QUERY_DAILY_SNAPSHOTS, variable_values={
            "poolId": pool_id.lower(),
            "days":   days,
        })
        return result.get("dailyPoolSnapshots", [])
    except Exception as e:
        logger.error(f"[fluxion] fetch_daily_snapshots failed: {e}")
        return []


def fetch_top_pools(limit: int = 20) -> list:
    """Fetch top Fluxion pools by volume."""
    try:
        client = get_client()
        result = client.execute(QUERY_TOP_POOLS, variable_values={"first": limit})
        return result.get("pools", [])
    except Exception as e:
        logger.error(f"[fluxion] fetch_top_pools failed: {e}")
        return []