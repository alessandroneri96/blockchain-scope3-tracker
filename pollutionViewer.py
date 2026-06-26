"""
Query the full Scope 3 CO2 footprint of a batch by its current batch ID.

Any downstream actor holding the final batch ID can retrieve the complete
upstream emission history — no prior knowledge of intermediate IDs required.

Reference:
  Neri, A., Butturi, M. A., Bonini, F., Lolli, F., & Gamberini, R. (2024).
  Blockchain-based carbon emissions tracking in supply chains: A smart
  contract solution for scope 3 reporting.
  Summer School Francesco Turco — Proceedings, 1–6.
"""

import json
import os
from dotenv import load_dotenv
from web3 import Web3

load_dotenv()

GANACHE_URL      = os.getenv("GANACHE_URL",      "http://127.0.0.1:7545")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")

if not CONTRACT_ADDRESS:
    raise EnvironmentError("Set CONTRACT_ADDRESS in .env")

with open("compiled_code.json") as f:
    data = json.load(f)
abi = data["contracts"]["BatchTracker.sol"]["BatchTracker"]["abi"]

w3 = Web3(Web3.HTTPProvider(GANACHE_URL))
assert w3.is_connected(), f"Cannot reach Ganache at {GANACHE_URL}"

contract = w3.eth.contract(CONTRACT_ADDRESS, abi=abi)

batch_id = input("Enter the batch ID to view: ").strip()
history  = contract.functions.getBatchHistory(batch_id).call()

if not history:
    print(f"No records found for batch ID '{batch_id}'.")
else:
    MODE_LABEL = {0: "Truck", 1: "Airplane", 2: "Ship"}
    total_co2 = 0
    print(f"\n{'─'*58}")
    print(f"  Scope 3 CO2 report  |  batch: {batch_id}")
    print(f"{'─'*58}")
    for i, leg in enumerate(history, start=1):
        mode = MODE_LABEL.get(leg[4], "Unknown")
        co2  = leg[5]
        total_co2 += co2
        pct = co2 / max(sum(l[5] for l in history), 1) * 100
        print(f"  Leg {i:>2}: {leg[3]:>6} km by {mode:<9}  {co2:>10} g CO2e  ({pct:4.1f}%)")
    print(f"{'─'*58}")
    print(f"  TOTAL                             {total_co2:>10} g CO2e")
    print(f"                                 ≈  {total_co2/1000:>9.2f} kg CO2e")
    print(f"{'─'*58}\n")
