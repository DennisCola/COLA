import streamlit as st
import pandas as pd
import requests
from io import BytesIO
from docx import Document
import google.generativeai as genai
import json

# --- 1. 初始化與頁面設定 ---
st.set_page_config(page_title="AI線控轉表工具", layout="wide")

if "GEMINI_API_KEY" not in st.secrets:
    st.error("請在 Secrets 中設定 GEMINI_API_KEY")
    st.stop()

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash')

# 11 個標準欄位與 Sheet 連結
COLS = ["日期", "星期", "天數", "行程大點", "午餐", "餐標", "晚餐", "餐標", "有料門票", "旅館", "星等"]
URL = "https://docs.google.com/spreadsheets/d/1y53LHsJkDx2xA1MsLzkdd5FYQYWcfQrhs2KeSbsKbZk/export?format=xlsx"

# --- 2. 資料庫連動檢查 ---
@st.cache_data(ttl=300)
def load_db():
    try:
        r = requests.get(URL)
        with BytesIO(r.content) as f:
            # 讀取三個分頁以確認 Sheet 連結正常
            f_db = pd.read_excel(f, "Fixed")
            s_db = pd.read_excel(f, "Shared")
            d_db = pd.read_excel(f, "Daily")
            return f_db, s_db, d_db
    except:
        return None, None, None

db_f, db_s, db_d = load_db()

st.title("📄 行程自動轉表 (純淨穩定版)")

if db_f is not None:
    st.success("✅ 成本資料庫連動成功")
else:
    st.error("❌ 資料庫連動失敗，請檢查網路或 Sheet 連結")

# --- 3. Word 處理邏輯 (忽略圖片、只讀文字) ---
up = st.file_uploader("1. 上傳行程 Word (.docx)", type=["docx"])

if up:
    # 如果檔案名稱變了，清空舊快取
    if 'fn' not in st.session_state or st.session_state.fn != up.name:
        st.session_state.fn = up.name
        if 'df' in st.session_state:
            del st.session_state.df

    if 'df' not in st.session_state:
        try:
            doc = Document(up)
            # 僅抓取段落與表格內的文字，這會自動過濾圖片
            txt_list = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
            for tbl in doc.tables:
                for row in tbl.rows:
                    for cell in row.cells:
                        if cell.text.strip():
                            txt_list.append(cell.text.strip())
            
            st.info("🔄 AI 正在閱讀行程，並依照格式留白...")
            
            # 餵給 AI 的內容限制在 3000 字內，防止超出 Token 限制
            prompt = f"""
            你是一位專業線控助理。請讀行程並轉換為 JSON 列表。
            欄位必須包含：{','.join(COLS)}。
            【規則】：
            1. 找不到資訊、讀不懂或無資料的格子，請「直接留空字串 ""」。
            2. 不要寫解釋文字。
            3. 天數請填純數字。
            內容：{(' '.join(txt_list))[:3000]}
            """
            
            res = model.generate_content(prompt)
            # 清洗 Markdown 標籤並轉為 JSON
            js_txt = res.text.replace('```json', '').replace('```', '').strip()
            data = json.loads(
