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

# Google Sheet 原始網址
SHEET_URL = "https://docs.google.com/spreadsheets/d/1y53LHsJkDx2xA1MsLzkdd5FYQYWcfQrhs2KeSbsKbZk/export?format=xlsx"

# --- 2. 側邊欄 ---
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
    
    st.header("1. 上傳行程 Word 檔")
    uploaded_file = st.file_uploader("請選擇 .docx 行程檔案", type=["docx"])

    if uploaded_file:
        doc = Document(uploaded_file)
        full_text = "\n".join([para.text for para in doc.paragraphs])
        
        st.info("🔄 AI 正在閱讀行程，並依照您的指定格式產出核對表...")
        
        prompt = f"""
        你是一位專業的旅行社線控助理。請閱讀以下行程內容，將其「去蕪存菁」後填入表格。
        請嚴格依照 JSON 格式回傳一個列表（List of Objects），包含以下 11 個欄位：
        "日期", "星期", "天數", "行程大點", "午餐", "餐標", "晚餐", "餐標", "有料門票", "旅館", "星等"
        
        規則：
        1. 如果行程沒提到某項內容，請填寫 "X"。
        2. "天數"請填寫純數字。
        3. 請只回傳純 JSON，不要包含 Markdown 文字。
        
        行程內容：
        {full_text[:3000]}
        """
        
        try:
            response = model.generate_content(prompt)
            clean_json = response.text.replace('```json', '').replace('```', '').strip()
            detected_data = json.loads(clean_json)
        except Exception as e:
            # 修正後的錯誤備援資料
            detected_data = [{
                "日期": "X", "星期": "X", "天數": 1, "行程大點": "辨識失敗，請手動新增", 
                "午餐": "X", "餐標": "X", "晚餐": "X", "餐標": "X", "有料門票": "X", "旅館": "X", "星等": "X"
            }]

        st.header("2. 線控核對表 (去蕪存菁結果)")
        st.caption("欄位已比照您的範例格式。請在此核對、修改或補充內容。")
        
        df_editor = pd.DataFrame(detected_
