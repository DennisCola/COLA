import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="線控三階段核價引擎 0112A-Update", layout="wide")

# --- 0. 資料庫連動 (讀取更新後的 GEMINI 的養分) ---
SHEET_BASE = "https://docs.google.com/spreadsheets/d/1y53LHsJkDx2xA1MsLzkdd5FYQYWcfQrhs2KeSbsKbZk/export?format=csv"

# 更新後的分頁 GID (請根據實際試算表網址中的 gid 調整，以下為對應你提供資料的設定)
# 註：如果 gid 有變動，請以此處為準
GID_MENU = "242124917"   # Menu 分頁
GID_TICKET = "0"         # Ticket 分頁
GID_SHARED = "109355798" # Shared 分頁 (導遊/大項)
GID_DAILY = "474017029"  # Daily 分頁 (耳機/網卡)

def fetch_comprehensive_db():
    try:
        # 抓取 Menu (餐食)
        df_menu = pd.read_csv(f"{SHEET_BASE}&gid={GID_MENU}")
        # 抓取 Ticket (門票)
        df_ticket = pd.read_csv(f"{SHEET_BASE}&gid={GID_TICKET}")
        
        db = {}
        # 處理 Menu 資料
        for _, row in df_menu.dropna(subset=['項目名稱', '單價']).iterrows():
            db[str(row['項目名稱']).strip()] = float(row['單價'])
            
        # 處理 Ticket 資料 (包含判斷文字)
        for _, row in df_ticket.dropna(subset=['項目名稱', '單價']).iterrows():
            name = str(row['項目名稱']).strip()
            # 優先使用判斷文字來對話，否則用品項名稱
            keyword = str(row['判斷文字']).strip() if pd.notna(row['判斷文字']) else name
            db[keyword] = float(row['單價'])
            
        return db
    except Exception as e:
        # 預備方案
        return {"六菜一湯": 18.0, "米其林": 75.0, "城堡區門票": 19.0}

# --- 初始化 Session State ---
if 'stage' not in st.session_state:
    st.session_state.stage = 1
if 'df_data' not in st.session_state:
    st.session_state.df_data = None

st.title("🛡️ 線控專業報價系統 0112A (分頁更新版)")

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
                if len(cells) >= 2:
                    while len(cells) < 6: cells.append("-")
                    rows.append(cells[:6])
            
            st.session_state.df_data = pd.DataFrame(rows, columns=["天數", "行程大點", "午餐", "晚餐", "門票", "旅館"])
            st.session_state.df_data["午?"] = True
            st.session_state.df_data["晚?"] = True
            st.session_state.df_data["門?"] = True
            st.session_state.df_data["旅?"] = True
            st.session_state.df_data = st.session_state.df_data[["天數", "行程大點", "午餐", "午?", "晚餐", "晚?", "門票", "門?", "旅館", "旅?"]]
            st.session_state.stage = 2
            st.rerun()

# ==========================================
# 步驟 2: 勾選決策
# ==========================================
elif st.session_state.stage == 2:
    st.subheader("步驟 2：勾選本階段計入成本之項目")
    edited_s2 = st.data_editor(st.session_state.df_data, use_container_width=True)
    
    if st.button("🪄 進行估價 (讀取新分頁資料)"):
        db = fetch_comprehensive_db()
        final_rows = []
        for _, row in edited_s2.iterrows():
            def get_price(content, is_checked):
                if not is_checked: return None # 未勾選則鎖定
                content_str = str(content)
                for key, price in db.items():
                    if key in content_str: return price
                return 0.0

            p_午 = get_price(row["午餐"], row["午?"])
            p_晚 = get_price(row["晚餐"], row["晚?"])
            p_門 = get_price(row["門票"], row["門?"])
            p_旅 = get_price(row["旅館"], row["旅?"])
            
            final_rows.append([row["天數"], row["行程大點"], row["午餐"], p_午, row["晚餐"], p_晚, row["門票"], p_門, row["旅館"], p_旅])
        
        st.session_state.final_df = pd.DataFrame(final_rows, columns=["天數", "行程大點", "午餐", "午預算", "晚餐", "晚預算", "門票", "門預算", "旅館", "旅預算"])
        st.session_state.stage = 3
        st.rerun()

# =
