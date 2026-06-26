"""
Deploy BatchTracker to a local Ganache instance.

Credentials are read from a .env file — never hardcode keys in source.
Copy .env.example to .env and fill in your Ganache values before running.

Reference:
  Neri, A., Butturi, M. A., Bonini, F., Lolli, F., & Gamberini, R. (2024).
  Blockchain-based carbon emissions tracking in supply chains: A smart
  contract solution for scope 3 reporting.
  Summer School Francesco Turco — Proceedings, 1–6.
"""

import json
import os
from dotenv import load_dotenv
from solcx import compile_standard, install_solc
from web3 import Web3

load_dotenv()

GANACHE_URL = os.getenv("GANACHE_URL", "http://127.0.0.1:7545")
CHAIN_ID    = int(os.getenv("CHAIN_ID", "1337"))
MY_ADDRESS  = os.getenv("MY_ADDRESS")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")

if not MY_ADDRESS or not PRIVATE_KEY:
    raise EnvironmentError("Set MY_ADDRESS and PRIVATE_KEY in your .env file.")

# ── Compile ──────────────────────────────────────────────────────────────────
with open("BatchTracker.sol", "r") as f:
    source = f.read()

print("Installing Solidity 0.8.0 compiler …")
install_solc("0.8.0")

compiled_sol = compile_standard(
    {
        "language": "Solidity",
        "sources": {"BatchTracker.sol": {"content": source}},
        "settings": {
            "outputSelection": {
                "*": {"*": ["abi", "metadata", "evm.bytecode", "evm.sourceMap"]}
            }
        },
    },
    solc_version="0.8.0",
)

with open("compiled_code.json", "w") as f:
    json.dump(compiled_sol, f)
print("Contract compiled → compiled_code.json")

bytecode = compiled_sol["contracts"]["BatchTracker.sol"]["BatchTracker"]["evm"]["bytecode"]["object"]
abi      = compiled_sol["contracts"]["BatchTracker.sol"]["BatchTracker"]["abi"]

# ── Deploy ───────────────────────────────────────────────────────────────────
w3 = Web3(Web3.HTTPProvider(GANACHE_URL))
assert w3.is_connected(), f"Cannot reach Ganache at {GANACHE_URL}"

contract = w3.eth.contract(abi=abi, bytecode=bytecode)
nonce    = w3.eth.get_transaction_count(MY_ADDRESS)

tx = contract.constructor().build_transaction(
    {"chainId": CHAIN_ID, "from": MY_ADDRESS, "nonce": nonce}
)
signed  = w3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

print(f"\nContract deployed at: {receipt.contractAddress}")
print("Copy this address into your .env as CONTRACT_ADDRESS=<address>")
