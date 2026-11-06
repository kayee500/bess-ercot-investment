"""Daily mixed-integer energy-arbitrage optimisation and ancillary-service valuation."""

import numpy as np
import pandas as pd
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import lil_matrix

from . import config


def optimise_day(prices: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Optimal charge and discharge (MWh per hour) for one delivery day.

    Decision vector x = [c_1..c_H, d_1..d_H, SOC_1..SOC_H, z_1..z_H]; z is binary (1 = charging).
    Maximises sum p_t (d_t - c_t), Eq. (1), subject to Eqs. (2)-(5).

    The formulation, variable order and constraint order follow the authors' original
    script (reconstruct_ercot_arbitrage.py) exactly. On days with several equally optimal
    schedules the solver's choice depends on this structure, so keeping it identical makes
    the ancillary-service values reproduce the manuscript to the cent.
    """
    n = len(prices)
    eta, e_max, p_max = config.ETA, config.USABLE_MWH, config.POWER_MW
    objective = np.r_[prices, -prices, np.zeros(2 * n)]          # milp minimises cost - sales
    integrality = np.r_[np.zeros(3 * n), np.ones(n)]
    lower = np.zeros(4 * n)
    upper = np.r_[np.full(n, p_max), np.full(n, p_max), np.full(n, e_max), np.ones(n)]
    rows, lbs, ubs = [], [], []
    for t in range(n):
        row = {2 * n + t: 1.0, t: -eta, n + t: 1.0 / eta}            # Eq. (2): SOC balance
        if t:
            row[2 * n + t - 1] = -1.0
        rows.append(row); lbs.append(0.0); ubs.append(0.0)
        rows.append({t: 1.0, 3 * n + t: -p_max}); lbs.append(-np.inf); ubs.append(0.0)      # c_t <= P z_t
        rows.append({n + t: 1.0, 3 * n + t: p_max}); lbs.append(-np.inf); ubs.append(p_max)  # d_t <= P(1 - z_t)
    rows.append({3 * n - 1: 1.0}); lbs.append(0.0); ubs.append(0.0)                          # Eq. (5): SOC_H = 0
    rows.append({n + t: 1.0 for t in range(n)}); lbs.append(-np.inf)
    ubs.append(config.DAILY_DISCHARGE_LIMIT_MWH)                                            # Eq. (5): daily limit
    a = lil_matrix((len(rows), 4 * n))
    for j, row in enumerate(rows):
        for i, v in row.items():
            a[j, i] = v
    res = milp(objective, integrality=integrality, bounds=Bounds(lower, upper),
               constraints=LinearConstraint(a.tocsr(), lbs, ubs),
               options={"mip_rel_gap": config.MILP_REL_GAP})
    if res.x is None or res.status != 0:
        raise RuntimeError(f"MILP failed: {res.message}")
    charge, discharge = res.x[:n], res.x[n:2 * n]
    _check_schedule(charge, discharge)
    return charge, discharge


def _check_schedule(charge: np.ndarray, discharge: np.ndarray, tol: float = 1e-6) -> None:
    """Independent feasibility checks on each solved schedule (always run)."""
    soc = np.cumsum(config.ETA * charge - discharge / config.ETA)
    checks = {
        "state of charge within 0 and usable capacity": soc.min() >= -tol and soc.max() <= config.USABLE_MWH + tol,
        "terminal state of charge equals zero": abs(soc[-1]) <= tol,
        "daily discharge limit": discharge.sum() <= config.DAILY_DISCHARGE_LIMIT_MWH + tol,
        "power limits": charge.max() <= config.POWER_MW + tol and discharge.max() <= config.POWER_MW + tol,
        "no simultaneous charging and discharging": not np.any((charge > tol) & (discharge > tol)),
    }
    failed = [name for name, ok in checks.items() if not ok]
    if failed:
        raise RuntimeError("Schedule check failed: " + ", ".join(failed))


def run_dispatch(market: pd.DataFrame, price_col: str = "price") -> pd.DataFrame:
    """Solve every delivery day independently and return the hourly schedule."""
    out = []
    for _, day in market.groupby("Delivery Date", sort=True):
        c, d = optimise_day(day[price_col].to_numpy(dtype=float))
        day = day.copy()
        day["charge"], day["discharge"] = c, d
        out.append(day)
    sched = pd.concat(out, ignore_index=True)
    sched["energy_margin"] = sched[price_col] * (sched["discharge"] - sched["charge"])
    return sched


def add_ancillary_value(sched: pd.DataFrame) -> pd.DataFrame:
    """Eq. (6): residual power capacity assigned to the highest-priced service each hour."""
    prices = sched[config.AS_PRODUCTS].to_numpy(dtype=float)
    residual = config.POWER_MW - np.maximum(sched["charge"], sched["discharge"]).to_numpy()
    top = prices.max(axis=1)
    sched = sched.copy()
    sched["as_residual_mw"] = residual
    sched["as_value"] = residual * top
    # Value attribution by service: when several services share the highest price,
    # the hour's value is split equally among them (the total is unaffected).
    tied = np.isclose(prices, top[:, None], rtol=0.0, atol=1e-9)
    share = tied / tied.sum(axis=1, keepdims=True)
    for k, svc in enumerate(config.AS_PRODUCTS):
        sched[f"as_value_{svc}"] = sched["as_value"] * share[:, k]
    return sched


def summarise(sched: pd.DataFrame) -> dict:
    charge_cost = float((sched["price"] * sched["charge"]).sum())
    discharge_rev = float((sched["price"] * sched["discharge"]).sum())

    return {
        "days": int(sched["Delivery Date"].nunique()),
        "discharged_mwh": float(sched["discharge"].sum()),
        "charged_mwh": float(sched["charge"].sum()),
        "discharge_revenue": discharge_rev,
        "charging_cost": charge_cost,
        "energy_gross_margin": discharge_rev - charge_cost,
        "equivalent_cycles": float(sched["discharge"].sum() / config.USABLE_MWH),   # delivered energy / usable capacity
        "as_value_100pct": float(sched["as_value"].sum()),
        "as_value_by_service": {s: float(sched[f"as_value_{s}"].sum()) for s in config.AS_PRODUCTS},
    }


def daily_margins(sched: pd.DataFrame) -> pd.DataFrame:
    """Paired daily energy margin and ancillary-service value (Monte Carlo input)."""
    return sched.groupby("Delivery Date")[["energy_margin", "as_value"]].sum().reset_index()


def spread_adjusted_prices(market: pd.DataFrame, factor: float) -> pd.Series:
    """Scale each hour's deviation from its daily mean price; the daily mean is unchanged."""
    daily_mean = market.groupby("Delivery Date")["price"].transform("mean")
    return daily_mean + factor * (market["price"] - daily_mean)
