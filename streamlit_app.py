import streamlit as st
import pandas as pd
import io
import re

st.set_page_config(page_title="線控專業試算台", layout="wide")

st.title("⚡ 線控行程快轉與深度編輯")
st.caption("流程：AI Studio 貼上文字 ⮕ 手動微調內容與成本 ⮕ 報價完成")

# 1. 貼上區
raw_input = st.text_area("1. 請貼上從 AI Studio 複製的內容：", height=200, 
                         placeholder="直接全選、複製、貼上到這裡...")

if raw_input:
    try:
        # --- 自動清理格式 ---
        lines = raw_input.strip().split('\n')
        clean_lines = [l for l in lines if not re.match(r'^[|\s:-]+$', l)]
        
        if '|' in clean_lines[0]:
            df = pd.read_csv(io.StringIO('\n'.join(clean_lines)), sep="|", skipinitialspace=True).dropna(axis=1, how='all')
        else:
            df = pd.read_csv(io.StringIO('\n'.join(clean_lines)), sep=None, engine='python')

        df.columns = [c.strip() for c in df.columns]
        df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)

        # --- 這裡加入「預算」欄位讓線控手動調整 ---
        if '每日預算(EUR)' not in df.columns:
            df['每日預算(EUR)'] = 150.0  # 預設一個平均值

        st.success("✅ 表格辨識成功！您可以直接在下方表格修改文字或預算。")
        
        # --- 2. 核心編輯區 ---
        st.subheader("📍 2. 行程內容與單日成本微調")
        
        # 使用 data_editor，這讓你像用 Excel 一樣
        # num_rows="dynamic" 讓你可以點擊表格下方的 (+) 增加天數
        edited_df = st.data_editor(
            df, 
            use_container_width=True, 
            num_rows="dynamic",
            column_config={
                "每日預算(EUR)": st.column_config.NumberColumn(format="€ %d")
            }
        )
        
        st.divider()
        
        # --- 3. 報價與匯率區 ---
        col1, col2, col3 = st.columns(3)
        with col1:
            ex_rate = st.number_input("今日匯率 (EUR)", value=35.5, step=0.1)
            airfare = st.number_input("機票成本 (TWD/人)", value=45000, step=500)
        with col2:
            # 這裡改為：加總表格中每一天的「每日預算」
            total_land_cost_eur = edited_df['每日預算(EUR)'].astype(float).sum()
            st.metric("總地接成本 (EUR)", f"€ {total_land_cost_eur:,.0f}")
            st.caption("這是根據您在表格內每一天填寫的金額加總後的結果")
        with col3:
            pax = st.number_input("成行人數", value=20)
            margin = st.slider("預期毛利率 (%)", 5, 40, 15)

        # 計算總價
        total_cost_twd = (total_land_cost_eur * ex_rate) + airfare
        suggested_price = total_cost_twd / (1 - (margin/100))
        
        st.write("---")
        st.metric("建議售價 (TWD)", f"{int(suggested_price):,}")
        st.info(f"💡 計算公式：({total_land_cost_eur} EUR * {ex_rate}) + {airfare} 機票 / {(100-margin)/100} (毛利係數)")

    except Exception as e:
        st.error("表格辨識失敗。請確保您有複製到完整的欄位名稱。")
