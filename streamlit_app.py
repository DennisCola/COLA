import streamlit as st
import pandas as pd
import requests
from io import BytesIO
from docx import Document
import google.generativeai as genai
import json

st.set_page_config(page_title="線控 Word 辨識強化版", layout="wide")

if "GEMINI_API_KEY" not in st.secrets:
    st.error("請設定 API Key"); st.stop()

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash')

COLS = ["天數", "日期", "星期", "行程大點", "午餐", "晚餐", "有料門票", "旅館"]

st.title("📄 行程辨識強化版")
st.caption("針對『讀不出內容』進行了指令優化，並加強了 Word 表格解析。")

up = st.file_uploader("上傳行程 Word (.docx)", type=["docx"])

if up:
    if 'df' not in st.session_state or st.session_state.get('fn') != up.name:
        try:
            doc = Document(up)
            # 1. 深度提取文字（包含標題、段落、表格）
            full_content = []
            for p in doc.paragraphs:
                if p.text.strip(): full_content.append(p.text.strip())
            for tbl in doc.tables:
                for row in tbl.rows:
                    row_txt = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                    if row_txt: full_content.append(" | ".join(row_txt))
            
            raw_text = "\n".join(full_content)
            st.session_state.raw_debug = raw_text # 留存原始文字供檢查
            
            st.info("🔄 AI 深度分析中，這份行程比較長，請稍等...")

            # 2. 強化指令：要求 AI 必須根據上下文推斷
            prompt = f"""
            你是一位專業的旅行社線控助理。請從下方的行程文字中，提取每日資訊並轉為 JSON 列表。
            欄位：{','.join(COLS)}。
            
            【提取指南】：
            - 『行程大點』：該日停留的城市或景點。
            - 『午餐/晚餐』：找尋有餐飲描述的地方（如：鱒魚餐、自理、中式餐）。
            - 『有料門票』：找尋提及『入內』、『含門票』或括號內的景點。
            - 『旅館』：找尋當晚住宿的飯店名稱或星等。
            - 如果該欄位沒提到，請留空字串 ""。
            
            文字內容：
            {raw_text[:4000]} 
            """
            
            res = model.generate_content(prompt)
            js_txt = res.text.replace('```json', '').replace('```', '').strip()
            data = json.loads(js_txt)
            
            st.session_state.df = pd.DataFrame(data).reindex(columns=COLS).fillna("").astype(str)
            st.session_state.fn = up.name
        except Exception as e:
            st.error("辨識失敗，請檢查 Word 是否加密或格式異常。")
            st.session_state.df = pd.DataFrame([["" for _ in COLS]], columns=COLS)

    # 3. 顯示表格
    if 'df' in st.session_state:
        st.subheader("📍 辨識結果核對")
        st.data_editor(st.session_state.df, use_container_width=True, num_rows="dynamic", key=f"ed_{up.name}")

    # 4. 偵錯模式 (如果您覺得還是空的，點開這個看看)
    with st.expander("🔍 偵錯：看看程式讀到了什麼文字？"):
        if 'raw_debug' in st.session_state:
            st.text_area("Word 原始提取文字", st.session_state.raw_debug, height=300)
        else:
            st.write("尚未讀取檔案")
