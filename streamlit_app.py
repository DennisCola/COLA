import streamlit as st
import pandas as pd
import requests
from io import BytesIO
from docx import Document
import google.generativeai as genai
import json

st.set_page_config(page_title="AI線控報價", layout="wide")
if "GEMINI_API_KEY" not in st.secrets:
    st.error("請設定 API Key"); st.stop()

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash')
URL = "https://docs.google.com/spreadsheets/d/1y53LHsJkDx2xA1MsLzkdd5FYQYWcfQrhs2KeSbsKbZk/export?format=xlsx"
CLS = ["日期", "星期", "天數", "行程大點", "午餐", "餐標", "晚餐", "餐標", "有料門票", "旅館", "星等"]

with st.sidebar:
    st.header("⚡ 參數")
    ex = st.number_input("匯率", value=35.0)
    ab = st.number_input("機票", value=32000)
    at = st.number_input("稅金", value=7500)
    pt = st.number_input("利潤", value=8000)

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
    up = st.file_uploader("1. 上傳行程 (.docx)", type=["docx"])
    if up:
        if 'df' not in st.session_state or st.session_state.get('fn') != up.name:
            try:
                doc = Document(up)
                tx = "\n".join([p.text.strip() for p in doc.paragraphs if p.text.strip()])
                pm = f"助理。讀行程回JSON列表({','.join(CLS)})。無填X。內容:{tx[:2500]}"
                res = model.generate_content(pm)
                js = json.loads(res.text.replace('```json', '').replace('```', '').strip())
                st.session_state.df = pd.DataFrame(js).reindex(columns=CLS).fillna("X").astype(str)
                st.session_state.fn = up.name
            except:
                st.session_state.df = pd.DataFrame([["" for _ in CLS]], columns=CLS)

        st.header("2. 核對表")
        edf = st.data_editor(st.session_state.df, use_container_width=True, num_rows="dynamic", key="v7")

        if st.button("計算報價"):
            st.divider()
            try:
                calc_df = pd.DataFrame(edf)
                total_eur = 0.0
                # 修正後的縮排區塊
                for _, row in calc_df.iterrows():
                    day_txt = f"{row['午餐']} {row['晚餐']} {row['有料門票']}"
                    for _, db_row in db_f.iterrows():
                        key = str(db_row['判斷文字'])
                        if key and key in day_txt:
                            total_eur += float(db_row['單價(EUR)'])
                
                sh_e = float(db_s.iloc[:, 1].sum()) if not db_s.empty else 0.0
                day_v = pd.to_numeric(calc_df["天數"], errors='coerce').fillna(0)
                mx_d = int(day_v.max()) if day_v.max() > 0 else
