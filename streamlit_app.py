import streamlit as st
import pandas as pd
import requests
from io import BytesIO

# --- 1. 頁面設定 ---
st.set_page_config(page_title="AI小線控(算報價)", layout="wide")

# Google Sheet 的原始網址
SHEET_URL = "https://docs.google.com/spreadsheets/d/1y53LHsJkDx2xA1MsLzkdd5FYQYWcfQrhs2KeSbsKbZk/export?format=xlsx"

# --- 2. 側邊欄 ---
with st.sidebar:
    st.header("⚡ 今日即時參數")
    exchange_rate = st.number_input("今日歐元匯率", value=35.0, step=0.1)
    airfare_base = st.number_input("機票票價 (TWD)", value=32000)
    airfare_tax = st.number_input("機票稅金 (TWD)", value=7500)
    profit_target = st.number_input("當團目標利潤 (TWD)", value=8000)

# --- 3. 讀取資料庫 (使用 Excel 導出模式，極度穩定) ---
@st.cache_data(ttl=300)
def load_data_v2():
    try:
        # 直接下載整個 Excel 檔案
        response = requests.get(SHEET_URL)
        with BytesIO(response.content) as f:
            # 分別讀取不同分頁
            fixed_pax = pd.read_excel(f, sheet_name="Fixed")
            shared_costs = pd.read_excel(f, sheet_name="Shared")
            daily_costs = pd.read_excel(f, sheet_name="Daily")
        return fixed_pax, shared_costs, daily_costs
    except Exception as e:
        st.error(f"資料讀取失敗，原因：{e}")
        return None, None, None

st.title("🌍 AI小線控(算報價)")

db_fixed, db_shared, db_daily = load_data_v2()

if db_fixed is not None:
    st.success("✅ 已成功連動 Google Sheets 資料庫")
    st.info("資料庫讀取成功！請開始進行報價作業。")
    
    # 這裡顯示資料庫內容讓你確認
    if st.checkbox("查看門票資料庫 (Fixed)"):
        st.write(db_fixed)
else:
    st.error("❌ 還是連不上。請檢查 Google Sheet 是否設為「知道連結的人均可檢視」。")

# --- 後續報價邏輯保持不變 ---
