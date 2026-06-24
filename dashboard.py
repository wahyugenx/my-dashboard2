import streamlit as st
import pandas as pd
import plotly.express as px
import io
import requests

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Dashboard By Wahyu", layout="wide")

GD_FILE_ID = "17g8veYSYApTnvJATHaSAwUfqE2iRK90D" 
GD_URL = f"https://drive.google.com/uc?id={GD_FILE_ID}"

st.markdown("""
    <style>
    .stApp { background-color: #F0F4F8; }
    .main-header { 
        color: #0077B6; font-size: 2rem; font-weight: bold; 
        border-left: 8px solid #0077B6; padding-left: 15px; margin-bottom: 20px; 
    }
    div[data-testid="stMetric"] {
        background-color: #E3F2FD; padding: 15px; border-radius: 10px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.05); text-align: center;
    }
    div[data-testid="column"]:nth-of-type(2) div[data-testid="stMetric"] { background-color: #FFEBEE; }
    div[data-testid="column"]:nth-of-type(2) [data-testid="stMetricValue"] { color: #C62828 !important; }
    
    .growth-badge {
        padding: 2px 8px; border-radius: 12px; font-size: 0.85rem; font-weight: bold;
        display: inline-flex; align-items: center; gap: 4px; white-space: nowrap;
    }
    .growth-up { background-color: #E8F5E9; color: #2E7D32; }
    .growth-down { background-color: #FFEBEE; color: #C62828; }
    
    table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
    th { background-color: #f8f9fa; padding: 8px; text-align: left; border-bottom: 2px solid #dee2e6; }
    td { padding: 8px; border-bottom: 1px solid #dee2e6; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA ENGINE ---
@st.cache_data(ttl=600)
def load_data(url):
    response = requests.get(url)
    return response.content if response.status_code == 200 else None

def process_sheet(excel_file, sheet_name):
    df_raw = excel_file.parse(sheet_name, header=None)
    
    header_row = 0
    for i in range(min(20, len(df_raw))):
        if df_raw.iloc[i].astype(str).str.contains('ITEM CODE|DESCRIPTION', case=False).any():
            header_row = i
            break
            
    df = df_raw.iloc[header_row+1:].copy()
    df.columns = df_raw.iloc[header_row].astype(str).str.strip()
    df.columns = [str(c).strip() for c in df.columns]
    return df

def find_col(df, keywords):
    for col in df.columns:
        if all(k.lower() in str(col).lower() for k in keywords): return col
    return None

def format_rupiah(val):
    return f"Rp {val:,.0f}".replace(',', '.')

def format_qty(val):
    return f"{val:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

def get_delta_val(curr, past):
    return (curr - past) / past * 100 if past and past != 0 else 0

def format_growth_html(val, inverse=False):
    if val == 0: return ""
    color_class = ("growth-up" if val > 0 else "growth-down") if not inverse else ("growth-down" if val > 0 else "growth-up")
    return f'<span class="growth-badge {color_class}">{"↑" if val > 0 else "↓"} {abs(val):.1f}%</span>'

def clean_and_convert_numeric(df, col):
    if col and col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

# --- 3. MAIN APP ---
raw_bytes = load_data(GD_URL)
if raw_bytes:
    excel_obj = pd.ExcelFile(io.BytesIO(raw_bytes))
    sheets = excel_obj.sheet_names
    
    with st.sidebar:
        st.title("📌 Navigasi")
        page = st.radio("Tampilan:", ["Dashboard Utama", "Analisa By Dept"])
        target_sheet = st.selectbox("Bulan Analisa:", sheets, index=len(sheets)-1)
        range_val = st.selectbox("Rentang Pembanding:", [1, 3, 6, 12], format_func=lambda x: f"{x} Bulan")
        top_n = st.slider("Top N Item:", 5, 50, 10)

    df_target = process_sheet(excel_obj, target_sheet)
    c_sales = find_col(df_target, ['SALES', 'VALUE'])
    c_shrink = find_col(df_target, ['SHRINK', 'VALUE'])
    c_dept = find_col(df_target, ['DEPT', 'NAME'])
    c_desc = 'DESCRIPTION'
    c_qty_s = find_col(df_target, ['SALES', 'QTY'])
    c_qty_r = find_col(df_target, ['SHRINK', 'QTY'])

    if not c_sales: c_sales = [col for col in df_target.columns if 'SALES VALUE' in str(col).upper()][0]
    if not c_shrink: c_shrink = [col for col in df_target.columns if 'SHRINK VALUE' in str(col).upper()][0]

    for c in
