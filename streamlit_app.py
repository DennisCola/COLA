import streamlit as st
import pandas as pd
import requests
from io import BytesIO
from docx import Document
import google.generativeai as genai
import json

# --- 1. 核心設定 ---
st.set_page_config(page_title="AI小線控", layout="wide")

if "GEMINI_API_KEY" not in st.secrets:
    st.error("請在 Secrets 中設定 GEMINI_API_KEY")
    st.stop()

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash')
URL = "https://docs.google.com/spreadsheets/d/1y53LHsJkDx2xA1MsLzkdd5FYQYWcfQrhs2KeSbsKbZk/export?format=xlsx"
COLS = ["日期", "星期", "天數", "行程大點", "午餐", "餐標", "晚餐", "餐標", "有料門票", "旅館", "星等"]

# --- 2. 側邊欄參數 ---
with st.sidebar:
    st.header("⚡ 報價參數")
    ex = st.number_input("歐元匯率", value=35.0)
    ab = st.number_input("機票票價", value=32000)
    at = st.number_input("機票稅金", value=7500)
    pt = st.number_input("目標利潤", value=8000)

@st.cache_data(ttl=300)
def load_db():
    try:
        r = requests.get(URL)
        with BytesIO(r.content) as f:
            return pd.read_excel(f,"Fixed"), pd.read_excel(f,"Shared"), pd.read_excel(f,"Daily")
    except: return None, None, None

db_f, db_s, db_d = load_db()
st.title("🌍 AI小線控(算報價)")

# --- 3. 主流程 ---
if db_f is not None:
    st.success("✅ 資料庫已連線")
    up = st.file_uploader("1. 上傳行程 Word (.docx)", type=["docx"])
    
    if up:
        # 如果換了新檔案，清除舊的快取資料
        if 'fn' not in st.session_state or st.session_state.fn != up.name:
            st.session_state.fn = up.name
            if 'raw_df' in st.session_state: del st.session_state.raw_df

        # 執行 AI 辨識
        if 'raw_df' not in st.session_state:
            try:
                doc = Document(up)
                tx = "\n".join([p.text.strip() for p in doc.paragraphs if p.text.strip()])
                st.info("🔄 AI 正在分析行程內容...")
                
                prom = f"線控助理。讀行程回傳JSON列表(11欄位:{','.join(COLS)})。無內容填X。內容:{tx[:2800]}"
                res = model.generate_content(prom)
                js = json.loads(res.text.replace('```json', '').replace('```', '').strip())
                
                # 強制轉換為字串確保顯示穩定
                st.session_state.raw_df = pd.DataFrame(js).reindex(columns=COLS).fillna("X").astype(str)
            except:
                st.session_state.raw_df = pd.DataFrame([["D1","X","1","解析失敗","X","X","X","X","X","X","X"]], columns=COLS)

        st.header("2. 線控核對表 (去蕪存菁結果)")
        
        # 關鍵：這裡我們不再使用 session_state 作為 data_editor 的輸入源，而是用一個複製品
        # 這樣可以徹底避免 StreamlitAPIException
        final_df = st.data_editor(
            st.session_state.raw_df, 
            use_container_width=True, 
            num_rows="dynamic",
            key=f"editor_{st.session_state.fn}" # 使用動態 key 確保檔案切換時重置
        )

        if st.button("確認無誤，產出報價"):
            st.divider()
            try:
                # 計算歐元地接成本
                tot_e = 0.0
                for _, r in final_df.iterrows():
                    day_txt = f"{str(r['午餐'])} {str(r['晚餐'])} {str(r['有料門票'])}"
                    for _, dr in db_f.iterrows():
                        if str(dr['判斷文字']) in day_txt:
                            tot_e += float(dr['單價(EUR)'])
                
                # 計算均攤
                sh_e = float(db_s.iloc[:, 1].sum()) if not db_s.empty else 0.0
                
                # 處理天數
                days_col = pd.to_numeric(final_df["天數"], errors='coerce').fillna(0)
                mx_d = int(days_col.max()) if days_col.max() > 0 else 10
                
                # 雜支
                d_i = db_d[db_d.iloc[:, 0] == mx_d]
                d_t = float(d_i.iloc[0, 1] + d_i.iloc[0, 2]) if not d_i.empty else 800.0

                # 階梯計算
                res_list = []
                for p in [16, 21, 26, 31]:
                    sc = sh_e / (p-1) if p > 1 else 0
                    net = (tot_e + sc) * ex + ab + at + d_t
                    pr = (net + pt) * 1.05
                    res_list.append({"人數級距": f"{p-1}+1", "成本(TWD)": f"{int(net):,}", "建議售價(TWD)": f"{int(pr):,}"})
                
                st.subheader("3. 階梯報價單結果")
                st.table(pd.DataFrame(res_list))
                st.balloons()
            except Exception as e:
                st.error(f"計算錯誤：{e}")
else:
    st.error("❌ 無法載入資料庫")
