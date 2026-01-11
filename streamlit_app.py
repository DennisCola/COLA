import streamlit as st
import pandas as pd
import requests
from io import BytesIO
from docx import Document
import google.generativeai as genai
import json

st.set_page_config(page_title="AI小線控", layout="wide")
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash')
URL = "https://docs.google.com/spreadsheets/d/1y53LHsJkDx2xA1MsLzkdd5FYQYWcfQrhs2KeSbsKbZk/export?format=xlsx"
COLS = ["日期", "星期", "天數", "行程大點", "午餐", "餐標", "晚餐", "餐標", "有料門票", "旅館", "星等"]

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
    st.success("✅ 資料庫已連線")
    up = st.file_uploader("1. 上傳行程", type=["docx"])
    
    if up:
        # 讀取並辨識 (只在檔案改變時運行)
        if 'data' not in st.session_state or st.session_state.get('fn') != up.name:
            try:
                doc = Document(up)
                tx = "\n".join([p.text.strip() for p in doc.paragraphs if p.text.strip()])
                prom = f"線控助理。讀行程回傳JSON列表(11欄位:{','.join(COLS)})。行程:{tx[:2500]}"
                res = model.generate_content(prom)
                js = json.loads(res.text.replace('```json', '').replace('```', '').strip())
                st.session_state.data = pd.DataFrame(js).reindex(columns=COLS).fillna("X").astype(str)
                st.session_state.fn = up.name
            except:
                st.session_state.data = pd.DataFrame([["D1","X","1","錯誤","X","X","X","X","X","X","X"]], columns=COLS)

        st.header("2. 線控核對表")
        # 關鍵修正：使用 key 讓編輯器穩定，並直接處理資料
        final_df = st.data_editor(st.session_state.data, use_container_width=True, num_rows="dynamic", key="editor_v1")

        if st.button("確認無誤，產出報價"):
            st.divider()
            tot_e = 0
            for _, r in final_df.iterrows():
                # 比對內容包含午餐、晚餐與門票
                txt = f"{r['午餐']} {r['晚餐']} {r['有料門票']}"
                for _, dr in db_f.iterrows():
                    if str(dr['判斷文字']) in txt: tot_e += float(dr['單價(EUR)'])
            
            sh_e = db_s.iloc[:, 1].sum() if not db_s.empty else 0
            try: mx_d = int(pd.to_numeric(final_df["天數"]).max())
            except: mx_d = 10
            
            d_i = db_d[db_d.iloc[:, 0] == mx_d]
            d_t = (d_i.iloc[0, 1] + d_i.iloc[0, 2]) if not d_i.empty else 800

            res_l = []
            for p in [16, 21, 26, 31]:
                sc = sh_e / (p-1) if p > 1 else 0
                nt = (tot_e + sc) * ex + ab + at + d_t
                pr = (nt + pt) * 1.05
                res_l.append({"人數": f"{p-1}+1", "成本": f"{int(nt):,}", "建議售價": f"{int(pr):,}"})
            st.table(pd.DataFrame(res_l))
            st.balloons()
else: st.error("❌ 載入失敗")
