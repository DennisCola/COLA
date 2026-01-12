import streamlit as st
import pandas as pd
import requests
import json
import re

st.set_page_config(page_title="線控快轉中心", layout="wide")

# 這裡依然使用你新申請的 Key
API_KEY = st.secrets["GEMINI_API_KEY"]
# 直接指定最穩定的 v1 穩定版路徑
API_URL = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={API_KEY}"

COLS = ["天數", "行程大點", "午餐", "晚餐", "有料門票", "旅館"]

st.title("⚡ 線控行程快轉中心")
st.caption("流程：Word 全選複製 ⮕ 貼上 ⮕ 直接報價")

# 1. 貼上區
raw_text = st.text_area("1. 請在此貼上 Word 行程內容：", height=200, placeholder="直接 Ctrl+V 貼上即可...")

if raw_text:
    if st.button("🪄 開始脫水轉表"):
        try:
            with st.spinner("AI 正在處理中..."):
                prompt = f"你是一位線控。請將以下行程『脫水』為 JSON 列表，欄位：{json.dumps(COLS, ensure_ascii=False)}。不要廢話，只給 JSON。內容：{raw_text[:5000]}"
                payload = {"contents": [{"parts": [{"text": prompt}]}]}
                
                response = requests.post(API_URL, json=payload, headers={'Content-Type': 'application/json'})
                
                if response.status_code == 200:
                    res_text = response.json()['candidates'][0]['content']['parts'][0]['text']
                    match = re.search(r'\[.*\]', res_text, re.DOTALL)
                    if match:
                        st.session_state.itinerary_df = pd.DataFrame(json.loads(match.group(0)))
                        st.success("✅ 轉換完成！")
                    else:
                        st.error("AI 回傳格式不符")
                else:
                    st.error(f"連線失敗，請檢查 API Key 權限。")
        except Exception as e:
            st.error(f"系統錯誤：{e}")

# 2. 表格編輯與報價 (合併在一起)
if 'itinerary_df' in st.session_state:
    st.divider()
    st.subheader("📍 2. 核對表格與即時報價")
    
    # 讓你可以直接在網頁改
    df = st.data_editor(st.session_state.itinerary_df, use_container_width=True, num_rows="dynamic")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        ex_rate = st.number_input("歐元匯率", value=35.5)
    with col2:
        airfare = st.number_input("機票成本", value=45000)
    with col3:
        margin = st.slider("預期毛利 %", 5, 30, 15)

    # 簡易試算邏輯
    land_cost = len(df) * 150 # 假設每天地接成本 150 歐
    total_cost = (land_cost * ex_rate) + airfare
    price = total_cost / (1 - (margin/100))
    
    st.metric("建議售價 (TWD)", f"{int(price):,}")
