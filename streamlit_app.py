import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="線控核價引擎 0112A-Fixed", layout="wide")

# --- 0. 資料庫連動 (維持您的正確 GID) ---
BASE_URL = "https://docs.google.com/spreadsheets/d/1y53LHsJkDx2xA1MsLzkdd5FYQYWcfQrhs2KeSbsKbZk/gviz/tq?tqx=out:csv"
GID_TICKET = "242124917"  # Ticket
GID_MENU = "474017029"    # Menu

def fetch_db():
    db = {}
    try:
        df_menu = pd.read_csv(f"{BASE_URL}&gid={GID_MENU}")
        for _, row in df_menu.dropna(subset=['項目名稱', '單價']).iterrows():
            db[str(row['項目名稱']).strip()] = float(row['單價'])
        df_ticket = pd.read_csv(f"{BASE_URL}&gid={GID_TICKET}")
        for _, row in df_ticket.dropna(subset=['項目名稱', '單價']).iterrows():
            name = str(row['項目名稱']).strip()
            keyword = str(row['判斷文字']).strip() if '判斷文字' in df_ticket.columns and pd.notna(row['判斷文字']) else name
            db[keyword] = float(row['單價'])
    except:
        pass
    return db

# --- 初始化 Session State (核心修復：確保資料持續性) ---
if 'stage' not in st.session_state:
    st.session_state.stage = 1
if 'itinerary_df' not in st.session_state:
    st.session_state.itinerary_df = None
if 'final_df' not in st.session_state:
    st.session_state.final_df = None

st.title("🛡️ 0112A 線控專業核價系統 (穩定修復版)")

# ==========================================
# 步驟 1: 匯入 (6轉10)
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
                cells = [c.strip() for c in (l.split('|') if '|' in l else re.split(r'\t| {2,}', l)) if c.strip()]
                if len(cells) >= 6: rows.append(cells[:6])
            
            if rows:
                temp_df = pd.DataFrame(rows, columns=["天數", "行程大點", "午餐", "晚餐", "門票", "旅館"])
                # 建立 10 行結構
                for col in ["午?", "晚?", "門?", "旅?"]: temp_df[col] = True
                st.session_state.itinerary_df = temp_df[["天數", "行程大點", "午餐", "午?", "晚餐", "晚?", "門票", "門?", "旅館", "旅?"]]
                st.session_state.stage = 2
                st.rerun()

# ==========================================
# 步驟 2: 勾選 (修復此處掛掉的問題)
# ==========================================
elif st.session_state.stage == 2:
    st.subheader("步驟 2：確認計費項目")
    st.info("💡 請勾選需要計算成本的項目。")
    
    # 核心修復：將編輯器的結果直接存回 session_state
    st.session_state.itinerary_df = st.data_editor(
        st.session_state.itinerary_df, 
        use_container_width=True, 
        key="s2_editor_fixed"
    )
    
    if st.button("🪄 進行估價 (前往步驟 3)"):
        with st.spinner("對照資料庫中..."):
            db = fetch_db()
            final_rows = []
            # 讀取剛才在編輯器裡勾選完的最新資料
            for _, row in st.session_state.itinerary_df.iterrows():
                def get_price(content, is_checked):
                    if not is_checked: return None
                    c_str = str(content)
                    for k, p in db.items():
                        if k in c_str: return p
                    return 0.0

                final_rows.append([
                    row["天數"], row["行程大點"], 
                    row["午餐"], get_price(row["午餐"], row["午?"]),
                    row["晚餐"], get_price(row["晚餐"], row["晚?"]),
                    row["門票"], get_price(row["門票"], row["門?"]),
                    row["旅館"], get_price(row["旅館"], row["旅?"])
                ])
            
            st.session_state.final_df = pd.DataFrame(final_rows, columns=["天數", "行程大點", "午餐", "午價", "晚餐", "晚價", "門票", "門價", "旅館", "旅價"])
            st.session_state.stage = 3
            st.rerun()

# ==========================================
# 步驟 3: 最終核價
# ==========================================
elif st.session_state.stage == 3:
    st.subheader("步驟 3：建議預算與手動調整")
    
    st.session_state.final_df = st.data_editor(
        st.session_state.final_df,
        use_container_width=True,
        column_config={
            "午價": st.column_config.NumberColumn("EUR", format="€%.1f"),
            "晚價": st.column_config.NumberColumn("EUR", format="€%.1f"),
            "門價": st.column_config.NumberColumn("EUR", format="€%.1f"),
            "旅價": st.column_config.NumberColumn("EUR", format="€%.1f"),
        },
        key="s3_editor_fixed"
    )
    
    # 計算加總
    cost_cols = ["午價", "晚價", "門價", "旅價"]
    total_eur = st.session_state.final_df[cost_cols].apply(pd.to_numeric, errors='coerce').sum().sum()
    
    st.divider()
    c1, c2, c3 = st.columns(3)
    with c1: ex_rate = st.number_input("歐元匯率", value=35.5)
    with c2: st.metric("地接總預算", f"€ {total_eur:,.1f}")
    with c3: st.metric("換算台幣", f"NT$ {int(total_eur * ex_rate):,}")
        
    if st.button("⬅️ 重置回第一步"):
        st.session_state.stage = 1
        st.session_state.itinerary_df = None
        st.session_state.final_df = None
        st.rerun()
