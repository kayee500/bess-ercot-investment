# Data

The raw ERCOT files are public and are not stored in this repository.
Download them from the ERCOT website and place them in `data/raw/` without renaming.

| Report | ERCOT ID | Report Type | Years used | File name contains |
|---|---|---|---|---|
| Historical DAM Load Zone and Hub Prices | NP4-180-ER | 13060 | 2025, 2026 | `DAMLZHBSPP_2025`, `DAMLZHBSPP_2026` |
| Historical DAM Clearing Prices for Capacity | NP4-181-ER | 13091 | 2025, 2026 | `DAMASMCPC_2025`, `DAMASMCPC_2026` |

Where to find them: on www.ercot.com, search for the ERCOT ID (for example "NP4-180-ER"),
open the data product page and download the yearly archive. Unzip each archive into `data/raw/`.

Files used in the manuscript:

- `rpt.00013060.0000000000000000.DAMLZHBSPP_2025.xlsx` (published 1 January 2026)
- `rpt.00013091.0000000000000000.20260101081728.DAMASMCPC_2025.csv` (published 1 January 2026)
- `rpt.00013060.0000000000000000.DAMLZHBSPP_2026.xlsx` (published 11 October 2026, data to 10 October 2026)
- `rpt.00013091.0000000000000000.20261011.080036.DAMASMCPC_2026.xlsx` (published 11 October 2026, data to 10 October 2026)

The loader reads either CSV or Excel versions and finds the header row automatically.
Only the `HB_NORTH` settlement point is used from the energy-price file.
