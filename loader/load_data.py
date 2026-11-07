"""Loader: downloads the ISTAT road-accident files and loads them into PostgreSQL.

Usage:
    python load_data.py                   # 100% of the data
    python load_data.py --fraction 0.25   # 25% sample, stratified by year, nested
"""
import argparse
import io
import os
import time
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import psycopg
import requests

DATA_DIR = Path("data/raw")
YEARS = [2020, 2021, 2022, 2023, 2024]
URL = ("https://www.istat.it/wp-content/themes/EGPbs5-child/microdata/download.php"
       "?file=%2F3%2F{year}%2F01%2F01.zip&filename=INCSTRAD_{year}_IT.zip")
SEED = 42

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
TABLE_COLS = ["accident_id"] + list(COLUMNS.values())       # same order as schema.sql


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


def sample(df, fraction):
    """Stratified (by year), nested and reproducible sample."""
    rng = np.random.default_rng(SEED)                        # fixed seed: same sample every run
    u = pd.Series(rng.random(len(df)), index=df.index)       # one random number per row
    pos = u.groupby(df["year"]).rank(pct=True)               # position inside its own year, 0-1
    return df[pos <= fraction]                               # 25% sits inside 50%, 50% inside 100%


def load_all():
    """Read and clean every year, then stack them oldest first."""
    return pd.concat([clean(read_year(y), y) for y in sorted(YEARS)], ignore_index=True)


def connect():
    """Connect to PostgreSQL. Inside Docker the host is the service name 'db'."""
    return psycopg.connect(
        host=os.environ.get("DB_HOST", "db"),
        port=int(os.environ.get("DB_PORT", 5432)),
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
    )


def wait_for_table(tries=30):
    """Wait until the database is up and the accidents table exists (from schema.sql)."""
    for _ in range(tries):
        try:
            with connect() as conn:
                if conn.execute("SELECT to_regclass('accidents')").fetchone()[0]:
                    return
        except psycopg.OperationalError:
            pass                                             # database not ready yet
        print("waiting for the database and the accidents table...")
        time.sleep(2)
    raise SystemExit("accidents table not found: is schema.sql loaded in the db?")


def load(df):
    """Empty the table, then send all rows at once with COPY."""
    buf = io.StringIO()
    df[TABLE_COLS].to_csv(buf, index=False, header=False)   # empty cell = NULL
    buf.seek(0)
    with connect() as conn, conn.cursor() as cur:
        cur.execute("TRUNCATE accidents")                    # every run starts clean
        with cur.copy(f"COPY accidents ({', '.join(TABLE_COLS)}) FROM STDIN WITH (FORMAT csv)") as copy:
            while chunk := buf.read(1 << 20):                # 1 MB at a time
                copy.write(chunk)
        n = cur.execute("SELECT count(*) FROM accidents").fetchone()[0]
    print(f"accidents table now has {n:,} rows")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--fraction", type=float, default=1.0, choices=[0.25, 0.5, 1.0],
                        help="share of the data to load (default 1.0)")
    args = parser.parse_args()

    t0 = time.perf_counter()
    df = sample(load_all(), args.fraction)
    t1 = time.perf_counter()
    print(f"\nfraction {args.fraction}: {len(df):,} rows")

    wait_for_table()
    t2 = time.perf_counter()
    load(df)
    t3 = time.perf_counter()

    # Person 5's benchmark can read these lines
    print(f"TIME read+clean: {t1 - t0:.2f} s")
    print(f"TIME copy into db: {t3 - t2:.2f} s")
    print(f"TIME total: {t3 - t0:.2f} s")