import streamlit as st
import pandas as pd
import requests
from io import BytesIO

# --- 1. 頁面設定 ---import streamlit as st
import pandas as pd
import requests
from io import BytesIO

# --- 1. 頁面設定 ---
st.set_page_config(page_title="AI小線控(算報價)", layout="wide")

# Google Sheet 的原始網址 (自動下載 Excel 格式)
SHEET_URL = "https://docs.google.com/spreadsheets/d/1y53LHsJkDx2xA1MsLzkdd5FYQYWcfQrhs2KeSbsKbZk/export?format=xlsx"

# --- 2. 側邊欄：今日報價參數 ---
with st.sidebar:
    st.header("⚡ 今日即時參數")
    exchange_rate = st.number_input("今日歐元匯率", value=35.0, step=0.1)
    airfare_base = st.number_input("機票票價 (TWD)", value=32000)
    airfare_tax = st.number_input("機票稅金 (TWD)", value=7500)
    profit_target = st.number_input("當團目標利潤 (TWD)", value=8000)
    st.divider()
    st.info("💡 匯率與票價手動輸入，不連動 Excel。")

# --- 3. 讀取資料庫 ---
@st.cache_data(ttl=300)
def load_data_v2():
    try:
        response = requests.get(SHEET_URL)
        with BytesIO(response.content) as f:
            # 同時讀取三個分頁
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
    
    # --- 讓你可以查看不同分頁的資料 ---
    st.header("🔍 資料庫內容檢查")
    tab1, tab2, tab3 = st.tabs(["📌 每人固定 (Fixed)", "🤝 均攤成本 (Shared)", "📅 天數計價 (Daily)"])
    
    with tab1:
        st.dataframe(db_fixed, use_container_width=True)
    with tab2:
        st.dataframe(db_shared, use_container_width=True)
    with tab3:
        st.dataframe(db_daily, use_container_width=True)
    
    st.divider()
    
    # --- 4. 上傳與計算邏輯 ---
    st.header("1. 上傳行程 Word 檔")
    uploaded_file = st.file_uploader("請選擇 .docx 檔案", type=["docx"])

    if uploaded_file:
        st.info("檔案已上傳。下一個版本我將為您串接 AI 辨識邏輯！")
        # 這裡之後會放 AI 辨識程式碼...
else:
    st.error("❌ 連線異常，請確認 Google Sheet 已開啟「知道連結的使用者皆可檢視」。")
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

