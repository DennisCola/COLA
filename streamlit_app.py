import streamlit as st
import pandas as pd
import requests
from io import BytesIO
from docx import Document
import google.generativeai as genai
import json

# --- 1. 頁面設定 ---
st.set_page_config(page_title="AI小線控(算報價)", layout="wide")

# 設定 Gemini AI
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash')

# Google Sheet 原始網址 (資料庫)
SHEET_URL = "https://docs.google.com/spreadsheets/d/1y53LHsJkDx2xA1MsLzkdd5FYQYWcfQrhs2KeSbsKbZk/export?format=xlsx"

# --- 2. 側邊欄：即時參數 ---
with st.sidebar:
    st.header("⚡ 今日即時參數")
    exchange_rate = st.number_input("今日歐元匯率", value=35.0, step=0.1)
    airfare_base = st.number_input("機票票價 (TWD)", value=32000)
    airfare_tax = st.number_input("機票稅金 (TWD)", value=7500)
    profit_target = st.number_input("當團目標利潤 (TWD)", value=8000)

# --- 3. 讀取資料庫 ---
@st.cache_data(ttl=300)
def load_db():
    try:
        response = requests.get(SHEET_URL)
        with BytesIO(response.content) as f:
            fixed_pax = pd.read_excel(f, sheet_name="Fixed")
            shared_costs = pd.read_excel(f, sheet_name="Shared")
            daily_costs = pd.read_excel(f, sheet_name="Daily")
        return fixed_pax, shared_costs, daily_costs
    except:
        return None, None, None

db_fixed, db_shared, db_daily = load_db()

st.title("🌍 AI小線控(算報價)")

if db_fixed is not None:
    st.success("✅ 資料庫連動成功")
    
    # --- 4. 上傳 Word 檔 ---
    st.header("1. 上傳行程 Word 檔")
    uploaded_file = st.file_uploader("請選擇 .docx 行程檔案", type=["docx"])

    if uploaded_file:
        doc = Document(uploaded_file)
        full_text = "\n".join([para.text for para in doc.paragraphs])
        
        st.info("🔄 AI 正在閱讀行程，並依照您的指定格式產出核對表...")
        
        # 定義您的標準格式範例
        format_example = "日期,星期,天數,行程大點,午餐,餐標,晚餐,餐標,有料門票,旅館,星等"
        
        prompt = f"""
        你是一位旅行社線控助理。請閱讀以下行程內容，並將其去蕪存菁。
        請嚴格依照 JSON 格式回傳一個列表，每個對象必須包含以下精確欄位：
        "日期", "星期", "天數", "行程大點", "午餐", "餐標", "晚餐", "餐標", "有料門票", "旅館", "星等"
        
        規則：
        1. 如果行程中沒提到餐標、門票或星等，請填寫 "X"。
        2. 輸出格式必須是純 JSON 列表。
        
        行程內容：
        {full_text[:3000]}
        """
        
        try:
            response = model.generate_content(prompt)
            raw_json = response.text.replace('```json', '').replace('```', '').strip()
            detected_data = json.loads(raw_json)
        except:
            detected_data = [{{ "日期": "X", "星期": "X", "天數": 1, "行程大點": "辨識失敗", "午餐": "X", "餐標": "X", "晚餐": "X", "餐標": "X", "有料門票": "X", "旅館": "X", "星等": "X" }}]

        # --- 5. 人工確認表格 (完全照抄您提供的格式) ---
        st.header("2. 線控核對表 (去蕪存菁結果)")
        st.caption("欄位已完全比照您的範例格式。請在此核對、修改或補充。")
        
        df_editor = pd.DataFrame(detected_data)
        # 強制排序欄位以符合範例
        columns_order = ["日期", "星期", "天數", "行程大點", "午餐", "餐標", "晚餐", "餐標", "有料門票", "旅館", "星等"]
        df_editor = df_editor.reindex(columns=columns_order)
        
        # 顯示可編輯表格
        final_check_df = st.data_editor(df_editor, use_container_width=True, num_rows="dynamic")

        # --- 6. 最終計算階段 ---
        if st.button("確認核對表無誤，產出報價"):
            st.divider()
            st.header("3. 最終階梯報價結果")
            
            # --- 計算邏輯：比對 Fixed 資料庫 ---
            total_itinerary_eur = 0
            
            # 遍歷核對表中的「午餐」、「晚餐」、「有料門票」欄位進行比對
            for _, row in final_check_df.iterrows():
                # 檢查門票與餐食
                content_to_check = f"{row['午餐']} {row['晚餐']} {row['有料門票']}"
                for _, db_row in db_fixed.iterrows():
                    if str(db_row['判斷文字']) in content_to_check:
                        total_itinerary_eur += db_row['單價(EUR)']
            
            # 讀取 Shared (均攤成本)
            total_shared_eur = db_shared.iloc[:, 1].sum() if not db_shared.empty else 0
            
            # 讀取天數雜支
            days_num = int(final_check_df["天數"].max())
            daily_info = db_daily[db_daily.iloc[:, 0] == days_num]
            daily_twd = (daily_info.iloc[0, 1] + daily_info.iloc[0, 2]) if not daily_info.empty else 800

            # 階梯計算
            pax_list = [16, 21, 26, 31]
            calc_results = []
            for p in pax_list:
                share_cost = total_shared_eur / (p-1)
                net_twd = (total_itinerary_eur + share_cost) * exchange_rate + airfare_base + airfare_tax + daily_twd
                sale_price = (net_twd + profit_target) * 1.05
                
                calc_results.append({
                    "人數級距": f"{p-1}+1",
                    "每人成本(TWD)": f"{int(net_twd):,}",
                    "建議售價(TWD)": f"{int(sale_price):,}"
                })
            
            st.table(pd.DataFrame(calc_results))
            st.balloons()
else:
    st.error("❌ 無法載入資料庫，請檢查 Google Sheet 權限。")
