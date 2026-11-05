import io
import zipfile
from pathlib import Path

import pandas as pd
import requests

DATA_DIR = Path("data/raw")
YEARS = [2020, 2021, 2022, 2023, 2024]
URL = ("https://www.istat.it/wp-content/themes/EGPbs5-child/microdata/download.php"
       "?file=%2F3%2F{year}%2F01%2F01.zip&filename=INCSTRAD_{year}_IT.zip")


def download(year):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_DIR / f"{year}.zip"
    if path.exists():
        print(f"{year}: already downloaded")
        return path
    print(f"{year}: downloading...")
    r = requests.get(URL.format(year=year), timeout=120)
    r.raise_for_status()                    
    path.write_bytes(r.content)
    print(f"{year}: saved {path.stat().st_size / 1e6:.1f} MB")
    return path


def read_year(year):
    with zipfile.ZipFile(download(year)) as z:
        name = [n for n in z.namelist() if n.startswith("MICRODATI/") and n.endswith(".txt")][0]
        raw = z.read(name)
    # tab-separated; dtype=str keeps codes like '058' with their leading zero
    df = pd.read_csv(io.BytesIO(raw), sep="\t", dtype=str, encoding="latin-1")
    df.columns = [c.strip().lower() for c in df.columns]   # 'Ora' -> 'ora'
    print(f"{year}: {len(df):,} rows, {len(df.columns)} columns")
    return df


if __name__ == "__main__":
    for year in YEARS:
        read_year(year)