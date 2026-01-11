import streamlit as st
import pandas as pd
import google.generativeai as genai
from docx import Document
import json
import re
from io import BytesIO

# --- 1. 頁面設定 ---
st.set_page_config(page_title="奧捷行程 AI 自動轉表", layout="wide")

if "GEMINI_API_KEY" not in st.secrets:
    st.error("請在 Secrets 設定 GEMINI_API_KEY"); st.stop()

# 修正模型初始化：直接使用字串名稱，不加 models/ 前綴
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash')

# 核心 6 欄位
COLS = ["天數", "行程大點", "午餐", "晚餐", "有料門票", "旅館"]

st.title("🌍 奧捷行程 AI 自動轉表 (強力提取版)")
st.info("💡 運作模式：上傳 Word 後，AI 會自動提取純文字並歸類為 6 個核心欄位。")

# --- 2. 檔案上傳與處理 ---
up = st.file_uploader("1. 上傳行程 Word (.docx)", type=["docx"])

if up:
    # 當檔案更換時，觸發重新辨識
    if 'fn' not in st.session_state or st.session_state.fn != up.name:
        try:
            # A. 讀取 Word 並轉換為純文字
            doc = Document(up)
            text_list = []
            
            # 讀取所有段落文字
            for p in doc.paragraphs:
                if p.text.strip():
                    text_list.append(p.text.strip())
            
            # 讀取所有表格文字 (旅行社行程通常在表格裡)
            for tbl in doc.tables:
                for row in tbl.rows:
                    cells = [c.text.strip() for c in row.cells if c.text.strip()]
                    if cells:
                        # 使用 dict.fromkeys 移除合併儲存格產生的重複文字
                        text_list.append(" | ".join(dict.fromkeys(cells)))
            
            pure_text = "\n".join(text_list)
            st.session_state.current_text = pure_text
            
            st.info("🔄 正在透過 Gemini-1.5-Flash 進行 6 欄位分類...")

            # B. 餵給 AI 進行純文字分類
            prompt = f"""
            你是一位專業線控。請根據以下行程文字，將內容精準分類為 JSON 列表格式。
            欄位必須為：{','.join(COLS)}。
            
            【指令】：
            - 『天數』：標註 1, 2, 3...。
            - 『行程大點』：造訪的主要城市或地區。
            - 『午餐/晚餐』：具體餐飲內容。
            - 『有料門票』：提及『含門票』、『入內』的景點。
            - 『旅館』：飯店名稱與星等。
            - 找不到資訊請填空字串 ""。
            - 不要包含 Markdown 標籤，只要純 JSON 列表。
            
            內容：
            {pure_text[:5000]}
            """
            
            res = model.generate_content(prompt)
            
            # C. 解析回傳內容 (使用更強大的正則表達式)
            js_match = re.search(r'\[.*\]', res.text, re.DOTALL)
            if js_match:
                data = json.loads(js_match.group(0))
                st.session_state.df = pd.DataFrame(data).reindex(columns=COLS).fillna("").astype(str)
                st.session_state.fn = up.name
                st.success("✅ 自動分類完成！")
            else:
                st.error("AI 辨識結果無法解析為 JSON，請重試。")
                
        except Exception as e:
            st.error(f"檔案讀取或辨識失敗：{str(e)}")

# --- 3. 顯示與核對表格 ---
if 'df' in st.session_state:
    st.divider()
    st.subheader("📍 AI 分類核對表")
    
    # 讓線控可以直接修改
    edited_df = st.data_editor(
        st.session_state.df, 
        use_container_width=True, 
        num_rows="dynamic",
        key="itinerary_editor"
    )
    
    # 偵錯工具
    with st.expander("🔍 檢視 Word 提取出的純文字"):
        if 'current_text' in st.session_state:
            st.text_area("純文字內容：", st.session_state.current_text, height=300)
