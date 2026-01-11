import streamlit as st
import pandas as pd
import requests
from io import BytesIO
from docx import Document
import google.generativeai as genai
import json

st.set_page_config(page_title="AI小線控", layout="wide")

# 1. 核心設定
if "GEMINI_API_KEY" not in st.secrets:
    st.error("請先在 Secrets 設定 GEMINI_API_KEY")
    st.stop()

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash')
URL = "https://docs.google.com/spreadsheets/d/1y53LHsJkDx2xA1MsLzkdd5FYQYWcfQrhs2KeSbsKbZk/export?format=xlsx"

# 標準 11 欄位
COLS = ["日期", "星期", "天數", "行程大點", "午餐", "餐標", "晚餐", "餐標", "有料門票", "旅館", "星等"]

# 2. 側邊欄
with st.sidebar:
    st.header("⚡ 報價參數")
    ex = st.number_input("歐元匯率", value=35.0)
    ab = st.number_input("機票票價", value=32000)
    at = st.number_input("機票稅金", value=7500)
    pt = st.number_input("目標利潤", value=8000)

@st.cache_data(ttl=300)
def load():
    try:
        r = requests.get(URL)
        with BytesIO(r.content) as f:
            return pd.read_excel(f, "Fixed"), pd.read_excel(f, "Shared"), pd.read_excel(f, "Daily")
    except: return None, None, None

db_f, db_s, db_d = load()
st.title("🌍 AI小線控(算報價)")

if db_f is not None:
    st.success("✅ 資料庫已連線")
    up = st.file_uploader("1. 上傳行程 Word (.docx)", type=["docx"])
    
    if up:
        # 重置 State 以確保新檔案能重新讀取
        if 'last_file' not in st.session_state or st.session_state.last_file != up.name:
            st.session_state.last_file = up.name
            if 'df_e' in st.session_state: del st.session_state.df_e

        if 'df_e' not in st.session_state:
            try:
                doc = Document(up)
                # 【關鍵修正】只抓取文字段落，徹底忽略圖片與亂碼物件
                paras = []
                for p in doc.paragraphs:
                    clean_text = p.text.strip()
                    if clean_text: # 只有非空白的文字段落才加入
                        paras.append(clean_text)
                
                # 同時抓取表格中的文字（許多行程是在表格裡）
                for table in doc.tables:
                    for row in table.rows:
                        for cell in row.cells:
                            cell_text = cell.text.strip()
                            if cell_text:
                                paras.append(cell_text)
                
                tx = "\n".join(paras)
                
                st.info("🔄 AI 正在過濾圖片並進行去蕪存菁...")
                
                prom = f"你是助理。讀取行程並回傳JSON格式列表，包含：{','.join(COLS)}。無內容填X。內容：{tx[:3000]}"
                res = model.generate_content(prom)
                raw = res.text.replace('```json', '').replace('```', '').strip()
                js_data = json.loads(raw)
                
                temp_df = pd.DataFrame(js_data)
                temp_df = temp_df.reindex(columns=COLS).fillna("X").astype(str)
                st.session_state.df_e = temp_df
            except Exception as e:
                st.warning("⚠️ 辨識遇到困難，已建立空白模板。")
                st.session_state.df_e = pd.DataFrame([["D1","X","1","請手動輸入","X","X","X","X","X","X","X"]], columns=COLS)

        st.header("2. 線控核對表")
        final = st.data_editor(st.session_state.df_e, use_container_width=True, num_rows="dynamic")

        if st.button("確認無誤，計算報價"):
            st.divider()
            tot_e = 0
            # 比對邏輯：將當天所有資訊合併後搜尋資料庫關鍵字
            for _, r in final.iterrows():
                row_t = f"{r['午餐']} {r['晚餐']} {r['有料門票']}"
                for _, dr in db_f.iterrows():
                    if str(dr['判斷文字']) in row_t: 
                        tot_e += float(
