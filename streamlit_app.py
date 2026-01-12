import streamlit as st
import pandas as pd

st.set_page_config(page_title="線控專業報價台", layout="wide")

st.title("📂 歐洲團體報價工作台")
st.caption("手動建立精確行程 ⮕ 多階梯人數成本拆算")

# --- 1. 基礎參數設定 ---
with st.sidebar:
    st.header("⚙️ 核心匯率與固定成本")
    ex_rate = st.number_input("歐元匯率", value=35.5, step=0.1)
    airfare = st.number_input("每人機票成本 (TWD)", value=45000)
    tax_insurance = st.number_input("稅金+保險+雜支 (TWD)", value=5000)
    
    st.divider()
    st.subheader("🚌 全團固定費用 (EUR)")
    bus_total = st.number_input("巴士總費用", value=3500)
    guide_fee = st.number_input("導遊/司機費 (總計)", value=1500)
    other_fixed = st.number_input("其他固定支出", value=500)

# --- 2. 行程與變動成本建立 ---
st.subheader("🗓️ 第一步：建立每日行程成本 (每人變動成本)")

# 初始化一個空的行程表
if 'itinerary_data' not in st.session_state:
    st.session_state.itinerary_data = pd.DataFrame([
        {"天數": 1, "行程大點": "抵達歐洲", "午餐": "機上", "午餐單價": 0, "晚餐": "中式六菜一湯", "晚餐單價": 18, "門票": "", "門票單價": 0, "飯店": "4★ Hotel", "飯店單價": 60}
    ])

# 使用 data_editor 讓使用者自由增減天數
st.info("💡 您可以像 Excel 一樣在下方輸入內容、修改單價，或點擊下方 (+) 增加天數。")
edited_df = st.data_editor(
    st.session_state.itinerary_data,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "天數": st.column_config.NumberColumn(width="small"),
        "午餐單價": st.column_config.NumberColumn(format="€%d"),
        "晚餐單價": st.column_config.NumberColumn(format="€%d"),
        "門票單價": st.column_config.NumberColumn(format="€%d"),
        "飯店單價": st.column_config.NumberColumn("每人半房費", format="€%d"),
    }
)

# --- 3. 自動計算邏輯 ---
# 計算每人總變動成本 (EUR)
per_pax_variable_eur = (
    edited_df["午餐單價"].sum() + 
    edited_df["晚餐單價"].sum() + 
    edited_df["門票單價"].sum() + 
    edited_df["飯店單價"].sum()
)

# --- 4. 多階梯人數價格分析 ---
st.divider()
st.subheader("📈 第二步：多階梯人數成本分析")

# 定義要測試的人數區間
pax_ranges = [16, 20, 25, 30]
analysis_data = []

for p in pax_ranges:
    # 固定成本平攤到每個人身上 (假設 FOC 領隊成本也平攤)
    # 這裡採用的邏輯是：(全團固定費 / 人數) + 每人變動費
    fixed_per_pax = (bus_total + guide_fee + other_fixed) / p
    total_land_eur = fixed_per_pax + per_pax_variable_eur
    
    # 換算台幣
    land_cost_twd = total_land_eur * ex_rate
    total_cost_twd = land_cost_twd + airfare + tax_insurance
    
    analysis_data.append({
        "人數 (Pax)": f"{p}+1",
        "平攤固定成本 (EUR)": round(fixed_per_pax, 1),
        "每人地接成本 (EUR)": round(total_land_eur, 1),
        "每人總成本 (TWD)": int(total_cost_twd),
        "15% 毛利售價": int(total_cost_twd / 0.85),
        "20% 毛利售價": int(total_cost_twd / 0.80)
    })

analysis_df = pd.DataFrame(analysis_data)
st.table(analysis_df)

# --- 5. 導出與結論 ---
st.success(f"📍 結論：目前行程每人基礎變動成本為 € {per_pax_variable_eur}")
st.write("這是一個「純手動、高精確」的試算表。您可以根據對手的價格，倒推回來看看 25+1 時您的利潤空間還有多少。")
