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

# 這次我們把所有可能的「模型名稱」與「版本」排列組合
MODELS = [
    "gemini-1.5-flash", 
    "gemini-1.5-flash-latest",
    "gemini-1.0-pro",
    "gemini-pro"
]
VERSIONS = ["v1", "v1beta"]

COLS = ["天數", "行程大點", "午餐", "晚餐", "有料門票", "旅館"]

st.title("🛡️ 線控行程分類器 (終極連線測試)")

up = st.file_uploader("1. 上傳 Word 行程表 (.docx)", type=["docx"])

if up:
    try:
        with st.spinner("正在逐一測試您的 API Key 支援哪種模型..."):
            doc = Document(up)
            content = ["\n".join([p.text for p in doc.paragraphs if p.text.strip()])]
            full_text = "\n".join(content)
            
            prompt = f"將行程『脫水』，產出 JSON 列表。格式：{json.dumps(COLS, ensure_ascii=False)}。內容：{full_text[:3000]}"
            payload = {"contents": [{"parts": [{"text": prompt}]}]}
            
            success = False
            last_error = ""

            # 開始地毯式搜索
            for ver in VERSIONS:
                for mdl in MODELS:
                    url = f"https://generativelanguage.googleapis.com/{ver}/models/{mdl}:generateContent?key={API_KEY}"
                    try:
                        res = requests.post(url, json=payload, headers={'Content-Type': 'application/json'}, timeout=5)
                        if res.status_code == 200:
                            data = res.json()
                            txt = data['candidates'][0]['content']['parts'][0]['text']
                            match = re.search(r'\[.*\]', txt, re.DOTALL)
                            if match:
                                st.session_state.raw_df = pd.DataFrame(json.loads(match.group(0))).reindex(columns=COLS).fillna("").astype(str)
                                success = True
                                st.success(f"🎉 連線成功！您的 Key 支援路徑: {ver}/models/{mdl}")
                                break
                        else:
                            last_error = f"{ver}/{mdl} -> {res.status_code}: {res.text}"
                    except:
                        continue
                if success: break
            
            if not success:
                st.error("❌ 所有已知模型路徑皆宣告失敗。")
                st.write("最後一個錯誤訊息：")
                st.code(last_error)
                
    except Exception as e:
        st.error(f"系統錯誤：{e}")

if 'raw_df' in st.session_state:
    st.subheader("📍 脫水結果表格")
    st.data_editor(st.session_state.raw_df, use_container_width=True, num_rows="dynamic")
