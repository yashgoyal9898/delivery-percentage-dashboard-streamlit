import streamlit as st
import pandas as pd
import altair as alt

st.title("📊 Delivery Percentage Dashboard (Daily + Weekly)")

# Upload CSV
uploaded_file = st.file_uploader("📎 Upload CSV File", type=["csv"])

if uploaded_file:
    df = pd.read_csv(uploaded_file)

    # Clean column names
    df.columns = [col.strip() for col in df.columns]
    df.rename(columns={
        'Symbol': 'symbol',
        'Date': 'date',
        'Traded Qty': 'traded_qty',
        'Deliverable Qty': 'deliverable_qty',
        '% Dly Qt to Traded Qty': 'delivery_pct'
    }, inplace=True)

    # Format data
    df['date'] = pd.to_datetime(df['date'].str.strip(), format='%d-%b-%Y')
    df['traded_qty'] = df['traded_qty'].str.replace(',', '').astype(int)
    df['deliverable_qty'] = df['deliverable_qty'].str.replace(',', '').astype(int)
    df['delivery_pct'] = df['delivery_pct'].astype(str).str.strip().str.replace('%', '').astype(float)

    # --------------------
    # Symbol Filter
    symbols = df['symbol'].unique().tolist()
    selected = st.multiselect("🔍 Select Symbols", symbols, default=symbols)
    df = df[df['symbol'].isin(selected)]

    # --------------------
    # 🗓️ DAILY VIEW
    st.subheader("📅 Daily Delivery Percentage")
    st.dataframe(df[['date', 'symbol', 'traded_qty', 'deliverable_qty', 'delivery_pct']])

    daily_chart = alt.Chart(df).mark_line(point=True).encode(
        x='date:T',
        y='delivery_pct:Q',
        color='symbol:N',
        tooltip=['date:T', 'symbol:N', 'delivery_pct:Q']
    ).properties(title='Daily Delivery %', width=900, height=400)

    st.altair_chart(daily_chart, use_container_width=True)

    # --------------------
    # 📆 WEEKLY VIEW
    df['week'] = df['date'].dt.to_period('W').apply(lambda r: r.start_time)
    weekly = df.groupby(['week', 'symbol']).agg({
        'traded_qty': 'sum',
        'deliverable_qty': 'sum'
    }).reset_index()
    weekly['delivery_pct'] = (weekly['deliverable_qty'] / weekly['traded_qty']) * 100

    st.subheader("🗓️ Weekly Delivery Percentage")
    st.dataframe(weekly)

    weekly_chart = alt.Chart(weekly).mark_line(point=True).encode(
        x='week:T',
        y='delivery_pct:Q',
        color='symbol:N',
        tooltip=['week:T', 'symbol:N', 'delivery_pct:Q']
    ).properties(title='Weekly Delivery %', width=900, height=400)

    st.altair_chart(weekly_chart, use_container_width=True)
