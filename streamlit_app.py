import streamlit as st
import pandas as pd
import io
import re

st.set_page_config(page_title="線控秒速試算中心", layout="wide")

st.title("⚡ 線控行程快轉試算")
st.caption("直接複製 AI Studio 的內容（就算看起來是文字也沒關係）並貼在下方")

# 1. 貼上區
raw_input = st.text_area("1. 請貼上從 AI Studio 複製的內容：", height=250, 
                         placeholder="直接把 AI 產出的結果全選、複製、貼上到這裡...")

if raw_input:
    try:
        # --- 自動清理格式的黑科技 ---
        lines = raw_input.strip().split('\n')
        
        # 1. 過濾掉 Markdown 的分隔線 (例如 |---|---| )
        clean_lines = [l for l in lines if not re.match(r'^[|\s:-]+$', l)]
        
        # 2. 判斷是用什麼符號隔開的
        if '|' in clean_lines[0]:
            # Markdown 格式處理
            df = pd.read_csv(io.StringIO('\n'.join(clean_lines)), sep="|", skipinitialspace=True)
            # 移除頭尾因為 | 產生的空欄位
            df = df.dropna(axis=1, how='all')
        else:
            # 可能是 Excel 或 Tab 隔開的格式
            df = pd.read_csv(io.StringIO('\n'.join(clean_lines)), sep=None, engine='python')

        # 3. 清理欄位名稱與內容的空格
        df.columns = [c.strip() for c in df.columns]
        df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)

        st.success("✅ 表格辨識成功！")
        
        # --- 2. 編輯與報價區 ---
        st.subheader("📍 2. 核對行程與動態報價")
        # 這裡就是你鑲嵌在網頁上的編輯器
        final_df = st.data_editor(df, use_container_width=True, num_rows="dynamic", key="editor")
        
        st.divider()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            ex_rate = st.number_input("今日匯率 (EUR)", value=35.5, step=0.1)
            airfare = st.number_input("機票成本 (TWD/人)", value=45000, step=500)
        with col2:
            # 這裡可以根據天數自動估算
            days = len(final_df)
            land_cost_eur = st.number_input("每人每日地接預算 (EUR)", value=150)
            st.caption(f"總地接成本預估: {days * land_cost_eur} EUR")
        with col3:
            pax = st.number_input("成行人數", value=20)
            margin = st.slider("預期毛利率 (%)", 5, 40, 15)

        # 計算公式
        total_cost_twd = (days * land_cost_eur * ex_rate) + airfare
        suggested_price = total_cost_twd / (1 - (margin/100))
        
        st.write("---")
        st.metric("建議售價 (TWD)", f"{int(suggested_price):,}")
        st.caption(f"每人預估毛利: NT$ {int(suggested_price - total_cost_twd):,}")

    except Exception as e:
        st.error("表格辨識失敗。請確保您有複製到完整的欄位名稱（天數、午餐...）。")
