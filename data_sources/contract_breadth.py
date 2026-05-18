"""
contract_breadth.py
Layer 3 AI Agent Detection — Contract Interaction Breadth
Queries eth_getLogs to detect multi-protocol behavior within a scan window.
"""

import logging
import json
import urllib.request

from config import MANTLE_RPC_URL

logger = logging.getLogger(__name__)

CONTRACT_REGISTRY = {
    "dex_router": [
        "0xeaee7ee68874218c3558b40063c42b82d3e7232a",
        "0x013e138ef6008ae5fdfde29700e3f2bc61d21e3a",
        "0x45a62b090df48243f12a21897e7ed91863e2c86b",
        "0x5628a59df0ecac3f3171f877a94beb26ba6dfaa0",
        "0xd772e655af24fe5af92504d613d1da0d9cfb6408",
        "0x319b69888b0d11cec22caa5034e25fffbdc88421",
        "0xb52b1f5e08c04a8c33f4c7363fa2de23b9bc169f",
    ],
    "position_mgmt": [
        "0xd4bd5e47548d8a6ba2a0bf4ce073cbf8fa523dcc",
        "0xe92249760e1443fbbea45b03f607ba84471fa793",
        "0x2b70c4e7ca8e920435a5db191e066e9e3afd8db3",
    ],
    "lending": [
        "0x458f293454fe0d67ec0655f3672301301dd51422",
        "0x9c6ccac66b1c9aba4855e2dd284b9e16e41e06ea",
    ],
    "synthetic": [
        "0x96702be57cd9777f835117a809c7124fe4ec989a",
        "0xe92f673ca36c5e2efd2de7628f815f84807e803f",
        "0xc845b2894dbddd03858fd2d643b4ef725fe0849d",
        "0xa753a7395cae905cd615da0b82a53e0560f250af",
        "0x9d275685dc284c8eb1c79f6aba7a63dc75ec890a",
        "0x90a2a4c76b5d8c0bc892a69ea28aa775a8f2dd48",
        "0xae2f842ef90c0d5213259ab82639d5bbf649b08e",
    ],
}

_ADDRESS_TO_CATEGORY: dict[str, str] = {}
for _cat, _addrs in CONTRACT_REGISTRY.items():
    for _addr in _addrs:
        _ADDRESS_TO_CATEGORY[_addr.lower()] = _cat

ALL_CONTRACT_ADDRESSES = [
    a for a in _ADDRESS_TO_CATEGORY.keys()
    if len(a) == 42 and a.startswith("0x")
]

def _rpc_call(payload: dict) -> dict:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        MANTLE_RPC_URL,
        data=data,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def get_contract_breadth(wallet: str, from_block: int, to_block: int) -> dict:
    wallet_lower = wallet.lower()
    result = {
        "contract_breadth": 0,
        "breadth_categories": [],
        "breadth_contracts": [],
    }

    try:
        payload = {
            "jsonrpc": "2.0",
            "method": "eth_getLogs",
            "params": [{
                "fromBlock": hex(from_block),
                "toBlock": hex(to_block),
                "address": ALL_CONTRACT_ADDRESSES,
            }],
            "id": 1,
        }

        response = _rpc_call(payload)

        if "error" in response:
            logger.warning("[breadth] eth_getLogs error: %s", response["error"])
            return result

        logs = response.get("result", [])
        categories_hit = set()
        contracts_hit = set()

        for log in logs:
            contract_addr = log.get("address", "").lower()
            topics = log.get("topics", [])
            wallet_in_topics = False

            for topic in topics[1:]:
                if topic and len(topic) == 66:
                    if ("0x" + topic[-40:]).lower() == wallet_lower:
                        wallet_in_topics = True
                        break

            if wallet_in_topics and contract_addr in _ADDRESS_TO_CATEGORY:
                categories_hit.add(_ADDRESS_TO_CATEGORY[contract_addr])
                contracts_hit.add(contract_addr)

        result["contract_breadth"] = len(categories_hit)
        result["breadth_categories"] = sorted(categories_hit)
        result["breadth_contracts"] = sorted(contracts_hit)

    except Exception as e:
        logger.debug("[breadth] failed for %s: %s", wallet, e)

    return result
