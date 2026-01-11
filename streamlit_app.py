import streamlit as st
import pandas as pd
import requests
from io import BytesIO
from docx import Document
import google.generativeai as genai
import json

# --- 基礎設定 ---
st.set_page_config(page_title="AI行程轉表工具", layout="wide")

if "GEMINI_API_KEY" not in st.secrets:
    st.error("請在 Secrets 中設定 GEMINI_API_KEY")
    st.stop()

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash')

# 定義您要求的 11 個標準欄位
COLS = ["日期", "星期", "天數", "行程大點", "午餐", "餐標", "晚餐", "餐標", "有料門票", "旅館", "星等"]

st.title("📄 Word 行程自動轉表")
st.caption("上傳 Word 檔，自動提取 11 欄位資訊。若 AI 無法辨識特定內容，將自動留白。")

up = st.file_uploader("上傳行程 Word (.docx)", type=["docx"])

if up:
    # 檔案切換檢查
    if 'fn' not in st.session_state or st.session_state.fn != up.name:
        st.session_state.fn = up.name
        if 'df' in st.session_state: del st.session_state.df

    if 'df' not in st.session_state:
        try:
            # 1. 提取 Word 文字（忽略圖片）
            doc = Document(up)
            paras = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
            # 包含表格內的文字
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        if cell.text.strip(): paras.append(cell.text.strip())
            
            full_text = "\n".join(paras)
            
            st.info("🔄 AI 正在提取行程骨架，請稍候...")

            # 2. 向 AI 發送指令：強調空白容錯
            prompt = f"""
            你是一名專業的旅遊業助理。請閱讀下方的 Word 行程內容，並將其轉換為 JSON 列表格式。
            必須包含以下 11 個鍵：{', '.join(COLS)}。
            
            【重要規則】：
            1. 如果行程中找不到某個欄位的資訊（例如沒寫餐標、沒寫門票），該欄位請直接留空字串 ""，不要寫 "無"、"X" 或任何解釋。
            2. 確保產出的是純粹的 JSON 格式。
            
            行程內容：
            {full_text[:3000]}
            """
            
            res = model.generate_content(prompt)
            # 清洗 AI 回傳的 Markdown 語法
            clean_json = res.text.replace('```json', '').replace('```', '').strip()
            data = json.loads(clean_json)
            
            # 3. 轉為 DataFrame 並確保格式對齊
            df = pd.DataFrame(data).reindex(columns=COLS).fillna("").astype(str)
            st.session_state.df = df
            
        except Exception as e:
            st.error(f"辨識過程中發生錯誤，請確保檔案格式正確。")
            st.session_state.df = pd.DataFrame([["" for _ in COLS]], columns=COLS)

    # 4. 顯示結果表格
    st.subheader("📍 線控核對表")
    # 使用動態 Key 避免當機
    edited_df = st.data_editor(
        st.session_state.df,
        use_container_width=True,
        num_rows="dynamic",
        key=f"editor_{st.session_state.fn}"
    )

    # 提供下載功能
    csv = edited_df.to_csv
