import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="線控核價引擎 0112C", layout="wide")

# --- 0. 資料庫連動 ---
BASE_URL = "https://docs.google.com/spreadsheets/d/1y53LHsJkDx2xA1MsLzkdd5FYQYWcfQrhs2KeSbsKbZk/gviz/tq?tqx=out:csv"
GID_TICKET = "242124917"
GID_MENU = "474017029"

@st.cache_data(ttl=300)
def fetch_db():
    db = {}
    try:
        df_m = pd.read_csv(f"{BASE_URL}&gid={GID_MENU}")
        for _, r in df_m.dropna(subset=['項目名稱', '單價']).iterrows():
            db[str(r['項目名稱']).strip()] = float(r['單價'])
        df_t = pd.read_csv(f"{BASE_URL}&gid={GID_TICKET}")
        for _, r in df_t.dropna(subset=['項目名稱', '單價']).iterrows():
            nm = str(r['項目名稱']).strip()
            kw = str(r['判斷文字']).strip() if '判斷文字' in df_t.columns and pd.notna(r['判斷文字']) else nm
            db[kw] = float(r['單價'])
    except: pass
    return db

# --- HTML 表格生成器 (Step 4: 合併與置中) ---
def generate_merged_html(df):
    if df is None or df.empty: return ""
    
    # 1. 重建完整資料結構以利計算 rowspan
    full_data = []
    last_day = ""
    # 暫存變數，用於填補空白的副行資訊
    last_point = ""
    last_lunch = ""
    last_l_price = None
    last_dinner = ""
    last_d_price = None
    last_hotel = ""
    last_h_price = None

    for _, row in df.iterrows():
        # 判斷是否為主行 (天數有值)
        current_day = str(row['天數']).strip() if pd.notna(row['天數']) else ""
        
        if current_day != "":
            # 是主行，更新暫存資訊
            last_day = current_day
            last_point = row['行程大點']
            last_lunch = row['午餐']
            last_l_price = row['午價']
            last_dinner = row['晚餐']
            last_d_price = row['晚價']
            last_hotel = row['旅館']
            last_h_price = row['旅價']
            
            full_data.append
