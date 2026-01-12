import streamlit as st
import pandas as pd

st.set_page_config(page_title="線控報價儀表板", layout="wide")

st.title("📊 線控報價與監控儀表板")
st.write("---")

# 這裡讓使用者輸入 Google Sheet 的公開連結
sheet_url = st.text_input("請貼上您的 Google Sheet 共用連結 (需開啟知道連結的人可檢視)：")

if sheet_url:
    try:
        # 將連結轉為 csv 下載路徑
        csv_url = sheet_url.replace('/edit?usp=sharing', '/export?format=csv').replace('/edit#gid=', '/export?format=csv&gid=')
        df = pd.read_csv(csv_url)
        
        st.subheader("📍 行程脫水資料 (從 Google Sheet 同步)")
        # 顯示你從 AI Studio 貼過去的資料
        edited_df = st.data_editor(df, use_container_width=True, num_rows="dynamic")
        
        st.write("---")
        st.subheader("💰 報價試算區")
        col1, col2 = st.columns(2)
        with col1:
            exchange_rate = st.number_input("今日歐元匯率", value=35.5)
        with col2:
            profit = st.number_input("預期利潤 (%)", value=15)
            
        st.info("💡 系統已自動對應 Google Sheet 中的各項成本...")
        # 這裡之後可以寫計算公式
        
    except Exception as e:
        st.error(f"讀取試算表失敗，請確認連結權限：{e}")
else:
    st.info("👋 請將 AI Studio 產出的表格貼到 Google Sheet 後，把連結貼到上方。")
