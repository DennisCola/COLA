import streamlit as st
import pandas as pd
import requests
from io import BytesIO
from docx import Document
import google.generativeai as genai
import json

# --- 1. 頁面設定 ---
st.set_page_config(page_title="線控 Word 轉表核心", layout="wide")

if "GEMINI_API_KEY" not in st.secrets:
    st.error("請在 Secrets 設定 API Key"); st.stop()

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash')

# 您指定的 8 個核心科目
COLS = ["天數", "日期", "星期", "行程大點", "午餐", "晚餐", "有料門票", "旅館"]

st.title("📄 行程骨架提取 (8 欄位純淨版)")
st.caption("專注於 Word 文字提取：自動無視圖片，未辨識內容一律留白。")

# --- 2. Word 處理邏輯 ---
up = st.file_uploader("上傳行程 Word (.docx)", type=["docx"])

if up:
    # 檔案更換檢查
    if 'fn' not in st.session_state or st.session_state.fn != up.name:
        st.session_state.fn = up.name
        if 'df' in st.session_state: del st.session_state.df

    if 'df' not in st.session_state:
        try:
            doc = Document(up)
            # 只抓文字段落與表格內的文字
            txts = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
            for tbl in doc.tables:
                for row in tbl.rows:
                    for cell in row.cells:
                        if cell.text.strip(): txts.append(cell.text.strip())
            
            st.info("🔄 AI 正在分析行程內容...")
            
            # 指令 AI 嚴格遵守 8 欄格式
            pm = f"""你是一名專業線控助理。請讀行程並轉換為 JSON 列表。
            欄位必須精確包含：{','.join(COLS)}。
            【規則】：
            1. 若找不到資訊、讀不懂或無資料，請直接填空字串 ""。
            2. 不要包含圖片描述，不要寫任何解釋文字。
            3. 天數請填純數字。
            內容：{(' '.join(txts))[:3500]}"""
            
            res = model.generate_content(pm)
            js_txt = res.text.replace('```json', '').replace('```', '').strip()
            data = json.loads(js_txt)
            
            # 強制轉換為 DataFrame 並確保型別為字串以防崩潰
            df_final = pd.DataFrame(data).reindex(columns=COLS).fillna("").astype(str)
            st.session_state.df = df_final
            
        except Exception as e:
            st.warning("⚠️ 辨識失敗，可能是檔案太複雜。已為您準備空白表。")
            st.session_state.df = pd.DataFrame([["" for _ in COLS]], columns=COLS)

    # --- 3. 穩定產出核對表 ---
    if 'df' in st.session_state:
        st.subheader("📍 線控核對表")
        st.write("請核對以下資訊，您可以直接點擊格子補齊留白的部分：")
        
        st.data_editor(
            st.session_state.df,
            use_container_width=True,
            num_rows="dynamic",
            key=f"editor_{st.session_state.fn}"
        )
        
        st.success("✅ 骨架提取完成。")
