"""Deterministic analyses: benchmark, scenarios, business models and sensitivities."""

import numpy as np
import pandas as pd

from . import config
from .dispatch import add_ancillary_value, run_dispatch, spread_adjusted_prices, summarise
from .finance import (annuity_factor, break_even_contracts, discounted_payback,
                      gross_revenue_requirement, irr, lcos, model_revenues, npv)


def benchmark(market: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    sched = add_ancillary_value(run_dispatch(market))
    summary = summarise(sched)
    summary["lcos_ref"] = lcos(config.CAPEX, summary["charging_cost"], summary["discharged_mwh"],
                               config.REFERENCE_RATE)
    return sched, summary


def deterministic_grid(gm: float, as_value: float, contracts: dict) -> pd.DataFrame:
    """90 cases. Merchant stacking and hybrid use the full (100%) indicative AS value."""
    rows = []
    for scen, mult in config.PRICE_SCENARIOS.items():
        for model in config.MODELS:
            revenue, capex = model_revenues(model, gm * mult, as_value, 1.0, contracts)
            cf = revenue - config.FIXED_OM
            for rate in config.DISCOUNT_RATES:
                rows.append({"scenario": scen, "model": model, "rate": rate,
                             "annual_net_cash_flow": cf, "npv": npv(capex, cf, rate),
                             "irr": irr(capex, cf),
                             "discounted_payback_years": discounted_payback(capex, cf, rate)})
    return pd.DataFrame(rows)


def as_realisation_tests(gm: float, as_value: float) -> pd.DataFrame:
    rows = []
    for share in config.AS_REALISATION_TESTS:
        combined = gm + share * as_value
        rows.append({"realisation": share, "combined_gross_margin": combined,
                     "npv_8pct": npv(config.CAPEX, combined - config.FIXED_OM, config.REFERENCE_RATE)})
    return pd.DataFrame(rows)


def spread_sensitivity(market: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for label, factor in config.SPREAD_FACTORS.items():
        m = market.copy()
        m["price"] = spread_adjusted_prices(market, factor)
        gm = summarise(add_ancillary_value(run_dispatch(m)))["energy_gross_margin"]
        rows.append({"case": label, "factor": factor, "energy_gross_margin": gm,
                     "merchant_npv_8pct": npv(config.CAPEX, gm - config.FIXED_OM, config.REFERENCE_RATE)})
    return pd.DataFrame(rows)


def contract_sensitivity(gm: float, as_value: float, contracts: dict) -> pd.DataFrame:
    rows = []
    for model in ["Contracted availability", "Hybrid", "Data-centre-linked"]:
        for f in config.CONTRACT_PAYMENT_FACTORS:
            c = dict(contracts)
            c[model] = contracts[model] * f
            revenue, capex = model_revenues(model, gm, as_value, 1.0, c)
            rows.append({"model": model, "payment_factor": f, "annual_payment": c[model],
                         "npv_8pct": npv(capex, revenue - config.FIXED_OM, config.REFERENCE_RATE)})
    return pd.DataFrame(rows)


def declining_revenue(gm: float, as_value: float, contracts: dict) -> pd.DataFrame:
    """Merchant revenue (energy and AS) falls by g per year from year 2; contracts stay fixed."""
    years = np.arange(1, config.PROJECT_YEARS + 1)
    rows = []
    for g in config.REVENUE_DECLINE_RATES:
        path = (1 - g) ** (years - 1)
        cases = {
            "Merchant arbitrage": gm * path,
            "Merchant stacking": (gm + as_value) * path,
            "Hybrid": (gm + as_value) * path + contracts["Hybrid"],
            "Data-centre-linked": gm * path + contracts["Data-centre-linked"],
        }
        for model, revenue in cases.items():
            rows.append({"decline_rate": g, "model": model,
                         "npv_8pct": npv(config.CAPEX, revenue - config.FIXED_OM, config.REFERENCE_RATE)})
    return pd.DataFrame(rows)


def thresholds(gm: float, as_value: float) -> dict:
    req = gross_revenue_requirement(config.REFERENCE_RATE)
    full = break_even_contracts(gm, as_value, as_realisation=1.0)
    central = break_even_contracts(gm, as_value, as_realisation=config.AS_REALISATION_CENTRAL)
    return {"gross_revenue_requirement_8pct": req,
            "contracts_full_as": full,
            "hybrid_contract_at_central_as": central["Hybrid"],
            "annuity_factor_8pct": annuity_factor(config.REFERENCE_RATE)}


def check_2026(market_2026: pd.DataFrame, market_2025: pd.DataFrame) -> dict:
    """Out-of-sample check: 2026 to date against the same calendar period of 2025."""
    last = market_2026["Delivery Date"].max()
    same = market_2025[market_2025["Delivery Date"] <= last.replace(year=2025)]
    s26 = summarise(add_ancillary_value(run_dispatch(market_2026)))
    s25 = summarise(add_ancillary_value(run_dispatch(same)))
    return {
        "period_end": str(last.date()),
        "days": s26["days"],
        "2026": s26,
        "2025_same_period": s25,
        "mean_price_2026": float(market_2026["price"].mean()),
        "mean_price_2025_same_period": float(same["price"].mean()),
        "sd_price_2026": float(market_2026["price"].std()),
        "sd_price_2025_same_period": float(same["price"].std()),
    }
