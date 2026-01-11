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

# 定義標準欄位
COLS = ["日期", "星期", "天數", "行程大點", "午餐", "餐標", "晚餐", "餐標", "有料門票", "旅館", "星等"]

if db_f is not None:
    st.success("✅ 資料庫已連線")
    up = st.file_uploader("1. 上傳行程 Word (.docx)", type=["docx"])
    
    if up:
        try:
            tx = "\n".join([p.text for p in Document(up).paragraphs])
            st.info("🔄 AI 正在去蕪存菁，請稍候...")
            
            prom = f"你是線控助理。請讀行程並回傳JSON格式列表，包含這11個鍵：{','.join(COLS)}。若無內容填X。行程內容：{tx[:2500]}"
            res = model.generate_content(prom)
            raw = res.text.replace('```json', '').replace('```', '').strip()
            js_data = json.loads(raw)
            
            # 強制對齊欄位格式
            df_e = pd.DataFrame(js_data).reindex(columns=COLS).fillna("X")
        except:
            st.warning("⚠️ AI 辨識遇到困難，已為您建立空白模板。")
            df_e = pd.DataFrame([["D1","X",1,"請手動輸入","X","X","X","X","X","X","X"]], columns=COLS)

        st.header("2. 線控核對表 (請確認內容)")
        final = st.data_editor(df_e, use_container_width=True, num_rows="dynamic")

        if st.button("確認無誤，計算報價"):
            st.divider()
            tot_e = 0
            # 遍歷核對表，對照 Fixed 資料庫
            for _, r in final.iterrows():
                row_t = f"{r['午餐']} {r['晚餐']} {r['有料門票']}"
                for _, dr in db_f.iterrows():
                    if str(dr['判斷文字']) in row_t: 
                        tot_e += dr['單價(EUR)']
            
            sh_e = db_s.iloc[:, 1].sum() if not db_s.empty else 0
            try:
                mx_d = int(pd.to_numeric(final["天數"]).max())
            except:
                mx_d = 10
            
            d_i = db_d[db_d.iloc[:, 0] == mx_d]
            d_t = (d_i.iloc[0, 1] + d_i.iloc[0, 2]) if not d_i.empty else 800

            res_l = []
            for p in [16, 21, 26, 31]:
                nt = (tot_e + (sh_e/(p-1))) * ex + ab + at + d_t
                pr = (nt + pt) * 1.05
                res_l.append({"人數": f"{p-1}+1", "成本": f"{int(nt):,}", "建議售價": f"{int(pr):,}"})
            
            st.subheader("3. 階梯報價單")
            st.table(pd.DataFrame(res_l))
            st.balloons()
else:
    st.error("❌ 資料庫載入失敗，請確認 Google Sheet 權限。")
