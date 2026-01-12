import streamlit as st
import pandas as pd
import io
import re

st.set_page_config(page_title="線控 10 格專業報價台", layout="wide")

# --- 1. 連動 Google Sheet 單價資料庫 ---
# 這裡使用你的資料庫連結
DB_URL = "https://docs.google.com/spreadsheets/d/1y53LHsJkDx2xA1MsLzkdd5FYQYWcfQrhs2KeSbsKbZk/export?format=csv&gid=242124917"

@st.cache_data
def get_cost_db():
    try:
        # 這裡建議在 Google Sheet 建立一個「單價表」分頁
        # 目前先用一個字典模擬，未來會直接讀取該分頁
        db = {
            "六菜一湯": 18.0,
            "米其林": 75.0,
            "肋排": 25.0,
            "美泉宮": 22.0,
            "霍夫堡": 18.0,
            "聖維特": 15.0,
            "自理": 0.0
        }
        return db
    except:
        return {}

COST_DB = get_cost_db()

# --- 2. 核心功能：單價比對邏輯 ---
def match_price(item_name):
    if not item_name or str(item_name).strip() == "":
        return 0.0
    for key, price in COST_DB.items():
        if key in str(item_name):
            return price
    return -1.0  # 代表「找不到」，之後用來觸發提醒

# --- 3. 網頁介面 ---
st.title("🛡️ 專業線控：10 格全功能報價台")
st.caption("流程：AI 6 格輸入 ⮕ 系統展開 10 格 ⮕ 手動校正單價 ⮕ 最終成本產出")

# 第一步：接收 AI Studio 的 6 格資料
raw_input = st.text_area("1. 請貼上 AI Studio 產出的 6 格內容：", height=150, placeholder="天數 | 行程大點 | 午餐 | 晚餐 | 門票 | 旅館")

if raw_input:
    # 模糊辨識解析 Markdown
    lines = [l.strip() for l in raw_input.strip().split('\n') if not re.match(r'^[|\s:-]+$', l.strip())]
    if len(lines) > 1:
        data = [[c.strip() for c in l.split('|') if c.strip() != ""] for l in lines]
        base_df = pd.DataFrame(data[1:], columns=data[0])
        
        # 第二步：展開為 10 格結構
        df = base_df.copy()
        
        # 定義需要對應價格的四個類別
        price_cols = {
            "午餐": "午餐價格",
            "晚餐": "晚餐價格",
            "門票": "門票單價",
            "旅館": "旅館單價"
        }
        
        for name, price_col in price_cols.items():
            if name in df.columns:
                # 建立包含開關 (預設 True)
                df[f"{name}_包含"] = True
                # 自動比對價格
                df[price_col] = df[name].apply(match_price)
        
        # 重新排列為你理想的「黃金 10 格」+ 包含開關
        # 排列順序：天數 | 大點 | 午餐 | 算? | 午餐價格 | 晚餐 | 算? | 晚餐價格 | ...
        final_cols = ["天數", "行程大點"]
        for name, price_col in price_cols.items():
            final_cols.extend([name, f"{name}_包含", price_col])
        
        df = df.reindex(columns=final_cols).fillna(0)

        st.success("✅ 已自動展開 10 格。請注意『-1.0』代表資料庫無此價格，請手動補上。")

        # 第三步：手動編輯區
        edited_df = st.data_editor(
            df,
            use_container_width=True,
            num_rows="dynamic",
            column_config={
                "午餐_包含": st.column_config.CheckboxColumn("算?"),
                "晚餐_包含": st.column_config.CheckboxColumn("算?"),
                "門票_包含": st.column_config.CheckboxColumn("算?"),
                "旅館_包含": st.column_config.CheckboxColumn("算?"),
                "午餐價格": st.column_config.NumberColumn("EUR", help="若為 -1 請手動輸入"),
                "晚餐價格": st.column_config.NumberColumn("EUR"),
                "門票單價": st.column_config.NumberColumn("EUR"),
                "旅館單價": st.column_config.NumberColumn("EUR"),
            }
        )

        # 第四步：計算總成本
        st.divider()
        total_eur = 0
        for name, price_col in price_cols.items():
            inc_col = f"{name}_包含"
            # 只計算打勾且價格 > 0 的部分
            total_eur += edited_df[edited_df[inc_col] == True][price_col].apply(lambda x: max(0, float(x))).sum()

        c1, c2, c3 = st.columns(3)
        with c1:
            ex_rate = st.number_input("歐元匯率", value=35.5)
            airfare = st.number_input("機票成本 (TWD)", value=45000)
        with c2:
            st.metric("地接總成本 (EUR)", f"€ {total_eur:,.1f}")
        with c3:
            total_cost_twd = (total_eur * ex_rate) + airfare
            st.metric("目前總成本 (TWD)", f"NT$ {int(total_cost_twd):,}")
            
        st.info("💡 接下來您可以拼上：分包商報價、稅金，完成最終成本表。")
