import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# --- 1. 頁面設定 ---
st.set_page_config(page_title="AI小線控(算報價)", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 2. 側邊欄 ---
with st.sidebar:
    st.header("⚡ 今日即時參數")
    exchange_rate = st.number_input("今日歐元匯率", value=35.0, step=0.1)
    airfare_base = st.number_input("機票票價 (TWD)", value=32000)
    airfare_tax = st.number_input("機票稅金 (TWD)", value=7500)
    profit_target = st.number_input("當團目標利潤 (TWD)", value=8000)

# --- 3. 讀取資料庫 (已改為英文分頁) ---
@st.cache_data(ttl=300)
def load_data():
    # 注意：這裡的分頁名稱必須與 Google Sheet 一致
    fixed_pax = conn.read(worksheet="Fixed")
    shared_costs = conn.read(worksheet="Shared")
    daily_costs = conn.read(worksheet="Daily")
    return fixed_pax, shared_costs, daily_costs

st.title("🌍 AI小線控(算報價)")

try:
    db_fixed, db_shared, db_daily = load_data()
    st.caption("✅ 已成功連動 Google Sheets 資料庫")
except Exception as e:
    st.error(f"連動失敗，請檢查 Secrets 或分頁名稱：{e}")
    st.stop()

# --- 4. 簡易顯示測試 ---
st.info("資料庫讀取成功！請開始進行報價作業。")
if st.checkbox("查看門票資料庫 (Fixed)"):
    st.write(db_fixed)
