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

## Processing
Filter Lazio, translate codes, compute accidents by hour and day, severity
(deaths + injured per accident) by weather, night/day and road type,
and compare Rome with the rest of Lazio.

## What the user sees
A Streamlit dashboard with charts for the three questions.

## Measurements
Load time, query time (with and without indexes), peak memory (docker stats)
and database size on disk, with 25%, 50% and 100% of the data.

