import streamlit as st
import pd
import requests
from docx import Document
import json
import re

st.set_page_config(page_title="線控終極工具台", layout="wide")

if "GEMINI_API_KEY" not in st.secrets:
    st.error("請在 Secrets 設定 GEMINI_API_KEY"); st.stop()

API_KEY = st.secrets["GEMINI_API_KEY"]
# 修正處：改用 gemini-1.5-flash-latest，這是目前 API 最通用的名稱
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={API_KEY}"

COLS = ["天數", "行程大點", "午餐", "晚餐", "有料門票", "旅館"]

st.title("🛡️ 線控行程「脫水」分類器 (連線校正版)")

up = st.file_uploader("1. 請上傳 Word 行程表 (.docx)", type=["docx"])

if up:
    if 'raw_df' not in st.session_state or st.session_state.get('last_fn') != up.name:
        try:
            with st.spinner("正在重新對準 Google 伺服器頻率..."):
                doc = Document(up)
                content = []
                for p in doc.paragraphs:
                    if p.text.strip(): content.append(p.text.strip())
                for tbl in doc.tables:
                    for row in tbl.rows:
                        row_data = [c.text.strip() for c in row.cells if c.text.strip()]
                        if row_data: content.append(" | ".join(dict.fromkeys(row_data)))
                
                full_text = "\n".join(content)
                prompt = f"你是一位線控。請將行程『脫水』，僅保留核心成本資訊。產出 JSON 列表，格式：{json.dumps(COLS, ensure_ascii=False)}。內容：{full_text[:5000]}"
                
                payload = {"contents": [{"parts": [{"text": prompt}]}]}
                headers = {'Content-Type': 'application/json'}
                
                response = requests.post(API_URL, json=payload, headers=headers)
                res_json = response.json()
                
                if response.status_code == 200:
                    res_text = res_json['candidates'][0]['content']['parts'][0]['text']
                    match = re.search(r'\[.*\]', res_text, re.DOTALL)
                    if match:
                        data = json.loads(match.group(0))
                        st.session_state.raw_df = pd.DataFrame(data).reindex(columns=COLS).fillna("").astype(str)
                        st.session_state.last_fn = up.name
                        st.success("✅ 終於成功連線了！")
                    else:
                        st.error("辨識內容有誤。")
                else:
                    # 如果失敗，顯示完整的錯誤，幫助我們判斷是否該換 gemini-1.0-pro
                    st.error(f"連線代碼：{response.status_code}")
                    st.json(res_json) 
        except Exception as e:
            st.error(f"系統錯誤：{e}")

if 'raw_df' in st.session_state:
    st.subheader("📍 確認脫水表格")
    st.data_editor(st.session_state.raw_df, use_container_width=True, num_rows="dynamic")
