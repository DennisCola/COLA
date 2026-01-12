import streamlit as st
import pandas as pd
import io
import re

st.set_page_config(page_title="線控黃金 10 行系統", layout="wide")

st.title("🛡️ 線控專業報價：黃金 10 行穩定版")
st.caption("公式：1天, 2大點, 3午, 4勾, 5晚, 6勾, 7門, 8勾, 9旅, 10勾 | 11價")

# 1. 輸入區
raw_input = st.text_area("請在此貼上 AI Studio 的內容：", height=150, placeholder="無論是用空格、Tab 還是 | 分隔都可以...")

if raw_input:
    try:
        # --- A. 強化版：多格式解析邏輯 ---
        lines = [l.strip() for l in raw_input.strip().split('\n') if l.strip()]
        
        rows = []
        for l in lines:
            # 跳過只有符號的分隔線
            if re.match(r'^[|\s:-]+$', l):
                continue
                
            # 分隔符號判斷：優先用 |, 次之用兩個以上的空格或 Tab
            if '|' in l:
                cells = [c.strip() for c in l.split('|') if c.strip()]
            else:
                # 使用正則表達式切分 2 個以上空格或 Tab
                cells = re.split(r'\t| {2,}', l)
                cells = [c.strip() for c in cells if c.strip()]
            
            # 確保有內容才加入
            if len(cells) >= 2:
                # 補齊不夠的欄位，避免 AI 漏掉最後的旅館或門票
                while len(cells) < 6:
                    cells.append("-")
                rows.append(cells[:6]) 
        
        if rows:
            # --- B. 依照你的公式建構 10+1 行 ---
            new_data = []
            for r in rows:
                new_data.append([
                    r[0],      # 1.天數
                    r[1],      # 2.大點
                    r[2],      # 3.午餐
                    True,      # 4.午勾
                    r[3],      # 5.晚餐 (原4->5)
                    True,      # 6.晚勾
                    r[4],      # 7.門票 (原5->7)
                    True,      # 8.門勾
                    r[5],      # 9.旅館 (原6->9)
                    True,      # 10.旅勾
                    0.0        # 11.單價
                ])
            
            col_names = ["天數", "行程大點", "午餐", "午?", "晚餐", "晚?", "門票", "門?", "旅館", "旅?", "EUR"]
            final_df = pd.DataFrame(new_data, columns=col_names)

            # --- C. 呈現 10 行橫向表格 ---
            st.subheader("📍 10 行橫向核價工作台")
            
            edited = st.data_editor(
                final_df,
                use_container_width=True,
                num_rows="dynamic",
                column_config={
                    "午?": st.column_config.CheckboxColumn(width="small"),
                    "晚?": st.column_config.CheckboxColumn(width="small"),
                    "門?": st.column_config.CheckboxColumn(width="small"),
                    "旅?": st.column_config.CheckboxColumn(width="small"),
                    "EUR": st.column_config.NumberColumn("單價", format="€%.1f")
                }
            )
            
            # --- D. 安全計算 ---
            st.divider()
            total_eur = pd.to_numeric(edited["EUR"], errors='coerce').sum()
            
            c1, c2 = st.columns(2)
            with c1:
                ex_rate = st.number_input("今日歐元匯率", value=35.5, step=0.1)
            with c2:
                st.metric("地接總預算 (EUR)", f"€ {total_eur:,.1f}")
                st.write(f"📊 換算台幣：**NT$ {int(total_eur * ex_rate):,}**")
                
        else:
            st.warning("⚠️ 系統無法識別內容，請確認貼上的文字有分欄。")

    except Exception as e:
        st.error(f"❌ 轉換失敗。錯誤資訊: {e}")
else:
    st.info("💡 請將內容貼在上方框框內。")
