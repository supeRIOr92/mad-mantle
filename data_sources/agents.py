# data_sources/agents.py — ERC-8004 Identity + Reputation Registry
# 92 agents on Mantle (as of v5.1)
# Calls: ownerOf() + getReputation() on-chain

import logging
from web3 import Web3
from config import (
    MANTLE_RPC_URL,
    ERC8004_IDENTITY_REGISTRY,
    ERC8004_REPUTATION_REGISTRY,
    AGENT_COUNT_MANTLE,
    ERC8004_HIGH_RISK_THRESHOLD,
)

logger = logging.getLogger(__name__)

# ── ABIs (minimal) ────────────────────────────────────────
IDENTITY_ABI = [
    {
        "inputs": [{"name": "tokenId", "type": "uint256"}],
        "name": "ownerOf",
        "outputs": [{"name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"name": "tokenId", "type": "uint256"}],
        "name": "tokenURI",
        "outputs": [{"name": "", "type": "string"}],
        "stateMutability": "view",
        "type": "function",
    },
]

REPUTATION_ABI = [
    {
        "inputs": [{"name": "tokenId", "type": "uint256"}],
        "name": "getReputation",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
]


# ── Web3 Setup ────────────────────────────────────────────
def get_web3() -> Web3:
    w3 = Web3(Web3.HTTPProvider(MANTLE_RPC_URL))
    if not w3.is_connected():
        raise ConnectionError(f"Cannot connect to Mantle RPC: {MANTLE_RPC_URL}")
    return w3


def get_identity_contract(w3: Web3):
    return w3.eth.contract(
        address=Web3.to_checksum_address(ERC8004_IDENTITY_REGISTRY),
        abi=IDENTITY_ABI,
    )


def get_reputation_contract(w3: Web3):
    return w3.eth.contract(
        address=Web3.to_checksum_address(ERC8004_REPUTATION_REGISTRY),
        abi=REPUTATION_ABI,
    )


# ── Fetchers ──────────────────────────────────────────────
def fetch_agent_owner(token_id: int) -> str | None:
    """Get wallet address that owns a given ERC-8004 token."""
    try:
        w3 = get_web3()
        contract = get_identity_contract(w3)
        owner = contract.functions.ownerOf(token_id).call()
        return owner.lower()
    except Exception as e:
        logger.error(f"[agents] ownerOf({token_id}) failed: {e}")
        return None


def fetch_agent_reputation(token_id: int) -> float | None:
    """Get reputation score for a given ERC-8004 token."""
    try:
        w3 = get_web3()
        contract = get_reputation_contract(w3)
        score = contract.functions.getReputation(token_id).call()
        return float(score)
    except Exception as e:
        logger.error(f"[agents] getReputation({token_id}) failed: {e}")
        return None


def fetch_all_agents(max_id: int = None) -> list[dict]:
    """
    Scan all known agent token IDs and return owner + reputation.
    Uses AGENT_COUNT_MANTLE as upper bound if max_id not provided.
    """
    max_id = max_id or AGENT_COUNT_MANTLE
    w3 = get_web3()
    identity = get_identity_contract(w3)
    reputation = get_reputation_contract(w3)

    agents = []
    for token_id in range(1, max_id + 1):
        try:
            owner = identity.functions.ownerOf(token_id).call().lower()
            score = float(reputation.functions.getReputation(token_id).call())
            agents.append({
                "token_id": str(token_id),
                "owner_address": owner,
                "reputation_score": score,
                "is_high_risk": score < ERC8004_HIGH_RISK_THRESHOLD,
            })
        except Exception:
            # Token may not exist yet — skip silently
            continue

    logger.info(f"[agents] Fetched {len(agents)} agents (scanned 1–{max_id})")
    return agents


def build_agent_map(agents: list[dict]) -> dict:
    """
    Returns dict: { wallet_address: { token_id, reputation_score, is_high_risk } }
    For fast O(1) lookup during L2 scoring.
    """
    return {
        a["owner_address"]: {
            "token_id": a["token_id"],
            "reputation_score": a["reputation_score"],
            "is_high_risk": a["is_high_risk"],
        }
        for a in agents
    }


def is_high_risk_agent(wallet: str, agent_map: dict) -> bool:
    """Check if wallet is a high-risk agent (reputation < threshold)."""
    entry = agent_map.get(wallet.lower())
    if not entry:
        return False
    return entry["is_high_risk"]

# ── Aliases for wallet_profiler.py compatibility ──────────
def get_agent_identity(wallet: str) -> dict | None:
    """
    Returns identity dict if wallet owns an ERC-8004 token, else None.
    Used by wallet_profiler.py for agent classification.
    """
    # Requires agent_map — used in build_agent_map context
    # Standalone lookup: scan all tokens to find owner match
    try:
        w3 = get_web3()
        identity = get_identity_contract(w3)
        for token_id in range(1, AGENT_COUNT_MANTLE + 1):
            try:
                owner = identity.functions.ownerOf(token_id).call().lower()
                if owner == wallet.lower():
                    return {"token_id": str(token_id), "owner": owner}
            except Exception:
                continue
    except Exception as e:
        logger.debug("get_agent_identity failed for %s: %s", wallet, e)
    return None

def get_agent_reputation(wallet: str) -> dict | None:
    """
    Returns reputation dict for wallet if registered as ERC-8004 agent.
    Used by wallet_profiler.py for rep score lookup.
    """
    identity = get_agent_identity(wallet)
    if not identity:
        return None
    try:
        token_id = int(identity["token_id"])
        score = fetch_agent_reputation(token_id)
        if score is not None:
            return {"score": score, "token_id": str(token_id)}
    except Exception as e:
        logger.debug("get_agent_reputation failed for %s: %s", wallet, e)
    return None
