"""
delivery_dashboard.py
~~~~~~~~~~~~~~~~~~~~~
Interactive dashboard for Daily / Weekly / Monthly / Quarterly / Half-Yearly
delivery percentage with optional Close‑price overlay.

Author  : Your Name
Last Mod: 2025‑07‑11
"""

from io import StringIO
import pandas as pd
import altair as alt
import streamlit as st

# ------------------------------------------------------------------#
# 1. Page config
# ------------------------------------------------------------------#
st.set_page_config(page_title="Delivery % Dashboard", layout="wide")
st.title("📊 Delivery Percentage Dashboard")

# ------------------------------------------------------------------#
# 2. File upload (support multiple CSVs)
# ------------------------------------------------------------------#
uploaded_files = st.sidebar.file_uploader(
    "📌 Upload one or more CSV files", type=["csv"], accept_multiple_files=True
)
if not uploaded_files:
    st.info("Upload at least one CSV to begin.")
    st.stop()

# ------------------------------------------------------------------#
# 3. Data loader & cleaner
# ------------------------------------------------------------------#
@st.cache_data(show_spinner=False)
def load_and_clean(raw_csv: str) -> pd.DataFrame:
    df = pd.read_csv(StringIO(raw_csv))
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    COL_MAP = {
        "symbol": "symbol",
        "date": "date",
        "qty_traded": "traded_qty",
        "total_traded_quantity": "traded_qty",
        "traded_qty": "traded_qty",
        "deliverable_qty": "deliverable_qty",
        "delivered_qty": "deliverable_qty",
        "delivery_percentage": "delivery_pct",
        "delivery_percent": "delivery_pct",
        "%_dly_qt_to_traded_qty": "delivery_pct",
        "delivery_pct": "delivery_pct",
        "closeprice": "close",
        "close_price": "close",
        "closing_price": "close",
        "close": "close",
    }
    df.rename(columns=lambda c: COL_MAP.get(c, c), inplace=True)

    REQUIRED = ["symbol", "date", "traded_qty", "deliverable_qty", "delivery_pct"]
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise ValueError(f"Missing column(s): {', '.join(missing)}")

    df.replace(["-", "NA", "N/A", "na", ""], pd.NA, inplace=True)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df.dropna(subset=["date"], inplace=True)

    numeric_cols = ["traded_qty", "deliverable_qty", "delivery_pct"]
    if "close" in df.columns:
        numeric_cols.append("close")

    for c in numeric_cols:
        df[c] = (
            df[c]
            .astype(str)
            .str.replace(",", "", regex=False)
            .str.replace("%", "", regex=False)
            .replace("", pd.NA)
        )
        df[c] = pd.to_numeric(df[c], errors="coerce")

    df.dropna(subset=numeric_cols, inplace=True)
    df["traded_qty"] = df["traded_qty"].astype(int)
    df["deliverable_qty"] = df["deliverable_qty"].astype(int)

    return df.reset_index(drop=True)

# ------------------------------------------------------------------#
# 4. Load, clean and merge multiple files
# ------------------------------------------------------------------#
dfs = []
for up in uploaded_files:
    part = load_and_clean(up.read().decode("utf-8", errors="ignore"))
    dfs.append(part)

df = (
    pd.concat(dfs, ignore_index=True)
    .drop_duplicates(subset=["symbol", "date"])
    .sort_values("date")
    .reset_index(drop=True)
)

# ------------------------------------------------------------------#
# 5. Sidebar filters
# ------------------------------------------------------------------#
symbols = df["symbol"].unique().tolist()
selected_symbols = st.sidebar.multiselect("🔍 Symbols", symbols, default=symbols)
df = df[df["symbol"].isin(selected_symbols)]

spike_thr = st.sidebar.slider("🚨 Spike threshold (%)", 0.0, 100.0, 75.0, step=0.5)

# ------------------------------------------------------------------#
# 6. Summary metrics
# ------------------------------------------------------------------#
st.subheader("📌 Summary Metrics")
col1, col2, col3 = st.columns(3)
col1.metric("Average Delivery %", f"{df['delivery_pct'].mean():.2f}")
col2.metric("Max Delivery %", f"{df['delivery_pct'].max():.2f}")
col3.metric("Total Days", int(df["date"].nunique()))

