"""Deterministic investment metrics: NPV, IRR, discounted payback, LCOS and break-even payments."""

import numpy as np
from scipy.optimize import brentq

from . import config


def annuity_factor(rate: float, years: int = config.PROJECT_YEARS) -> float:
    return float(sum((1 + rate) ** -t for t in range(1, years + 1)))


def npv(capex: float, cash_flows, rate: float) -> float:
    """Eq. (7). ``cash_flows`` is a constant annual amount or a sequence for years 1..T."""
    cf = np.broadcast_to(np.asarray(cash_flows, dtype=float), (config.PROJECT_YEARS,))
    years = np.arange(1, config.PROJECT_YEARS + 1)
    return float(-capex + np.sum(cf / (1 + rate) ** years))


def irr(capex: float, annual_cash_flow: float) -> float | None:
    if annual_cash_flow * config.PROJECT_YEARS <= capex:
        return None
    return float(brentq(lambda r: npv(capex, annual_cash_flow, r), -0.99, 10.0))


def discounted_payback(capex: float, annual_cash_flow: float, rate: float) -> int | None:
    cumulative = -capex
    for t in range(1, config.PROJECT_YEARS + 1):
        cumulative += annual_cash_flow / (1 + rate) ** t
        if cumulative >= -1e-6:   # tolerance: break-even cases are zero up to rounding
            return t
    return None


def lcos(capex: float, charging_cost: float, discharged_mwh: float, rate: float) -> float:
    """Eq. (9): discounted cost (CAPEX, fixed O&M, charging) per discounted MWh discharged."""
    a = annuity_factor(rate)
    return (capex + a * (config.FIXED_OM + charging_cost)) / (a * discharged_mwh)


def gross_revenue_requirement(rate: float, capex: float = config.CAPEX) -> float:
    """Annual revenue (net of charging cost) needed for zero NPV."""
    return capex / annuity_factor(rate) + config.FIXED_OM


def model_revenues(model: str, energy_margin: float, as_value: float, as_realisation: float,
                   contracts: dict) -> tuple[float, float]:
    """Annual operating revenue (before fixed O&M) and CAPEX for a business model."""
    if model == "Merchant arbitrage":
        return energy_margin, config.CAPEX
    if model == "Merchant stacking":
        return energy_margin + as_realisation * as_value, config.CAPEX
    if model == "Contracted availability":
        return contracts["Contracted availability"], config.CAPEX
    if model == "Hybrid":
        return energy_margin + as_realisation * as_value + contracts["Hybrid"], config.CAPEX
    if model == "Renewable co-location":
        return energy_margin, config.CAPEX_COLOCATION
    if model == "Data-centre-linked":
        return energy_margin + contracts["Data-centre-linked"], config.CAPEX
    raise ValueError(model)


def break_even_contracts(energy_margin: float, as_value: float, rate: float = config.REFERENCE_RATE,
                         as_realisation: float = 1.0) -> dict:
    """Eq. (10): contract payments giving zero NPV in the reference market scenario."""
    req = gross_revenue_requirement(rate)
    return {
        "Contracted availability": req,
        "Hybrid": req - energy_margin - as_realisation * as_value,
        "Data-centre-linked": req - energy_margin,
    }
