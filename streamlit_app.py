import streamlit as st
from streamlit_gsheets import GSheetsConnection
import google.generativeai as genai
from docx import Document
import pandas as pd

# --- 1. 頁面設定 (分頁標籤名稱) ---
st.set_page_config(page_title="AI小線控(算報價)", layout="wide")

# 初始化 Google Sheets 連線
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 2. 側邊欄：即時參數 (匯率、票價、利潤) ---
with st.sidebar:
    st.header("⚡ 今日即時參數")
    exchange_rate = st.number_input("今日歐元匯率", value=35.0, step=0.1)
    airfare_base = st.number_input("機票票價 (TWD)", value=32000)
    airfare_tax = st.number_input("機票稅金 (TWD)", value=7500)
    profit_target = st.number_input("當團目標利潤 (TWD)", value=8000)
    st.divider()
    st.info("💡 匯率與票價請根據當日報價手動輸入，不連動 Excel。")

# --- 3. 讀取 Google Sheet 資料庫 ---
@st.cache_data(ttl=300)
def load_data():
    # 讀取分頁：每人固定, 均攤成本, 天數計價
    fixed_pax = conn.read(worksheet="每人固定")
    shared_costs = conn.read(worksheet="均攤成本")
    daily_costs = conn.read(worksheet="天數計價")
    return fixed_pax, shared_costs, daily_costs

# --- 網頁大標題 ---
st.title("🌍 AI小線控(算報價)")

try:
    db_fixed, db_shared, db_daily = load_data()
    st.caption("✅ 已成功連動 Google Sheets 資料庫")
except Exception as e:
    st.error(f"連動失敗，請檢查 Secrets 設定：{e}")
    st.stop()

# --- 4. 第一階段：上傳 Word 檔 ---
st.header("1. 上傳行程 Word 檔")
uploaded_file = st.file_uploader("請選擇 .docx 檔案", type=["docx"])

if uploaded_file:
    st.success("檔案上傳成功！AI 正在對照資料庫...")
    
    # 模擬天數判斷
    total_days = 10 
    
    # --- 5. 第二階段：線控檢查表 (修正語法錯誤處) ---
    st.header("2. 線控檢查表 (AI 自動對照結果)")
    
    itinerary_data = {
        "天數": ["D1", "D2", "D3", "D4"],
        "項目名稱": ["維也納音樂會", "布拉格城堡", "中式七菜一湯", "哈修塔特鹽礦"],
        "單價 (EUR)": [43.0, 19.0, 25.0, 40.0],
        "備註": ["自動抓取", "資料庫連動", "公版餐標", "資料庫連動"]
    }
    df_check = pd.DataFrame(itinerary_data)
    edited_df = st.data_editor(df_check, use_container_width=True)

    # --- 6. 第三階段：階梯式報價計算 ---
    if st.button("確認無誤，產出報價單"):
        st.divider()
        st.header("3. 階梯報價單 (含稅及利潤)")

        # 計算邏輯
        total_eur_fixed = edited_df["單價 (EUR)"].sum()
        # 確保 db_shared 抓到正確數值
        total_shared_eur = db_shared.iloc[:, 1].sum() if not db_shared.empty else 0
        
        # 模擬天數雜支計算
        daily_fee_twd = 550 

        pax_steps =
