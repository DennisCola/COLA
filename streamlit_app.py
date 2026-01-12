import streamlit as st
import pandas as pd
import io
import re

st.set_page_config(page_title="線控自動核價系統", layout="wide")

# --- 1. 設定與連動 Google Sheet 資料庫 ---
# 這裡使用你提供的 Google Sheet 連結
DB_URL = "https://docs.google.com/spreadsheets/d/1y53LHsJkDx2xA1MsLzkdd5FYQYWcfQrhs2KeSbsKbZk/export?format=csv&gid=242124917"

@st.cache_data
def load_cost_db():
    try:
        # 這裡模擬讀取單價表，實際應用時可建立一個專門存放「品名 | 單價」的分頁
        db_df = pd.read_csv(DB_URL)
        # 建立一個簡單的字典供示範用
        # 建議在 Google Sheet 另開一分頁專門放單價對照表
        cost_mapping = {
            "六菜一湯": 18.0,
            "米其林一星": 75.0,
            "美泉宮": 22.0,
            "霍夫堡": 18.0,
            "自理": 0.0
        }
        return cost_mapping
    except:
        return {}

COST_DB = load_cost_db()

def get_price(item_name):
    for key, price in COST_DB.items():
        if key in str(item_name): return price
    return 0.0

# --- 2. 介面設計 ---
st.title("🛡️ 線控自動核價儀表板")
st.caption("連動資料庫：Cola-Enjoy Europe BUS 資料檔")

raw_input = st.text_area("請貼上 AI Studio 產出的內容 (Markdown 格式)：", height=150)

if raw_input:
    try:
        # 資料清洗與轉換
        lines = raw_input.strip().split('\n')
        clean_lines = [l for l in lines if not re.match(r'^[|\s:-]+$', l)]
        df = pd.read_csv(io.StringIO('\n'.join(clean_lines)), sep="|", skipinitialspace=True).dropna(axis=1, how='all')
        df.columns = [c.strip() for c in df.columns]
        
        # 定義核心成本類別
        categories = ["午餐", "晚餐", "景點門票", "旅館"]
        
        # 新增邏輯：一個格子多個門票的特殊處理
        def handle_multiple_items(item_str):
            # 若有 | 或 + 號，代表多個門票
            items = re.split(r'[|+]', str(item_str))
            return sum([get_price(i.strip()) for i in items])

        for cat in categories:
            # 功能一：預設包含打勾
            df[f"{cat}_包含"] = True
            # 功能二：自動抓單價 (支援多項目加總)
            df[f"{cat}_單價"] = df[cat].apply(handle_multiple_items if cat == "景點門票" else get_price)

        # 欄位重新排序
        cols = ["天數", "行程大點"]
        for cat in categories:
            cols.extend([cat, f"{cat}_包含", f"{cat}_單價"])
        df = df.reindex(columns=cols).fillna(0)

        # 呈現編輯表格
        edited_df = st.data_editor(
            df,
            use_container_width=True,
            num_rows="dynamic",
            column_config={
                "午餐_包含": st.column_config.CheckboxColumn("合約?"),
                "晚餐_包含": st.column_config.CheckboxColumn("合約?"),
                "景點門票_包含": st.column_config.CheckboxColumn("合約?"),
                "旅館_包含": st.column_config.CheckboxColumn("合約?"),
                "午餐_單價": st.column_config.NumberColumn("EUR", format="€%.1f"),
                "晚餐_單價": st.column_config.NumberColumn("EUR", format="€%.1f"),
                "景點門票_單價": st.column_config.NumberColumn("EUR", format="€%.1f"),
                "旅館_單價": st.column_config.NumberColumn("EUR", format="€%.1f"),
            }
        )

        # 總金額動態試算
        st.divider()
        total_eur = 0
        for cat in categories:
            # 只有打勾的才算錢
            total_eur += edited_df[edited_df[f"{cat}_包含"] == True][f"{cat}_單價"].sum()

        c1, c2 = st.columns(2)
        with c1:
            ex_rate = st.number_input("匯率 (EUR to TWD)", value=35.5)
        with c2:
            st.metric("地接總成本 (EUR/人)", f"€ {total_eur:,.1f}")
            st.metric("換算台幣", f"NT$ {int(total_eur * ex_rate):,}")

    except Exception as e:
        st.error(f"表格辨識異常，請檢查 AI Studio 的輸出格式。")
