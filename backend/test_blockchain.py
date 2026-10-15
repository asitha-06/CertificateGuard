
import os
import json
from dotenv import load_dotenv
from web3 import Web3

load_dotenv(override=True)

rpc = os.getenv("SEPOLIA_RPC_URL")
address = os.getenv("CONTRACT_ADDRESS")

if not rpc:
    print("ERROR: SEPOLIA_RPC_URL is empty")
    raise SystemExit(1)

if not address:
    print("ERROR: CONTRACT_ADDRESS is empty")
    raise SystemExit(1)

try:
    w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": 15}))

    print("RPC connected:", w3.is_connected())

    if not w3.is_connected():
        raise RuntimeError("Could not connect to the RPC endpoint")

    print("Chain ID:", w3.eth.chain_id)

    if w3.eth.chain_id != 11155111:
        raise RuntimeError("The endpoint is not connected to Sepolia")

    address = Web3.to_checksum_address(address)
    code = w3.eth.get_code(address)
    print("Contract bytecode length:", len(code))

    if not code:
        raise RuntimeError("No contract bytecode at this address")

    with open("ImageVerification_ABI.json", encoding="utf-8") as f:
        abi = json.load(f)

    contract = w3.eth.contract(address=address, abi=abi)

    try:
        print("Contract owner:", contract.functions.owner().call())
    except Exception as e:
        print("owner() failed:", type(e).__name__, str(e)[:200])

    try:
        record = contract.functions.getImageRecord(
            "certificateguard-test"
        ).call()
        print("Test record exists:", record[-1])
    except Exception as e:
        print("getImageRecord() failed:", type(e).__name__, str(e)[:200])

except Exception as e:
    print("TEST ERROR:", type(e).__name__, str(e)[:300])
