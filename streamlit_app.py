import streamlit as st
import pandas as pd
import io
import re

st.set_page_config(page_title="線控 10 格專業報價台", layout="wide")

# --- 1. 模擬單價搜尋 (未來對接 Google Sheet) ---
def find_price(item_name):
    if not item_name or str(item_name).strip() == "" or "自理" in str(item_name):
        return 0.0
    # 這裡可以加入更多關鍵字比對
    db = {"六菜一湯": 18.0, "米其林": 75.0, "肋排": 25.0, "美泉宮": 22.0, "霍夫堡": 18.0}
    for key, price in db.items():
        if key in str(item_name):
            return price
    return 0.0 # 找不到預設 0.0，讓線控手動填

# --- 2. 介面與標題 ---
st.title("🛡️ 專業線控：黃金 10 格報價台")
st.write("步驟：AI Studio 產出 6 格 ⮕ 貼入下方 ⮕ 系統擴充為 10 格並自動核價")

# --- 3. 資料輸入與解析 ---
raw_input = st.text_area("請貼上 AI Studio 的 6 格表格內容：", height=150)

if raw_input:
    try:
        # 強力解析 Markdown 文字
        lines = [l.strip() for l in raw_input.strip().split('\n') if not re.match(r'^[|\s:-]+$', l.strip())]
        if len(lines) > 1:
            rows = [[c.strip() for c in l.split('|') if c.strip() != ""] for l in lines]
            df = pd.DataFrame(rows[1:], columns=rows[0])
            
            # 清理欄位名，避免空格導致抓不到
            df.columns = [c.strip() for c in df.columns]
            
            # --- 強制轉型為「黃金 10 格」結構 ---
            # 1.天數 2.行程大點 3.午餐 4.午餐包含 5.午餐價格 6.晚餐 7.晚餐包含 8.晚餐價格 9.門票 10.門票單價 11.旅館 12.旅館單價
            # (雖然是12格，但符合你說的 10 格核心資訊)
            
            cats = ["午餐", "晚餐", "門票", "旅館"]
            for c in cats:
                if c in df.columns:
                    df[f"{c}包含"] = True
                    # 只有單價欄位是空的或是原本沒有才去抓
                    price_col = "門票單價" if c == "門票" else "旅館單價" if c == "旅館" else f"{c}價格"
                    df[price_col] = df[c].apply(find_price)

            # 重新排列欄位順序
            final_order = ["天數", "行程大點"]
            for c in cats:
                p_col = "門票單價" if c == "門票" else "旅館單價" if c == "旅館" else f"{c}價格"
                final_order.extend([c, f"{c}包含", p_col])
            
            df = df.reindex(columns=final_order).fillna(0)

            # --- 4. 專業數據編輯器 ---
            st.subheader("📍 行程與成本明細 (可直接修改內容或金額)")
            
            # 設定欄位顯示樣式
            config = {f"{c}包含": st.column_config.CheckboxColumn("算?") for c in cats}
            for c in cats:
                p_col = "門票單價" if c == "門票" else "旅館單價" if c == "旅館" else f"{c}價格"
                config[p_col] = st.column_config.NumberColumn("EUR", format="
