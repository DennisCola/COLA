import streamlit as st
import pandas as pd
import io
import re

st.set_page_config(page_title="線控自動核價系統", layout="wide")

# --- 1. 模擬單價資料庫 (未來可連動你的 Google Sheet) ---
def get_unit_price(item_name):
    # 這裡的邏輯：如果行程大點或餐食名稱包含關鍵字，自動帶入金額
    db = {
        "六菜一湯": 18.0,
        "米其林": 75.0,
        "肋排": 25.0,
        "美泉宮": 22.0,
        "霍夫堡": 18.0,
        "聖維特": 15.0,
        "自理": 0.0
    }
    total = 0.0
    item_str = str(item_name)
    # 支援一天多門票處理：若文字中有 | 或 + 則拆開計算
    sub_items = re.split(r'[|+]', item_str)
    for sub in sub_items:
        for key, price in db.items():
            if key in sub:
                total += price
                break 
    return total

# --- 2. 核心解析函式：處理 AI Studio 的文字表格 ---
def parse_ai_table(text):
    lines = [l.strip() for l in text.strip().split('\n') if not re.match(r'^[|\s:-]+$', l.strip())]
    if not lines: return None
    
    data = []
    for line in lines:
        # 切分欄位並過濾空值
        cells = [c.strip() for c in line.split('|')]
        cells = [c for c in cells if c != ""]
        data.append(cells)
    
    if len(data) > 1:
        # 確保所有行長度一致（以標題行為準）
        cols_count = len(data[0])
        valid_data = [d for d in data[1:] if len(d) == cols_count]
        return pd.DataFrame(valid_data, columns=data[0])
    return None

# --- 3. 網頁介面 ---
st.title("🛡️ 線控自動核價系統")
st.caption("版本 1.5 - 已修正語法與多門票邏輯")

raw_input = st.text_area("1. 貼上區：請貼上自 AI Studio 複製的表格文字", height=150)

if raw_input:
    df = parse_ai_table(raw_input)
    
    if df is not None:
        try:
            # 清理欄位名稱
            df.columns = [c.strip() for c in df.columns]
            categories = ["午餐", "晚餐", "景點門票", "旅館"]
            
            # 動態建立「包含」與「單價」欄位
            for cat in categories:
                if cat in df.columns:
                    df[f"{cat}_包含"] = True
                    df[f"{cat}_單價"] = df[cat].apply(get_unit_price)

            # 重新排列欄位順序：內容 | 包含? | 單價
            ordered_cols = ["天數", "行程大點"]
            for cat in categories:
                if cat in df.columns:
                    ordered_cols.extend([cat, f"{cat}_包含", f"{cat}_單價"])
            
            df = df.reindex(columns=[c for c in ordered_cols if c in df.columns])

            st.success("✅ 解析成功！請在下方調整單價或勾選合約項目。")
            
            # 編輯器介面
            edited_df = st.data_editor(
                df,
                use_container_width=True,
                num_rows="dynamic",
                column_config={
                    f"{c}_包含": st.column_config.CheckboxColumn("算?") for c in categories
                }
            )

            # --- 4. 自動算錢 ---
            st.divider()
            total_eur = 0
            for cat in categories:
                inc_col = f"{cat}_包含"
                prc_col = f"{cat}_單價"
                if inc_col in edited_df.columns:
                    # 強制轉為浮點數計算，避免文字錯誤
                    costs = edited_df[edited_df[inc_col] == True][prc_col].astype(float)
                    total_eur += costs.sum()

            c1, c2, c3 = st.columns(3)
            with c1:
                ex_rate = st.number_input("歐元匯率", value=35.5)
            with c2:
                st.metric("地接總成本 (EUR)", f"€ {total_eur:,.1f}")
            with c3:
                st.metric("換算台幣 (TWD)", f"NT$ {int(total_eur * ex_rate):,}")
                
        except Exception as e:
            st.error(f"資料處理時發生錯誤：{e}")
    else:
        st.error("❌ 無法辨識表格，請確認貼上的文字包含完整的標題行。")
