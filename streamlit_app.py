import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="線控核價引擎 0112A-Final", layout="wide")

# --- 0. 資料庫連動 (更新 GID 對應) ---
BASE_URL = "https://docs.google.com/spreadsheets/d/1y53LHsJkDx2xA1MsLzkdd5FYQYWcfQrhs2KeSbsKbZk/gviz/tq?tqx=out:csv"

# 根據你的最新提供進行修正
GID_TICKET = "242124917"  # Ticket 門票分頁
GID_MENU = "474017029"    # Menu 餐食分頁

@st.cache_data(ttl=600) # 快取 10 分鐘，避免頻繁抓取
def fetch_db():
    db = {}
    try:
        # 1. 抓取 Menu (餐食)
        df_menu = pd.read_csv(f"{BASE_URL}&gid={GID_MENU}")
        df_menu = df_menu.dropna(subset=['項目名稱', '單價'])
        for _, row in df_menu.iterrows():
            db[str(row['項目名稱']).strip()] = float(row['單價'])
            
        # 2. 抓取 Ticket (門票)
        df_ticket = pd.read_csv(f"{BASE_URL}&gid={GID_TICKET}")
        df_ticket = df_ticket.dropna(subset=['項目名稱', '單價'])
        for _, row in df_ticket.iterrows():
            name = str(row['項目名稱']).strip()
            # 優先使用判斷文字，若無則用品項名稱
            keyword = str(row['判斷文字']).strip() if '判斷文字' in df_ticket.columns and pd.notna(row['判斷文字']) else name
            db[keyword] = float(row['單價'])
            
        return db
    except Exception as e:
        st.error(f"⚠️ 雲端資料庫讀取失敗: {e}")
        return {}

# --- 初始化 Session State ---
if 'stage' not in st.session_state:
    st.session_state.stage = 1
if 'df_data' not in st.session_state:
    st.session_state.df_data = None
if 'final_df' not in st.session_state:
    st.session_state.final_df = None

st.title("🛡️ 0112A 線控專業核價系統")

# ==========================================
# 步驟 1: 6 行轉 10 行
# ==========================================
if st.session_state.stage == 1:
    st.subheader("步驟 1：匯入 AI Studio 內容")
    raw_input = st.text_area("請貼上文字內容：", height=150)
    if st.button("轉換並進入步驟 2"):
        if raw_input:
            lines = [l.strip() for l in raw_input.strip().split('\n') if l.strip()]
            rows = []
            for l in lines:
                if re.match(r'^[|\s:-]+$', l): continue
                # 模糊辨識：支援 | 或 兩個以上空格
                cells = [c.strip() for c in (l.split('|') if '|' in l else re.split(r'\t| {2,}', l)) if c.strip()]
                if len(cells) >= 6: rows.append(cells[:6])
            
            if rows:
                temp_df = pd.DataFrame(rows, columns=["天數", "行程大點", "午餐", "晚餐", "門票", "旅館"])
                for col in ["午?", "晚?", "門?", "旅?"]: temp_df[col] = True
                # 重新排列為 10 行結構
                st.session_state.df_data = temp_df[["天數", "行程大點", "午餐", "午?", "晚餐", "晚?", "門票", "門?", "旅館", "旅?"]]
                st.session_state.stage = 2
                st.rerun()

#
