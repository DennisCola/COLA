import streamlit as st
import pandas as pd
import requests
from io import BytesIO
from docx import Document
import google.generativeai as genai
import json

# --- 1. 頁面設定 ---
st.set_page_config(page_title="奧捷行程辨識引擎", layout="wide")

if "GEMINI_API_KEY" not in st.secrets:
    st.error("請在 Secrets 設定 API Key"); st.stop()

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
# 使用 flash 模型確保速度
model = genai.GenerativeModel('gemini-1.5-flash')

# 核心 6 欄位
COLS = ["天數", "行程大點", "午餐", "晚餐", "有料門票", "旅館"]

st.title("🌍 奧捷行程提取器 (強力解析版)")
st.caption("針對複雜 Word 排版優化：強制提取所有天數內容。")

up = st.file_uploader("1. 上傳您的行程 Word (.docx)", type=["docx"])

if up:
    if 'df' not in st.session_state or st.session_state.get('fn') != up.name:
        try:
            doc = Document(up)
            all_text = []
            
            # 遍歷段落
            for p in doc.paragraphs:
                if p.text.strip(): all_text.append(p.text.strip())
            
            # 遍歷表格 (這是旅行社行程最愛放的地方)
            for tbl in doc.tables:
                for row in tbl.rows:
                    cells = [c.text.strip() for c in row.cells if c.text.strip()]
                    if cells: all_text.append(" | ".join(dict.fromkeys(cells)))
            
            raw_content = "\n".join(all_text)
            st.session_state.raw_debug = raw_content 
            
            st.info("🔄 AI 正在深度掃描文字內容，請稍候...")

            # 強力 Prompt 指令
            prompt = f"""
            你是一位資深旅行社線控助理。請從下方的行程文字中，提取每日資訊並轉為 JSON 列表。
            欄位必須精確包含：{','.join(COLS)}。
            
            【提取規範】：
            - 『天數』：請標註 Day 1, Day 2... 或是 1, 2...
            - 『行程大點』：抓出當天造訪的城市（如：布拉格、薩爾斯堡）。
            - 『午餐/晚餐』：只要有提到餐點關鍵字（如：豬腳餐、六菜一湯、飯店內、自理）就抓出來。
            - 『有料門票』：找尋有提到『入內』、『包含門票』、『參觀』的景點（如：鹽礦、天文鐘、城堡區）。
            - 『旅館』：抓出飯店名稱（如：HILTON）或星等。
            - 如果該項真的沒提到，請填入空字串 ""。不要寫任何解釋。
            
            文字內容：
            {raw_content[:4000]}
            """
            
            res = model.generate_content(prompt)
            # 清理 JSON 字串
            js_txt = res.text.replace('```json', '').replace('```', '').strip()
            data = json.loads(js_txt)
            
            # 轉為 DataFrame 並強制型別
            st.session_state.df = pd.DataFrame(data).reindex(columns=COLS).fillna("").astype(str)
            st.session_state.fn = up.name
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
        else:
            st.write("目前沒有數據。")
