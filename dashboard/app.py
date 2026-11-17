import pandas as pd
import plotly.express as px
import streamlit as st
from database.db import init_db, load_rows, get_state
from config import SYMBOLS, MARKETS, STARTING_CASH

st.set_page_config(page_title="ZERO COST AI TRADER", layout="wide")
init_db()
st.title("ZERO COST AI TRADER")
st.caption("Multi-asset paper trading — public indicative market quotes and simulated orders only.")
cash = get_state("cash", STARTING_CASH)
st.metric("Shared virtual cash balance", f"{cash:,.2f} USD")
selected = st.selectbox(
    "Select market",
    SYMBOLS,
    format_func=lambda s: f"{s} — {MARKETS[s]['name']}",
)
prices = load_rows("prices", 500, symbol=selected)
trades = load_rows("trades", 100, symbol=selected)
signals = load_rows("signals", 100, symbol=selected)
quantity = get_state(f"quantity:{selected}", 0.0)
cost = get_state(f"position_cost:{selected}", 0.0)
a, b, c = st.columns(3)
a.metric("Open virtual quantity", f"{quantity:.8f}")
b.metric("Position cost basis", f"{cost:,.2f} USD")
b2 = st.columns(1)[0]
if prices:
    df = pd.DataFrame(list(reversed(prices)))
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    latest = float(df.iloc[-1]["price"])
    c.metric("Latest recorded quote", f"{latest:,.6f} {MARKETS[selected]['quote']}")
    st.subheader(f"Price history — {selected}")
    st.plotly_chart(px.line(df, x="timestamp", y="price"), use_container_width=True)
else:
    st.info("No price history for this market yet. The first scheduled runs will collect quotes.")
st.subheader("Paper-trade history")
if trades:
    st.dataframe(pd.DataFrame(trades), use_container_width=True, hide_index=True)
else:
    st.write("No simulated trades for this market yet.")
st.subheader("Recent signals")
if signals:
    st.dataframe(pd.DataFrame(signals), use_container_width=True, hide_index=True)
else:
    st.write("No signals recorded yet.")
st.caption("Gold uses a COMEX futures proxy (GC=F); FX quotes are indicative/delayed via Yahoo Finance. Crypto spot quotes use Binance public data. No real broker connection or orders.")
