"""Load and match ERCOT day-ahead energy and ancillary-service prices."""

from pathlib import Path

import pandas as pd

from . import config

KEYS = ["Delivery Date", "Hour Ending", "Repeated Hour Flag"]


def _find(pattern: str) -> Path:
    files = sorted(config.RAW_DIR.glob(pattern))
    if not files:
        raise FileNotFoundError(
            f"No file matching '{pattern}' in {config.RAW_DIR}. "
            "See data/README.md for download instructions."
        )
    return files[0]


def _read_table(path: Path, sheet_name=None) -> pd.DataFrame:
    """Read an ERCOT CSV or Excel report, locating the header row if needed."""
    if path.suffix.lower() == ".csv":
        df = pd.read_csv(path)
        df.columns = [str(c).strip() for c in df.columns]
        return df
    sheets = pd.read_excel(path, sheet_name=sheet_name, header=None)
    if isinstance(sheets, pd.DataFrame):
        sheets = {"_": sheets}
    frames = []
    for raw in sheets.values():
        hdr = raw.index[raw.iloc[:, 0].astype(str).str.strip() == "Delivery Date"][0]
        df = raw.iloc[hdr + 1:].copy()
        df.columns = [str(c).strip() for c in raw.iloc[hdr]]
        frames.append(df.dropna(subset=["Delivery Date"]))
    return pd.concat(frames, ignore_index=True)


def load_energy_prices(year: int, point: str = config.SETTLEMENT_POINT) -> pd.DataFrame:
    """Hourly day-ahead settlement-point prices (Report Type 13060)."""
    df = _read_table(_find(f"*DAMLZHBSPP_{year}*"))
    df = df[df["Settlement Point"] == point].copy()
    df["price"] = pd.to_numeric(df["Settlement Point Price"])
    return df[KEYS + ["price"]]


def load_as_prices(year: int) -> pd.DataFrame:
    """Hourly day-ahead ancillary-service clearing prices (Report Type 13091)."""
    df = _read_table(_find(f"*DAMASMCPC_{year}*"))
    for col in config.AS_PRODUCTS:
        df[col] = pd.to_numeric(df[col])
    return df[KEYS + config.AS_PRODUCTS]


def load_market(year: int) -> pd.DataFrame:
    """Energy and ancillary-service prices matched by date, hour and repeated-hour flag."""
    energy = load_energy_prices(year)
    ancillary = load_as_prices(year)
    for df in (energy, ancillary):
        df["Delivery Date"] = pd.to_datetime(df["Delivery Date"], format="%m/%d/%Y")
        df["Hour Ending"] = df["Hour Ending"].astype(str).str.strip()
        df["Repeated Hour Flag"] = df["Repeated Hour Flag"].astype(str).str.strip()
    merged = energy.merge(ancillary, on=KEYS, how="inner", validate="one_to_one")
    if len(merged) != len(energy) or len(merged) != len(ancillary):
        raise ValueError("Energy and ancillary-service records do not match one-to-one.")
    # Keep original market-time order; the repeated hour (flag Y) follows its first instance.
    merged = merged.sort_values(KEYS, kind="stable").reset_index(drop=True)
    return merged


def data_summary(market: pd.DataFrame) -> dict:
    lengths = market.groupby("Delivery Date").size()
    return {
        "hours": int(len(market)),
        "days": int(lengths.size),
        "first_day": str(lengths.index.min().date()),
        "last_day": str(lengths.index.max().date()),
        "non_24_hour_days": {str(d.date()): int(n) for d, n in lengths[lengths != 24].items()},
        "repeated_hours": int((market["Repeated Hour Flag"] == "Y").sum()),
        "missing_prices": int(market[["price"] + config.AS_PRODUCTS].isna().sum().sum()),
        "mean_energy_price": float(market["price"].mean()),
    }
