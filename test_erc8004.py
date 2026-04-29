from web3 import Web3

w3 = Web3(Web3.HTTPProvider("https://rpc.mantle.xyz"))
REGISTRY = "0x8004A169FB4a3325136EB29fA0ceB6D2e539a432"

# Test berbagai kemungkinan function name
tests = [
    ("totalSupply", [{"inputs":[],"name":"totalSupply","outputs":[{"name":"","type":"uint256"}],"stateMutability":"view","type":"function"}]),
    ("agentCount",  [{"inputs":[],"name":"agentCount","outputs":[{"name":"","type":"uint256"}],"stateMutability":"view","type":"function"}]),
    ("getAgentCount",[{"inputs":[],"name":"getAgentCount","outputs":[{"name":"","type":"uint256"}],"stateMutability":"view","type":"function"}]),
]

for name, abi in tests:
    try:
        c = w3.eth.contract(address=w3.to_checksum_address(REGISTRY), abi=abi)
        result = getattr(c.functions, name)().call()
        print(f"{name}(): {result}")
    except Exception as e:
        print(f"{name}(): ERROR — {e}")

# Test ownerOf dengan token_id 0
abi_owner = [{"inputs":[{"name":"tokenId","type":"uint256"}],"name":"ownerOf","outputs":[{"name":"","type":"address"}],"stateMutability":"view","type":"function"}]
c2 = w3.eth.contract(address=w3.to_checksum_address(REGISTRY), abi=abi_owner)
for tid in [0, 1, 2]:
    try:
        print(f"ownerOf({tid}):", c2.functions.ownerOf(tid).call())
    except Exception as e:
        print(f"ownerOf({tid}): ERROR — {e}")
