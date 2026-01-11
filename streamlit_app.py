import streamlit as st
import pandas as pd
import requests
from io import BytesIO
from docx import Document
import google.generativeai as genai
import json

# --- 1. 基礎設定 ---
st.set_page_config(page_title="AI線控報價系統", layout="wide")

if "GEMINI_API_KEY" not in st.secrets:
    st.error("請在 Secrets 中設定 GEMINI_API_KEY")
    st.stop()

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash')

# 門票與成本資料庫網址
SHEET_URL = "https://docs.google.com/spreadsheets/d/1y53LHsJkDx2xA1MsLzkdd5FYQYWcfQrhs2KeSbsKbZk/export?format=xlsx"
COLS = ["日期", "星期", "天數", "行程大點", "午餐", "餐標", "晚餐", "餐標", "有料門票", "旅館", "星等"]

# --- 2. 側邊欄：浮動成本按鈕 (回來了！) ---
with st.sidebar:
    st.header("⚡ 報價即時參數")
    ex_rate = st.number_input("今日歐元匯率", value=35.0, step=0.1)
    air_base = st.number_input("機票票價 (TWD)", value=32000)
    air_tax = st.number_input("機票稅金 (TWD)", value=7500)
    profit = st.number_input("當團目標利潤 (TWD)", value=8000)
    st.divider()
    st.info("💡 修改參數後，下方的報價單會自動重新計算。")

# --- 3. 讀取資料庫 ---
@st.cache_data(ttl=300)
def load_db():
    try:
        r = requests.get(SHEET_URL)
        with BytesIO(r.content) as f:
            return pd.read_excel(f,"Fixed"), pd.read_excel(f,"Shared"), pd.read_excel(f,"Daily")
    except: return None, None, None

db_f, db_s, db_d = load_db()

st.title("🌍 AI小線控(算報價)")

# --- 4. 主流程 ---
if db_f is not None:
    up = st.file_uploader("1. 上傳行程 Word (.docx)", type=["docx"])
    
    if up:
        if 'fn' not in st.session_state or st.session_state.fn != up.name:
            st.session_state.fn = up.name
            try:
                doc = Document(up)
                paras = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
                for table in doc.tables:
                    for row in table.rows:
                        for cell in row.cells:
                            if cell.text.strip(): paras.append(cell.text.strip())
                
                st.info("🔄 AI 正在去蕪存菁...")
                pm = f"助理。讀行程回JSON列表({','.join(COLS)})。若無資訊留空字串''。內容:{(' '.join(paras))[:2500]}"
                res = model.generate_content(pm)
                js = json.loads(res.text.replace('```json', '').replace('```', '').strip())
                st.session_state.df = pd.DataFrame(js).reindex(columns=COLS).fillna("").astype(str)
            except:
                st.session_state.df = pd.DataFrame([["" for _ in COLS]], columns=COLS)

        st.header("2. 線控核對表")
        # 顯示 11 欄核對表
        final_df = st.data_editor(st.session_state.df, use_container_width=True, num_rows="dynamic", key=f"ed_{st.session_state.fn}")

        # --- 5. 自動計算結果 ---
        if st.button("確認核對表無誤，產出報價"):
            st.divider()
            try:
                # 計算地接歐元 (掃描表格內容並比對資料庫)
                total_fixed_eur = 0.0
                for _, r in final_df.iterrows():
                    # 合併當天所有可能包含項目的文字
                    day_text = f"{r['午餐']} {r['晚餐']} {r['有料門票']}"
                    for _, dr in db_f.iterrows():
                        if str(dr['判斷文字']) in day_text and str(dr['判斷文字']) != "":
                            total_fixed_eur += float(dr['單價(EUR)'])
                
                # 均攤成本 (Shared)
                total_shared_eur = float(db_s.iloc[:, 1].sum()) if not db_s.empty else 0.0
                
                # 天數雜支 (Daily)
                days_col = pd.to_numeric(final_df["天數"],
