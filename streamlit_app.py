import streamlit as st
import pandas as pd
import io
import re

st.set_page_config(page_title="線控自動核價-穩定版", layout="wide")

# --- 1. 核心解析函式：解決「無法辨識」的問題 ---
def robust_parse_markdown(text):
    # 去除 Markdown 的分隔線行 (---|---|---)
    lines = [l.strip() for l in text.strip().split('\n') if not re.match(r'^[|\s:-]+$', l.strip())]
    if not lines: return None
    
    # 將每一行按 | 切分，並去除頭尾空格與空欄位
    processed_data = []
    for line in lines:
        cells = [c.strip() for c in line.split('|')]
        # 去除因為開頭或結尾有 | 產生的空字串
        cells = [c for i, c in enumerate(cells) if not (i in [0, len(cells)-1] and c == "")]
        processed_data.append(cells)
    
    # 建立 DataFrame
    if len(processed_data) > 1:
        df = pd.DataFrame(processed_data[1:], columns=processed_data[0])
        return df
    return None

# --- 2. 模擬資料庫連動 ---
def get_unit_price(name):
    # 這裡可以接你的 Google Sheet 邏輯
    db = {"六菜一湯": 18, "米其林": 70, "美泉宮": 22, "自理": 0}
    for
