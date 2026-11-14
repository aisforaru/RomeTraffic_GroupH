"""
Benchmark: load 25%, 50% and 100% of the data, 3 runs each.

For every run it records:
  - the times printed by the loader (read+clean, copy into db, total)
  - the peak memory (RAM) of the loader and db containers, read with docker stats

Results are saved in measure/results.csv and a summary is printed at the end.

How to run (from the project folder, with Docker Desktop open):
    python measure/benchmark.py
"""

import csv
import re
import statistics
import subprocess
import threading
import time
from pathlib import Path

FRACTIONS = [0.25, 0.5, 1.0]
RUNS = 3
ROOT = Path(__file__).resolve().parent.parent      # the project folder
OUT = ROOT / "measure" / "results.csv"

UNITS = {"B": 1 / 1024**2, "KiB": 1 / 1024, "MiB": 1, "GiB": 1024,
         "kB": 1 / 1000, "MB": 1, "GB": 1000}


def to_mib(text):
    """'512.3MiB / 7.6GiB' -> 512.3 (memory used, in MiB)."""
    m = re.match(r"([\d.]+)\s*([A-Za-z]+)", text.strip())
    return float(m.group(1)) * UNITS.get(m.group(2), 1) if m else 0.0


def watch_memory(names, peaks, stop):
    """Every second, read docker stats and keep the highest memory seen per container."""
    while not stop.is_set():
        out = subprocess.run(
            ["docker", "stats", "--no-stream", "--format", "{{.Name}};{{.MemUsage}}"],
            capture_output=True, text=True).stdout
        for line in out.splitlines():
            name, _, mem = line.partition(";")
            for key, match in names.items():
                if match in name:
                    peaks[key] = max(peaks[key], to_mib(mem))
        time.sleep(1)


def one_run(fraction, run):
    """Run the loader once with the given fraction and return its measurements."""
    container = f"bench_loader_{int(fraction * 100)}_{run}"
    peaks = {"loader": 0.0, "db": 0.0}
    stop = threading.Event()
    watcher = threading.Thread(target=watch_memory,
                               args=({"loader": container, "db": "-db-"}, peaks, stop))
    watcher.start()

    start = time.perf_counter()
    result = subprocess.run(
        ["docker", "compose", "run", "--rm", "--name", container,
         "loader", "python", "load_data.py", "--fraction", str(fraction)],
        cwd=ROOT, capture_output=True, text=True)
    wall = time.perf_counter() - start

    stop.set()
    watcher.join()

    if result.returncode != 0:
        print(result.stdout[-2000:], result.stderr[-2000:])
        raise SystemExit(f"loader failed at fraction {fraction}, run {run}")

    times = dict(re.findall(r"TIME (.+?): ([\d.]+) s", result.stdout))
    rows = re.search(r"accidents table now has ([\d,]+) rows", result.stdout)
    return {
        "fraction": fraction,
        "run": run,
        "rows": int(rows.group(1).replace(",", "")) if rows else "",
        "read_clean_s": float(times.get("read+clean", 0)),
        "copy_db_s": float(times.get("copy into db", 0)),
        "total_s": float(times.get("total", 0)),
        "wall_s": round(wall, 2),                    # includes starting the container
        "loader_peak_mib": round(peaks["loader"], 1),
        "db_peak_mib": round(peaks["db"], 1),
    }


def main():
    print("Starting the database (if it is not running yet)...")
    subprocess.run(["docker", "compose", "up", "-d", "--wait", "db"], cwd=ROOT, check=True)

    results = []
    for fraction in FRACTIONS:
        for run in range(1, RUNS + 1):
            print(f"\n{int(fraction * 100)}% - run {run}/{RUNS} ...", flush=True)
            r = one_run(fraction, run)
            results.append(r)
            print(f"  {r['rows']:,} rows | total {r['total_s']:.2f} s "
                  f"(read+clean {r['read_clean_s']:.2f} s, copy {r['copy_db_s']:.2f} s) | "
                  f"RAM loader {r['loader_peak_mib']:.0f} MiB, db {r['db_peak_mib']:.0f} MiB")

    with open(OUT, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)
    print(f"\nSaved {OUT.relative_to(ROOT)}")

    print("\nSUMMARY (mean of the runs; min-max in brackets)")
    print(f"{'data':>5} | {'rows':>9} | {'total s':>18} | {'read+clean s':>18} | "
          f"{'copy s':>16} | {'RAM loader':>10} | {'RAM db':>7}")
    for fraction in FRACTIONS:
        rs = [r for r in results if r["fraction"] == fraction]

        def cell(key):
            vals = [r[key] for r in rs]
            return f"{statistics.mean(vals):.2f} ({min(vals):.2f}-{max(vals):.2f})"

        print(f"{int(fraction * 100):>4}% | {rs[0]['rows']:>9,} | {cell('total_s'):>18} | "
              f"{cell('read_clean_s'):>18} | {cell('copy_db_s'):>16} | "
              f"{max(r['loader_peak_mib'] for r in rs):>6.0f} MiB | "
              f"{max(r['db_peak_mib'] for r in rs):>3.0f} MiB")


if __name__ == "__main__":
    main()
