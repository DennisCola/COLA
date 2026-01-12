import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="線控核價 0112B-Final", layout="wide")

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
# 步驟 1: 匯入 (優化：副行改為完全空白)
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
                    
                    # 主列：顯示所有資訊
                    all_rows.append([day, point, lunch, True, dinner, True, tks[0], True, hotel, True])
                    
                    # 副列：將 "〃" 改為 "" (空字串)，達成逐行合併視覺感
                    if len(tks) > 1:
                        for extra in tks[1:]:
                            all_rows.append(["", "", "", False, "", False, extra, True, "", False])
            
            if all_rows:
                st.session_state.itinerary_df = pd.DataFrame(all_rows, columns=["天數", "行程大點", "午餐", "午?", "晚餐", "晚?", "門票", "門?", "旅館", "旅?"])
                st.session_state.stage = 2
                st.rerun()

# ==========================================
# 步驟 2: 勾選 (此時 5/6/7 列的其餘格子會是空的)
# ==========================================
elif st.session_state.stage == 2:
    st.subheader("步驟 2：確認計費項目")
    st.session_state.itinerary_df = st.data_editor(st.session_state.itinerary_df, use_container_width=True, key="editor_s2")
    
    if st.button("🪄 進行估價"):
        db = fetch_db()
        final_list = []
        def match_p(content, is_chk, database):
            if not is_chk or not content or content in ["", "-", "〃"]: return None
            for k, p in database.items():
                if k in str(content): return p
            return 0.0

        for _, row in st.session_state.itinerary_df.iterrows():
            final_list.append([
                row["天數"], row["行程大點"],
                row["午餐"], match_p(row["午餐"], row["午?"], db),
                row["晚餐"], match_p(row["晚餐"], row["晚?"], db),
                row["門票"], match_p(row["門票"], row
