"""Model assumptions used throughout the analysis.

Every number reported in the manuscript is produced from these values.
Change a value here and rerun ``run_all.py`` to regenerate all results.
"""

from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
RESULTS_DIR = ROOT / "results"
FIGURES_DIR = ROOT / "figures"

# ---------------------------------------------------------------------------
# Market data
# ---------------------------------------------------------------------------
SETTLEMENT_POINT = "HB_NORTH"          # ERCOT hub used for energy prices
REFERENCE_YEAR = 2025                  # complete reference market year
CHECK_YEAR = 2026                      # partial-year out-of-sample check
AS_PRODUCTS = ["REGDN", "REGUP", "RRS", "NSPIN", "ECRS"]
AS_NAMES = {
    "REGUP": "Regulation Up",
    "NSPIN": "Non-Spinning Reserve",
    "REGDN": "Regulation Down",
    "RRS": "Responsive Reserve",
    "ECRS": "ERCOT Contingency Reserve",
}

# ---------------------------------------------------------------------------
# Battery (1 MW / 4 MWh LFP)
# ---------------------------------------------------------------------------
POWER_MW = 1.0                         # charge and discharge power limit
NAMEPLATE_MWH = 4.0
DEPTH_OF_DISCHARGE = 0.80
USABLE_MWH = NAMEPLATE_MWH * DEPTH_OF_DISCHARGE   # 3.2 MWh
ROUND_TRIP_EFFICIENCY = 0.85
ETA = ROUND_TRIP_EFFICIENCY ** 0.5     # charge = discharge efficiency (92.20%)
DAILY_DISCHARGE_LIMIT_MWH = USABLE_MWH # max energy delivered to the grid per day (MWh)
MILP_REL_GAP = 1e-8

# ---------------------------------------------------------------------------
# Investment assumptions
# ---------------------------------------------------------------------------
CAPEX = 1_284_000.0                    # USD, reference installed cost
CAPEX_COLOCATION = 1_187_700.0         # USD, renewable co-location case
FIXED_OM = 14_880.0                    # USD per year
PROJECT_YEARS = 15
REFERENCE_RATE = 0.08
DISCOUNT_RATES = [0.05, 0.08, 0.10, 0.12, 0.15]

# Illustrative energy-price scenarios (applied to energy prices only)
PRICE_SCENARIOS = {"Low": 0.89, "Reference": 1.00, "High": 1.17}

# Ancillary-service realisation
AS_REALISATION_CENTRAL = 0.75
AS_REALISATION_TESTS = [0.40, 0.75, 1.00]

# Sensitivities
SPREAD_FACTORS = {"20% narrower": 0.80, "Observed": 1.00, "20% wider": 1.20}
REVENUE_DECLINE_RATES = [0.01, 0.02]
CONTRACT_PAYMENT_FACTORS = [0.80, 1.00, 1.20]

# ---------------------------------------------------------------------------
# Monte Carlo
# ---------------------------------------------------------------------------
MC_DRAWS = 10_000
MC_SEED = 20261012
MC_SIZES = [5_000, 10_000, 20_000]
# Triangular distributions: (minimum, mode, maximum)
COST_TRIANGLE = (0.85, 1.00, 1.20)            # CAPEX and fixed O&M multipliers
AS_REALISATION_TRIANGLE = (0.40, 0.75, 1.00)  # ancillary-service realisation
# Robustness: deviation from the mode is scaled by these factors (AS realisation clipped to 0-1)
UNCERTAINTY_WIDTHS = {"Narrower": 0.5, "Baseline": 1.0, "Wider": 1.5}

# Business models in reporting order
MODELS = [
    "Merchant arbitrage",
    "Merchant stacking",
    "Contracted availability",
    "Hybrid",
    "Renewable co-location",
    "Data-centre-linked",
]
