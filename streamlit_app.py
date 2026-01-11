import streamlit as st
import pandas as pd
import requests
from io import BytesIO
from docx import Document
import google.generativeai as genai
import json
import re

# --- 1. 頁面設定 ---
st.set_page_config(page_title="奧捷行程辨識引擎", layout="wide")

if "GEMINI_API_KEY" not in st.secrets:
    st.error("請在 Secrets 設定 API Key"); st.stop()

# 修正模型名稱調用方式
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash')

# 核心 6 欄位
COLS = ["天數", "行程大點", "午餐", "晚餐", "有料門票", "旅館"]

st.title("🌍 奧捷行程提取器 (強力解析版)")
st.caption("已修正模型調用路徑，請重新嘗試上傳。")

up = st.file_uploader("1. 上傳您的行程 Word (.docx)", type=["docx"])

if up:
    if 'df' not in st.session_state or st.session_state.get('fn') != up.name:
        try:
            doc = Document(up)
            all_text = []
            
            # 提取所有段落
            for p in doc.paragraphs:
                if p.text.strip(): all_text.append(p.text.strip())
            
            # 提取所有表格文字
            for tbl in doc.tables:
                for row in tbl.rows:
                    cells = [c.text.strip() for c in row.cells if c.text.strip()]
                    if cells: all_text.append(" | ".join(dict.fromkeys(cells)))
            
            raw_content = "\n".join(all_text)
            st.session_state.raw_debug = raw_content 
            
            st.info("🔄 AI 正在深度掃描文字內容...")

            # 強力 Prompt 指令
            prompt = f"""
            你是一位資深旅行社線控助理。請從下方的行程文字中，提取每日資訊並轉為 JSON 列表格式。
            欄位必須精確包含：{','.join(COLS)}。
            
            【提取規範】：
            - 『天數』：標註 Day 1, Day 2... 
            - 『行程大點』：造訪城市或景點。
            - 『午餐/晚餐』：抓出餐飲關鍵字（如：中式、自理、鱒魚餐）。
            - 『有料門票』：找尋提及『入內』、『含門票』的項目。
            - 『旅館』：抓出飯店名稱。
            - 無資訊請填入 ""。
            
            文字內容：
            {raw_content[:4000]}
            """
            
            # 呼叫 AI
            response = model.generate_content(prompt)
            
            # 使用正則表達式精準提取 JSON 區塊，防止 AI 回傳多餘文字
            match = re.search(r'\[\s*\{.*\}\s*\]', response.text, re.DOTALL)
            if match:
                js_txt = match.group(0)
                data = json.loads(js_txt)
                st.session_state.df = pd.DataFrame(data).reindex(columns=COLS).fillna("").astype(str)
                st.session_state.fn = up.name
            else:
                st.error("AI 回傳格式不正確，請再試一次。")
                
        except Exception as e:
            st.error(f"解析發生錯誤：{e}")
            st.session_state.df = pd.DataFrame([["" for _ in COLS]], columns=COLS)

    # 顯示表格
    if 'df' in st.session_state:
        st.subheader("📍 核心內容核對")
        st.data_editor(
            st.session_state.df, 
            use_container_width=True, 
            num_rows="dynamic", 
            key=f"ed_{up.name}"
        )

    # 偵錯工具
    with st.expander("🔍 看看程式從 Word 裡讀到了什麼文字？"):
        if 'raw_debug' in st.session_state:
            st.text_area("讀取到的文字內容：", st.session_state.raw_debug, height=300)
