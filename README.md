# Road accidents in Lazio

*When and where are road accidents in Lazio most dangerous?*
1.⁠ ⁠Which hours and days have the most accidents in Rome?
2.⁠ ⁠Are accidents more serious in the rain, at night, or on certain road types?
3.⁠ ⁠Is Rome more dangerous than the rest of Lazio?

## Team 
Aruzhan Rakhmzhan
Sofia De Santis
Chiara Rossi
Eldar Kurbanov
Artem Shelygin

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

