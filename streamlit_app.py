import streamlit as st
import pandas as pd
import io
import re

st.set_page_config(page_title="線控黃金 10 行系統", layout="wide")

st.title("🛡️ 線控專業報價：10 行橫向展開台")
st.caption("公式：1天, 2大點, 3午, 4勾, 5晚, 6勾, 7門, 8勾, 9旅, 10勾 | 11價")

raw_input = st.text_area("1. 請貼上 AI Studio 產出的 6 格內容：", height=150)

if raw_input:
    try:
        # --- A. 解析 AI Studio 的 6 直行資料 ---
        lines = [l.strip() for l in raw_input.strip().split('\n') if not re.match(r'^[|\s:-]+$', l.strip())]
        
        if len(lines) > 1:
            rows = []
            for l in lines[1:]: # 跳過標題
                cells = [c.strip() for c in l.split('|') if c.strip() != ""]
                if len(cells) >= 6:
                    rows.append(cells[:6]) 
            
            # --- B. 依照「行」的順序重新建構 ---
            new_data = []
            for r in rows:
                new_row = {
                    "1.天數": r[0],
                    "2.行程大點": r[1],
                    "3.午餐": r[2],
                    "4.午算?": True,   # 第 4 行
                    "5.晚餐": r[3],   # 原 4 -> 5
                    "6.晚算?": True,   # 第 6 行
                    "7.門票": r[4],   # 原 5 -> 7
                    "8.門算?": True,   # 第 8 行
                    "9.旅館": r[5],   # 原 6 -> 9
                    "10.旅算?": True,  # 第 10 行
                    "11.單價(EUR)": 0.0
                }
                new_data.append(new_row)
            
            final_df = pd.DataFrame(new_data)

            # --- C. 呈現 10 行橫向表格 ---
            st.subheader("📍 10 行橫向核價工作台")
            
            edited = st.data_editor(
                final_df,
                use_container_width=True,
                num_rows="dynamic",
                column_config={
                    "4.午算?": st.column_config.CheckboxColumn("午?"),
                    "6.晚算?": st.column_config.CheckboxColumn("晚?"),
                    "8.門算?": st.column_config.CheckboxColumn("門?"),
                    "10.旅算?": st.column_config.CheckboxColumn("旅?"),
                    "11.單價(EUR)": st.column_config.NumberColumn("單價", format="€%.1f")
                }
            )
            
            # --- D. 計算與匯率 ---
            st.divider()
            total_eur = edited["11.單價(EUR)"].sum()
            
            c1, c2 = st.columns(2)
            with c1:
                ex_rate = st.number_input("歐元匯率", value=35.5)
            with c2:
                st.metric("地接總預算", f"€ {total_eur}")
                st.write(f"📊 換算台幣：**NT$ {int(total_eur * ex_rate):,}**")

        else:
            st.warning("資料不足，請確認 AI Studio 輸出。")

    except Exception as e:
        st.error(f"轉換失敗。錯誤: {e}")
