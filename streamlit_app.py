import streamlit as st
import pandas as pd
import google.generativeai as genai
import json
import re

# --- 1. 頁面設定 ---
st.set_page_config(page_title="奧捷行程 AI 分類", layout="wide")

if "GEMINI_API_KEY" not in st.secrets:
    st.error("請先在 Secrets 設定 GEMINI_API_KEY"); st.stop()

# --- 2. 最簡化模型初始化 ---
# 這裡我們完全移除 api_version 參數，改用最通用的寫法
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash')

COLS = ["天數", "行程大點", "午餐", "晚餐", "有料門票", "旅館"]

st.title("🌍 奧捷行程 AI 分類器 (極簡版)")
st.info("💡 請全選 Word 內容並貼在下方文字框中。")

# --- 3. 輸入區 ---
raw_text = st.text_area("👉 請貼上行程內容：", height=400)

if st.button("🚀 執行分類"):
    if not raw_text.strip():
        st.warning("請先貼上文字內容喔！")
    else:
        try:
            with st.spinner("AI 正在辨識分類中..."):
                # 簡化 Prompt，讓 AI 更容易理解
                prompt = f"""
                將以下行程文字轉為 JSON 列表。
                欄位：{','.join(COLS)}。
                
                規範：
                - 只回傳 JSON。
                - 沒提到的欄位填 ""。
                
                文字內容：
                {raw_text[:4000]}
                """
                
                # 最純粹的呼叫，不帶任何 options
                response = model.generate_content(prompt)
                
                # 提取 JSON
                match = re.search(r'\[.*\]', response.text, re.DOTALL)
                if match:
                    data = json.loads(match.group(0))
                    st.session_state.final_df = pd.DataFrame(data).reindex(columns=COLS).fillna("").astype(str)
                    st.success("✅ 表格已生成！")
                else:
                    st.error("AI 辨識格式有誤。")
                    
        except Exception as e:
            # 這裡顯示最原始的錯誤，幫我看看它又說了什麼
            st.error(f"❌ 發生錯誤：{e}")

# --- 4. 顯示結果 ---
if 'final_df' in st.session_state:
    st.divider()
    st.data_editor(st.session_state.final_df, use_container_width=True, num_rows="dynamic")
