import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="線控核價 0112B-4", layout="wide")

# --- 0. 資料庫連動 (GID 確認) ---
BASE_URL = "https://docs.google.com/spreadsheets/d/1y53LHsJkDx2xA1MsLzkdd5FYQYWcfQrhs2KeSbsKbZk/gviz/tq?tqx=out:csv"
GID_TICKET = "242124917"  # Ticket 門票
GID_MENU = "474017029"    # Menu 餐食

@st.cache_data(ttl=600)
def fetch_db():
    db = {}
    try:
        # 讀取 Menu
        df_m = pd.read_csv(f"{BASE_URL}&gid={GID_MENU}")
        if '項目名稱' in df_m.columns:
            for _, row in df_m.dropna(subset=['項目名稱', '單價']).iterrows():
                db[str(row['項目名稱']).strip()] = float(row['單價'])
        # 讀取 Ticket
        df_t = pd.read_csv(f"{BASE_URL}&gid={GID_TICKET}")
        if '項目名稱' in df_t.columns:
            for _, row in df_t.dropna(subset=['項目名稱', '單價']).iterrows():
                name = str(row['項目名稱']).strip()
                kw = str(row['判斷文字']).strip() if '判斷文字' in df_t.columns and pd.notna(row['判斷文字']) else name
                db[kw] = float(row['單價'])
    except: pass
    return db

# --- 1. Session 初始化 ---
if 'stage' not in st.session_state: st.session_state.stage = 1
if 'itinerary_df' not in st.session_state: st.session_state.itinerary_df = None

st.title("🛡️ 線控報價系統 (0112B-4)")

# ==========================================
# 步驟 1: 匯入轉換
# ==========================================
if st.session_state.stage == 1:
    st.subheader("步驟 1：匯入 AI Studio 文字")
    raw_input = st.text_area("請貼上文字內容：", height=200)
    
    if st.button("🚀 轉換並拆分門票"):
        if raw_input:
            # 移除空白行
            lines = [l.strip() for l in raw_input.split('\n') if l.strip()]
            all_rows = []
            
            for line in lines:
                # 過濾 Markdown 分隔符
                if re.match(r'^[|\s:-]+$', line): continue
                
                # 切分欄位 (支援 | 或 Tab 或多空格)
                parts = [p.strip() for p in (line.split('|') if '|' in line else re.split(r'\t| {2,}', line)) if p.strip()]
                
                if
