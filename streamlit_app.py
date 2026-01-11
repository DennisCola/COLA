import streamlit as st
import pandas as pd
import google.generativeai as genai
from docx import Document
import json
import re
from io import BytesIO

# --- 1. 頁面設定 ---
st.set_page_config(page_title="奧捷行程 AI 自動轉表", layout="wide")

# 安全檢查 API Key
if "GEMINI_API_KEY" not in st.secrets:
    st.error("請在 Secrets 設定 GEMINI_API_KEY"); st.stop()

# --- 2. 修正模型調用 ---
# 針對 404 錯誤：我們改用最保險的初始化方式
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    # 這裡直接使用模型名稱，不加任何前綴
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    st.error(f"模型初始化失敗: {e}"); st.stop()

# 核心 6 欄位
COLS = ["天數", "行程大點", "午餐", "晚餐", "有料門票", "旅館"]

st.title("🌍 奧捷行程 AI 自動轉表")
st.info("💡 運作模式：上傳 Word ⮕ 轉換純文字 ⮕ AI 重新分類 ⮕ 產出 6 欄表")

# --- 3. 檔案上傳與處理 ---
up = st.file_uploader("1. 上傳行程 Word (.docx)", type=["docx"])

if up:
    # 檔案切換檢查
    if 'fn' not in st.session_state or st.session_state.fn != up.name:
        try:
            # A. 提取純文字 (模擬複製貼上的動作)
            doc = Document(up)
            text_chunks = []
            
            # 抓取所有段落
            for p in doc.paragraphs:
                if p.text.strip():
                    text_chunks.append(p.text.strip())
            
            # 抓取所有表格文字 (旅行社行程的核心)
            for tbl in doc.tables:
                for row in tbl.rows:
                    row_data = [c.text.strip() for c in row.cells if c.text.strip()]
                    if row_data:
                        # 移除合併儲存格產生的重複字
                        text_chunks.append(" | ".join(dict.fromkeys(row_data)))
            
            full_pure_text = "\n".join(text_chunks)
            st.session_state.current_raw = full_pure_text
            
            st.info("🔄 文字提取成功！AI 正在依照 6 欄位重新分類...")

            # B. 餵給 AI (加上 Few-shot 範例引導提高準確度)
            prompt = f"""
            你是一位專業旅行社線控助理。請將以下行程純文字重新分類，並轉換為 JSON 列表格式。
            欄位名稱必須精確為：{','.join(COLS)}。
            
            【分類準則】：
            - 『天數』：標註 Day 1, Day 2... 
            - 『行程大點』：該日造訪城市。
            - 『午餐/晚餐』：抓出餐點內容 (如：鱒魚餐、自理、中式)。
            - 『有料門票』：抓出提到入內參觀、包含門票的景點。
            - 『旅館』：飯店名稱。
            - 若無資訊請填空字串 ""。
            
            行程內容：
            {full_pure_text[:5000]}
            """
            
            # C. 執行辨識
            res = model.generate_content(prompt)
            
            # D. 強力解析 JSON (防止 AI 回傳多餘文字)
            js_match = re.search(r'\[.*\]', res.text, re.DOTALL)
            if js_match:
                data = json.loads(js_match.group(0))
                # 建立並標準化 DataFrame
                st.session_state.df = pd.DataFrame(data).reindex(columns=COLS).fillna("").astype(str)
                st.session_state.fn = up.name
                st.success("✅ 自動分類完成！")
            else:
                st.error("AI 辨識失敗：回傳格式不正確")
                
        except Exception as e:
            st.error(f"檔案讀取失敗：{str(e)}")

# --- 4. 顯示與核對表格 ---
if 'df' in st.session_state:
    st.divider()
    st.subheader("📍 AI 分類核對表")
    
    # 讓線控手動覆核修改
    edited_df = st.data_editor(
        st.session_state.df, 
        use_container_width=True, 
        num_rows="dynamic",
        key="itinerary_table"
    )
    
    # 偵錯與原始文字檢視
    with st.expander("🔍 檢視 Word 提取出的純文字 (確認是否有遺漏資訊)"):
        if 'current_raw' in st.session_state:
            st.text_area("提取內容：", st.session_state.current_raw, height=300)
