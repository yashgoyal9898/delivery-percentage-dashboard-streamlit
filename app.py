import streamlit as st
import pandas as pd
import altair as alt

st.title("📊 Delivery Percentage Dashboard (Daily + Weekly)")

# Upload CSV
uploaded_file = st.file_uploader("📎 Upload CSV File", type=["csv"])

if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file)
        st.success("✅ File uploaded successfully")
        st.write("📄 Raw CSV preview:")
        st.dataframe(df.head())

        # Clean column names
        df.columns = [col.strip() for col in df.columns]
        expected_columns = ['Symbol', 'Date', 'Traded Qty', 'Deliverable Qty', '% Dly Qt to Traded Qty']
        missing_cols = [col for col in expected_columns if col not in df.columns]
        if missing_cols:
            st.error(f"❌ Missing columns in CSV: {missing_cols}")
            st.stop()

        df.rename(columns={
            'Symbol': 'symbol',
            'Date': 'date',
            'Traded Qty': 'traded_qty',
            'Deliverable Qty': 'deliverable_qty',
            '% Dly Qt to Traded Qty': 'delivery_pct'
        }, inplace=True)

        # Format data
        df['date'] = pd.to_datetime(df['date'].str.strip(), format='%d-%b-%Y', errors='coerce')
        df = df.dropna(subset=['date'])

        df['traded_qty'] = df['traded_qty'].astype(str).str.replace(',', '').astype(int)
        df['deliverable_qty'] = df['deliverable_qty'].astype(str).str.replace(',', '').astype(int)
        df['delivery_pct'] = df['delivery_pct'].astype(str).str.strip().str.replace('%', '').astype(float)

        # Symbol filter
        symbols = df['symbol'].unique().tolist()
        selected = st.multiselect("🔍 Select Symbols", symbols, default=symbols)
        df = df[df['symbol'].isin(selected)]

        # Daily view
        st.subheader("📅 Daily Delivery Percentage")
        st.dataframe(df[['date', 'symbol', 'traded_qty', 'deliverable_qty', 'delivery_pct']])

        daily_chart = alt.Chart(df).mark_line(point=True).encode(
            x='date:T',
            y='delivery_pct:Q',
            color='symbol:N',
            tooltip=['date:T', 'symbol:N', 'delivery_pct:Q']
        ).properties(title='Daily Delivery %', width=900, height=400)

        st.altair_chart(daily_chart, use_container_width=True)

        # Weekly view
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

    except Exception as e:
        st.error(f"❌ Error processing file: {e}")
