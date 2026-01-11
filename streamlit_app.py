import streamlit as st
import google.generativeai as genai
from docx import Document
import pandas as pd

# --- 1. 系統設定 ---
st.set_page_config(page_title="AI 線控報價系統", layout="wide")
st.title("🌍 2026 常旅客版 - 智慧線控報價系統")

# 側邊欄：設定變動參數 (機票、匯率、利潤)
with st.sidebar:
    st.header("⚙️ 核心成本參數")
    exchange_rate = st.number_input("歐元匯率", value=37.0, step=0.1)
    airfare_base = st.number_input("機票票價 (TWD)", value=30000)
    airfare_tax = st.number_input("機票稅金 (TWD)", value=7000)
    profit_target = st.number_input("目標利潤 (TWD)", value=7000)
    
    st.divider()
    st.write("其他台幣雜支：")
    misc_twd = 250 + 200 + 450 + 200 # 耳機+保險+網卡+製作物

# --- 2. 第一階段：上傳與 AI 解析 ---
st.header("第一階段：上傳行程 Word")
uploaded_file = st.file_uploader("請上傳紊亂的 Word 行程檔", type=["docx"])

if uploaded_file:
    # 這裡會串接你的 Gemini API 進行解析 (簡化示意)
    st.success("檔案上傳成功！AI 正在轉換為線控檢查表...")
    
    # 模擬 AI 產出的結構化表格 (Day 1 - Day 10)
    # 實際運作時會呼叫 genai 讀取 Word 並填入
    data = {
        "天數": ["D1", "D2", "D3", "D4", "D5"],
        "城市/區域": ["機上", "布拉格", "布拉格", "卡羅維瓦利", "皮爾森"],
        "行程內容": ["直飛維也納", "舊城巡禮", "伏爾塔瓦河遊船", "溫泉小鎮", "啤酒廠巡禮"],
        "門票項目": ["-", "布拉格城堡(含導覽)", "伏爾塔瓦河遊船", "-", "皮爾森啤酒廠"],
        "門票歐元": [0, 19, 18, 0, 16],
        "午餐內容": ["機上", "捷克牛肉風味", "自理", "中式七菜一湯", "啤酒廠特色餐"],
        "午餐餐標(€)": [0, 30, 0, 25, 40],
        "晚餐內容": ["機上", "中式七菜一湯", "地窖烤肉", "特色豬腳餐", "中式七菜一湯"],
        "晚餐餐標(€)": [0, 25, 50, 45, 25]
    }
    
    df = pd.DataFrame(data)
    
    st.subheader("第二階段：線控檢查表 (可直接修改格子)")
    edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True)
    
    # --- 3. 第三階段：自動計算報價 ---
    if st.button("確認檢查無誤，產出報價單"):
        st.divider()
        st.header("第三階段：16+1 ~ 31+1 階梯報價")
        
        # 計算總歐元成本 (門票 + 午餐 + 晚餐)
        total_eur = edited_df["門票歐元"].sum() + edited_df["午餐餐標(€)"].sum() + edited_df["晚餐餐標(€)"].sum()
        
        # 建立報價表
        pax_list = [16, 21, 26, 31]
        quotes = []
        
        for pax in pax_list:
            # 簡化報價邏輯 (模擬你的 Google Sheet 公式)
            # 這裡可以根據人數調整地接車資分攤 (假設車資總額 5200 EUR)
            bus_share = 5200 / (pax-1) 
            local_cost_twd = (total_eur + bus_share + 950) * exchange_rate # 假設房費總額 950
            total_net = local_cost_twd + airfare_base + airfare_tax + misc_twd
            suggested_price = (total_net + profit_target) * 1.05
            
            quotes.append({
                "人數檔次": f"{pax-1}+1",
                "每人淨成本": f"{int(total_net):,}",
                "建議售價(含稅)": f"{int(suggested_price):,}"
            })
            
        st.table(pd.DataFrame(quotes))
        st.balloons()