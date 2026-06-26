# Blockchain Scope 3 Tracker

> **Immutable, per-batch Scope 3 carbon accounting on Ethereum — from any product's first shipment to its final destination.**

This repository contains the proof-of-concept smart contract and Python toolchain described in:

> Neri, A., Butturi, M. A., Bonini, F., Lolli, F., & Gamberini, R. (2024).
> **Blockchain-based carbon emissions tracking in supply chains: A smart contract solution for scope 3 reporting.**
> *Summer School Francesco Turco — Proceedings*, 1–6.

The system implements the **distance-based method** of the GHG Protocol (Category 4 — Upstream Transportation and Distribution). Every transport leg is recorded as an on-chain transaction: tamper-proof, traceable, and queryable by any downstream stakeholder holding the final batch ID.

---

## Why this matters

The EU Corporate Sustainability Reporting Directive (CSRD, 2022) requires companies to disclose **Scope 3** emissions — those occurring outside direct operational control — starting from 2025. Transport emissions alone can account for 70 %+ of an organisation's total carbon footprint, yet most ESG disclosures omit them entirely.

Traditional tracking methods rely on surveys across multi-tier suppliers, which are slow, incomplete, and hard to audit. A blockchain ledger solves this by letting each actor in the chain write their own leg autonomously: the data becomes collectively owned, individually unalterable, and instantly verifiable.

---

## How it works

### Smart contract — `BatchTracker.sol`

Each transfer leg is stored as a `Transfer` struct:

| Field           | Type     | Description                                    |
|-----------------|----------|------------------------------------------------|
| `newBatchId`    | string   | Identifier assigned after this leg             |
| `prevBatchId`   | string   | Identifier before this leg                     |
| `batchSize`     | uint256  | Batch weight (kg)                              |
| `distance`      | uint256  | Distance travelled (km)                        |
| `transportMode` | enum     | 0 = TRUCK \| 1 = AIRPLANE \| 2 = SHIP         |
| `co2Emissions`  | uint256  | Computed CO₂e (grams)                          |

CO₂ is calculated on-chain using the **distance-based method**:

```
CO₂ [g] = (distance [km] × emission_rate [g/km] × batchSize [kg]) / vehicle_capacity [kg]
```

| Mode     | Emission rate (g CO₂e/km) | Capacity (kg) |
|----------|--------------------------|---------------|
| Truck    | 123                      | 3 500         |
| Airplane | 1 012                    | 23 000        |
| Ship     | 10                       | 123 450       |

When a new leg is recorded, the contract copies the **full history** of the previous batch ID into the new one. This means any downstream actor — an OEM, an auditor, or a consumer — only needs the *final* batch ID to reconstruct the entire upstream chain.

### Python scripts

| Script                | Role                                                                  |
|-----------------------|-----------------------------------------------------------------------|
| `contractDeployer.py` | Compile `BatchTracker.sol` and deploy it to a Ganache blockchain      |
| `transferUpdater.py`  | Record one transfer leg; Haversine distance is computed from GPS coords |
| `pollutionViewer.py`  | Query and print the full CO₂ breakdown for any batch ID              |

---

## Illustrative example — ECU supply chain

The paper's case study traces a lot of **Electronic Control Units (ECUs)** from a Tier-1 manufacturer in Taiwan to an OEM in Stuttgart. The table below reproduces the multimodal logistics pathway from Table 1 of the paper.

```
🏭 Taiwan (manufacturing)
   └─ 🚛 Truck ──────────────────► 🚢 Port of Kaohsiung
       └─ 🚢 Ship ────────────────► ✈️ Hong Kong (trans-Pacific flight)
           └─ ✈️ Airplane ──────────────────────────────────► 🗽 New York
               ├─ 🚛 Truck ──────────────────────────────────► 🌁 San Francisco
               └─ 🚢 Ship ───────────────────────────────────► 🌷 Amsterdam
                   └─ ✈️  Airplane ─────────────────────────► 🚗 Stuttgart (OEM)
```

### Step-by-step usage

**1 — Deploy the contract** (run once by the supply chain manager):

```bash
python contractDeployer.py
# → Contract deployed at: 0x...
# Copy the address into .env as CONTRACT_ADDRESS
```

**2 — Record each leg** (run by the responsible actor at each handover):

