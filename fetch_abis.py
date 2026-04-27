# fetch_abis.py — Auto-fetch ABIs from MantleScan
# Run once: python fetch_abis.py
# Saves all ABIs to subgraph/abis/

import os
import json
import requests
import time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

MANTLESCAN_API_KEY = os.getenv("MANTLESCAN_API_KEY", "")
BASE_URL = "https://api.etherscan.io/v2/api"
ABI_DIR = Path("subgraph/abis")

# ── Contracts to fetch ────────────────────────────────────
CONTRACTS = [
    {
        "name": "AgniFactory",
        "address": "0x25780dc8Fc3cfBD75F33bFDAB65e969b603b2035",
    },
    {
        "name": "MoeLBFactory",
        "address": "0xa6630671775c4EA2743840F9A5016dCf2A104054",
    },
    {
        "name": "FluxionFactory",
        "address": "0x560d064493de5a23e72ed916caf92ec6e8924948",
    },
    {
        "name": "ERC8004IdentityRegistry",
        "address": "0x8004A169FB4a3325136EB29fA0ceB6D2e539a432",
    },
    {
        "name": "ERC8004ReputationRegistry",
        "address": "0x8004BAa17C55a88189AE136b182e5fdA19dE9b63",
    },
]

# Pool ABIs — fetch from a known deployed pool address
# These share ABI with all other pools of the same DEX
POOL_CONTRACTS = [
    {
    "name": "AgniPool",
    "address": "0x8e2c009e45420d2b36bc15315f9de8ceca2cc724",
    },
    {
    "name": "MoeLBPair",
    "address": "0x48c1a89af1102cad358549e9bb16ae5f96cddfec", # USDC/USDT
    },
    {
    "name": "FluxionPool",
    "address": "", # masih perlu — cari di fluxion.finance
    },
]


def fetch_abi(name: str, address: str) -> dict | None:
    """Fetch verified ABI from MantleScan."""
    params = {
        "module": "contract",
        "action": "getabi",
        "address": address,
        "apikey": MANTLESCAN_API_KEY, "chainid": 5000,
    }

    try:
        resp = requests.get(BASE_URL, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        if data.get("status") == "1":
            abi = json.loads(data["result"])
            print(f"  ✅ {name} ({address[:10]}...) — {len(abi)} entries")
            return abi
        else:
            msg = data.get("result", "unknown error")
            print(f"  ❌ {name} — {msg}")
            return None

    except Exception as e:
        print(f"  ❌ {name} — request failed: {e}")
        return None


def save_abi(name: str, abi: list):
    """Save ABI to subgraph/abis/<name>.json"""
    path = ABI_DIR / f"{name}.json"
    with open(path, "w") as f:
        json.dump(abi, f, indent=2)
    print(f"  💾 Saved: {path}")


def filter_abi_for_subgraph(abi: list, event_names: list[str]) -> list:
    """
    Extract only relevant events + functions from full ABI.
    Keeps: specified events + all functions.
    Reduces file size for subgraph compilation.
    """
    filtered = []
    for item in abi:
        if item.get("type") == "event" and item.get("name") in event_names:
            filtered.append(item)
        elif item.get("type") in ("function", "constructor", "fallback", "receive"):
            filtered.append(item)
    return filtered


# ── Event filters per contract ────────────────────────────
EVENTS_FILTER = {
    "AgniFactory": ["PoolCreated"],
    "AgniPool": ["Swap", "Mint", "Burn", "Initialize"],
    "MoeLBFactory": ["LBPairCreated"],
    "MoeLBPair": ["Swap", "DepositedToBins", "WithdrawnFromBins"],
    "FluxionFactory": ["PoolCreated"],
    "FluxionPool": ["Swap", "Mint", "Burn", "Initialize"],
}


def main():
    print("\n🔍 RealClaw — ABI Fetcher")
    print(f"📁 Output dir: {ABI_DIR.resolve()}\n")

    # Create abis dir
    ABI_DIR.mkdir(parents=True, exist_ok=True)

    all_contracts = CONTRACTS + [c for c in POOL_CONTRACTS if c["address"]]
    success = 0
    failed = 0

    for contract in all_contracts:
        name = contract["name"]
        address = contract["address"]

        if not address:
            print(f"  ⏭ {name} — no address provided, skipping")
            continue

        print(f"\nFetching {name}...")
        abi = fetch_abi(name, address)

        if abi:
            # Filter to relevant events only
            events = EVENTS_FILTER.get(name, [])
            if events:
                filtered = filter_abi_for_subgraph(abi, events)
                save_abi(name, filtered)
            else:
                save_abi(name, abi)
            success += 1
        else:
            failed += 1

        # Rate limit — MantleScan free tier: 5 req/sec
        time.sleep(0.3)

    print(f"\n{'='*50}")
    print(f"✅ Success: {success} | ❌ Failed: {failed}")
    print(f"\n⚠️ Pool ABIs with empty address — fill in POOL_CONTRACTS manually:")
    for c in POOL_CONTRACTS:
        if not c["address"]:
            print(f"  • {c['name']} — needs a deployed pool address")
    print(f"\nNext: find pool addresses at https://api.etherscan.io/v2/api")
    print(f"  Agni pools: search 'Agni' or check app.agni.finance")
    print(f"  Moe pairs: check merchantmoe.com/pools")
    print(f"  Fluxion: check fluxion.finance\n")


if __name__ == "__main__":
    main()
