# Road accidents in Lazio

*When and where are road accidents in Lazio most dangerous?*
1.⁠ ⁠Which hours and days have the most accidents in Rome?
2.⁠ ⁠Are accidents more serious in the rain, at night, or on certain road types?
3.⁠ ⁠Is Rome more dangerous than the rest of Lazio?

## Team 
Aruzhan Rakhmzhan, Sofia De Santis, Chiara Rossi, Eldar Kurbanov, Artem Shelygin

## How to run

**Requirements:** Docker Desktop (running) and Git. Nothing else is needed: Python, PostgreSQL and all the libraries run inside containers.

```bash
git clone https://github.com/aisforaru/RomeTraffic_GroupH.git
cd RomeTraffic_GroupH
cp .env.example .env            # Windows PowerShell: Copy-Item .env.example .env
docker compose up --build -d
```

Then open **http://localhost:8501** in the browser.

What happens after `docker compose up`:
1. **db** starts PostgreSQL and, on the first start, creates the tables (`schema.sql`, `lookups.sql`).
2. **loader** waits until the database is healthy, downloads the ISTAT files 2020–2024 (~38 MB, saved in `./data`), loads 775,951 accidents into the database and then stops. `Exited (0)` is normal: it means it finished without errors.
3. **app** starts after the loader and serves the Streamlit dashboard on port 8501.

The first run takes about 2 minutes (building the images and downloading the data). Later runs take about 30 seconds.

### Useful commands

| Command | What it does |
|---|---|
| `docker compose ps -a` | Shows all containers and their status (db should be `healthy`, loader `Exited (0)`, app `Up`) |
| `docker compose logs -f loader` | Shows the loader messages and the load times (press Ctrl+C to stop watching) |
| `docker compose down` | Stops everything; the data stays in the database volume |
| `docker compose down -v` | Stops everything and **deletes the database**. Use it for a fresh start: the tables are created only when the database is new |

If port 5432 or 8501 is already used on your laptop (for example by a local PostgreSQL), stop that program or change the left number in `ports:` in `docker-compose.yml`.

## Data
ISTAT – Incidenti stradali con lesioni a persone, public-use microdata file (mIcro.STAT), year 2024.
One row per accident with injuries in Italy (~173,000 rows, ~87 MB). We keep only Lazio
(provinces 056–060, ~20,000 accidents) and Rome (province 058, municipality 091).
Source: https://www.istat.it/microdati/incidenti-stradali-con-lesioni-a-persone/

## Database
PostgreSQL. Every accident has the same fixed columns, and most values are numeric codes
(e.g. weather 3 = rain), so we store one table of accidents plus small lookup tables
that translate the codes, linked with SQL joins.

## Database
PostgreSQL 16 (`schema.sql`, `lookups.sql`). Every accident has the same fixed columns, and most values are numeric codes, so we use a star-like schema with one central fact table plus three small lookup tables linked via SQL joins:
- **`accidents`** (775,951 rows, 17 columns): stores one row per accident (`accident_id` primary key, `year`, `province_code`, `municipality_code`, `weekday`, `quarter`, `hour`, road/weather codes, `deaths_24h`, `deaths_30d`, `injured`).
- **`weather_lookup`**, **`road_surface_lookup`**, **`province_lookup`**: decode numeric ISTAT codes into human-readable labels.

To speed up dashboard filters and joins, four B-tree indexes are created on `accidents`:
- `idx_accidents_geo_year (province_code, municipality_code, year)` — speeds up area and year filters (`WHERE` clauses across Q1–Q3).
- `idx_accidents_year (year)` — speeds up year-only filtering.
- `idx_accidents_weather (weather)` and `idx_accidents_road_surface (road_surface)` — speed up joins and groupings in Q2.


## Processing
Filter Lazio, translate codes, compute accidents by hour and day, severity
(deaths + injured per accident) by weather, night/day and road type,
and compare Rome with the rest of Lazio.

## What the user sees
A Streamlit dashboard with charts for the three questions.

## Results

### Q1 · Which hours and days have the most accidents in Rome?

Rome city (ISTAT codes 058/091), 2024: **13,924 accidents with injuries**,
**134 deaths** within 30 days and **17,196 injured**.

| Finding | Value |
|---|---|
| Busiest hour | **08:00**, 917 accidents |
| Second peak | **18:00**, 909 accidents |
| Quietest hours | **03:00–04:00**, 112 and 127 accidents |
| Busiest day | **Friday**, 2,233 accidents |
| Quietest day | **Sunday**, 1,421 accidents |
| Weekend vs weekday | Saturdays and Sundays have **28% fewer** accidents per day than Monday–Friday |
| Busiest single slot | **Tuesday 08:00**, 192 accidents |

- On weekdays, accidents form two peaks: around **08:00** and **17:00–18:00**.
- On weekends there is no clear morning peak. The accidents are spread more evenly over late morning and afternoon.
- Between midnight and 05:00 there are far fewer accidents than during the day.

