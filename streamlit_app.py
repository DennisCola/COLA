import streamlit as st
import pandas as pd
import requests
from io import BytesIO
from docx import Document
import google.generativeai as genai
import json
import re

st.set_page_config(page_title="線控專用-精準提取版", layout="wide")

if "GEMINI_API_KEY" not in st.secrets:
    st.error("請設定 API Key"); st.stop()

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash')

COLS = ["天數", "行程大點", "午餐", "晚餐", "有料門票", "旅館"]

st.title("🛡️ 結構化行程提取 (穩定版)")
st.caption("改用表格掃描與範例引導，大幅提升提取精準度。")

up = st.file_uploader("1. 上傳 .docx 檔案", type=["docx"])

if up:
    if 'df' not in st.session_state or st.session_state.get('fn') != up.name:
        try:
            doc = Document(up)
            extracted_data = []
            
            # 第一階段：優先掃描 Word 內的表格內容（最精準）
            for tbl in doc.tables:
                for row in tbl.rows:
                    row_txt = [c.text.strip() for c in row.cells if c.text.strip()]
                    if row_txt:
                        extracted_data.append(" | ".join(dict.fromkeys(row_txt)))
            
            # 第二階段：補足段落內容
            for p in doc.paragraphs:
                if p.text.strip(): extracted_data.append(p.text.strip())
            
            raw_text = "\n".join(extracted_data)
            st.session_state.raw_debug = raw_text 

            # 強力引導 Prompt
            prompt = f"""
            你是一位專業線控。請將行程文字轉換為 JSON。
            範例輸入：『Day 3 薩爾斯堡。午餐：鱒魚餐、晚餐：六菜一湯。入內美泉宮。住：HILTON』
            範例輸出：[{{"天數":"3","行程大點":"薩爾斯堡","午餐":"鱒魚餐","晚餐":"六菜一湯","有料門票":"美泉宮","旅館":"HILTON"}}]
            
            目標格式：{json.dumps(COLS, ensure_ascii=False)}
            
            行程內容：
            {raw_text[:4500]}
            """
            
            res = model.generate_content(prompt)
            # 濾除 AI 廢話，只抓 JSON 括號內容
            match = re.search(r'\[.*\]', res.text, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                st.session_state.df = pd.DataFrame(data).reindex(columns=COLS).fillna("").astype(str)
                st.session_state.fn = up.name
            else:
                st.error("AI 無法解析結構，請確認 Word 是否有文字內容。")

        except Exception as e:
            st.error(f"提取失敗: {e}")

    if 'df' in st.session_state:
        st.subheader("📍 提取結果核對")
        st.data_editor(st.session_state.df, use_container_width=True, num_rows="dynamic", key=f"ed_{up.name}")

    with st.expander("🔍 查看底層提取文字 (如果沒抓到，請確認此處是否有字)"):
        if 'raw_debug' in st.session_state:
            st.text_area("提取文本：", st.session_state.raw_debug, height=300)
