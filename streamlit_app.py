import streamlit as st
import pandas as pd
import requests
from io import BytesIO
from docx import Document
import google.generativeai as genai
import json

# --- 1. 基礎設定 ---
st.set_page_config(page_title="線控行程轉表工具", layout="wide")

if "GEMINI_API_KEY" not in st.secrets:
    st.error("請在 Secrets 設定 GEMINI_API_KEY"); st.stop()

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash')

# 11 個標準欄位
COLS = ["日期", "星期", "天數", "行程大點", "午餐", "餐標", "晚餐", "餐標", "有料門票", "旅館", "星等"]
URL = "https://docs.google.com/spreadsheets/d/1y53LHsJkDx2xA1MsLzkdd5FYQYWcfQrhs2KeSbsKbZk/export?format=xlsx"

# --- 2. 資料庫連動 ---
@st.cache_data(ttl=300)
def load_db():
    try:
        r = requests.get(URL)
        with BytesIO(r.content) as f:
            # 測試讀取以確認連動
            return pd.read_excel(f, "Fixed"), pd.read_excel(f, "Shared"), pd.read_excel(f, "Daily")
    except: return None, None, None

db_f, db_s, db_d = load_db()

st.title("📄 行程自動轉表 (核對專用)")

if db_f is not None:
    st.success("✅ 成本資料庫連動成功")
else:
    st.error("❌ 資料庫連動失敗")

# --- 3. Word 處理 ---
up = st.file_uploader("上傳行程 Word (.docx)", type=["docx"])

if up:
    # 檔案切換檢查
    if 'fn' not in st.session_state or st.session_state.fn != up.name:
        st.session_state.fn = up.name
        if 'df' in st.session_state: del st.session_state.df

    if 'df' not in st.session_state:
        try:
            doc = Document(up)
            # 提取文字與表格文字，忽略圖片
            txts = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
            for tbl in doc.tables:
                for row in tbl.rows:
                    for cell in row.cells:
                        if cell.text.strip(): txts.append(cell.text.strip())
            
            st.info("🔄 AI 正在分析行程內容...")
            pm = f"助理。讀行程回JSON列表({','.join(COLS)})。無資訊留空字串''。內容:{(' '.join(txts))[:2500]}"
            res = model.generate_content(pm)
            js = json.loads(res.text.replace('```json', '').replace('```', '').strip())
            
            # 轉為 DataFrame 並確保 11 欄位完整，且全部轉字串避免當機
            df_res = pd.DataFrame(js).reindex(columns=COLS).fillna("").astype(str)
            st.session_state.df = df_res
        except Exception:
            st.session_state.df = pd.DataFrame([["" for _ in COLS]], columns=COLS)

    st.subheader("📍 線控核對表")
