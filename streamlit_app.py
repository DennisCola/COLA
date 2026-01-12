import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="線控核價引擎 0112B-1", layout="wide")

# --- 0. 資料庫連動 (GID 保持正確) ---
BASE_URL = "https://docs.google.com/spreadsheets/d/1y53LHsJkDx2xA1MsLzkdd5FYQYWcfQrhs2KeSbsKbZk/gviz/tq?tqx=out:csv"
GID_TICKET = "242124917"  # Ticket 門票
GID_MENU = "474017029"    # Menu 餐食

def fetch_db():
    db = {}
    try:
        df_menu = pd.read_csv(f"{BASE_URL}&gid={GID_MENU}").dropna(subset=['項目名稱', '單價'])
        for _, row in df_menu.iterrows(): db[str(row['項目名稱']).strip()] = float(row['單價'])
        df_ticket = pd.read_csv(f"{BASE_URL}&gid={GID_TICKET}").dropna(subset=['項目名稱', '單價'])
        for _, row in df_ticket.iterrows():
            kw = str(row['判斷文字']).strip() if '判斷文字' in df_ticket.columns and pd.notna(row['判斷文字']) else str(row['項目名稱']).strip()
            db[kw] = float(row['單價'])
    except: pass
    return db

# --- 初始化 Session ---
if 'stage' not in st.session_state: st.session_state.stage = 1
if 'itinerary_df' not in st.session_state: st.session_state.itinerary_df = None

st.title("🛡️ 線控專業核價系統 (0112B-1)")

# ==========================================
# 步驟 1: 匯入與拆分
# ==========================================
if st.session_state.stage == 1:
    st.subheader("步驟 1：匯入行程")
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
                    
                    # 拆分門票關鍵字
                    ticket_list = re.split(r'\+|、|\n', ticket)
                    ticket_list = [t.strip() for t in ticket_list if t.strip()]
                    
                    # 第一列 (主列)
                    final_rows.append([day, point, lunch, True, dinner, True, ticket_list[0], True, hotel, True])
                    
                    # 如果有第二個門票，產生副列 (視覺合併：其餘留白且不勾選)
                    if len(ticket_list) > 1:
                        for extra_t in ticket_list[1:]:
                            final_rows.append(["〃", "〃", "", False, "", False, extra_t, True, "", False])
            
            st.session_state.itinerary_df = pd.DataFrame(final_rows, columns=["天數", "行程大點", "午餐", "午?", "晚餐", "晚?", "門票", "門?", "旅館", "旅?"])
            st.session_state.stage = 2
            st.rerun()

# ==========================================
# 步驟 2: 勾選
# ==========================================
elif st.session_state.stage == 2:
    st.subheader("步驟 2：確認計費項目")
    # 強制將編輯後的內容存回 session
    st.session_state.itinerary_df = st.data_editor(st.session_state.itinerary_df, use_container_width=True, key="s2_b1")
    
    if st.button("🪄 進行估價 (前往步驟 3)"):
        db = fetch_db()
        final_rows = []
        for _, row in st.session_state.itinerary_df.iterrows():
            def get_p(content, is_checked):
                if not is_checked or not content or content == "〃": return None
                for k, p in db.items():
                    if k in str(content): return p
                return 0.0

            final_rows.append([
                row["天數"], row["行程大點"], 
                row["午餐"], get_p(row["午餐"], row["午?"]),
                row["晚餐"], get_p(row["晚餐"], row["晚?"]),
                row["門票"], get_p(row["門票"], row["門?"]),
