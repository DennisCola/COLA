import streamlit as st
import pandas as pd
import requests
from docx import Document
import json
import re

st.set_page_config(page_title="線控終極工作台", layout="wide")

if "GEMINI_API_KEY" not in st.secrets:
    st.error("請在 Secrets 設定 GEMINI_API_KEY"); st.stop()

API_KEY = st.secrets["GEMINI_API_KEY"]

# 定義三種可能的 API 端點路徑
ENDPOINTS = [
    f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={API_KEY}",
    f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={API_KEY}",
    f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={API_KEY}"
]

COLS = ["天數", "行程大點", "午餐", "晚餐", "有料門票", "旅館"]

st.title("🛡️ 線控行程「脫水」分類器 (多路徑連線版)")

up = st.file_uploader("1. 請上傳 Word 行程表 (.docx)", type=["docx"])

if up:
    if 'raw_df' not in st.session_state or st.session_state.get('last_fn') != up.name:
        try:
            with st.spinner("正在嘗試多種加密路徑連線 Google 伺服器..."):
                doc = Document(up)
                content = ["\n".join([p.text for p in doc.paragraphs if p.text.strip()])]
                for tbl in doc.tables:
                    for row in tbl.rows:
                        content.append(" | ".join(dict.fromkeys([c.text.strip() for c in row.cells if c.text.strip()])))
                
                full_text = "\n".join(content)
                prompt = f"你是一位線控。請將行程『脫水』，僅保留核心成本資訊。產出 JSON 列表，格式：{json.dumps(COLS, ensure_ascii=False)}。內容：{full_text[:5000]}"
                payload = {"contents": [{"parts": [{"text": prompt}]}]}
                
                success = False
                last_res = {}
                
                # 自動嘗試所有可能的路徑
                for url in ENDPOINTS:
                    response = requests.post(url, json=payload, headers={'Content-Type': 'application/json'})
                    if response.status_code == 200:
                        res_json = response.json()
                        res_text = res_json['candidates'][0]['content']['parts'][0]['text']
                        match = re.search(r'\[.*\]', res_text, re.DOTALL)
                        if match:
                            st.session_state.raw_df = pd.DataFrame(json.loads(match.group(0))).reindex(columns=COLS).fillna("").astype(str)
                            st.session_state.last_fn = up.name
                            success = True
                            st.success(f"✅ 連線成功！(透過路徑: {url.split('/')[3]})")
                            break
                    else:
                        last_res = response.json()
                
                if not success:
                    st.error("❌ 所有連線路徑皆失效。")
                    st.json(last_res)
                    st.info("💡 最後絕招：請確認你的 API Key 是否為『限制存取』狀態。")
                    
        except Exception as e:
            st.error(f"系統錯誤：{e}")

if 'raw_df' in st.session_state:
    st.subheader("📍 確認脫水表格")
    st.data_editor(st.session_state.raw_df, use_container_width=True, num_rows="dynamic", key="main_editor")
