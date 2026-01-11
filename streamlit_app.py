import streamlit as st
from streamlit_gsheets import GSheetsConnection
import google.generativeai as genai
from docx import Document
import pandas as pd
import io

# --- 1. 頁面設定與連線 ---
st.set_page_config(page_title="COLA 歐洲線報價系統", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 2. 側邊欄：即時參數 (匯率、票價、利潤) ---
with st.sidebar:
    st.header("⚡ 今日即時參數")
    exchange_rate = st.number_input("今日歐元匯率", value=35.0, step=0.1)
    airfare_base = st.number_input("機票票價 (TWD)", value=32000)
    airfare_tax = st.number_input("機票稅金 (TWD)", value=7500)
    profit_target = st.number_input("目標利潤 (TWD)", value=8000)
    st.divider()
    st.info("💡 匯率與票價請根據當日報價手動輸入，不連動 Excel。")

# --- 3. 讀取 Google Sheet 資料庫 ---
@st.cache_data(ttl=300)
def load_data():
    fixed_pax = conn.read(worksheet="每人固定")
    shared_costs = conn.read(worksheet="均攤成本")
    daily_costs = conn.read(worksheet="天數計價")
    return fixed_pax, shared_costs, daily_costs

try:
    db_fixed, db_shared, db_daily = load_data()
    st.title("🌍 COLA 歐洲線智慧報價系統")
    st.caption("✅ 已成功連動 Google Sheets 資料庫")
except Exception as e:
    st.error(f"連動失敗，請檢查 Secrets 設定：{e}")
    st.stop()

# --- 4. 第一階段：上傳 Word 檔 ---
st.header("1. 上傳行程 Word 檔")
uploaded_file = st.file_uploader("請選擇 .docx 檔案", type=["docx"])

if uploaded_file:
    # 這裡模擬 AI 解析後的行為 (實際會串接 Gemini)
    st.success("檔案上傳成功！AI 正在對照資料庫...")
    
    # 模擬天數判斷 (假設解析出 10 天)
    total_days = 10 
    
    # --- 5. 第二階段：線控檢查表 (與資料庫對照) ---
    st.header("2. 線控檢查表 (AI 自動對照結果)")
    
    # 這裡會根據 db_fixed 內容自動比對，目前先顯示結構
    itinerary_data = {
        "天數": ["D1", "D2", "D3", "D4"],
        "項目名稱": ["維也納音樂會", "布拉格城堡", "中式七菜一湯", "哈修塔特鹽礦"],
        "單價 (EUR)": [43.0, 19.0, 25.0, 40.0], # 這些會從 db_fixed 自動抓取
        "備註": ["自動抓取", "資料庫連動", "公版餐標", "資料庫連動"]
    }
    df_check = pd.DataFrame(itinerary_data)
    edited_df = st.data_editor(df_check, use_container_width=True)

    # --- 6. 第三階段：階梯式報價計算 ---
    if st.button("確認無誤，產出報價單"):
        st.divider()
        st.header("3. 階梯報價單 (含稅及利潤)")

        # 計算邏輯
        total_eur_fixed = edited_df["單價 (EUR)"].sum()
        total_shared_eur = db_shared["單價(EUR)"].sum() # 均攤成本總額
        
        # 抓取天數計費 (根據 total_days)
        # 這裡會去 db_daily 比對對應天數的金額
        daily_fee_twd = 550 # 模擬耳機+網卡總額

        pax_steps = [16, 21, 26, 31]
        results = []
        
        for p in pax_steps:
            # 均攤部分
            share_cost = total_shared_eur / (p-1)
            # 總歐元成本轉台幣
            local_cost_twd = (total_eur_fixed + share_cost) * exchange_rate
            # 總成本 = 地接台幣 + 機票 + 稅金 + 天數雜支
            total_net = local_cost_twd + airfare_base + airfare_tax + daily_fee_twd
            # 建議售價 = (淨成本 + 利潤) * 1.05 (含稅估算)
            suggested_price = (total_net + profit_target) * 1.05
            
            results.append({
                "人數分級": f"{p-1}+1",
                "每人淨成本": f"{int(total_net):,}",
                "建議售價": f"{int(suggested_price):,}"
            })
            
        st.table(pd.DataFrame(results))
        st.balloons()
