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
# Q2: Severity by weather, road surface, and night/day in Lazio

Q2_BY_WEATHER = f"""
select 
    coalesce(
        case 
            when w.description = 'Sereno' then 'Clear'
            when w.description = 'Nebbia' then 'Fog'
            when w.description = 'Pioggia' then 'Rain'
            when w.description = 'Nevischio / Neve' then 'Sleet / Snow'
            when w.description = 'Grandine' then 'Hail'
            else 'Other / Unknown'
        end, 
        'Other / Unknown'
    ) as weather,
    count(*) as accidents,
    sum(a.deaths_24h + a.deaths_30d) as deaths,
    sum(a.injured) as injured,
    round(cast(sum(a.deaths_24h + a.deaths_30d) as numeric) / nullif(count(*), 0) * 100, 2) as mortality_index,
    round(cast(sum(a.injured) as numeric) / nullif(count(*), 0) * 100, 2) as injury_index
from accidents a
left join weather_lookup w on a.weather = w.code
{_FILTER}
group by 1
having count(*) > 30
order by mortality_index desc
"""

Q2_BY_SURFACE = f"""
select 
    coalesce(
        case 
            when r.description = 'Pavimentazione asciutta' then 'Dry'
            when r.description = 'Pavimentazione bagnata' then 'Wet'
            when r.description = 'Viscido' then 'Slippery'
            when r.description = 'Innevato' then 'Snowy'
            when r.description = 'Ghiacciato' then 'Icy'
            else 'Other / Unspecified'
        end, 
        'Other / Unspecified'
    ) as road_surface,
    count(*) as accidents,
    sum(a.deaths_24h + a.deaths_30d) as deaths,
    sum(a.injured) as injured,
    round(cast(sum(a.deaths_24h + a.deaths_30d) as numeric) / nullif(count(*), 0) * 100, 2) as mortality_index,
    round(cast(sum(a.injured) as numeric) / nullif(count(*), 0) * 100, 2) as injury_index
from accidents a
left join road_surface_lookup r on a.road_surface = r.code
{_FILTER}
group by 1
having count(*) > 20
order by mortality_index desc
"""

Q2_BY_LIGHTING = f"""
select 
    case 
        when hour >= 20 or hour <= 5 then 'Night (20:00–05:59)'
        when hour >= 6 and hour <= 19 then 'Day (06:00–19:59)'
        else 'Unknown'
    end as lighting,
    count(*) as accidents,
    sum(deaths_24h + deaths_30d) as deaths,
    sum(injured) as injured,
    round(cast(sum(deaths_24h + deaths_30d) as numeric) / nullif(count(*), 0) * 100, 2) as mortality_index,
    round(cast(sum(injured) as numeric) / nullif(count(*), 0) * 100, 2) as injury_index
from accidents
{_FILTER} and hour is not null
group by 1
order by mortality_index desc
"""

# ---------------------------------------------------------------- Q3 · ROME VS LAZIO
# Q3: Rome City vs Rome Province Belt vs other 4 Lazio provinces

Q3_GEOGRAPHIC = """
select 
    case 
        when a.province_code = '058' and a.municipality_code = '091' then 'Rome (City)'
        when a.province_code = '058' and a.municipality_code != '091' then 'Rome (Province belt)'
        when a.province_code = '056' then 'Viterbo'
        when a.province_code = '057' then 'Rieti'
        when a.province_code = '059' then 'Latina'
        when a.province_code = '060' then 'Frosinone'
        else 'Other'
    end as area,
    count(*) as accidents,
    sum(a.deaths_24h + a.deaths_30d) as deaths,
    sum(a.injured) as injured,
    round(cast(sum(a.deaths_24h + a.deaths_30d) as numeric) / nullif(count(*), 0) * 100, 2) as mortality_index,
    round(cast(sum(a.injured) as numeric) / nullif(count(*), 0) * 100, 2) as injury_index
from accidents a
where a.province_code in ('056', '057', '058', '059', '060')
  and (%(year)s::int is null or a.year = %(year)s::int)
group by 1
order by accidents desc
"""
