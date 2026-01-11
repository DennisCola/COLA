import streamlit as st
import pandas as pd
import requests
from io import BytesIO
from docx import Document
import google.generativeai as genai
import json

# 1. 基礎設定
st.set_page_config(page_title="AI線控報價", layout="wide")
if "GEMINI_API_KEY" not in st.secrets:
    st.error("請在 Secrets 中設定 GEMINI_API_KEY"); st.stop()

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash')
URL = "https://docs.google.com/spreadsheets/d/1y53LHsJkDx2xA1MsLzkdd5FYQYWcfQrhs2KeSbsKbZk/export?format=xlsx"
COLS = ["日期", "星期", "天數", "行程大點", "午餐", "餐標", "晚餐", "餐標", "有料門票", "旅館", "星等"]

# 2. 側邊欄：浮動成本按鈕
with st.sidebar:
    st.header("⚡ 報價即時參數")
    ex = st.number_input("今日歐元匯率", value=35.0)
    ab = st.number_input("機票票價 (TWD)", value=32000)
    at = st.number_input("機票稅金 (TWD)", value=7500)
    pt = st.number_input("當團目標利潤 (TWD)", value=8000)

@st.cache_data(ttl=300)
def load():
    try:
        r = requests.get(URL)
        with BytesIO(r.content) as f:
            return pd.read_excel(f,"Fixed"), pd.read_excel(f,"Shared"), pd.read_excel(f,"Daily")
    except: return None, None, None

db_f, db_s, db_d = load()
st.title("🌍 AI小線控(算報價)")

if db_f is not None:
    up = st.file_uploader("1. 上傳行程 Word (.docx)", type=["docx"])
    
    if up:
        # 當上傳新檔案或初次執行時
        if 'df' not in st.session_state or st.session_state.get('fn') != up.name:
            try:
                doc = Document(up)
                tx = "\n".join([p.text.strip() for p in doc.paragraphs if p.text.strip()])
                st.info("🔄 AI 正在分析行程內容...")
                pm = f"助理。讀行程回JSON列表({','.join(COLS)})。無資訊留空''。內容:{tx[:2800]}"
                res = model.generate_content(pm)
                js = json.loads(res.text.replace('```json', '').replace('```', '').strip())
                st.session_state.df = pd.DataFrame(js).reindex(columns=COLS).fillna("").astype(str)
                st.session_state.fn = up.name
            except:
                st.session_state.df = pd.DataFrame([["" for _ in COLS]], columns=COLS)

        st.header("2. 線控核對表")
        # 顯示編輯器，並給予固定 Key
        edf = st.data_editor(st.session_state.df, use_container_width=True, num_rows="dynamic", key="main_editor")

        if st.button("確認無誤，產出報價"):
            st.divider()
            try:
                # 確保 edf 是 DataFrame 格式以防 AttributeError
                calc_df = pd.DataFrame(edf)
                
                tot_e = 0.0
                for _, r in calc_df.iterrows():
                    row_t = f"{str(r['午餐'])} {str(r['晚餐'])} {str(r['有料門票'])}"
                    for _, dr in db_f.iterrows():
                        key_word = str(dr['判斷文字'])
                        if key_word and key_word in row_t:
                            tot_e += float(dr['單價(EUR)'])
                
                sh_e = float(db_s.iloc[:, 1].sum()) if not db_s.empty else 0.0
                day_v = pd.to_numeric(calc_df["天數"], errors='coerce').fillna(0)
                mx_d = int(day_v.max()) if day_v.max() > 0 else 10
                
                d_info = db_d[db_d.iloc[:, 0] == mx_d]
                d_twd = float(d_info.iloc[0, 1] + d_info.iloc[0, 2]) if not d_info.empty else 800.0

                res_l = []
                for p in [16, 21, 26, 31]:
                    sc = sh_e / (p-
