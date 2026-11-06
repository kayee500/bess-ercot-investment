"""Monte Carlo uncertainty analysis and robustness tests (Section 2.8).

The random-number sequence follows the authors' original scripts exactly
(rebuild_ercot_financial.py and ercot_three_robustness_checks.py), so the
published probabilities reproduce to the last digit:

* Main analysis: one set of draws (seed 20261012) is generated in the order
  day indices, CAPEX multiplier, O&M multiplier, AS realisation, and is reused
  for every scenario, business model and discount rate (common random numbers).
* Robustness: each test restarts the generator from the same seed and draws
  in chunks of 1,000.
"""

import numpy as np
import pandas as pd

from . import config
from .finance import annuity_factor, model_revenues


def draw_inputs(daily: pd.DataFrame, n: int = config.MC_DRAWS, seed: int = config.MC_SEED) -> dict:
    """Paired daily bootstrap of annual revenues and triangular cost/realisation multipliers."""
    rng = np.random.default_rng(seed)
    margin = daily["energy_margin"].to_numpy()
    as_val = daily["as_value"].to_numpy()
    idx = rng.integers(0, len(daily), size=(n, len(daily)), dtype=np.int16)   # same-day pairs
    energy = margin[idx].sum(axis=1)
    ancillary = as_val[idx].sum(axis=1)
    del idx
    lo, mode, hi = config.COST_TRIANGLE
    capex_mult = rng.triangular(lo, mode, hi, size=n)
    om_mult = rng.triangular(lo, mode, hi, size=n)
    lo, mode, hi = config.AS_REALISATION_TRIANGLE
    as_real = rng.triangular(lo, mode, hi, size=n)
    return {"energy": energy, "ancillary": ancillary, "capex_mult": capex_mult,
            "om_mult": om_mult, "as_real": as_real}


def simulate_npv(inputs: dict, model: str, price_mult: float, rate: float, contracts: dict) -> np.ndarray:
    revenue, capex = model_revenues(model, inputs["energy"] * price_mult, inputs["ancillary"],
                                    inputs["as_real"], contracts)
    net = revenue - config.FIXED_OM * inputs["om_mult"]
    return -capex * inputs["capex_mult"] + annuity_factor(rate) * net


def summarise_npv(values: np.ndarray) -> dict:
    return {
        "median_npv": float(np.median(values)),
        "p05_npv": float(np.percentile(values, 5)),
        "p95_npv": float(np.percentile(values, 95)),
        "prob_positive": float((values > 0).mean()),
    }


def run_grid(daily: pd.DataFrame, contracts: dict, n: int = config.MC_DRAWS) -> pd.DataFrame:
    """All scenario x model x discount-rate combinations (90 cases), common random numbers."""
    inputs = draw_inputs(daily, n)
    rows = []
    for scen, mult in config.PRICE_SCENARIOS.items():
        for model in config.MODELS:
            for rate in config.DISCOUNT_RATES:
                vals = simulate_npv(inputs, model, mult, rate, contracts)
                rows.append({"scenario": scen, "model": model, "rate": rate, **summarise_npv(vals)})
    return pd.DataFrame(rows)


def robustness(daily: pd.DataFrame, contracts: dict, rate: float = config.REFERENCE_RATE) -> pd.DataFrame:
    """Uncertainty width x revenue persistence x simulation size, for two cases.

    Width scales each triangular distribution's deviation from its mode
    (0.5 = narrower, 1.0 = baseline, 1.5 = wider); AS realisation is clipped to [0, 1].
    'independent_annual_draws' resamples a new year of days for each of the 15 years.
    """
    ed = daily["energy_margin"].to_numpy()
    md = daily["as_value"].to_numpy()
    disc = np.array([(1 + rate) ** (-y) for y in range(1, config.PROJECT_YEARS + 1)])
    ann = annuity_factor(rate)
    cases = [("High data-centre", config.PRICE_SCENARIOS["High"], "Data-centre-linked", False),
             ("Reference hybrid", config.PRICE_SCENARIOS["Reference"], "Hybrid", True)]
    c_lo, c_mode, c_hi = config.COST_TRIANGLE
    a_lo, a_mode, a_hi = config.AS_REALISATION_TRIANGLE
    rows = []
    for name, factor, model, has_as in cases:
        contract = contracts[model]
        for temporal in ["persistent_15_years", "independent_annual_draws"]:
            years = 1 if temporal == "persistent_15_years" else config.PROJECT_YEARS
            for label, width in config.UNCERTAINTY_WIDTHS.items():
                for n in config.MC_SIZES:
                    rng = np.random.default_rng(config.MC_SEED)
                    parts = []
                    for lo in range(0, n, 1000):
                        nn = min(1000, n - lo)
                        idx = rng.integers(0, len(daily), size=(nn, years, len(daily)), dtype=np.int16)
                        en = ed[idx].sum(axis=2) * factor
                        anc = md[idx].sum(axis=2)
                        del idx
                        cm = rng.triangular(c_lo, c_mode, c_hi, size=nn)
                        om = rng.triangular(c_lo, c_mode, c_hi, size=nn)
                        cm = 1 + width * (cm - 1)
                        om = 1 + width * (om - 1)
                        ar = rng.triangular(a_lo, a_mode, a_hi, size=(nn, years))
                        ar = np.clip(a_mode + width * (ar - a_mode), 0, 1)
                        gross = en + (anc * ar if has_as else 0) + contract
                        net = gross - config.FIXED_OM * om[:, None]
                        if years == 1:
                            parts.append(-config.CAPEX * cm + net[:, 0] * ann)
                        else:
                            parts.append(-config.CAPEX * cm + (net * disc[None, :]).sum(axis=1))
                    vals = np.concatenate(parts)
                    rows.append({"case": name, "temporal_model": temporal, "uncertainty": label,
                                 "width": width, "draws": n, **summarise_npv(vals)})
    return pd.DataFrame(rows)
