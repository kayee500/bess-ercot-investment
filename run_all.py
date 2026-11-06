"""Reproduce every result, table and figure in the manuscript.

Usage:
    python run_all.py

Outputs are written to results/ (CSV and JSON) and figures/ (PNG and PDF).
"""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import numpy as np
import scipy

from bess_ercot import config, figures
from bess_ercot.analysis import (as_realisation_tests, benchmark, check_2026, contract_sensitivity,
                                 declining_revenue, deterministic_grid, spread_sensitivity, thresholds)
from bess_ercot.data_io import data_summary, load_market
from bess_ercot.dispatch import daily_margins
from bess_ercot.montecarlo import robustness, run_grid


def main() -> None:
    start = time.time()
    config.RESULTS_DIR.mkdir(exist_ok=True)
    out = {"software": {"python": sys.version.split()[0], "numpy": np.__version__, "scipy": scipy.__version__}}

    print("1/8 Loading ERCOT data")
    m25 = load_market(config.REFERENCE_YEAR)
    out["data_2025"] = data_summary(m25)

    print("2/8 Daily MILP dispatch, 2025 (365 problems)")
    sched, bench = benchmark(m25)
    sched.to_csv(config.RESULTS_DIR / "hourly_schedule_2025.csv", index=False)
    daily = daily_margins(sched)
    daily.to_csv(config.RESULTS_DIR / "daily_margins_2025.csv", index=False)
    out["benchmark_2025"] = bench
    gm, as_value = bench["energy_gross_margin"], bench["as_value_100pct"]

    print("3/8 Thresholds and deterministic grid (90 cases)")
    thr = thresholds(gm, as_value)
    out["thresholds"] = thr
    contracts = thr["contracts_full_as"]
    grid = deterministic_grid(gm, as_value, contracts)
    grid.to_csv(config.RESULTS_DIR / "deterministic_grid.csv", index=False)
    as_tests = as_realisation_tests(gm, as_value)
    as_tests.to_csv(config.RESULTS_DIR / "as_realisation_tests.csv", index=False)

    print("4/8 Sensitivities")
    spread = spread_sensitivity(m25)
    spread.to_csv(config.RESULTS_DIR / "spread_sensitivity.csv", index=False)
    contract_sens = contract_sensitivity(gm, as_value, contracts)
    contract_sens.to_csv(config.RESULTS_DIR / "contract_sensitivity.csv", index=False)
    decline = declining_revenue(gm, as_value, contracts)
    decline.to_csv(config.RESULTS_DIR / "declining_revenue.csv", index=False)

    print("5/8 Monte Carlo (90 cases x 10,000 draws)")
    mc = run_grid(daily, contracts)
    mc.to_csv(config.RESULTS_DIR / "montecarlo_grid.csv", index=False)
    # Hybrid recalibrated at the central (75%) ancillary-service realisation
    central = dict(contracts, Hybrid=thr["hybrid_contract_at_central_as"])
    mc_c = run_grid(daily, central)
    mc_c[mc_c["model"] == "Hybrid"].to_csv(config.RESULTS_DIR / "montecarlo_hybrid_central.csv", index=False)

    print("6/8 Monte Carlo robustness")
    rob = robustness(daily, contracts)
    rob.to_csv(config.RESULTS_DIR / "montecarlo_robustness.csv", index=False)

    print("7/8 Out-of-sample check, 2026 to date")
    m26 = load_market(config.CHECK_YEAR)
    out["data_2026"] = data_summary(m26)
    out["check_2026"] = check_2026(m26, m25)

    print("8/8 Figures")
    figures.figure1_framework()
    figures.figure2_ancillary(bench["as_value_by_service"])
    figures.figure3_spread(spread)
    figures.figure4_npv(grid)
    figures.figure5_montecarlo(mc)

    with open(config.RESULTS_DIR / "summary.json", "w") as f:
        json.dump(out, f, indent=2, default=float)
    print(f"Done in {time.time() - start:.0f} s. Results in {config.RESULTS_DIR}")


if __name__ == "__main__":
    main()
