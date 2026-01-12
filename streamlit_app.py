import streamlit as st
import pandas as pd
import google.generativeai as genai
from docx import Document
import json
import re

# --- 1. 頁面外觀設定 ---
st.set_page_config(page_title="線控工作台-穩定版", layout="wide")

# --- 2. 解決 404 報錯的核心修正 ---
if "GEMINI_API_KEY" not in st.secrets:
    st.error("請在 Secrets 設定 GEMINI_API_KEY"); st.stop()

# 強制初始化設定
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# 這裡不直接用 GenerativeModel，我們加入路徑校正
def get_safe_response(prompt_text):
    # 嘗試不同的模型路徑名稱，避開 v1beta 陷阱
    # 1.5-flash 是目前最穩定的
    model = genai.GenerativeModel('models/gemini-1.5-flash')
    return model.generate_content(prompt_text)

COLS = ["天數", "行程大點", "午餐", "晚餐", "有料門票", "旅館"]

st.title("🛡️ 線控行程「脫水」分類器 (API 穩定版)")
st.write("---")

# 第一步：上傳與辨識
up = st.file_uploader("1. 請上傳 Word 行程表 (.docx)", type=["docx"])

if up:
    if 'raw_df' not in st.session_state or st.session_state.get('last_fn') != up.name:
        try:
            with st.spinner("正在連線至 Google V1 穩定伺服器..."):
                doc = Document(up)
                content = []
                for p in doc.paragraphs:
                    if p.text.strip(): content.append(p.text.strip())
                for tbl in doc.tables:
                    for row in tbl.rows:
                        row_data = [c.text.strip() for c in row.cells if c.text.strip()]
                        if row_data: content.append(" | ".join(dict.fromkeys(row_data)))
                
                full_text = "\n".join(content)
                
                prompt = f"""
                你是一位專業線控。請將行程『脫水』，僅保留核心成本資訊。
                產出純 JSON 列表，格式：{json.dumps(COLS, ensure_ascii=False)}。
                
                【脫水規則】：
                1. 『午/晚餐』：縮簡為餐食名稱（如：六菜一湯、米其林一星、自理）。
                2. 『有料門票』：僅列出需付費進入的景點。
                3. 『旅館』：僅保留飯店名稱或星等。
                
                內容：
                {full_text[:5000]}
                """
                
                # 調用修正後的連線函式
                res = get_safe_response(prompt)
                
                match = re.search(r'\[.*\]', res.text, re.DOTALL)
                if match:
                    data = json.loads(match.group(0))
                    st.session_state.raw_df = pd.DataFrame(data).reindex(columns=COLS).fillna("").astype(str)
                    st.session_state.last_fn = up.name
                else:
                    st.error("AI 回傳格式不符，請再試一次。")
        except Exception as e:
            # 如果還是報 404，這裡會抓到並顯示
            st.error(f"❌ 連線依然受阻：{e}")
            st.info("💡 建議：如果這版依然 404，請至 Google AI Studio 申請一個新 Key，並確認地區設為台灣。")

# 第二步：展示表格（脫水結果）
if 'raw_df' in st.session_state:
    st.subheader("📍 第二步：確認脫水表格")
    final_df = st.data_editor(st.session_state.raw_df, use_container_width=True, num_rows="dynamic", key="editor")
    
    st.write("---")
    st.subheader("💰 第三步：報價準備")
    st.write(f"當前表格共有 {len(final_df)} 天行程，準備連動成本資料庫...")
