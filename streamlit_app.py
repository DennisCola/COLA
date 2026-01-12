import streamlit as st
import pandas as pd
import requests
from docx import Document
import json
import re

st.set_page_config(page_title="線控工作台-終極連線版", layout="wide")

if "GEMINI_API_KEY" not in st.secrets:
    st.error("請在 Secrets 設定 GEMINI_API_KEY"); st.stop()

API_KEY = st.secrets["GEMINI_API_KEY"]
# 直接寫死 V1 穩定版的網址，不讓套件亂跳 v1beta
API_URL = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={API_KEY}"

COLS = ["天數", "行程大點", "午餐", "晚餐", "有料門票", "旅館"]

st.title("🛡️ 線控行程「脫水」分類器 (手動連線版)")
st.write("---")

up = st.file_uploader("1. 請上傳 Word 行程表 (.docx)", type=["docx"])

if up:
    if 'raw_df' not in st.session_state or st.session_state.get('last_fn') != up.name:
        try:
            with st.spinner("正在直接連線 Google 核心伺服器..."):
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
                
                # 手動建立請求，完全不使用 genai 套件
                payload = {
                    "contents": [{
                        "parts": [{"text": prompt}]
                    }]
                }
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
                    else:
                        st.error("辨識格式錯誤，請再試一次。")
                else:
                    st.error(f"連線失敗！錯誤碼：{response.status_code}，訊息：{res_json.get('error', {}).get('message')}")
        except Exception as e:
            st.error(f"系統錯誤：{e}")

if 'raw_df' in st.session_state:
    st.subheader("📍 確認脫水表格")
    st.data_editor(st.session_state.raw_df, use_container_width=True, num_rows="dynamic")
