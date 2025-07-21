"""
delivery_dashboard.py
~~~~~~~~~~~~~~~~~~~~~
Interactive dashboard for Daily / Weekly / Monthly / Quarterly / Half-Yearly
delivery percentage with optional Close‑price overlay.

Author  : Your Name
Last Mod: 2025‑07‑21
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
# 📚 Table of Contents (Sidebar Links)
# ------------------------------------------------------------------#
st.sidebar.markdown("## 📚 Table of Contents")
st.sidebar.markdown("[1. Summary Metrics](#summary-metrics)")
st.sidebar.markdown("[2. Daily Delivery % Table](#daily-delivery-table)")
st.sidebar.markdown("[3. Weekly Delivery % Table](#weekly-delivery-table)")
st.sidebar.markdown("[4. Monthly Delivery % Table](#monthly-delivery-table)")
st.sidebar.markdown("[5. Quarterly Delivery % Table](#quarterly-delivery-table)")
st.sidebar.markdown("[6. Half-Yearly Delivery % Table](#half-yearly-delivery-table)")
st.sidebar.markdown("[7. Yearly Delivery % Table](#yearly-delivery-table)")


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
        "open_price": "open",
        "open": "open",
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
    if "open" in df.columns:
        numeric_cols.append("open")
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

    df.dropna(subset=["traded_qty", "deliverable_qty", "delivery_pct"], inplace=True)
    df["traded_qty"] = df["traded_qty"].astype(int)
    df["deliverable_qty"] = df["deliverable_qty"].astype(int)

    # ✅ Calculate Net Value = Deliverable Qty × Open Price
    df["net_value"] = pd.NA
    if "open" in df.columns:
        df["net_value"] = df["deliverable_qty"] * df["open"]

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
spike_thr = st.sidebar.slider("🚨 Spike threshold (%)", 0.0, 100.0, 75.0, step=0.5)
net_value_thr = st.sidebar.slider("💰 Net Value Spike (₹ Cr)", 0.0, 50.0, 3.0, step=0.5)

# ------------------------------------------------------------------#
# 6. Summary metrics
# ------------------------------------------------------------------#
st.markdown('<a name="summary-metrics"></a>', unsafe_allow_html=True)
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
# 8. Daily Delivery % Table
# ------------------------------------------------------------------#
st.markdown('<a name="daily-delivery-table"></a>', unsafe_allow_html=True)
st.subheader("📆 Daily Delivery % (Quantities in Millions, Net Value in ₹ Crores)")

df = df.sort_values(["symbol", "date"])
df["traded_qty_chg_%"] = df.groupby("symbol")["traded_qty"].pct_change() * 100
df["deliverable_qty_chg_%"] = df.groupby("symbol")["deliverable_qty"].pct_change() * 100

daily_disp = df.copy()
daily_disp["traded_qty_mn"] = (daily_disp["traded_qty"] / 1e6).round(2)
daily_disp["deliverable_qty_mn"] = (daily_disp["deliverable_qty"] / 1e6).round(2)
daily_disp["net_value_crore"] = (daily_disp["net_value"] / 1e7).round(2)
daily_disp["traded_qty_chg_%"] = daily_disp["traded_qty_chg_%"].round(2)
daily_disp["deliverable_qty_chg_%"] = daily_disp["deliverable_qty_chg_%"].round(2)

daily_columns = [
    "date",
    "symbol",
    "traded_qty_mn",
    "deliverable_qty_mn",
    "delivery_pct",
    "net_value_crore",
    "traded_qty_chg_%",
    "deliverable_qty_chg_%",
]

def highlight_net_value(val):
    if pd.notna(val) and val > net_value_thr:
        return "background-color: #ffe6e6; font-weight: bold"
    return ""

styled_df = daily_disp[daily_columns].style.applymap(
    highlight_net_value, subset=["net_value_crore"]
)

st.dataframe(styled_df, use_container_width=True)

# ------------------------------------------------------------------#
# 9. Weekly Aggregation
# ------------------------------------------------------------------#
st.markdown('<a name="weekly-delivery-table"></a>', unsafe_allow_html=True)
st.subheader("📅 Weekly Delivery % (Quantities in Millions, Net Value in ₹ Crores)")

df["week"] = df["date"].dt.to_period("W").apply(lambda r: r.start_time)
weekly = (
    df.groupby(["week", "symbol"], as_index=False)[["traded_qty", "deliverable_qty", "net_value"]]
    .sum()
)
weekly["delivery_pct"] = 100 * weekly["deliverable_qty"] / weekly["traded_qty"]
weekly = weekly.sort_values(["symbol", "week"])
weekly["traded_qty_chg_%"] = weekly.groupby("symbol")["traded_qty"].pct_change() * 100
weekly["deliverable_qty_chg_%"] = weekly.groupby("symbol")["deliverable_qty"].pct_change() * 100

weekly_disp = weekly.copy()
weekly_disp["traded_qty_million"] = (weekly_disp["traded_qty"] / 1e6).round(2)
weekly_disp["deliverable_qty_million"] = (weekly_disp["deliverable_qty"] / 1e6).round(2)
weekly_disp["net_value_crore"] = (weekly_disp["net_value"] / 1e7).round(2)
weekly_disp["traded_qty_chg_%"] = weekly_disp["traded_qty_chg_%"].round(2)
weekly_disp["deliverable_qty_chg_%"] = weekly_disp["deliverable_qty_chg_%"].round(2)
weekly_disp = weekly_disp[
    ["week", "symbol", "traded_qty_million", "deliverable_qty_million", "delivery_pct",
     "net_value_crore", "traded_qty_chg_%", "deliverable_qty_chg_%"]
]
styled_weekly = weekly_disp.style.applymap(highlight_net_value, subset=["net_value_crore"])
st.dataframe(styled_weekly, use_container_width=True)

wk_chart = (
    alt.Chart(weekly)
    .mark_line(point=True)
    .encode(x="week:T", y="delivery_pct:Q", color="symbol:N",
            tooltip=["week:T", "symbol:N", "delivery_pct:Q"])
    .properties(width=900, height=400, title="Weekly Delivery %")
)
st.altair_chart(wk_chart, use_container_width=True)


# ------------------------------------------------------------------#
# 10. Monthly Aggregation (Millions)
# ------------------------------------------------------------------#

st.markdown('<a name="monthly-delivery-table"></a>', unsafe_allow_html=True)
st.subheader("📅 Monthly Delivery % (Quantities in Millions, Net Value in ₹ Crores)")


df["month"] = df["date"].dt.to_period("M").apply(lambda r: r.start_time)
monthly = (
    df.groupby(["month", "symbol"], as_index=False)[["traded_qty", "deliverable_qty", "net_value"]]
    .sum()
)
monthly["delivery_pct"] = 100 * monthly["deliverable_qty"] / monthly["traded_qty"]
monthly = monthly.sort_values(["symbol", "month"])
monthly["traded_qty_chg_%"] = monthly.groupby("symbol")["traded_qty"].pct_change() * 100
monthly["deliverable_qty_chg_%"] = monthly.groupby("symbol")["deliverable_qty"].pct_change() * 100

monthly_disp = monthly.copy()
monthly_disp["traded_qty_million"] = (monthly_disp["traded_qty"] / 1e6).round(2)
monthly_disp["deliverable_qty_million"] = (monthly_disp["deliverable_qty"] / 1e6).round(2)
monthly_disp["net_value_crore"] = (monthly_disp["net_value"] / 1e7).round(2)
monthly_disp["traded_qty_chg_%"] = monthly_disp["traded_qty_chg_%"].round(2)
monthly_disp["deliverable_qty_chg_%"] = monthly_disp["deliverable_qty_chg_%"].round(2)
monthly_disp = monthly_disp[
    ["month", "symbol", "traded_qty_million", "deliverable_qty_million", "delivery_pct",
     "net_value_crore", "traded_qty_chg_%", "deliverable_qty_chg_%"]
]
styled_monthly = monthly_disp.style.applymap(highlight_net_value, subset=["net_value_crore"])
st.dataframe(styled_monthly, use_container_width=True)

mo_chart = (
    alt.Chart(monthly)
    .mark_line(point=True)
    .encode(x="month:T", y="delivery_pct:Q", color="symbol:N",
            tooltip=["month:T", "symbol:N", "delivery_pct:Q"])
    .properties(width=900, height=400, title="Monthly Delivery %")
)
st.altair_chart(mo_chart, use_container_width=True)

# ------------------------------------------------------------------#
# 11. Quarterly Aggregation (Millions)
# ------------------------------------------------------------------#
st.markdown('<a name="quarterly-delivery-table"></a>', unsafe_allow_html=True)
st.subheader("📊 Quarterly Delivery % (Quantities in Millions, Net Value in ₹ Crores)")

df["quarter"] = df["date"].dt.to_period("Q").apply(lambda r: r.start_time)
quarterly = (
    df.groupby(["quarter", "symbol"], as_index=False)[["traded_qty", "deliverable_qty", "net_value"]]
    .sum()
)
quarterly["delivery_pct"] = 100 * quarterly["deliverable_qty"] / quarterly["traded_qty"]

quarterly_disp = quarterly.copy()
quarterly_disp["traded_qty_million"] = (quarterly_disp["traded_qty"] / 1e6).round(2)
quarterly_disp["deliverable_qty_million"] = (quarterly_disp["deliverable_qty"] / 1e6).round(2)
quarterly_disp["net_value_crore"] = (quarterly_disp["net_value"] / 1e7).round(2)
quarterly_disp = quarterly_disp[
    ["quarter", "symbol", "traded_qty_million", "deliverable_qty_million", "delivery_pct", "net_value_crore"]
]
styled_quarterly = quarterly_disp.style.applymap(highlight_net_value, subset=["net_value_crore"])
st.dataframe(styled_quarterly, use_container_width=True)

qt_chart = (
    alt.Chart(quarterly)
    .mark_line(point=True)
    .encode(x="quarter:T", y="delivery_pct:Q", color="symbol:N",
            tooltip=["quarter:T", "symbol:N", "delivery_pct:Q"])
    .properties(width=900, height=400, title="Quarterly Delivery %")
)
st.altair_chart(qt_chart, use_container_width=True)

# ------------------------------------------------------------------#
# 12. Half-Yearly Aggregation (Millions)
# ------------------------------------------------------------------#
st.markdown('<a name="half-yearly-delivery-table"></a>', unsafe_allow_html=True)
st.subheader("📈 Half-Yearly Delivery % (Quantities in Millions, Net Value in ₹ Crores)")

def get_half_year(d):
    year = d.year
    return pd.Timestamp(f"{year}-01-01") if d.month <= 6 else pd.Timestamp(f"{year}-07-01")

df["half_year"] = df["date"].apply(get_half_year)
half_yearly = (
    df.groupby(["half_year", "symbol"], as_index=False)[["traded_qty", "deliverable_qty", "net_value"]]
    .sum()
)
half_yearly["delivery_pct"] = 100 * half_yearly["deliverable_qty"] / half_yearly["traded_qty"]

half_disp = half_yearly.copy()
half_disp["traded_qty_million"] = (half_disp["traded_qty"] / 1e6).round(2)
half_disp["deliverable_qty_million"] = (half_disp["deliverable_qty"] / 1e6).round(2)
half_disp["net_value_crore"] = (half_disp["net_value"] / 1e7).round(2)
half_disp = half_disp[
    ["half_year", "symbol", "traded_qty_million", "deliverable_qty_million", "delivery_pct", "net_value_crore"]
]
styled_half = half_disp.style.applymap(highlight_net_value, subset=["net_value_crore"])
st.dataframe(styled_half, use_container_width=True)

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

# ------------------------------------------------------------------#
# 13. Yearly Aggregation (Millions)
# ------------------------------------------------------------------#
st.markdown('<a name="yearly-delivery-table"></a>', unsafe_allow_html=True)
st.subheader("📅 Yearly Delivery % (Quantities in Millions, Net Value in ₹ Crores)")

df["year"] = df["date"].dt.to_period("Y").apply(lambda r: r.start_time)
yearly = (
    df.groupby(["year", "symbol"], as_index=False)[["traded_qty", "deliverable_qty", "net_value"]]
    .sum()
)
yearly["delivery_pct"] = 100 * yearly["deliverable_qty"] / yearly["traded_qty"]

year_disp = yearly.copy()
year_disp["traded_qty_million"] = (year_disp["traded_qty"] / 1e6).round(2)
year_disp["deliverable_qty_million"] = (year_disp["deliverable_qty"] / 1e6).round(2)
year_disp["net_value_crore"] = (year_disp["net_value"] / 1e7).round(2)
year_disp = year_disp[
    ["year", "symbol", "traded_qty_million", "deliverable_qty_million", "delivery_pct", "net_value_crore"]
]
styled_year = year_disp.style.applymap(highlight_net_value, subset=["net_value_crore"])
st.dataframe(styled_year, use_container_width=True)
