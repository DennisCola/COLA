import streamlit as st
import pandas as pd
import io
import re

st.set_page_config(page_title="線控黃金 10 行系統 0112A-Lock", layout="wide")

# --- 1. 連動 Google Sheet 資料庫 (保持 0112A 穩定性) ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1y53LHsJkDx2xA1MsLzkdd5FYQYWcfQrhs2KeSbsKbZk/export?format=csv&gid=242124917"

def fetch_db_prices():
    try:
        db_df = pd.read_csv(SHEET_URL)
        return dict(zip(db_df.iloc[:, 0].astype(str), db_df.iloc[:, 1].astype(float)))
    except:
        return {"六菜一湯": 18.0, "米其林": 75.0, "美泉宮": 22.0, "霍夫堡": 18.0}

# --- 2. 介面設計 ---
st.title("🛡️ 0112A+ 線控自動核價引擎 (鎖定版)")
st.caption("功能：未勾選項目在配對後將自動歸零且不可計費")

raw_input = st.text_area("1. 請在此貼上 AI Studio 內容：", height=150)

if raw_input:
    try:
        # --- A. 0112A 解析邏輯 ---
        lines = [l.strip() for l in raw_input.strip().split('\n') if l.strip()]
        rows = []
        for l in lines:
            if re.match(r'^[|\s:-]+$', l): continue
            if '|' in l:
                cells = [c.strip() for c in l.split('|') if c.strip()]
            else:
                cells = re.split(r'\t| {2,}', l)
                cells = [c.strip() for c in cells if c.strip()]
            if len(cells) >= 2:
                while len(cells) < 6: cells.append("-")
                rows.append(cells[:6])
        
        if rows:
            # 初始化資料 (如果 session_state 裡還沒有)
            if 'itinerary_df' not in st.session_state:
                new_data = []
                for r in rows:
                    new_data.append([r[0], r[1], r[2], True, r[3], True, r[4], True, r[5], True, 0.0])
                col_names = ["天數", "行程大點", "午餐", "午?", "晚餐", "晚?", "門票", "門?", "旅館", "旅?", "EUR單價"]
                st.session_state.itinerary_df = pd.DataFrame(new_data, columns=col_names)

            # --- B. 10 行核價工作台 ---
            st.subheader("📍 10 行核價工作台 (步驟 1: 確認內容與勾選項目)")
            
            # 使用 data_editor
            edited_df = st.data_editor(
                st.session_state.itinerary_df, 
                use_container_width=True, 
                num_rows="dynamic",
                key="editor_1"
            )

            # --- C. 按鈕：開始配對 (執行鎖定與歸零邏輯) ---
            st.write("---")
            if st.button("🪄 步驟 2：開始資料庫單價配對 (並鎖定未勾選項)"):
                with st.spinner("正在計算並執行合約排除邏輯..."):
                    db = fetch_db_prices()
                    
                    def match_and_lock_logic(row):
                        total = 0.0
                        check_list = [("午餐", "午?"), ("晚餐", "晚?"), ("門票", "門?"), ("旅館", "旅?")]
                        
                        for content_col, check_col in check_list:
                            # 關鍵邏輯：只有「打勾」且「非合約包含」才去 DB 找價格
                            if row[check_col]: 
                                content = str(row[content_col])
                                found = False
                                for key, price in db.items():
                                    if key in content:
                                        total += price
                                        found = True
                                        break
                                # 如果沒找到價格，則維持原樣(可供手動填寫)
                            else:
                                # 未打勾，該項對應的單價貢獻必為 0
                                pass 
                        return total

                    edited_df["EUR單價"] = edited_df.apply(match_and_lock_logic, axis=1)
                    st.session_state.itinerary_df = edited_df
                    st.success("✅ 配對完成！未勾選項目之成本已自動排除。")
                    st.rerun()

            # --- D. 安全計算 ---
            total_eur = pd.to_numeric(edited_df["EUR單價"], errors='coerce').sum()
            
            c1, c2 = st.columns(2)
            with c1:
                ex_rate = st.number_input("今日歐元匯率", value=35.5, step=0.1)
            with c2:
                st.metric("地接總預算 (EUR)", f"€ {total_eur:,.1f}")
                st.write(f"📊 換算台幣：**NT$ {int(total_eur * ex_rate):,}**")

    except Exception as e:
        st.error(f"❌ 0112A 轉換失敗: {e}")
