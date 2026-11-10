"""Streamlit dashboard: Road accidents in Lazio.

Reads everything from PostgreSQL (filled by the loader). One tab per question.
Run inside Docker (see docker-compose.yml) and open http://localhost:8501
"""
import os
import time

import altair as alt
import pandas as pd
import psycopg
import streamlit as st

import queries as q

st.set_page_config(page_title="Road accidents in Lazio", page_icon="🚦", layout="wide")


# ---------------------------------------------------------------- database
def connect():
    """Inside Docker the host is the service name 'db', not localhost."""
    return psycopg.connect(
        host=os.environ.get("DB_HOST", "db"),
        port=int(os.environ.get("DB_PORT", 5432)),
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
    )


@st.cache_data(ttl=600, show_spinner=False)
def run(sql, area="TRUE", year=None):
    """Run one query; return (DataFrame, seconds). Cached for 10 minutes."""
    t0 = time.perf_counter()
    with connect() as conn, conn.cursor() as cur:
        cur.execute(sql.format(area=area), {"year": year})
        cols = [d.name for d in cur.description]
        df = pd.DataFrame(cur.fetchall(), columns=cols)
    return df, time.perf_counter() - t0


TIMINGS = []  # (query name, seconds) shown at the bottom of the page


def query(name, sql, area="TRUE", year=None):
    df, secs = run(sql, area, year)
    TIMINGS.append((name, secs))
    return df


# ---------------------------------------------------------------- data ready?
try:
    years = query("years", q.YEARS)["year"].tolist()
except psycopg.OperationalError:
    st.warning("Cannot reach the database yet. Wait a few seconds and refresh.")
    st.stop()

if not years:
    st.info("The accidents table is still empty: the loader is probably still running. Refresh in a minute.")
    run.clear()
    st.stop()

# ---------------------------------------------------------------- sidebar filters
st.sidebar.header("Filters")
area_name = st.sidebar.radio("Area", list(q.AREAS), index=0)
year_label = st.sidebar.selectbox("Year", ["All years"] + [str(y) for y in reversed(years)], index=1)
year = None if year_label == "All years" else int(year_label)
area = q.AREAS[area_name]
st.sidebar.caption("Source: ISTAT, road accidents with injuries (public-use microdata).")

st.title("Road accidents in Lazio")
st.caption(f"{area_name} · {year_label}")

tab1, tab2, tab3 = st.tabs(["Q1 · When", "Q2 · Severity", "Q3 · Rome vs Lazio"])

# ---------------------------------------------------------------- Q1
with tab1:
    st.subheader("Which hours and days have the most accidents?")

    tot = query("Q1 totals", q.Q1_TOTALS, area, year).iloc[0]
    by_hour = query("Q1 by hour", q.Q1_BY_HOUR, area, year)
    by_day = query("Q1 by weekday", q.Q1_BY_WEEKDAY, area, year)
    grid = query("Q1 hour x weekday", q.Q1_HOUR_X_WEEKDAY, area, year)
    by_qtr = query("Q1 by quarter", q.Q1_BY_QUARTER, area, year)

    by_day["day"] = by_day["weekday"].map(q.WEEKDAYS)
    grid["day"] = grid["weekday"].map(q.WEEKDAYS)
    day_order = list(q.WEEKDAYS.values())

    peak_hour = by_hour.loc[by_hour["accidents"].idxmax()]
    peak_day = by_day.loc[by_day["accidents"].idxmax()]
    weekday_avg = by_day.loc[by_day["weekday"] <= 5, "accidents"].mean()
    weekend_avg = by_day.loc[by_day["weekday"] >= 6, "accidents"].mean()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Accidents", f"{int(tot['accidents']):,}")
    c2.metric(f"Busiest hour · {int(peak_hour['accidents']):,} accidents", f"{int(peak_hour['hour']):02d}:00")
    c3.metric(f"Busiest day · {int(peak_day['accidents']):,} accidents", peak_day["day"])
    c4.metric("Weekend day vs weekday", f"{weekend_avg / weekday_avg - 1:+.0%}")

    left, right = st.columns(2)
    with left:
        st.markdown("**By hour of day**")
        st.altair_chart(
            alt.Chart(by_hour).mark_bar().encode(
                x=alt.X("hour:O", title="Hour", axis=alt.Axis(labelAngle=0)),
                y=alt.Y("accidents:Q", title="Accidents"),
                tooltip=["hour", "accidents"],
            ),
            use_container_width=True,
        )
    with right:
        st.markdown("**By day of week**")
        st.altair_chart(
            alt.Chart(by_day).mark_bar().encode(
                x=alt.X("day:N", sort=day_order, title=None, axis=alt.Axis(labelAngle=0)),
                y=alt.Y("accidents:Q", title="Accidents"),
                tooltip=["day", "accidents"],
            ),
            use_container_width=True,
        )

    st.markdown("**Hour × day: when exactly?**")
    st.altair_chart(
        alt.Chart(grid).mark_rect().encode(
            x=alt.X("hour:O", title="Hour", axis=alt.Axis(labelAngle=0)),
            y=alt.Y("day:N", sort=day_order, title=None),
            color=alt.Color("accidents:Q", title="Accidents", scale=alt.Scale(scheme="blues")),
            tooltip=["day", "hour", "accidents"],
        ).properties(height=260),
        use_container_width=True,
    )

    with st.expander("By quarter of the year"):
        by_qtr["quarter"] = "Q" + by_qtr["quarter"].astype(str)
        st.bar_chart(by_qtr, x="quarter", y="accidents")

    st.caption(
        f"Hours are rounded by ISTAT (0–23). {int(tot['unknown_hour']):,} accidents with unknown hour "
        "are left out of the hour charts. ISTAT gives the weekday and quarter but not the exact date."
    )

# ---------------------------------------------------------------- Q2 / Q3 (placeholders)
with tab2:
    st.subheader("Are accidents more serious in the rain, at night, or on certain road types?")
    st.info("In progress. Add the Q2 queries to queries.py and the charts here.")

with tab3:
    st.subheader("Is Rome more dangerous than the rest of Lazio?")
    st.info("In progress. Add the Q3 queries to queries.py and the charts here.")

# ---------------------------------------------------------------- timings (for the measurements)
with st.expander("Query timings"):
    st.caption("Time of the first, uncached run of each query on this page.")
    st.dataframe(
        pd.DataFrame(TIMINGS, columns=["query", "seconds"]).round(4),
        hide_index=True,
        use_container_width=True,
    )
