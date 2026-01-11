import streamlit as st
import pandas as pd
import requests
from io import BytesIO
from docx import Document
import google.generativeai as genai
import json

st.set_page_config(page_title="AI小線控(算報價)", layout="wide")

# 1. 設定 AI
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash')

# 2. 資料庫網址
SHEET_URL = "https://docs.google.com/spreadsheets/d/1y53LHsJkDx2xA1MsLzkdd5FYQYWcfQrhs2KeSbsKbZk/export?format=xlsx"

# 3. 側邊欄參數
with st.sidebar:
    st.header("⚡ 今日即時參數")
    exchange_rate = st.number_input("歐元匯率", value=35.0)
    airfare_base = st.number_input("機票票價", value=32000)
    airfare_tax = st.number_input("機票稅金", value=7500)
    profit_target = st.number_input("目標利潤", value=8000)

@st.cache_data(ttl=300)
def load_db():
    try:
        response = requests.get(SHEET_URL)
        with BytesIO(response.content) as f:
            f_fix = pd.read_excel(f, sheet_name="Fixed")
            f_sha = pd.read_excel(f, sheet_name="Shared")
            f_day = pd.read_excel(f, sheet_name="Daily")
        return f_fix, f_sha, f_day
    except: return None, None, None

db_fix, db_sha, db_day = load_db()

st.title("🌍 AI小線控(算報價)")

if db_fix is not None:
    st.success("✅ 資料庫連動成功")
    uploaded_file = st.file_uploader("1. 上傳行程 Word 檔", type=["docx"])

    if uploaded_file:
        doc = Document(uploaded_file)
        full_text = "\n".join([p.text for p in doc.paragraphs])
        st.info("🔄 AI 正在生成核對表...")

        prompt = f"""
        你是一位線控助理。請閱讀以下行程，回傳一個 JSON 列表，包含 11 個欄位：
        "日期", "星期", "天數", "行程大點", "午餐", "餐標", "晚餐", "餐標", "有料門票", "旅館", "星等"
        規則：若無內容請填 "X"。行程：{full_text[:3000]}
        """
        try:
            res = model.generate_content(prompt)
            data = json.loads(res.text.replace('```json', '').replace('```', '').strip())
        except:
            data = [{"日期": "X", "天數": 1, "行程大點": "辨識失敗"}]

        st.header("2. 線控核對表")
        cols = ["日期", "星期", "天數", "行程大點", "午餐", "餐標", "晚餐", "餐標", "有料門票", "旅館", "星等"]
        df_edit = pd.DataFrame(data).reindex(columns=cols)
        final_df = st.data_editor(df_edit, use_container_width=True, num_rows="dynamic")

        if st.button("確認無誤，產出報價"):
            st.divider()
            # 計算邏輯
            total_eur = 0
            for _, r in final_df.iterrows():
                txt = f"{r
