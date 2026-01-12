import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="線控專業試算台", layout="wide")

st.title("⚡ 線控秒速試算中心")
st.caption("最強流程：AI Studio 產出表格 ⮕ 複製 ⮕ 貼到下方 ⮕ 報價完成")

# 1. 貼上區：這裡設計成可以直接接收表格資料
raw_data = st.text_area("1. 請貼上從 AI Studio 複製的表格內容：", height=250, 
                        placeholder="選取 AI Studio 產出的表格內容，Ctrl+C 複製，Ctrl+V 貼到這裡...")

if raw_data:
    try:
        # 自動辨識 AI Studio 的 Markdown 表格格式並轉為 DataFrame
        # 濾掉表格邊框符號
        clean_data = raw_data.replace('|', ',').strip()
        df = pd.read_csv(io.StringIO(raw_data), sep="|", skipinitialspace=True).dropna(axis=1, how='all')
        # 去除欄位名稱的多餘空格
        df.columns = [c.strip() for c in df.columns]
        # 去除內容的多餘空格
        df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)
        # 過濾掉 Markdown 分隔線行 (如 ---|---|---)
        df = df[~df.iloc[:, 0].str.contains('---', na=False)]

        st.success("✅ 表格讀取成功！")
        
        # 2. 編輯與報價區
        st.subheader("📍 行程核對與即時報價")
        final_df = st.data_editor(df, use_container_width=True, num_rows="dynamic")
        
        st.divider()
        
        c1, c2, c3 = st.columns(3)
        with c1:
            ex_rate = st.number_input("今日歐元匯率", value=35.5)
            airfare = st.number_input("機票成本 (TWD)", value=45000)
        with c2:
            meal_std = st.number_input("平均餐標 (EUR)", value=30)
            hotel_std = st.number_input("平均房費 (EUR)", value=120)
        with c3:
            pax = st.number_input("成行人數", value=20)
            margin = st.slider("預期毛利 %", 5, 30, 15)

        # 核心計算邏輯
        days = len(final_df)
        total_eur = (days * 2 * meal_std) + ((days-1) * hotel_std)
        total_twd = (total_eur * ex_rate) + airfare
        suggested_price = total_twd / (1 - (margin/100))
        
        st.write("---")
        st.metric("建議售價 (TWD)", f"{int(suggested_price):,}")
        st.caption(f"預估每人毛利：NT$ {int(suggested_price - total_twd):,}")

    except Exception as e:
        st.error("表格格式解析失敗，請確保您完整複製了 AI Studio 的表格內容。")
        # st.write(e) # 除錯用