# ------------------------------------------------------------------#
# 7. Spike alerts
# ------------------------------------------------------------------#
spikes = df[df["delivery_pct"] >= spike_thr]
if not spikes.empty:
    st.warning(f"🚨 {len(spikes)} spike(s) ≥ {spike_thr}%")
    st.dataframe(spikes[["date", "symbol", "delivery_pct"]])

# ------------------------------------------------------------------#
# 8. Daily chart (with Close Price)
# ------------------------------------------------------------------#
st.subheader("🗓️ Daily Delivery % (with Close Price overlay)")

base = alt.Chart(df).encode(x="date:T", color="symbol:N")
delivery_line = base.mark_line(point=True).encode(
    y=alt.Y("delivery_pct:Q", axis=alt.Axis(title="Delivery %")),
    tooltip=["date:T", "symbol:N", "delivery_pct:Q"],
)

if "close" in df.columns:
    close_line = base.mark_line(strokeWidth=2).encode(
        y=alt.Y("close:Q", axis=alt.Axis(title="Close Price", orient="right")),
        tooltip=["date:T", "symbol:N", "close:Q"],
    )
    daily_chart = alt.layer(delivery_line, close_line).resolve_scale(y="independent")
else:
    daily_chart = delivery_line

st.altair_chart(daily_chart.properties(width=900, height=400), use_container_width=True)

# ------------------------------------------------------------------#
# 9. Weekly Aggregation (Millions)
# ------------------------------------------------------------------#
st.subheader("📅 Weekly Delivery % (quantities in Millions, ∆ vs prev week)")
df["week"] = df["date"].dt.to_period("W").apply(lambda r: r.start_time)
weekly = (
    df.groupby(["week", "symbol"], as_index=False)[["traded_qty", "deliverable_qty"]]
    .sum()
)
weekly["delivery_pct"] = 100 * weekly["deliverable_qty"] / weekly["traded_qty"]
weekly = weekly.sort_values(["symbol", "week"])
weekly["traded_qty_chg_%"] = weekly.groupby("symbol")["traded_qty"].pct_change() * 100
weekly["deliverable_qty_chg_%"] = weekly.groupby("symbol")["deliverable_qty"].pct_change() * 100
weekly_disp = weekly.copy()
weekly_disp["traded_qty_million"] = (weekly_disp["traded_qty"] / 1e6).round(2)
weekly_disp["deliverable_qty_million"] = (weekly_disp["deliverable_qty"] / 1e6).round(2)
weekly_disp["traded_qty_chg_%"] = weekly_disp["traded_qty_chg_%"].round(2)
weekly_disp["deliverable_qty_chg_%"] = weekly_disp["deliverable_qty_chg_%"].round(2)
weekly_disp = weekly_disp[
    ["week", "symbol", "traded_qty_million", "deliverable_qty_million", "delivery_pct", "traded_qty_chg_%", "deliverable_qty_chg_%"]
]
st.dataframe(weekly_disp)
wk_chart = (
    alt.Chart(weekly)
    .mark_line(point=True)
    .encode(x="week:T", y="delivery_pct:Q", color="symbol:N", tooltip=["week:T", "symbol:N", "delivery_pct:Q"])
    .properties(width=900, height=400, title="Weekly Delivery %")
)
st.altair_chart(wk_chart, use_container_width=True)

