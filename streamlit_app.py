import streamlit as st
import pandas as pd
import google.generativeai as genai
from docx import Document
import json
import re

# --- 1. 頁面設定 ---
st.set_page_config(page_title="奧捷行程自動轉表", layout="wide")

if "GEMINI_API_KEY" not in st.secrets:
    st.error("請在 Secrets 設定 API Key"); st.stop()

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash')

# 核心 6 欄位
COLS = ["天數", "行程大點", "午餐", "晚餐", "有料門票", "旅館"]

st.title("🌍 奧捷行程 AI 自動轉表")
st.info("💡 運作模式：上傳 Word 後，AI 會自動提取純文字並歸類為 6 個核心欄位。")

# --- 2. 檔案上傳與處理 ---
up = st.file_uploader("1. 上傳行程 Word (.docx)", type=["docx"])

if up:
    # 當檔案更換時，觸發重新辨識
    if 'fn' not in st.session_state or st.session_state.fn != up.name:
        try:
            # A. 讀取 Word 並轉換為純文字 (排除圖片干擾)
            doc = Document(up)
            text_list = []
            for p in doc.paragraphs:
                if p.text.strip(): text_list.append(p.text.strip())
            for tbl in doc.tables:
                for row in tbl.rows:
                    cells = [c.text.strip() for c in row.cells if c.text.strip()]
                    if cells: text_list.append(" | ".join(dict.fromkeys(cells)))
            
            pure_text = "\n".join(text_list)
            
            st.info("🔄 AI 已自動提取純文字，正在進行 6 欄位分類...")

            # B. 餵給 AI 進行純文字分類
            prompt = f"""
            你是一位專業線控。請根據以下行程文字，將內容精準分類為 JSON 列表。
            欄位必須為：{','.join(COLS)}。
            
            【分類細則】：
            - 『天數』：標註 1, 2, 3...。
            - 『行程大點』：造訪的主要城市或地區。
            - 『午餐/晚餐』：具體餐飲內容（如：鱒魚餐、中式六菜一湯、自理）。
            - 『有料門票』：提及『含門票』、『入內』的景點。
            - 『旅館』：飯店名稱與星等。
            - 找不到資訊請填空字串 ""。不要寫任何解釋文字。
            
            行程內容：
            {pure_text[:5000]}
            """
            
            res = model.generate_content(prompt)
            
            # C. 解析回傳內容
            match = re.search(r'\[\s*\{.*\}\s*\]', res.text, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                st.session_state.df = pd.DataFrame(data).reindex(columns=COLS).fillna("").astype(str)
                st.session_state.fn = up.name
                st.success("✅ 自動分類完成！")
            else:
                st.error("AI 辨識結果格式有誤，請再試一次。")
                
        except Exception as e:
            st.error(f"檔案讀取失敗：{e}")

# --- 3. 顯示與核對表格 ---
if 'df' in st.session_state:
    st.divider()
    st.subheader("📍 AI 分類核對表")
    # 讓線控可以直接修改 AI 抓錯的地方
    edited_df = st.data_editor(
        st.session_state.df, 
        use_container_width=True, 
        num_rows="dynamic",
        key="itinerary_editor"
    )
    
    # 顯示提取出的純文字 (偵錯用)
    with st.expander("🔍 查看 AI 讀到的純文字內容"):
        st.write(pure_text if 'pure_text' in locals() else "檔案已讀取")
