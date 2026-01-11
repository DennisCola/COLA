import streamlit as st
import pandas as pd
import requests
from io import BytesIO
from docx import Document
import google.generativeai as genai
import json

st.set_page_config(page_title="AI線控轉表", layout="wide")
if "GEMINI_API_KEY" not in st.secrets:
    st.error("請設定 API Key"); st.stop()

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash')

# 11 欄位與資料庫連結
COLS = ["日期", "星期", "天數", "行程大點", "午餐", "餐標", "晚餐", "餐標", "有料門票", "旅館", "星等"]
URL = "https://docs.google.com/spreadsheets/d/1y53LHsJkDx2xA1MsLzkdd5FYQYWcfQrhs2KeSbsKbZk/export?format=xlsx"

@st.cache_data(ttl=300)
def load_db():
    try:
        r = requests.get(URL)
        with BytesIO(r.content) as f:
            return pd.read_excel(f, "Fixed"), pd.read_excel(f, "Shared"), pd.read_excel(f, "Daily")
    except: return None, None, None

db_f, db_s, db_d = load_db()
st.title("📄 行程自動轉表 (核對專用)")

if db_f is not None:
    st.success("✅ 成本資料庫連動成功")
    up = st.file_uploader("上傳 Word (.docx)", type=["docx"])
    
    if up:
        if 'df' not in st.session_state or st.session_state.get('fn') != up.name:
            try:
                doc = Document(up)
                # 僅提取文字，自動過濾圖片
                txts = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
                for t in doc.tables:
                    for r in t.rows:
                        for c in r.cells:
                            if c.text.strip(): txts.append(c.text.strip())
                
                st.info("🔄 AI 正在分析...")
                pm = f"助理。讀行程回JSON列表({','.join(COLS)})。無資訊留空字串''。內容:{(' '.join(txts))[:2500]}"
                res = model.generate_content(pm)
                js = json.loads(res.text.replace('```json', '').replace('```', '').strip())
                # 強制轉換所有內容為字串並留白
                st.session_state.df = pd.DataFrame(js).reindex(columns=COLS).fillna("").astype(str)
                st.session_state.fn = up.name
            except:
                st.session_state.df = pd.DataFrame([["" for _ in COLS]], columns=COLS)

        if 'df' in st.session_state:
            st.subheader("📍 線控核對表")
            st.data_editor(st.session_state.df, use_container_width=True, num_rows="dynamic", key=f"ed_{st.session_state.fn}")
else:
    st.error("❌ 無法連動資料庫")