**Limits of the data:** ISTAT rounds the hour, and 578 accidents (4%) have no
recorded hour, so they are left out of the hour charts. The data gives the
weekday and the quarter, but not the exact date, so holidays or specific days
cannot be analysed.

## Measurements
Load time, query time (with and without indexes), peak memory (docker stats)
and database size on disk, with 25%, 50% and 100% of the data.

### First results (checkpoint, 12 Nov)

Full pipeline started with `docker compose up --build`, with 100% of the data (ISTAT 2020–2024, 775,951 accidents).
Laptop: Windows, AMD Ryzen AI 7 350, 16 GB RAM.

| Date | Run | Read + clean | Copy into db | Total loader time |
|---|---|---|---|---|
| 7 Nov | First run (ISTAT files downloaded) | 21.86 s | 2.81 s | 24.68 s |
| 10 Nov | ISTAT files already in `./data` | 13.64 s | 3.68 s | 17.36 s |

What we see so far:
- Copying 775,951 rows into PostgreSQL with `COPY` takes less than 4 seconds: most of the time goes into reading and cleaning the five files.
- Downloading the ISTAT files adds about 7 seconds, so later runs are faster.
- From `docker compose up` (images already built): the database is ready after about 9 s, the loader finishes after about 27 s, then the dashboard starts. Building the images the first time takes about 64 s.

### Scalability: 25%, 50% and 100% of the data (14 Nov)

Script: `measure/benchmark.py` (run it with `python measure/benchmark.py`). It runs the loader 3 times for each fraction and reads the peak memory of the containers with `docker stats` every second. Raw results: `measure/results.csv`. Same laptop as above, with the dashboard off and other programs closed.

| Data | Rows | Read + clean | Copy into db | Total loader time | Peak RAM loader | Peak RAM db |
|---|---|---|---|---|---|---|
| 25% | 193,986 | 7.70 s | 0.61 s | 8.33 s (7.91–8.68) | 408 MiB | 60 MiB |
| 50% | 387,974 | 7.03 s | 1.08 s | 8.13 s (8.05–8.25) | 371 MiB | 104 MiB |
| 100% | 775,951 | 6.95 s | 2.07 s | 9.03 s (8.81–9.20) | 395 MiB | 144 MiB |

Times are the mean of 3 runs; min–max of the total in brackets.

What we see:
- **Copy into the database scales linearly:** doubling the rows roughly doubles the time (0.61 → 1.08 → 2.07 s), about 375,000 rows per second.
- **Read + clean stays around 7 s** for every fraction, because the loader always reads all five ISTAT files and samples afterwards. This is the bottleneck: with 100% of the data it is 77% of the total time.
- So **the total grows only from 8.3 s to 9.0 s** while the data becomes four times bigger.
- **Loader memory stays around 400 MiB** for the same reason: all rows are in memory before sampling. **Database memory grows with the data:** 60 → 104 → 144 MiB.
- The 3 runs differ by less than 0.8 s, so the results are stable. They are faster than the 10 Nov run (17.36 s) because the dashboard was off and fewer programs were open.
- With much more data, the first thing to change would be the loader: reading the files in chunks would keep its memory low, while `COPY` already scales well.

Still to add: queries with and without indexes, and database size on disk compared with the original ISTAT files.


### Query times (with and without indexes) and disk size

Measured on 100% of the data (775,951 rows) in PostgreSQL 16 (GitHub Codespaces). Query times are the mean of 3 runs (`\timing on` in `psql`).

| Query | Filter / Operation | Without indexes | With indexes | Speedup |
|---|---|---|---|---|
| Q1 (`Q1_HOUR_X_WEEKDAY`) | Rome city + 2024 | 84.0 ms | 4.5 ms | ~19× |
| Q2 (`Q2_BY_WEATHER`) | Lazio + 2024 + join | 80.6 ms | 51.1 ms | ~1.6× |
| Q3 (`Q3_GEOGRAPHIC`) | Lazio (all years) | 162.8 ms | 15.8 ms | ~10× |

**Disk size (original ISTAT files vs PostgreSQL):**
- Original ISTAT `.zip` files (`data/raw`): **~38 MB**
- PostgreSQL database without custom indexes: **75 MB** (`accidents` table: 68 MB)
- PostgreSQL database with 4 custom indexes: **114 MB** (`accidents` table + indexes: 107 MB; indexes take 39 MB)

What we see:
- **Composite index on `(province_code, municipality_code, year)` cuts Q1 latency by ~19×** (84.0 → 4.5 ms) and Q3 by ~10× (162.8 → 15.8 ms), avoiding full sequential scans on 775,951 rows.
- **Q2 improves more moderately** (80.6 → 51.1 ms) because filtering across all 5 Lazio provinces in 2024 still aggregates a larger slice of rows and joins `weather_lookup`.
- **Disk overhead is small:** the 4 B-tree indexes add 39 MB (bringing the total database to 114 MB vs ~38 MB of compressed ISTAT `.zip` archives), keeping all dashboard queries well under 55 ms.