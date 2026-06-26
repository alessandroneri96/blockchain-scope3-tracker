"""
Record a new supply-chain transfer leg on the blockchain.

Input format (single comma-separated line):
  latSource, lonSource, latDest, lonDest, prevBatchId, newBatchId, batchSize[kg], transportMode

Transport modes: 0=TRUCK  1=AIRPLANE  2=SHIP

The Haversine great-circle distance between the two geographic coordinates is
computed locally and passed to the smart contract as an integer (km, rounded up).

Reference:
  Neri, A., Butturi, M. A., Bonini, F., Lolli, F., & Gamberini, R. (2024).
  Blockchain-based carbon emissions tracking in supply chains: A smart
  contract solution for scope 3 reporting.
  Summer School Francesco Turco — Proceedings, 1–6.
"""

import json
import math
import os
from dotenv import load_dotenv
from web3 import Web3

load_dotenv()

GANACHE_URL      = os.getenv("GANACHE_URL",      "http://127.0.0.1:7545")
CHAIN_ID         = int(os.getenv("CHAIN_ID",     "1337"))
MY_ADDRESS       = os.getenv("MY_ADDRESS")
PRIVATE_KEY      = os.getenv("PRIVATE_KEY")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")

if not all([MY_ADDRESS, PRIVATE_KEY, CONTRACT_ADDRESS]):
    raise EnvironmentError("Set MY_ADDRESS, PRIVATE_KEY, and CONTRACT_ADDRESS in .env")

with open("compiled_code.json") as f:
    data = json.load(f)
abi = data["contracts"]["BatchTracker.sol"]["BatchTracker"]["abi"]

w3 = Web3(Web3.HTTPProvider(GANACHE_URL))
assert w3.is_connected(), f"Cannot reach Ganache at {GANACHE_URL}"

contract  = w3.eth.contract(CONTRACT_ADDRESS, abi=abi)
nonce     = w3.eth.get_transaction_count(MY_ADDRESS)
gas_price = w3.eth.gas_price


def haversine_km(lat1, lon1, lat2, lon2) -> int:
    """Great-circle distance in km, rounded up (Solidity requires integers)."""
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return math.ceil(2 * math.asin(math.sqrt(a)) * 6371)


raw = input("Enter transfer data (latSource,lonSource,latDest,lonDest,prevID,newID,kg,mode): ")
vals = raw.split(",")
lat_s, lon_s, lat_d, lon_d = map(float, vals[:4])
prev_id, new_id = vals[4].strip(), vals[5].strip()
batch_size, transport_mode = int(vals[6]), int(vals[7])

distance = haversine_km(lat_s, lon_s, lat_d, lon_d)
print(f"Computed distance: {distance} km")

tx = contract.functions.addTransfer(
    new_id, prev_id, batch_size, distance, transport_mode
).build_transaction(
    {"chainId": CHAIN_ID, "from": MY_ADDRESS, "nonce": nonce,
     "gasPrice": gas_price, "gas": 6_721_975}
)
signed  = w3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
receipt = w3.eth.wait_for_transaction_receipt(
    w3.eth.send_raw_transaction(signed.raw_transaction)
)
print(f"Transfer recorded — tx: {receipt.transactionHash.hex()}")