```bash
python transferUpdater.py
# Input: latSource,lonSource,latDest,lonDest,prevID,newID,kg,mode

# Leg 1 — Taiwan manufacturing → Port of Kaohsiung (truck, 500 kg)
24.779137,120.991945,22.618577,120.274241,,TAY-UPNXR2024,500,0

# Leg 2 — Kaohsiung → Hong Kong (ship)
22.618577,120.274241,22.304858,114.215523,TAY-UPNXR2024,TAY-ZDIYJ2024,500,2

# Leg 3 — Hong Kong → New York (airplane)
22.304858,114.215523,40.991530,-73.656155,TAY-ZDIYJ2024,CHI-DFXKK2024,500,1

# Leg 4a — New York → San Francisco (truck, batch split: 250 kg)
40.991530,-73.656155,37.774929,-122.419416,CHI-DFXKK2024,USA-YRTOE2024,250,0

# Leg 4b — New York → Amsterdam (ship, 250 kg)
40.991530,-73.656155,52.359530,5.025779,CHI-DFXKK2024,EUR-TMHKU2024,250,2

# Leg 5 — Amsterdam → Stuttgart (airplane)
52.359530,5.025779,48.778953,9.157644,EUR-TMHKU2024,EUR-WDZKM2024,250,1
```

**3 — Query the full footprint** (accessible to the OEM or any auditor):

```bash
python pollutionViewer.py
# Enter the batch ID to view: EUR-WDZKM2024
```

```
──────────────────────────────────────────────────────────
  Scope 3 CO2 report  |  batch: EUR-WDZKM2024
──────────────────────────────────────────────────────────
  Leg  1:     74 km by Truck           1 300 g CO2e  ( 0.4%)
  Leg  2:    345 km by Ship               14 g CO2e  ( 0.0%)
  Leg  3:  12893 km by Airplane      284 482 g CO2e  (90.0%)
  Leg  4:   5817 km by Ship              118 g CO2e  ( 0.0%)
  Leg  5:    595 km by Airplane       13 638 g CO2e  ( 4.3%)
──────────────────────────────────────────────────────────
  TOTAL                               299 552 g CO2e
                                  ≈    299.55 kg CO2e
──────────────────────────────────────────────────────────
```

The air leg Hong Kong → New York dominates (~90 % of the total), consistent with the paper's findings. The OEM now has an **immutable, auditable Scope 3 record** — without requiring any single actor to share proprietary data beyond their own leg.

---

## Quick start

### Prerequisites

- [Ganache](https://trufflesuite.com/ganache/) — local Ethereum simulator, running on port 7545
- Python 3.9+

### Install

```bash
pip install -r requirements.txt
```

### Configure

```bash
cp .env.example .env
# Fill in MY_ADDRESS and PRIVATE_KEY from the Ganache GUI
```

### Run

```bash
python contractDeployer.py    # deploy; copy address into .env
python transferUpdater.py     # record a leg
python pollutionViewer.py     # query a batch
```

---

## Project structure

```
blockchain-scope3-tracker/
├── BatchTracker.sol          # Solidity smart contract
├── contractDeployer.py       # Compile & deploy
├── transferUpdater.py        # Record a transfer leg
├── pollutionViewer.py        # Query CO2 history
├── requirements.txt
├── .env.example              # Credential template (never commit .env)
├── .gitignore
└── LICENSE
```

---

## Limitations

As discussed in the paper, the current prototype has the following known limitations:

- Only the **distance-based** GHG Protocol method is implemented; fuel-based and spend-based methods are not yet supported.
- Emission factors are **indicative averages**; real deployments should integrate carrier-specific data.
- The system covers **upstream (Category 4)** emissions only; downstream distribution is out of scope.
- No IoT/sensor integration or user-facing interface; data entry is manual.
- Tested on a **local Ganache network**; deployment to a public or permissioned chain requires additional gas and access-control design.

---

## Citation

If you use this code in academic work, please cite:

```bibtex
@inproceedings{neri2024blockchain,
  author    = {Neri, Alessandro and Butturi, Maria Angela and Bonini, Francesco
               and Lolli, Francesco and Gamberini, Rita},
  title     = {Blockchain-based carbon emissions tracking in supply chains:
               {A} smart contract solution for scope 3 reporting},
  booktitle = {Summer School Francesco Turco -- Proceedings},
  pages     = {1--6},
  year      = {2024}
}
```

See [LICENSE](LICENSE) for full terms.

---

## Funding

This project was partially funded under the National Recovery and Resilience Plan (NRRP), Mission 04 Component 2 Investment 1.5 — NextGenerationEU (Award No. 0001052, 23 June 2022), and partially by ESF REACT-EU — PON "Ricerca e Innovazione" 2014–2020 (DM 1062, 10 August 2021).

---

*University of Bologna — Department of Industrial Engineering*
*University of Modena and Reggio Emilia — Department of Sciences and Methods for Engineering*
