import streamlit as st
import pandas as pd
import io
import re

st.set_page_config(page_title="線控黃金 10 格系統", layout="wide")

st.title("🛡️ 線控專業報價：4,6,8,10 打勾工作台")
st.caption("公式確認：1天, 2大點, 3午內容, 4午勾, 5晚內容, 6晚勾, 7門內容, 8門勾, 9旅館, 10旅館勾 | 11單價")

raw_input = st.text_area("請貼上 AI Studio 產出的 6 格文字：", height=150)

if raw_input:
    try:
        # 解析原始 6 格 (天, 大點, 午, 晚, 門, 住)
        lines = [l.strip() for l in raw_input.strip().split('\n') if not re.match(r'^[|\s:-]+$', l.strip())]
        if len(lines) > 1:
            rows = [[c.strip() for c in l.split('|') if c.strip() != ""] for l in lines]
            old_df = pd.DataFrame(rows[1:], columns=rows[0])
            old_df.columns = [c.strip() for c in old_df.columns]
            
            # --- 建立 10+1 橫向結構 ---
            new_df = pd.DataFrame()
            
            new_df["1.天數"] = old_df.iloc[:, 0]        # 1 -> 1
            new_df["2.行程大點"] = old_df.iloc[:, 1]    # 2 -> 2
            new_df["3.午餐內容"] = old_df.iloc[:, 2]    # 3 -> 3
            new_df["4.午算?"] = True                    # 打勾欄
            new_df["5.晚餐內容"] = old_df.iloc[:, 3]    # 4 -> 5
            new_df["6.晚算?"] = True                    # 打勾欄
            new_df["7.景點門票"] = old_df.iloc[:, 4]    # 5 -> 7
            new_df["8.門算?"] = True                    # 打勾欄
            new_df["9.旅館名稱"] = old_df.iloc[:, 5]    # 6 -> 9
            new_df["10.旅算?"] = True                   # 打勾欄
            new_df["11.單日預算(EUR)"] = 0.0             # 價格欄

            # --- 顯示編輯器 ---
            st.subheader("📍 橫向核價工作台")
            
            edited = st.data_editor(
                new_df,
                use_container_width=True,
                num_rows="dynamic",
                column_config={
                    "4.午算?": st.column_config.CheckboxColumn("午?"),
                    "6.晚算?": st.column_config.CheckboxColumn("晚?"),
                    "8.門算?": st.column_config.CheckboxColumn("門?"),
                    "10.旅算?": st.column_config.CheckboxColumn("旅?"),
                    "11.單日預算(EUR)": st.column_config.NumberColumn("單價", format="€%.1f")
                }
            )
            
            # --- 自動計算 ---
            st.divider()
            total_eur = edited["11.單日預算(EUR)"].sum()
            
            c1, c2 = st.columns(2)
            with c1:
                ex_rate = st.number_input("歐元匯率", value=35.5)
            with c2:
                st.metric("地接總預算 (EUR)", f"€ {total_eur}")
                st.caption(f"換算台幣：NT$ {int(total_eur * ex_rate):,}")

    except Exception as e:
        st.error(f"解析失敗，請確認 AI Studio 輸出的格數正確。")
