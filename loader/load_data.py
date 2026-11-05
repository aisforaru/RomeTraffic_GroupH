"""Loader: downloads the ISTAT road-accident files and loads them into PostgreSQL."""
import io
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import requests

DATA_DIR = Path("data/raw")
YEARS = [2020, 2021, 2022, 2023, 2024]
URL = ("https://www.istat.it/wp-content/themes/EGPbs5-child/microdata/download.php"
       "?file=%2F3%2F{year}%2F01%2F01.zip&filename=INCSTRAD_{year}_IT.zip")

# ISTAT column -> our column (agreed in Step 0)
COLUMNS = {
    "anno": "year",
    "provincia": "province_code",
    "comune": "municipality_code",
    "giorno": "weekday",
    "trimestre": "quarter",
    "ora": "hour",
    "localizzazione_incidente": "location_type",
    "tipo_di_strada": "carriageway_type",
    "intersezione_o_non_interse3": "road_feature",
    "fondo_stradale": "road_surface",
    "condizioni_meteorologiche": "weather",
    "natura_incidente": "accident_type",
    "tipo_veicolo_a": "vehicle_a_type",
    "morti_entro_24_ore": "deaths_24h",
    "morti_entro_30_giorni": "deaths_30d",
    "feriti": "injured",
}
TEXT_COLS = ["province_code", "municipality_code"]           # keep leading zeros
NUMBER_COLS = [c for c in COLUMNS.values() if c not in TEXT_COLS + ["year"]]


def download(year):
    """Download data/raw/<year>.zip from ISTAT, unless it is already there."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_DIR / f"{year}.zip"
    if path.exists():
        print(f"{year}: already downloaded")
        return path
    print(f"{year}: downloading...")
    r = requests.get(URL.format(year=year), timeout=120)
    r.raise_for_status()                      # stop if ISTAT answers with an error
    path.write_bytes(r.content)
    print(f"{year}: saved {path.stat().st_size / 1e6:.1f} MB")
    return path


def read_year(year):
    """Open the zip and read the accidents .txt inside MICRODATI/."""
    with zipfile.ZipFile(download(year)) as z:
        name = [n for n in z.namelist() if n.startswith("MICRODATI/") and n.endswith(".txt")][0]
        raw = z.read(name)
    # tab-separated; dtype=str keeps codes like '058' with their leading zero
    df = pd.read_csv(io.BytesIO(raw), sep="\t", dtype=str, encoding="latin-1")
    df.columns = [c.strip().lower() for c in df.columns]   # 'Ora' -> 'ora'
    print(f"{year}: {len(df):,} rows, {len(df.columns)} columns")
    return df


def clean(df, year):
    """Keep our 16 columns, rename them, and give them the right types."""
    missing = [c for c in COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"{year}: missing columns {missing}")
    df = df[list(COLUMNS)].rename(columns=COLUMNS)
    df["year"] = year                                        # file says 24, we store 2024
    for c in TEXT_COLS:
        df[c] = df[c].str.strip().str.zfill(3)               # '58' -> '058'
    for c in NUMBER_COLS:
        df[c] = pd.to_numeric(df[c].str.strip(), errors="coerce").astype("Int16")
    df.loc[df["hour"] == 25, "hour"] = pd.NA                 # 25 = unknown hour
    df.insert(0, "accident_id", year * 1_000_000 + np.arange(len(df)))
    return df


if __name__ == "__main__":
    df = pd.concat([clean(read_year(y), y) for y in YEARS], ignore_index=True)
    print(f"\nTotal: {len(df):,} rows, {len(df.columns)} columns")
    print(df.head(3).T)                                      # first 3 accidents, sideways

    d24 = df[df["year"] == 2024]
    lazio = d24[d24["province_code"].isin(["056", "057", "058", "059", "060"])]
    rome = d24[(d24["province_code"] == "058") & (d24["municipality_code"] == "091")]
    print(f"\n2024 checks: Lazio {len(lazio):,} (plan: 21,240), Rome city {len(rome):,} (plan: 13,924)")
    print(f"Unknown hour (was 25): {df['hour'].isna().sum():,}")