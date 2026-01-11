import streamlit as st
import pandas as pd
import requests
from io import BytesIO
from docx import Document
import google.generativeai as genai
import json

# --- 1. 頁面設定 ---
st.set_page_config(page_title="AI線控轉表工具", layout="wide")

if "GEMINI_API_KEY" not in st.secrets:
    st.error("請在 Secrets 中設定 GEMINI_API_KEY")
    st.stop()

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash')

# 11 個標準欄位與資料庫連結
COLS = ["日期", "星期", "天數", "行程大點", "午餐", "餐標", "晚餐", "餐標", "有料門票", "旅館", "星等"]
URL = "https://docs.google.com/spreadsheets/d/1y53LHsJkDx2xA1MsLzkdd5FYQYWcfQrhs2KeSbsKbZk/export?format=xlsx"

# --- 2. 資料庫連動檢查 ---
@st.cache_data(ttl=300)
def load_db():
    try:
        r = requests.get(URL)
        with BytesIO(r.content) as f:
            # 讀取三個分頁以確認 Sheet 連結正常
            return pd.read_excel(f, "Fixed"), pd.read_excel(f, "Shared"), pd.read_excel(f, "Daily")
    except:
        return None, None, None

db_f, db_s, db_d = load_db()

st.title("📄 行程自動轉表 (核對專用版)")

if db_f is not None:
    st.success("✅ 成本資料庫連動成功")
else:
    st.error("❌ 資料庫連動失敗，請檢查權限")

# --- 3. Word 處理邏輯 ---
up = st.file_uploader("上傳行程 Word (.docx)", type=["docx"])

if up:
    # 檔案更換檢查
    if 'fn' not in st.session_state or st.session_state.fn != up.name:
        st.session_state.fn = up.name
        if 'df' in st.session_state:
            del st.session_state.df

    if 'df' not in st.session_state:
        try:
            doc = Document(up)
            # 僅提取段落文字與表格文字（自動過濾圖片）
            txts = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
            for tbl in doc.tables:
                for row in tbl.rows:
                    for cell in row.cells:
                        if cell.text.strip():
                            txts.append(cell.text.strip())
            
            st.info("🔄 AI 正在去蕪存菁，請稍候...")
            
            # 指令 AI 找不到就留白 ""
            pm = f"""你是一名旅遊助理。請讀行程並轉換為 JSON 列表。
            欄位：{','.join(COLS)}。
            規則：找不到資訊、讀不懂或無資料的格子請直接填空字串 ""。
            內容：{(' '.join(txts))[:2500]}"""
            
            res = model.generate_content(pm)
            js_txt = res.text.replace('```json', '').replace('```', '').strip()
            data = json.loads(js_txt)
            
            # 轉換為 DataFrame 並強制型別為字串以確保穩定
            df_final = pd.DataFrame(data).reindex(columns=COLS).fillna("").astype(str)
            st.session_state.df = df_final
            
        except Exception as e:
            st.warning("⚠️ 辨識遇到困難，已建立空白表格。")
            st.session_state.df = pd.DataFrame([["" for _ in COLS]], columns=COLS)

    # --- 4. 顯示 11 欄核對表 ---
    if 'df' in st.session_state:
        st.subheader("📍 線控核對表")
        st.caption("您可以點擊格子直接修改內容。AI 讀不到的資訊已自動留白。")
        
        # 使用動態 Key 隔離不同檔案的編輯狀態
        st.data_editor(
            st.session_state.df,
            use_container_width=True,
            num_rows="dynamic",
            key=f"editor_{st.session_state.fn}"
        )
