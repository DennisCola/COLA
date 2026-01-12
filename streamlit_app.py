import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="線控核價 0112B-Final Plus", layout="wide")

# --- 0. 資料庫連動 ---
BASE_URL = "https://docs.google.com/spreadsheets/d/1y53LHsJkDx2xA1MsLzkdd5FYQYWcfQrhs2KeSbsKbZk/gviz/tq?tqx=out:csv"
GID_TICKET = "242124917"
GID_MENU = "474017029"

@st.cache_data(ttl=300)
def fetch_db():
    db = {}
    try:
        df_m = pd.read_csv(f"{BASE_URL}&gid={GID_MENU}")
        for _, row in df_m.dropna(subset=['項目名稱', '單價']).iterrows():
            db[str(row['項目名稱']).strip()] = float(row['單價'])
        df_t = pd.read_csv(f"{BASE_URL}&gid={GID_TICKET}")
        for _, row in df_t.dropna(subset=['項目名稱', '單價']).iterrows():
            name = str(row['項目名稱']).strip()
            kw = str(row['判斷文字']).strip() if '判斷文字' in df_t.columns and pd.notna(row['判斷文字']) else name
            db[kw] = float(row['單價'])
    except: pass
    return db

if 'stage' not in st.session_state: st.session_state.stage = 1
if 'itinerary_df' not in st.session_state: st.session_state.itinerary_df = None

st.title("🛡️ 線控報價系統 (0112B-Final Plus)")

# ==========================================
# 步驟 1: 匯入 (副行改為完全空白)
# ==========================================
if st.session_state.stage == 1:
    st.subheader("步驟 1：貼上行程文字")
    raw_input = st.text_area("請在此貼上內容：", height=250)
    
    if st.button("🚀 轉換並生成表格"):
        if raw_input:
            lines = [l.strip() for l in raw_input.split('\n') if l.strip()]
            all_rows = []
            for line in lines:
                if re.match(r'^[|\s:-]+$', line): continue
                parts = [p.strip() for p in (line.split('|') if '|' in line else re.split(r'\t| {2,}', line)) if p.strip()]
                if len(parts) >= 1:
                    while len(parts) < 6: parts.append("-")
                    day, point, lunch, dinner, ticket, hotel = parts[:6]
                    tks = re.split(r'\+|、', ticket)
                    tks = [t.strip() for t in tks if t.strip()]
                    if not tks: tks = ["-"]
                    
                    # 主列 (Day X 資訊)
                    all_rows.append([day, point, lunch, True, dinner, True, tks[0], True, hotel, True])
                    
                    # 副列 (其餘格子留白 "")
                    if len(tks) > 1:
                        for extra in tks[1:]:
                            all_rows.append(["", "", "", False, "", False, extra, True, "", False])
            
            if all_rows:
                st.session_state.itinerary_df = pd.DataFrame(all