# ------------------------------------------------------------------#
# 10. Monthly Aggregation (Millions)
# ------------------------------------------------------------------#
st.subheader("📅 Monthly Delivery % (quantities in Millions, ∆ vs prev month)")
df["month"] = df["date"].dt.to_period("M").apply(lambda r: r.start_time)
monthly = (
    df.groupby(["month", "symbol"], as_index=False)[["traded_qty", "deliverable_qty"]]
    .sum()
)
monthly["delivery_pct"] = 100 * monthly["deliverable_qty"] / monthly["traded_qty"]
monthly = monthly.sort_values(["symbol", "month"])
monthly["traded_qty_chg_%"] = monthly.groupby("symbol")["traded_qty"].pct_change() * 100
monthly["deliverable_qty_chg_%"] = monthly.groupby("symbol")["deliverable_qty"].pct_change() * 100
monthly_disp = monthly.copy()
monthly_disp["traded_qty_million"] = (monthly_disp["traded_qty"] / 1e6).round(2)
monthly_disp["deliverable_qty_million"] = (monthly_disp["deliverable_qty"] / 1e6).round(2)
monthly_disp["traded_qty_chg_%"] = monthly_disp["traded_qty_chg_%"].round(2)
monthly_disp["deliverable_qty_chg_%"] = monthly_disp["deliverable_qty_chg_%"].round(2)
monthly_disp = monthly_disp[
    ["month", "symbol", "traded_qty_million", "deliverable_qty_million", "delivery_pct", "traded_qty_chg_%", "deliverable_qty_chg_%"]
]
st.dataframe(monthly_disp)
mo_chart = (
    alt.Chart(monthly)
    .mark_line(point=True)
    .encode(x="month:T", y="delivery_pct:Q", color="symbol:N", tooltip=["month:T", "symbol:N", "delivery_pct:Q"])
    .properties(width=900, height=400, title="Monthly Delivery %")
)
st.altair_chart(mo_chart, use_container_width=True)

# ------------------------------------------------------------------#
# 11. Quarterly Aggregation (Millions)
# ------------------------------------------------------------------#
st.subheader("📊 Quarterly Delivery % (quantities in Millions)")
df["quarter"] = df["date"].dt.to_period("Q").apply(lambda r: r.start_time)
quarterly = (
    df.groupby(["quarter", "symbol"], as_index=False)[["traded_qty", "deliverable_qty"]]
    .sum()
)
quarterly["delivery_pct"] = 100 * quarterly["deliverable_qty"] / quarterly["traded_qty"]
quarterly_disp = quarterly.copy()
quarterly_disp["traded_qty"] = (quarterly_disp["traded_qty"] / 1e6).round(2)
quarterly_disp["deliverable_qty"] = (quarterly_disp["deliverable_qty"] / 1e6).round(2)
quarterly_disp.rename(
    columns={"traded_qty": "traded_qty_million", "deliverable_qty": "deliverable_qty_million"},
    inplace=True,
)
st.dataframe(quarterly_disp)
qt_chart = (
    alt.Chart(quarterly)
    .mark_line(point=True)
    .encode(x="quarter:T", y="delivery_pct:Q", color="symbol:N", tooltip=["quarter:T", "symbol:N", "delivery_pct:Q"])
    .properties(width=900, height=400, title="Quarterly Delivery %")
)
st.altair_chart(qt_chart, use_container_width=True)


# ------------------------------------------------------------------#
# 12. Half-Yearly Aggregation (Millions)
# ------------------------------------------------------------------#
st.subheader("📈 Half-Yearly Delivery % (quantities in Millions)")

# Create a new 'half_year' column as 'YYYY-H1' or 'YYYY-H2'
def get_half_year(d):
    year = d.year
    if d.month <= 6:
        return pd.Timestamp(f"{year}-01-01")  # H1
    else:
        return pd.Timestamp(f"{year}-07-01")  # H2

df["half_year"] = df["date"].apply(get_half_year)

# Aggregate
half_yearly = (
    df.groupby(["half_year", "symbol"], as_index=False)[["traded_qty", "deliverable_qty"]]
    .sum()
)
half_yearly["delivery_pct"] = 100 * half_yearly["deliverable_qty"] / half_yearly["traded_qty"]

# Prepare display table
half_disp = half_yearly.copy()
half_disp["traded_qty_million"] = (half_disp["traded_qty"] / 1e6).round(2)
half_disp["deliverable_qty_million"] = (half_disp["deliverable_qty"] / 1e6).round(2)
half_disp = half_disp[
    ["half_year", "symbol", "traded_qty_million", "deliverable_qty_million", "delivery_pct"]
]

st.dataframe(half_disp)

# Chart
half_chart = (
    alt.Chart(half_yearly)
    .mark_line(point=True)
    .encode(
        x=alt.X("half_year:T", title="Half-Year"),
        y=alt.Y("delivery_pct:Q", title="Delivery %"),
        color="symbol:N",
        tooltip=["half_year:T", "symbol:N", "delivery_pct:Q"]
    )
    .properties(width=900, height=400, title="Half-Yearly Delivery %")
)

st.altair_chart(half_chart, use_container_width=True)
