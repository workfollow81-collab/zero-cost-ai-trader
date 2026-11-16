import pandas as pd
import plotly.express as px
import streamlit as st
from database.db import init_db, load_rows
from config import SYMBOL, STARTING_CASH

st.set_page_config(page_title="ZERO COST AI TRADER", layout="wide")
init_db()
st.title("ZERO COST AI TRADER")
st.caption("وضع تجريبي محلي — لا أوامر حقيقية ولا اتصال بمنصة تداول.")
prices = load_rows("prices", 500)
trades = load_rows("trades", 100)
if prices:
    df = pd.DataFrame(list(reversed(prices)))
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    latest = float(df.iloc[-1]["price"])
    a, b, c = st.columns(3)
    a.metric("آخر سعر تجريبي", f"{latest:,.2f} USDT")
    b.metric("عدد نقاط الأسعار", len(df))
    c.metric("رصيد البداية الافتراضي", f"{STARTING_CASH:,.2f} USDT")
    st.subheader(f"حركة السعر التجريبية — {SYMBOL}")
    st.plotly_chart(px.line(df, x="timestamp", y="price"), use_container_width=True)
else:
    st.info("لا توجد بيانات بعد. شغّل البوت واتركه يعمل قليلاً ثم حدّث الصفحة.")
st.subheader("سجل الصفقات الافتراضية")
if trades:
    st.dataframe(pd.DataFrame(trades), use_container_width=True, hide_index=True)
else:
    st.write("لا توجد صفقات افتراضية حتى الآن.")
st.caption("الأسعار مولّدة عشوائياً لأغراض اختبار المشروع فقط.")
