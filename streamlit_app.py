import streamlit as st
import pandas as pd
import requests
from io import BytesIO
from docx import Document
import google.generativeai as genai
import json

# --- 1. 頁面設定 ---
st.set_page_config(page_title="線控 6 欄位辨識版", layout="wide")

if "GEMINI_API_KEY" not in st.secrets:
    st.error("請設定 API Key"); st.stop()

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash')

# 核心 6 欄位：保留天數作為座標
COLS = ["天數", "行程大點", "午餐", "晚餐", "有料門票", "旅館"]

st.title("📄 行程內容提取 (6 欄位座標版)")
st.caption("保留『天數』作為基準，專注抓取每日的核心成本項目。")

up = st.file_uploader("上傳行程 Word (.docx)", type=["docx"])

if up:
    if 'df' not in st.session_state or st.session_state.get('fn') != up.name:
        try:
            doc = Document(up)
            content = []
            # 提取段落與表格文字
            for p in doc.paragraphs:
                if p.text.strip(): content.append(p.text.strip())
            for tbl in doc.tables:
                for row in tbl.rows:
                    row_txt = [c.text.strip() for c in row.cells if c.text.strip()]
                    if row_txt: content.append(" | ".join(dict.fromkeys(row_txt)))
            
            raw_text = "\n".join(content)
            st.session_state.raw_debug = raw_text 
            
            st.info("🔄 AI 正在以『天數』為基準進行掃描...")

            pm = f"""你是一名專業線控。請讀行程並轉換為每日 JSON 列表。
            欄位必須精確包含：{','.join(COLS)}。
            
            【指令】：
            1. 『天數』：請識別這是第幾天（如：1, 2, 3...）。
            2. 『行程大點』：抓出該日的主要城市。
            3. 『午餐/晚餐』：抓出餐飲內容，找不到就留空。
            4. 『有料門票』：找尋『入內』、『含門票』關鍵字。
            5. 『旅館』：抓出飯店名稱。
            6. 若無資訊則留空字串 ""。
            
            內容：
            {raw_text[:4000]}"""
            
            res = model.generate_content(pm)
            js_txt = res.text.replace('```json', '').replace('```', '').strip()
            data = json.loads(js_txt)
            
            # 強制轉換並對齊
            st.session_state.df = pd.DataFrame(data).reindex(columns=COLS).fillna("").astype(str)
            st.session_state.fn = up.name
        except Exception:
            st.session_state.df = pd.DataFrame([["" for _ in COLS]], columns=COLS)

    if 'df' in st.session_state:
        st.subheader("📍 核心內容核對")
        st.data_editor(st.session_state.df, use_container_width=True, num_rows="dynamic", key=f"ed_{up.name}")
