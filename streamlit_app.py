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
            # 讀取三個分頁
            return pd.read_excel(f,"Fixed"), pd.read_excel(f,"Shared"), pd.read_excel(f,"Daily")
    except: return None, None, None

db_f, db_s, db_d = load()
st.title("🌍 AI小線控(算報價)")

if db_f is not None:
    st.success("✅ 資料庫連線成功")
    up = st.file_uploader("1. 上傳行程 (.docx)", type=["docx"])
    
    if up:
        # 檔案更換時清除快取
        if 'df' not in st.session_state or st.session_state.get('fn') != up.name:
            try:
                doc = Document(up)
                tx = "\n".join([p.text.strip() for p in doc.paragraphs if p.text.strip()])
                pm = f"線控助理。讀行程回JSON列表({','.join(CLS)})。無內容填X。行程內容:{tx[:2500]}"
                res = model.generate_content(pm)
                js = json.loads(res.text.replace('```json', '').replace('```', '').strip())
                st.session_state.df = pd.DataFrame(js).reindex(columns=CLS).fillna("X").astype(str)
                st.session_state.fn = up.name
            except:
                st.session_state.df = pd.DataFrame([["D1","X","1","解析失敗","X","X","X","X","X","X","X"]], columns=CLS)

        st.header("2. 線控核對表")
        # 顯示可編輯表格
        edf = st.data_editor(st.session_state.df, use_container_width=True, num_rows="dynamic", key="v4")

        if st.button("確認無誤，產出報價"):
            st.divider()
            try:
                # 1. 計算地接歐元 (Fixed)
                tot_e = 0.0
                for _, r in edf.iterrows():
                    # 合併當天文字進行搜尋
                    day_txt = f"{str(r['午餐'])} {str(r['晚餐'])} {str(r['有料門票'])}"
                    for _, dr in db_f.iterrows():
                        if str(dr['判斷文字']) in day_txt:
                            tot_e += float(dr['單價(EUR)'])
                
                # 2. 計算均攤歐元 (Shared)
                sh_e = float(db_s.iloc[:, 1].sum()) if not db_s.empty else 0.0
                
                # 3. 處理總天數 (找出最大天數，避免 ValueError)
                day_col = pd.to_numeric(edf["天數"], errors='coerce').fillna(0)
                mx_d = int(day_col.max()) if day_col.max() > 0 else 10
                
                # 4. 抓取天數計價 (Daily)
                d_i = db_d[db_d.iloc[:, 0] == mx_d]
                d_t = float(d_i.iloc[0, 1] + d_i.iloc[0, 2]) if not d_i.empty else 800.0

                # 5. 階梯報價計算
                res_list = []
                for p in [16, 21, 26, 31]:
                    sc = sh_e / (p-1) if p > 1 else 0.0
                    # 成本 = (地接+均攤)*匯率 + 機票 + 稅金 + 天數雜支
                    nt = (tot_e + sc) * ex + ab + at + d_t
                    # 建議售價 = (成本+利潤)*稅金5%
                    pr = (nt + pt) * 1.05
                    res_list.append({
                        "人數級距": f"{p-1}+1",
                        "每人成本(TWD)": f"{int(nt):,}",
                        "建議售價(TWD)": f"{int(pr):,}"
                    })
                
                st.subheader("3. 最終報價結果")
                st.table(pd.DataFrame(res_list))
                st.balloons()
            except Exception as e:
                st.error(f"計算過程中發生錯誤，請檢查核對表內容是否正確。錯誤訊息: {e}")
else:
    st.error("❌ 無法載入資料庫，請檢查 Google Sheet 權限。")
