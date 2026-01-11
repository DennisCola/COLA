import streamlit as st
import pandas as pd
import requests
from io import BytesIO
from docx import Document
import google.generativeai as genai
import json

# --- 1. 基礎設定與 AI 初始化 ---
st.set_page_config(page_title="線控行程轉表工具", layout="wide")

if "GEMINI_API_KEY" not in st.secrets:
    st.error("請先在 Secrets 設定 GEMINI_API_KEY")
    st.stop()

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash')

# Google Sheet 資料庫連結
SHEET_URL = "https://docs.google.com/spreadsheets/d/1y53LHsJkDx2xA1MsLzkdd5FYQYWcfQrhs2KeSbsKbZk/export?format=xlsx"
# 您指定的 11 個標準欄位
COLS = ["日期", "星期", "天數", "行程大點", "午餐", "餐標", "晚餐", "餐標", "有料門票", "旅館", "星等"]

# --- 2. 資料庫連動檢查 ---
@st.cache_data(ttl=300)
def load_db():
    try:
        r = requests.get(SHEET_URL)
        with BytesIO(r.content) as f:
            # 讀取三個分頁以確保連動正常
            df_f = pd.read_excel(f, sheet_name="Fixed")
            df_s = pd.read_excel(f, sheet_name="Shared")
            df_d = pd.read_excel(f, sheet_name="Daily")
            return df_f, df_s, df_d
    except Exception as e:
        return None, None, None

db_fixed, db_shared, db_daily = load_db()

st.title("📄 行程自動轉表 (純淨版)")

if db_fixed is not None:
    st.success("✅ 成本資料庫連動成功")
else:
    st.error("❌ 資料庫連動失敗，請檢查 Google Sheet 網址或權限")

# --- 3. Word 讀取與處理 ---
up = st.file_uploader("上傳行程 Word (.docx)", type=["docx"])

if up:
    # 檔案切換邏輯：若上傳新檔案則清除舊快取
    if 'fn' not in st.session_state or st.session_state.fn != up.name:
        st.session_state.fn = up.name
        if 'df' in st.session_state:
            del st.session_state.df

    if 'df' not in st.session_state:
        try:
            doc = Document(up)
            # 僅提取文字段落（自動忽略圖片）
            content_list = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
            # 提取 Word 表格內的文字
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        if cell.text.strip():
                            content_list.append(cell.text.strip())
            
            full_text = "\n".join(content_list)
            
            st.info("🔄 AI 正在閱讀行程並轉換格式...")

            # AI 指令：嚴格要求格式與留白
            prompt = f"""
            你是一位專業線控助理。請閱讀行程內容，轉換為 JSON 列表。
            必須包含這 11 個欄位：{', '.join(COLS)}。
            
            【規則】：
            1. 找不到資訊、讀不懂或行程未提及的格子，請直接留空字串 ""。
            2. 不要寫任何解釋性文字或 "無"。
            3. "天數" 欄位請填純數字。
            
            內容：
            {full_text[:3000]}
            """
            
            res = model.generate_content(prompt)
            clean_js = res.text.replace('```json', '').replace('```', '').strip()
            data = json.loads(clean_js)
            
            # 轉換為 DataFrame 並確保 11 欄完整
            df_res
