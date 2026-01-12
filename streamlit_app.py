import streamlit as st
import pandas as pd
import io
import re

st.set_page_config(page_title="線控 10 格專業報價台", layout="wide")

# --- 1. 模擬單價搜尋 (未來對接 Google Sheet) ---
def find_price(item_name):
    if not item_name or str(item_name).strip() == "" or "自理" in str(item_name):
        return 0.0
    db = {"六菜一湯": 18.0, "米其林": 75.0, "肋排": 25.0, "美泉宮": 22.0, "霍夫堡": 18.0}
    for key, price in db.items():
        if key in str(item_name):
            return price
    return 0.0 

# --- 2. 介面與標題 ---
st.title("🛡️ 專業線控：黃金 10 格報價台")
st.caption("AI Studio 6 格數據 ⮕ 自動擴展 10 格核價 ⮕ 拼上機票與分包商報價")

raw_input = st.text_area("請貼上 AI Studio 的 6 格表格內容：", height=150)

if raw_input:
    try:
        # 強力解析 Markdown 文字
        lines = [l.strip() for l in raw_input.strip().split('\n') if not re.match(r'^[|\s:-]+$', l.strip())]
        if len(lines) > 1:
            rows = [[c.strip() for c in l.split('|') if c.strip() != ""] for l in lines]
            df = pd.DataFrame(rows[1:], columns=rows[0])
            df.columns = [c.strip() for c in df.columns]
            
            # 定義 4 個核心成本類別
            cats = ["午餐", "晚餐", "門票", "旅館"]
            
            # --- 建立黃金 10 格結構 ---
            for c in cats:
                if c in df.columns:
                    # 建立開關與價格欄位
                    df[f"{c}包含"] = True
                    p_col = "門票單價" if c == "門票" else "旅館單價" if c == "旅館" else f"{c}價格"
                    df[p_col] = df[c].apply(find_price)

            # 重新排列欄位順序 (天數 | 大點 | 午餐 | 算? | 價格 | ...)
            final_order = ["天數", "行程大點"]
            for c in cats:
                p_col = "門票單價" if c == "門票" else "旅館單價" if c == "旅館" else f"{c}價格"
                if c in df.columns:
                    final_order.extend([c, f"{c}包含", p_col])
            
            df = df.reindex(columns=final_order).fillna(0)

            # --- 3. 數據編輯器設定 ---
            st.subheader("📍 行程內容與單價校正")
            
            # 建立欄位顯示設定
            column_config = {}
            for c in cats:
                column_config[f"{c}包含"] = st.column_config.CheckboxColumn("算?", width="small")
                p_col = "門票單價" if c == "門票" else "旅館單價" if c == "旅館" else f"{c}價格"
                column_config[p_col] = st.column_config.NumberColumn("EUR", format="€%.1f")

            edited_df = st.data_editor(df, use_container_width=True, num_rows="dynamic", column_config=column_config)

            # --- 4.
