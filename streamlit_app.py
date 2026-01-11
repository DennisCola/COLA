import streamlit as st
import pandas as pd
import google.generativeai as genai
import json
import re

st.set_page_config(page_title="線控專用-最強辨識器", layout="wide")

# 1. 直接了當的 API 設定
if "GEMINI_API_KEY" not in st.secrets:
    st.error("請在 Secrets 設定 API Key"); st.stop()

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# 使用最保險的模型名稱
model = genai.GenerativeModel('gemini-1.5-flash')

COLS = ["天數", "行程大點", "午餐", "晚餐", "有料門票", "旅館"]

st.title("🌍 奧捷行程 AI 分類器 (保證成功版)")
st.write("這一次，我們不玩檔案上傳了，直接把文字餵給 AI 吃！")

# 2. 文字輸入區
raw_text = st.text_area("👉 請打開 Word，按 Ctrl+A 全選，然後貼在這裡：", height=400)

if st.button("🚀 執行分類"):
    if not raw_text:
        st.warning("你還沒貼上內容喔！")
    else:
        try:
            with st.spinner("AI 正在幫你歸類 6 個科目..."):
                prompt = f"""
                你是一位專業線控助理。請將以下行程文字重新分類，產出純 JSON 列表。
                欄位：{json.dumps(COLS, ensure_ascii=False)}。
                
                【提取指南】：
                - 天數：1, 2, 3...
                - 行程大點：該日城市。
                - 午餐/晚餐：具體餐食。
                - 有料門票：含門票/入內景點。
                - 旅館：飯店名稱。
                - 沒提到的通通留空字串 ""。
                
                內容：
                {raw_text[:5000]}
                """
                
                response = model.generate_content(prompt)
                
                # 強力解析 JSON 區塊
                match = re.search(r'\[.*\]', response.text, re.DOTALL)
                if match:
                    data = json.loads(match.group(0))
                    st.session_state.final_df = pd.DataFrame(data).reindex(columns=COLS).fillna("").astype(str)
                    st.success("✅ 分類成功！")
                else:
                    st.error("AI 辨識不出格式，請確認貼上的文字是否正確。")
        except Exception as e:
            st.error(f"連線失敗，請檢查 API Key 或網路：{e}")

# 3. 顯示表格
if 'final_df' in st.session_state:
    st.divider()
    st.subheader("📍 核對你的 6 欄位表格")
    st.data_editor(st.session_state.final_df, use_container_width=True, num_rows="dynamic")
