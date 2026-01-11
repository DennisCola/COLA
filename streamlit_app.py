import streamlit as st
import pandas as pd
import requests
from io import BytesIO
from docx import Document
import google.generativeai as genai
import json

st.set_page_config(page_title="AI小線控", layout="wide")
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
    st.success("✅ 已連線")
    up = st.file_uploader("1. 上傳行程 (.docx)", type=["docx"])
    if up:
        if 'df' not in st.session_state or st.session_state.get('fn') != up.name:
            try:
                doc = Document(up)
                tx = "\n".join([p.text.strip() for p in doc.paragraphs if p.text.strip()])
                pm = f"線控助理。讀行程回JSON列表({','.join(CLS)})。無填X。內容:{tx[:2500]}"
                res = model.generate_content(pm)
                js = json.loads(res.text.replace('```json', '').replace('```', '').strip())
                st.session_state.df = pd.DataFrame(js).reindex(columns=CLS).fillna("X").astype(str)
                st.session_state.fn = up.name
            except:
                st.session_state.df = pd.DataFrame([["D1","X","1","解析失敗"]], columns=CLS).reindex(columns=CLS).fillna("X")

        st.header("2. 核對表")
        edf = st.data_editor(st.session_state.df, use_container_width=True, num_rows="dynamic", key="v3")

        if st.button("計算報價"):
            st.divider()
            tot_e = 0
            for _, r in edf.iterrows():
                row_t = f"{r['午餐']} {r['晚餐']} {r['有料門票']}"
                for _, dr in db_f.iterrows():
                    if str(dr['判斷文字']) in row_t: tot_e += float(dr['單價(EUR)'])
            
            sh_e = db_s.iloc[:, 1].sum() if not db_s.empty else 0
            try: mx_d = int(pd.to_numeric(edf["天數"]).max())
            except: mx_d = 10
            
            d_i = db_d[db_d.iloc[:, 0] == mx_d]
            d_t = (d_i.iloc[0, 1] + d_i.iloc[0, 2]) if not d_i.empty else 800

            res = []
            for p in [16, 21, 26, 31]:
                sc = sh_e / (p-1) if p > 1 else 0
                nt = (tot_e + sc) * ex + ab + at + d_t
                pr = (nt + pt) * 1.05
                res.append({"人數": f"{p-1}+1", "成本": f"{int(nt):,}", "建議售價": f"{int(pr):,}"})
            st.table(pd.DataFrame(res))
            st.balloons()
else: st.error("❌ 載入失敗")
