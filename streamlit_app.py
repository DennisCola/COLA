import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="線控三階段核價 0112A-Final", layout="wide")

# --- 0. 資料庫連動 (增加容錯處理) ---
SHEET_BASE = "https://docs.google.com/spreadsheets/d/1y53LHsJkDx2xA1MsLzkdd5FYQYWcfQrhs2KeSbsKbZk/export?format=csv"
GID_MENU = "242124917"   
GID_TICKET = "0"         

def fetch_comprehensive_db():
    db = {}
    try:
        # 讀取 Menu
        df_menu = pd.read_csv(f"{SHEET_BASE}&gid={GID_MENU}")
        for _, row in df_menu.dropna(subset=['項目名稱', '單價']).iterrows():
            db[str(row['項目名稱']).strip()] = float(row['單價'])
        # 讀取 Ticket
        df_ticket = pd.read_csv(f"{SHEET_BASE}&gid={GID_TICKET}")
        for _, row in df_ticket.dropna(subset=['項目名稱', '單價']).iterrows():
            name = str(row['項目名稱']).strip()
            keyword = str(row['判斷文字']).strip() if pd.notna(row.get('判斷文字')) else name
            db[keyword] = float(row['單價'])
    except Exception as e:
        st.error(f"資料庫讀取提醒: {e} (將使用手動輸入模式)")
    return db

# --- 初始化 Session State ---
if 'stage' not in st.session_state:
    st.session_state.stage = 1
if 'df_data' not in st.session_state:
    st.session_state.df_data = None
if 'final_df' not in st.session_state:
    st.session_state.final_df = None

st.title("🛡️ 線控專業報價系統 0112A")

# ==========================================
# 步驟 1: 轉換 6 行 ⮕ 10 行
# ==========================================
if st.session_state.stage == 1:
    st.subheader("步驟 1：匯入行程文字")
    raw_input = st.text_area("請貼上 AI Studio 的 6 行文字：", height=200)
    
    if st.button("轉換並進入下一步"):
        if raw_input:
            lines = [l.strip() for l in raw_input.strip().split('\n') if l.strip()]
            rows = []
            for l in lines:
                if re.match(r'^[|\s:-]+$', l): continue
                cells = [c.strip() for c in (l.split('|') if '|' in l else re.split(r'\t| {2,}', l)) if c.strip()]
                if len(cells) >= 6:
                    rows.append(cells[:6])
            
            if rows:
                temp_df = pd.DataFrame(rows, columns=["天數", "行程大點", "午餐", "晚餐", "門票", "旅館"])
                # 建立 10 行結構
                temp_df["午?"] = True
                temp_df["晚?"] = True
                temp_df["門?"] = True
                temp_df["旅?"] = True
                st.session_state.df_data = temp_df[["天數", "行程大點", "午餐", "午?", "晚餐", "晚?", "門票", "門?", "旅館", "旅?"]]
                st.session_state.stage = 2
                st.rerun()

# ==========================================
# 步驟 2: 勾選決策
# ==========================================
elif st.session_state.stage == 2:
    st.subheader("步驟 2：勾選計入成本項目")
    # 使用 key 確保編輯後的內容被保存
    edited_s2 = st.data_editor(st.session_state.df_data, use_container_width=True, key="s2_editor")
    
    if st.button("🪄 進行估價 (前往步驟 3)"):
        db = fetch_comprehensive_db()
        final_rows = []
        for _, row in edited_s2.iterrows():
            def get_price(content, is_checked):
                if not is_checked: return None 
                content_str = str(content)
                for key, price in db.items():
                    if key in content_str: return price
                return
