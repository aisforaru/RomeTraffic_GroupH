"""SQL used by the dashboard. One section per research question.

Every query takes the same two filters, so all tabs stay consistent:
  {area}  -> a fixed WHERE fragment chosen from AREAS (never user text)
  %(year)s -> a year such as 2024, or NULL for "all years"
"""

# Which accidents count as "Rome" / "Lazio" (ISTAT codes, see README > Data)
AREAS = {
    "Rome (city)": "province_code = '058' AND municipality_code = '091'",
    "Rome (province)": "province_code = '058'",
    "Lazio (region)": "province_code IN ('056', '057', '058', '059', '060')",
}

# ISTAT: giorno 1 = Monday ... 7 = Sunday
WEEKDAYS = {1: "Mon", 2: "Tue", 3: "Wed", 4: "Thu", 5: "Fri", 6: "Sat", 7: "Sun"}

YEARS = "SELECT DISTINCT year FROM accidents ORDER BY year"

_FILTER = "WHERE {area} AND (%(year)s::int IS NULL OR year = %(year)s::int)"

# ---------------------------------------------------------------- Q1 · WHEN
# Q1. Which hours and days have the most accidents in Rome?

Q1_TOTALS = f"""
SELECT count(*)                           AS accidents,
       count(*) FILTER (WHERE hour IS NULL) AS unknown_hour,
       coalesce(sum(injured), 0)          AS injured,
       coalesce(sum(deaths_30d), 0)       AS deaths_30d
FROM accidents
{_FILTER}
"""

Q1_BY_HOUR = f"""
SELECT hour, count(*) AS accidents
FROM accidents
{_FILTER} AND hour IS NOT NULL
GROUP BY hour
ORDER BY hour
"""

Q1_BY_WEEKDAY = f"""
SELECT weekday, count(*) AS accidents
FROM accidents
{_FILTER}
GROUP BY weekday
ORDER BY weekday
"""

Q1_HOUR_X_WEEKDAY = f"""
SELECT weekday, hour, count(*) AS accidents
FROM accidents
{_FILTER} AND hour IS NOT NULL
GROUP BY weekday, hour
"""

Q1_BY_QUARTER = f"""
SELECT quarter, count(*) AS accidents
FROM accidents
{_FILTER}
GROUP BY quarter
ORDER BY quarter
"""

# ---------------------------------------------------------------- Q2 · SEVERITY
# (Person 4) Add the Q2 queries here, using the same {_FILTER}.

# ---------------------------------------------------------------- Q3 · ROME VS LAZIO
# (Person 4) Add the Q3 queries here.
