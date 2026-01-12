import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="線控核價引擎 0112B-3", layout="wide")

# --- 0. 資料庫連動 (GID 保持正確) ---
BASE_URL = "https://docs.google.com/spreadsheets/d/1y53LHsJkDx2xA1MsLzkdd5FYQYWcfQrhs2KeSbsKbZk/gviz/tq?tqx=out:csv"
GID_TICKET = "242124917"  # Ticket 門票
GID_MENU = "474017029"    # Menu 餐食

def fetch_db():
    db = {}
    try:
        df_menu = pd.read_csv(f"{BASE_URL}&gid={GID_MENU}").dropna(subset=['項目名稱', '單價'])
        for _, row in df_menu.iterrows():
            db[str(row['項目名稱']).strip()] = float(row['單價'])
        
        df_ticket = pd.read_csv(f"{BASE_URL}&gid={GID_TICKET}").dropna(subset=['項目名稱', '單價'])
        for _, row in df_ticket.iterrows():
            name = str(row['項目名稱']).strip()
            kw = str(row['判斷文字']).strip() if '判斷文字' in df_ticket.columns and pd.notna(row['判斷文字']) else name
            db[kw] = float(row['單價'])
    except:
        pass
    return db

# --- 初始化 Session ---
if 'stage' not in st.session_state:
    st.session_state.stage = 1
if 'itinerary_df' not in st.session_state:
    st.session_state.itinerary_df = None
if 'final_df' not in st.session_state:
    st.session_state.final_df = None

st.title("🛡️ 線控專業核價系統 (0112B-3)")

# ==========================================
# 步驟 1: 匯入與拆分 (修正語法錯誤)
# ==========================================
if st.session_state.stage == 1:
    st.subheader("步驟 1：匯入行程內容")
    raw_input = st.text_area("請貼上文字內容：", height=150)
    
    if st.button("轉換並處理多門票"):
        if raw_input:
            lines = [l.strip() for l in raw_input.strip().split('\n') if l.strip()]
            final_rows = []
            for l in lines:
                if re.match(r'^[|\s:-]+$', l): continue
                cells = [c.strip() for c in (l.split('|') if '|' in l else re.split(r'\t| {2,}', l)) if c.strip()]
                if len(cells) >= 6:
                    day, point, lunch, dinner, ticket, hotel = cells[:6]
                    
                    # 門票拆分邏輯：支援 +、、以及空格
                    t_list = re.split(r'\+|、', ticket)
                    t_list = [t.strip() for t in t_list if t.strip()]
                    if not t_list: t_list
