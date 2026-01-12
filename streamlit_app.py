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
            
            full_data.append({
                'is_main': True,
                'day': last_day,
                'point': last_point,
                'lunch': last_lunch, 'l_price': last_l_price,
                'dinner': last_dinner, 'd_price': last_d_price,
                'ticket': row['門票'], 't_price': row['門價'],
                'hotel': last_hotel, 'h_price': last_h_price
            })
        else:
            # 是副行 (空白行)，繼承 last_day 用於分組，但標記為副行
            full_data.append({
                'is_main': False,
                'day': last_day, # 用於計算 rowspan
                'ticket': row['門票'], 't_price': row['門價']
            })
    
    # 計算每個 day 的 rowspan
    rowspans = {}
    for item in full_data:
        d = item['day']
        rowspans[d] = rowspans.get(d, 0) + 1
        
    # 生成 HTML
    html = """
    <style>
        .quote-table { width: 100%; border-collapse: collapse; font-family: Arial, sans-serif; font-size: 14px; }
        .quote-table th { background-color: #f0f2f6; border: 1px solid #ddd; padding: 10px; text-align: center; font-weight: bold; }
        .quote-table td { border: 1px solid #ddd; padding: 8px; vertical-align: middle; text-align: center; }
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
    
    for item in full_data:
        day = item['day']
        span = rowspans[day]
        html += "<tr>"
        
        # 如果這是該天數群組的第一行 (主行)，寫入合併儲存格
        if day not in processed_days:
            # 格式化價格
            lp = f"€{item['l_price']:.1f}" if pd.notna(item['l_price']) else "-"
            dp = f"€{item['d_price']:.1f}" if pd.notna(item['d_price']) else "-"
            hp = f"€{item['h_price']:.1f}" if pd.notna(item['h_price']) else "-"
            
            html += f'<td rowspan="{span}" class="merged-cell"><b>{day}</b></td>'
            html += f'<td rowspan="{span}" class="merged-cell">{item["point"]}</td>'
            html += f'<td rowspan="{span}" class="merged-cell">{item["lunch"]}</td>'
            html += f'<td rowspan="{span}" class="merged-cell">{lp}</td>'
            html += f'<td rowspan="{span}" class="merged-cell">{item["dinner"]}</td>'
            html += f'<td rowspan="{span}" class="merged-cell">{dp}</td>'
            
            processed_days.add(day) # 標記已處理
        
        # 門票 (永遠不合併)
        tp = f"€{item['t_price']:.1f}" if pd.notna(item['t_price']) else "-"
        html += f'<td>{item["ticket"]}</td>'
        html += f'<td>{tp}</td>'
        
        # 旅館 (只在第一行寫入 rowspan，後續行不寫)
        if item.get('is_main', False):
             hp = f"€{item['h_price']:.1f}" if pd.notna(item['h_price']) else "-"
             html += f'<td rowspan="{span}" class="merged-cell">{item["hotel"]}</td>'
             html += f'<td rowspan="{span}" class="merged-cell">{hp}</td>'
             
        html += "</tr>"
        
    html += "</tbody></table>"
    return html

# --- 初始化 ---
if 'stage' not in st.session_state: st.session_state.stage = 1
if 'itinerary_df' not in st.session_state: st.session_state.itinerary_df = None

st.title("🛡️ 0112C 線控核價系統 (完整版)")

# ==========================================
# 步驟 1: 匯入
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
                    # 主列
                    all_rows.append([day, point, lunch, True, dinner, True, tks[0], True, hotel, True])
                    # 副列 (留白)
                    if len(tks) > 1:
                        for extra in tks[1:]:
                            all_rows.append(["", "", "", False, "", False, extra, True, "", False])
            if all_rows:
                st.session_state.itinerary_df = pd.DataFrame(all_rows, columns=["天數", "行程大點", "午餐", "午?", "晚餐", "晚?", "門票", "門?", "旅館", "旅?"])
                st.session_state.stage = 2
                st.rerun()

# ==========================================
# 步驟 2: 勾選
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
    
    # 修正：確保這一行完整不被截斷
    cols_to_sum = ["午價", "晚價", "門價", "旅價"]
    total = final_edit[cols_to_sum].apply(pd.to_numeric, errors='coerce').sum().sum()
    
    st.divider()
    c1, c2 = st.columns(2)
    with c1: ex = st.number_input("匯率 (EUR/TWD)", value=35.5)
    with c2: st.metric("總預算 (EUR)", f"€ {total:,.1f}", delta=f"NT$ {int(total * ex):,}")
    
    # --- Step 4: 合併預覽 ---
    st.divider()
    st.subheader("步驟 4：合併報價單預覽")
    st.info("👇 以下表格已將天數相同的項目合併並置中，可直接截圖。")
    
    html_out = generate_merged_html(final_edit)
    st.markdown(html_out, unsafe_allow_html=True)

    st.divider()
    if st.button("⬅️ 重置"):
        st.session_state.stage = 1
        st.session_state.itinerary_df = None
        st.rerun()
