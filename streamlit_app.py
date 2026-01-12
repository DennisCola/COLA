import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="線控核價引擎 0112B13", layout="wide")

# --- 0. 資料庫連動 (GID 保持正確) ---
BASE_URL = "https://docs.google.com/spreadsheets/d/1y53LHsJkDx2xA1MsLzkdd5FYQYWcfQrhs2KeSbsKbZk/gviz/tq?tqx=out:csv"
GID_TICKET = "242124917"
GID_MENU = "474017029"

@st.cache_data(ttl=300)
def fetch_db():
    db = {}
    try:
        df_m = pd.read_csv(f"{BASE_URL}&gid={GID_MENU}")
        for _, r in df_m.dropna(subset=['項目名稱', '單價']).iterrows():
            db[str(r['項目名稱']).strip()] = float(r['單價'])
        df_t = pd.read_csv(f"{BASE_URL}&gid={GID_TICKET}")
        for _, r in df_t.dropna(subset=['項目名稱', '單價']).iterrows():
            nm = str(r['項目名稱']).strip()
            kw = str(r['判斷文字']).strip() if '判斷文字' in df_t.columns and pd.notna(r['判斷文字']) else nm
            db[kw] = float(r['單價'])
    except: pass
    return db

if 'stage' not in st.session_state: st.session_state.stage = 1
if 'itinerary_df' not in st.session_state: st.session_state.itinerary_df = None

st.title("🛡️ 0112B13 線控核價系統")

# ==========================================
# 步驟 1: 匯入與拆分 (副行欄位留白)
# ==========================================
if st.session_state.stage == 1:
    st.subheader("步驟 1：匯入行程內容")
    raw_input = st.text_area("請在此貼上文字：", height=200)
    if st.button("🚀 生成表格"):
        if raw_input:
            lines = [l.strip() for l in raw_input.split('\n') if l.strip()]
            all_rows = []
            for line in lines:
                if re.match(r'^[|\s:-]+$', line): continue
                parts = [p.strip() for p in (line.split('|') if '|' in line else re.split(r'\t| {2,}', line)) if p.strip()]
                if len(parts) >= 1:
                    while len(parts) < 6: parts.append("-")
                    day, point, lunch, dinner, ticket, hotel = parts[:6]
                    tks = [t.strip() for t in re.split(r'\+|、', ticket) if t.strip()]
                    if not tks: tks = ["-"]
                    # 主列
                    all_rows.append([day, point, lunch, True, dinner, True, tks[0], True, hotel, True])
                    # 副列 (視覺合併效果：除門票外全部留白)
                    if len(tks) > 1:
                        for extra in tks[1:]:
                            all_rows.append(["", "", "", False, "", False, extra, True, "", False])
            if all_rows:
                st.session_state.itinerary_df = pd.DataFrame(all_rows, columns=["天數", "行程大點", "午餐", "午?", "晚餐", "晚?", "門票", "門?", "旅館", "旅?"])
                st.session_state.stage = 2
                st.rerun()

# ==========================================
# 步驟 2: 勾選決策
# ==========================================
elif st.session_state.stage == 2:
    st.subheader("步驟 2：確認計費項目")
    st.session_state.itinerary_df = st.data_editor(st.session_state.itinerary_df, use_container_width=True, key="ed_s2")
    if st.button("🪄 開始估價"):
        db = fetch_db()
        final_list = []
        def match_p(content, is_chk, database):
            if not is_chk or not content or str(content).strip() in ["", "-", "〃"]: return None
            for k, p in database.items():
                if k in str(content): return p
            return 0.0
        for _, row in st.session_state.itinerary_df.iterrows():
            # 簡化邏輯確保不被截斷
            p_l = match_p(row["午餐"], row["午?"], db)
            p_d = match_p(row["晚餐"], row["晚?"], db)
            p_t = match_p(row["門票"], row["門?"], db)
            p_h = match_p(row["旅館"], row["旅?"], db)
            final_list.append([row["天數"], row["行程大點"], row["午餐"], p_l, row["晚餐"], p_d, row["門票"], p_t, row["旅館"], p_h])
        st.session_state.final_df = pd.DataFrame(final_list, columns=["天數", "行程大點", "午餐", "午價", "晚餐", "晚價", "門票", "門價", "旅館", "旅價"])
        st.session_state.stage = 3
        st.rerun()

# ==========================================
# 步驟 3: 核價總結
# ==========================================
elif st.session_state.stage == 3:
    st.subheader("步驟 3：調整單價 (EUR)")
    final_edit = st.data_editor(st.session_state.final_df, use_container_width=True,
        column_config={
            "午價": st.column_config.NumberColumn(format="€%.1f"),
            "晚價": st.column_config.NumberColumn(format="€%.1f"),
            "門價": st.column_config.NumberColumn(format="€%.1f"),
            "旅價": st.column_config.NumberColumn(format="€%.1f"),
        }, key="ed_s3")
    total = final_edit[["午價", "晚價", "門價", "旅價"]].apply(pd.to_numeric, errors='coerce').sum().sum()
    st.divider()
    c1, c2 = st.columns(2)
    with c1: ex = st.number_input("匯率 (EUR/TWD)", value=35.5)
    with c2: st.metric("地接總預算 (EUR)", f"€ {total:,.1f}", help=f"約 NT$ {int(total * ex):,}")
    if st.button("⬅️ 重置"):
        st.session_state.stage = 1
        st.session_state.itinerary_df = None
        st.rerun()
