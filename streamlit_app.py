import streamlit as st
import pandas as pd
import requests
from docx import Document
import json
import re

st.set_page_config(page_title="線控終極工作台", layout="wide")

# 檢查 API Key
if "GEMINI_API_KEY" not in st.secrets:
    st.error("請在 Secrets 設定 GEMINI_API_KEY"); st.stop()

API_KEY = st.secrets["GEMINI_API_KEY"]
# 使用最保險的最新版模型網址
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={API_KEY}"

COLS = ["天數", "行程大點", "午餐", "晚餐", "有料門票", "旅館"]

st.title("🛡️ 線控行程「脫水」分類器")
st.write("---")

up = st.file_uploader("1. 請上傳 Word 行程表 (.docx)", type=["docx"])

if up:
    if 'raw_df' not in st.session_state or st.session_state.get('last_fn') != up.name:
        try:
            with st.spinner("正在讀取並過濾行程精華..."):
                # 讀取 Word
                doc = Document(up)
                content = []
                for p in doc.paragraphs:
                    if p.text.strip(): content.append(p.text.strip())
                for tbl in doc.tables:
                    for row in tbl.rows:
                        row_data = [c.text.strip() for c in row.cells if c.text.strip()]
                        if row_data: content.append(" | ".join(dict.fromkeys(row_data)))
                
                full_text = "\n".join(content)
                
                # 脫水指令
                prompt = f"""你是一位專業線控。請將行程『脫水』，僅保留核心成本資訊。
                請輸出 JSON 列表，欄位：{json.dumps(COLS, ensure_ascii=False)}。
                
                【脫水規則】：
                1. 『午/晚餐』：縮簡為餐食名稱（如：六菜一湯、米其林一星、自理）。
                2. 『有料門票』：僅列出需付費進入的景點。
                3. 『旅館』：僅保留飯店名稱或星等。
                
                內容：
                {full_text[:5000]}"""
                
                payload = {"contents": [{"parts": [{"text": prompt}]}]}
                headers = {'Content-Type': 'application/json'}
                
                response = requests.post(API_URL, json=payload, headers=headers)
                res_json = response.json()
                
                if response.status_code == 200:
                    res_text = res_json['candidates'][0]['content']['parts'][0]['text']
                    # 尋找 JSON 區塊
                    match = re.search(r'\[.*\]', res_text, re.DOTALL)
                    if match:
                        data = json.loads(match.group(0))
                        st.session_state.raw_df = pd.DataFrame(data).reindex(columns=COLS).fillna("").astype(str)
                        st.session_state.last_fn = up.name
                        st.success("✅ 辨識成功！")
                    else:
                        st.error("AI 回傳格式不正確，請確認內容。")
                else:
                    st.error(f"連線失敗 (代碼 {response.status_code})")
                    st.json(res_json)
        except Exception as e:
            st.error(f"系統錯誤：{e}")

# 展示與編輯
if 'raw_df' in st.session_state:
    st.subheader("📍 確認脫水表格")
    st.info("您可以直接在表格中修改內容。")
    st.data_editor(st.session_state.raw_df, use_container_width=True, num_rows="dynamic", key="main_editor")
