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

# --- HTML 表格生成器 (實現合併與置中) ---
def generate_merged_html(df):
    if df is None or df.empty: return ""
    
    # 計算每一天的出現次數 (Rowspan)
    # 假設 '天數' 是不重複的群組鍵，若天數空白代表是副行
    # 我們需要先還原完整資料來計算 rowspan
    
    # 1. 重建完整資料結構以利計算
    full_data = []
    last_day = ""
    for _, row in df.iterrows():
        current_day = row['天數']
        if current_day and str(current_day).strip() != "":
            last_day = current_day
        full_data.append({'day_key': last_day, 'row': row})
    
    # 計算 rowspan
    rowspans = {}
    for item in full_data:
        d = item['day_key']
        rowspans[d] = rowspans.get(d, 0) + 1
        
    html = """
    <style>
        .quote-table { width: 100%; border-collapse: collapse; font-family: Arial, sans-serif; }
        .quote-table th { background-color: #f2f2f2; border: 1px solid #ddd; padding: 8px; text-align: center; }
        .quote-table td { border: 1px solid #ddd; padding: 8px; vertical-align: middle; }
        .center-text { text-align: center; }
        .merged-cell { background-color: #ffffff; }
    </style>
    <table class="quote-table">
        <thead>
            <tr>
                <th>天數</th><th>行程大點</th><th>午餐</th><th>午價</th>
                <th>晚餐</th><th>晚價</th><th>門票內容</th><th>門價</th>
                <th>旅館</th><th>旅價</th>
            </tr>
        </thead>
        <tbody>
    """
    
    processed_days = set()
    
    for i, item in enumerate(full_data):
        day_key = item['day_key']
        row = item['row']
        span = rowspans[day_key]
        
        html += "<tr>"
        
        # 如果是該天數的第一筆，寫入合併儲存格 (天數/行程/餐食/旅館)
        if day_key not in processed_days:
            # 天數
            html += f'<td rowspan="{span}" class="center-text merged-cell"><b>{row["天數"]}</b></td>'
            # 行程
            html += f'<td rowspan="{span}" class="center-text merged-cell">{row["行程大點"]}</td>'
            # 午餐 + 價格
            l_price = f"€{row['午價']}" if pd.notna(row['午價']) else "-"
            html += f'<td rowspan="{span}" class="center-text merged-cell">{row["午餐"]}</td>'
            html += f'<td rowspan="{span}" class="center-text merged-cell">{l_price}</td>'
            # 晚餐 + 價格
            d_price = f"€{row['晚價']}" if pd.notna(row['晚價']) else "-"
            html += f'<td rowspan="{span}" class="center-text merged-cell">{row["晚餐"]}</td>'
            html += f'<td rowspan="{span}" class="center-text merged-cell">{d_price}</td>'
            
            # 標記已處理
            processed_days.add(day_key)
        
        # 門票 (不合併，每行獨立)
        t_price = f"€{row['門價']}" if pd.notna(row['門價']) else "-"
        html += f'<td class="center-text">{row["門票"]}</td>'
        html += f'<td class="center-text">{t_price}</td>'
        
        # 旅館 (合併) - 邏輯同上，只在第一筆寫入
        # 注意：因為 HTML 寫入順序，旅館必須要在門票後面寫，但 rowspan 邏輯是共用的
        # 這裡有一個順序問題：HTML是逐行寫的。
        # 如果是第一筆，我們寫入旅館並設 rowspan。如果是後續筆，我們完全跳過旅館欄位的輸出。
        
        if i == full_data.index(item): # 簡單判斷：如果是該群組的第一個 index
             h_price = f"€{row['旅價']}" if pd.notna(row['旅價']) else "-"
             html += f'<td rowspan="{span}" class="center-text merged-cell">{row["旅館"]}</td>'
             html += f'<td rowspan="{span}" class="center-text merged-cell">{h_price}</td>'
        
        html += "</tr>"
        
    html += "</tbody></table>"
    return html

# --- 初始化 ---
if 'stage' not in st.session_state: st.session_state.stage = 1
if 'itinerary_df' not in st.session_state: st.session_state.itinerary_df = None

st.title("🛡️ 0112C 線控核價系統 (合併預覽版)")

# ==========================================
# 步驟 1
# ==========================================
if st.session_state.stage == 1:
    st.subheader("步驟 1：匯入行程")
    raw_input = st.text_area("請在此貼上文字：", height=200)
    if st.button("🚀 生成表格"):
        if raw_input:
            lines = [l.strip() for l in raw_input.split('\n') if l.strip()]
            all_rows = []
            for line in lines:
                if re.match(r'^[|\s:-]+$', line): continue
                parts = [p.strip() for p in (line.split('|') if '|' in line else re.split(r'\t| {2,}', line)) if p.strip()]
                if len(parts) >= 1:
                    while len(parts) < 6: parts.append("-")
                    day, point, lunch, dinner, ticket, hotel = parts[:6]
                    tks = [t.strip() for t in re.split(r'\+|、', ticket) if t.strip()]
                    if not tks: tks = ["-"]
                    all_rows.append([day, point, lunch, True, dinner, True, tks[0], True, hotel, True])
                    if len(tks) > 1:
                        for extra in tks[1:]:
                            all_rows.append(["", "", "", False, "", False, extra, True, "", False])
            if all_rows:
                st.session_state.itinerary_df = pd.DataFrame(all_rows, columns=["天數", "行程大點", "午餐", "午?", "晚餐", "晚?", "門票", "門?", "旅館", "旅?"])
                st.session_state.stage = 2
                st.rerun()

# ==========================================
# 步驟 2
# ==========================================
elif st.session_state.stage == 2:
    st.subheader("步驟 2：確認項目")
    st.session_state.itinerary_df = st.data_editor(st.session_state.itinerary_df, use_container_width=True, key="ed_s2")
    if st.button("🪄 開始估價"):
        db = fetch_db()
        final_list = []
        def match_p(content, is_chk, database):
            if not is_chk or not content or str(content).strip() in ["", "-", "〃"]: return None
            for k, p in database.items():
                if k in str(content): return p
            return 0.0
        for _, row in st.session_state.itinerary_df.iterrows():
            p_l = match_p(row["午餐"], row["午?"], db)
            p_d = match_p(row["晚餐"], row["晚?"], db)
            p_t = match_p(row["門票"], row["門?"], db)
            p_h = match_p(row["旅館"], row["旅?"], db)
            final_list.append([row["天數"], row["行程大點"], row["午餐"], p_l, row["晚餐"], p_d, row["門票"], p_t, row["旅館"], p_h])
        st.session_state.final_df = pd.DataFrame(final_list, columns=["天數", "行程大點", "午餐", "午價", "晚餐", "晚價", "門票", "門價", "旅館", "旅價"])
        st.session_state.stage = 3
        st.rerun()

# ==========================================
# 步驟 3 & 4
# ==========================================
elif st.session_state.stage == 3:
    st.subheader("步驟 3：調整單價 (EUR)")
    final_edit = st.data_editor(st.session_state.final_df, use_container_width=True,
        column_config={
            "午價": st.column_config.NumberColumn(format="€%.1f"),
            "晚價": st.column_config.NumberColumn(format="€%.1f"),
            "門價": st.column_config.NumberColumn(format="€%.1f"),
            "旅價": st.column_config.NumberColumn(format="€%.1f"),
        }, key="ed_s3")
    
    total = final_edit[["午價
