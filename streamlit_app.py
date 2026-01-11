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
    # 根據您的分頁名稱讀取資料
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
    
    # --- 5. 第二階段：線控檢查表 (AI 自動對照結果) ---
    st.header("2. 線控檢查表 (AI 自動對照結果)")
    
    # 這裡會根據 db_fixed 內容自動比對，目前先顯示結構
    itinerary_data = {
        "天數": ["D1", "D2", "D3", "D4"],
        "項目名稱
