# Investment economics of grid-scale battery storage in ERCOT

Code and processed results for the manuscript:

> John, K. S., John, S. A., Ezealigo, C., & Oreoluwa, A. S. (2026). *Investment Economics and Business Models for Grid-Scale
> Lithium-Ion Battery Storage in ERCOT under AI-Related Demand Uncertainty.* Manuscript submitted
> for publication.

The code reproduces every number, table and figure in the manuscript from public ERCOT
day-ahead market data. One command runs the full analysis in under a minute.

## What the model does

A 1 MW / 4 MWh lithium iron phosphate battery (3.2 MWh usable, 85% round-trip efficiency)
is evaluated at the ERCOT `HB_NORTH` hub using complete 2025 hourly day-ahead prices.

1. **Dispatch.** Each of the 365 delivery days is solved as a mixed-integer linear programme
   that maximises energy-arbitrage margin with perfect day-ahead price knowledge, at most 3.2 MWh
   delivered to the grid per day, zero start and end state of charge, and no simultaneous charging and
   discharging.
2. **Ancillary services.** Power capacity not used for arbitrage in each hour is assigned to the
   highest-priced ERCOT ancillary service (value split equally when services tie on price).
   This is an indicative capacity-price value, not
   settled revenue.
3. **Investment.** LCOS, NPV, IRR and discounted payback for six business models, three
   illustrative price scenarios and five discount rates (90 cases), plus break-even contract
   payments.
4. **Sensitivities.** Ancillary-service realisation, intraday price spreads, contract payments
   and declining merchant revenue.
5. **Monte Carlo.** 10,000 draws per case: daily paired bootstrap of energy and ancillary
   revenue, triangular CAPEX, O&M and realisation multipliers, fixed seed `20261012`.
   Robustness tests scale each distribution's spread by 0.5 and 1.5, resample revenue
   independently for each year, and use 5,000 to 20,000 draws.
6. **Out-of-sample check.** The same model on 2026 data to 10 October 2026, compared with the
   same calendar period of 2025.

## Quick start

```bash
git clone https://github.com/kayee500/bess-ercot-investment.git
cd bess-ercot-investment
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
# download the four ERCOT files into data/raw/ (see data/README.md)
python run_all.py
```

## Repository structure

```
bess-ercot-investment/
├── run_all.py                 # runs everything, in order
├── requirements.txt           # exact package versions used
├── src/bess_ercot/
│   ├── config.py              # every model assumption in one place
│   ├── data_io.py             # load and match ERCOT energy and ancillary prices
│   ├── dispatch.py            # daily MILP (Eqs. 1-5) and ancillary value (Eq. 6)
│   ├── finance.py             # NPV, IRR, payback, LCOS, break-even payments (Eqs. 7-10)
│   ├── analysis.py            # benchmark, scenarios, sensitivities, 2026 check
│   ├── montecarlo.py          # Monte Carlo and robustness tests
│   └── figures.py             # Figures 1-5
├── data/README.md             # how to download the ERCOT data
├── results/                   # CSV and JSON outputs (created by run_all.py)
└── figures/                   # PNG (600 dpi) and PDF figures (created by run_all.py)
```

## Where each manuscript result comes from

| Manuscript item | Output file |
|---|---|
| Section 2.2 data checks | `results/summary.json` → `data_2025` |
| Section 3.1, LCOS, ancillary value by service | `results/summary.json` → `benchmark_2025` |
| Break-even contract payments, Table 1 | `results/summary.json` → `thresholds` |
| Ancillary realisation tests (40%, 75%, 100%) | `results/as_realisation_tests.csv` |
| Section 3.2 scenarios, Section 3.3, Figure 4 | `results/deterministic_grid.csv` |
| Intraday spread sensitivity, Figure 3 | `results/spread_sensitivity.csv` |
| Contract-payment sensitivity | `results/contract_sensitivity.csv` |
| Declining-revenue sensitivity | `results/declining_revenue.csv` |
| Section 3.5, Table 3, Figure 5 | `results/montecarlo_grid.csv` |
| Hybrid recalibrated at 75% realisation (Section 3.5) | `results/montecarlo_hybrid_central.csv` |
| Monte Carlo robustness checks | `results/montecarlo_robustness.csv` |
| Section 3.6 2026 check | `results/summary.json` → `check_2026` |
| Paired daily inputs to the Monte Carlo | `results/daily_margins_2025.csv` |

## Key results (2025, HB_NORTH, 8% discount rate)

| Result | Value |
|---|---|
| Energy delivered per year | 1,142.28 MWh (356.96 equivalent full cycles, delivered energy / 3.2 MWh) |
| Merchant arbitrage gross margin | $52,540.75 |
| Indicative ancillary-service value (100%) | $18,614.76 |
| LCOS | $166.01/MWh |
| Merchant arbitrage NPV | −$961,644 |
| Break-even contract: availability / hybrid / data-centre-linked | $164,889 / $93,734 / $112,348 per year |
| P(NPV > 0), data-centre-linked, high-price scenario | 70.91% |

## Reproducibility notes

- **Exact match with the manuscript.** The dispatch formulation (variable and constraint order)
  and the random-number sequence follow the authors' original analysis scripts, so every
  deterministic and Monte Carlo result reproduces the manuscript exactly.
- **Software.** Tested with Python 3.13, SciPy 1.18.1 (HiGHS MILP, relative gap 1e-8),
  NumPy 2.5.3 and pandas 3.0.5. The original results were produced with SciPy 1.17.0; the outputs
  are identical.
- **Equally optimal schedules.** On a few days several dispatch schedules give exactly the same
  arbitrage margin. The margin never changes, but the spare capacity left for ancillary services
  can depend on which one the solver returns, so keep the model structure unchanged if you need
  identical ancillary values.
- **Tied ancillary prices.** In 1,254 hours of 2025 two or more services share the highest
  clearing price. The value of those hours is split equally among the tied services when
  reporting the breakdown by service. The total is unaffected.
- **Random numbers.** The main analysis draws once (seed `20261012`) and reuses the draws for all
  90 cases. Each robustness test restarts from the same seed.
- **Every assumption** lives in `src/bess_ercot/config.py`.

## Data licence and citation

ERCOT market data are public and remain subject to ERCOT's terms of use. Please cite the
manuscript if you use this code. Code is released under the MIT licence.

## Contact

Kayode Solomon John (corresponding author), Department of Economics, Umeå School of Business,
Economics and Statistics (USBE), Umeå University, Sweden. ORCID: 0009-0002-6413-8554.
