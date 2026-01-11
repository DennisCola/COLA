import streamlit as st
import pandas as pd
import google.generativeai as genai
import json
import re

# --- 1. 頁面基礎設定 ---
st.set_page_config(page_title="奧捷行程 AI 提取器", layout="wide")

if "GEMINI_API_KEY" not in st.secrets:
    st.error("請在 Secrets 設定 API Key"); st.stop()

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash')

# 核心 6 欄位
COLS = ["天數", "行程大點", "午餐", "晚餐", "有料門票", "旅館"]

st.title("🌍 奧捷行程 AI 提取器 (文字貼上版)")
st.info("💡 操作說明：請全選 Word 內容 (Ctrl+A)，複製 (Ctrl+C)，然後貼在下方框格內。")

# --- 2. 文字輸入區 ---
# 使用 st.text_area 接收純文字輸入
raw_input = st.text_area("👉 請在此貼上行程內容：", height=450, placeholder="貼上後點擊下方按鈕...")

if st.button("🚀 開始辨識並分類"):
    if not raw_input.strip():
        st.warning("請輸入內容後再辨識！")
    else:
        try:
            st.info("🔄 AI 正在分析文字結構，請稍候...")

            # 強化指令：要求精準分類
            prompt = f"""
            你是一位專業的旅遊線控。請將以下行程文字重新分類，並轉換為 JSON 列表格式。
            欄位名稱必須精確為：{','.join(COLS)}。
            
            【分類準則】：
            1. 『天數』：標註 Day 1, Day 2 等。
            2. 『行程大點』：抓出該日的主要造訪城市。
            3. 『午餐/晚餐』：抓出餐食名稱，若為自理請註明。
            4. 『有料門票』：抓出行程中明確提到入內、包含門票的項目。
            5. 『旅館』：抓出飯店名稱與星等。
            6. 若文中未提到該科目，請直接填入 "" (空字串)。
            
            文字內容：
            {raw_input[:5000]}
            """
            
            # 調用 AI
            response = model.generate_content(prompt)
            
            # 使用正則表達式提取 JSON 區塊
            match = re.search(r'\[\s*\{.*\}\s*\]', response.text, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                # 建立 DataFrame 並存入 session_state
                st.session_state.itinerary_df = pd.DataFrame(data).reindex(columns=COLS).fillna("").astype(str)
                st.success("✅ 分類完成！")
            else:
                st.error("AI 無法理解此段內容的結構，請嘗試分段貼上或檢查內容。")
                
        except Exception as e:
            st.error(f"辨識發生錯誤：{e}")

# --- 3. 顯示分類結果表格 ---
if 'itinerary_df' in st.session_state:
    st.divider()
    st.subheader("📍 AI 分類結果核對表")
    st.caption("您可以直接在表格中點擊修改。確認無誤後，這就是您的成本基礎。")
    
    # 讓使用者可以編輯辨識出的結果
    edited_df = st.data_editor(
        st.session_state.itinerary_df, 
        use_container_width=True, 
        num_rows="dynamic",
        key="main_table_editor"
    )
    
    # 未來可以在這裡加入「計算總價」的按鈕
