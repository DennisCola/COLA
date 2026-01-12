import streamlit as st
import pandas as pd
import io
import re

st.set_page_config(page_title="線控黃金 10 行系統", layout="wide")

st.title("🛡️ 線控專業報價：黃金 10 行穩定版")
st.caption("公式：1天, 2大點, 3午, 4勾, 5晚, 6勾, 7門, 8勾, 9旅, 10勾 | 11價")

# 1. 輸入區
raw_input = st.text_area("請在此貼上 AI Studio 的 6 格內容：", height=150, placeholder="天數 | 行程大點 | 午餐 | 晚餐 | 門票 | 旅館")

if raw_input:
    try:
        # --- A. 解析 AI Studio 的 6 欄原始資料 ---
        lines = [l.strip() for l in raw_input.strip().split('\n') if not re.match(r'^[|\s:-]+$', l.strip())]
        
        if len(lines) > 1:
            rows = []
            for l in lines[1:]: # 跳過標題行
                cells = [c.strip() for c in l.split('|') if c.strip() != ""]
                if len(cells) >= 6:
                    rows.append(cells[:6]) 
            
            # --- B. 依照你的公式建構 10+1 行 ---
            # 1天, 2大點, 3午, 4勾, 5晚, 6勾, 7門, 8勾, 9旅, 10勾, 11價
            new_data = []
            for r in rows:
                new_data.append([
                    r[0],      # 1.天數
                    r[1],      # 2.大點
                    r[2],      # 3.午餐
                    True,      # 4.午勾 (預設打勾)
                    r[3],      # 5.晚餐 (原4->5)
                    True,      # 6.晚勾 (預設打勾)
                    r[4],      # 7.門票 (原5->7)
                    True,      # 8.門勾 (預設打勾)
                    r[5],      # 9.旅館 (原6->9)
                    True,      # 10.旅勾 (預設打勾)
                    0.0        # 11.單價
                ])
            
            # 定義欄位名稱
            col_names = ["天數", "行程大點", "午餐", "午?", "晚餐", "晚?", "門票", "門?", "旅館", "旅?", "單日預算"]
            final_df = pd.DataFrame(new_data, columns=col_names)

            # --- C. 呈現 10 行橫向表格 ---
            st.subheader("📍 10 行橫向核價工作台")
            
            # 設定編輯器
            edited = st.data_editor(
                final_df,
                use_container_width=True,
                num_rows="dynamic",
                column_config={
                    "午?": st.column_config.CheckboxColumn(width="small"),
                    "晚?": st.column_config.CheckboxColumn(width="small"),
                    "門?": st.column_config.CheckboxColumn(width="small"),
                    "旅?": st.column_config.CheckboxColumn(width="small"),
                    "單日預算": st.column_config.NumberColumn("EUR", format="€%.1f")
                }
            )
            
            # --- D. 安全計算總和 ---
            st.divider()
            # 改用位置索引抓取最後一欄 (單日預算) 以避免名稱錯誤
            total_eur = pd.to_numeric(edited.iloc[:, -1], errors='coerce').sum()
            
            c1, c2 = st.columns(2)
            with c1:
                ex_rate = st.number_input("今日歐元匯率", value=35.5, step=0.1)
            with c2:
                st.metric("地接總預算 (EUR)", f"€ {total_eur:,.1f}")
                st.write(f"📊 換算台幣：**NT$ {int(total_eur * ex_rate):,}**")
                
        else:
            st.warning("⚠️ 偵測到的資料行數不足，請確認是否完整複製 AI Studio 的表格內容。")

    except Exception as e:
        st.error(f"❌ 轉換失敗。請確認輸入格式。錯誤資訊: {e}")

else:
    st.info("💡 請從 AI Studio 複製表格文字並貼在上方框框內。")
