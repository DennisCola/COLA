import streamlit as st
import pandas as pd
import google.generativeai as genai
from google.generativeai.types import RequestOptions
import json
import re

# --- 1. 頁面設定 ---
st.set_page_config(page_title="奧捷線控神器", layout="wide")

if "GEMINI_API_KEY" not in st.secrets:
    st.error("請在 Secrets 設定 API Key"); st.stop()

# --- 2. 強制指定 API 版本 (解決 404 核心) ---
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    # 這裡是最關鍵的修正：明確要求使用 v1 版本，並簡化模型名稱
    model = genai.GenerativeModel(
        model_name='gemini-1.5-flash',
        # 強制指定請求選項
    )
    # 建立一個測試用的選項，強制走 v1 穩定路徑
    safe_config = RequestOptions(api_version='v1')
except Exception as e:
    st.error(f"初始化失敗：{e}"); st.stop()

COLS = ["天數", "行程大點", "午餐", "晚餐", "有料門票", "旅館"]

st.title("🌍 奧捷行程 AI 歸類器 (穩定版)")
st.info("💡 請直接『複製 Word 文字』並『貼在下方』，這能避開所有檔案格式錯誤。")

# --- 3. 輸入區 ---
raw_text = st.text_area("👉 請貼上行程內容：", height=400)

if st.button("🚀 執行分類"):
    if not raw_text.strip():
        st.warning("請先貼上文字內容喔！")
    else:
        try:
            with st.spinner("AI 正在依照 6 個科目歸類..."):
                prompt = f"""
                你是一位專業線控。請將以下行程文字重新分類，產出 JSON 列表。
                欄位：{json.dumps(COLS, ensure_ascii=False)}。
                
                【規則】：
                - 僅回傳 JSON 格式，不要廢話。
                - 沒提到的資訊填入空字串 ""。
                
                文字內容：
                {raw_text[:4500]}
                """
                
                # 在調用時強制帶入 v1 版本設定
                response = model.generate_content(prompt, request_options=safe_config)
                
                # 解析 JSON
                match = re.search(r'\[.*\]', response.text, re.DOTALL)
                if match:
                    data = json.loads(match.group(0))
                    st.session_state.final_df = pd.DataFrame(data).reindex(columns=COLS).fillna("").astype(str)
                    st.success("✅ 成功！表格已長出來了。")
                else:
                    st.error("AI 辨識失敗，請確認貼上的文字是否完整。")
        except Exception as e:
            st.error(f"❌ 依然連線失敗：{e}")
            st.info("備註：這可能是 API 金鑰權限問題或 Google 伺服器地區限制。")

# --- 4. 顯示表格 ---
if 'final_df' in st.session_state:
    st.divider()
    st.subheader("📍 核心內容核對")
    st.data_editor(st.session_state.final_df, use_container_width=True, num_rows="dynamic")
