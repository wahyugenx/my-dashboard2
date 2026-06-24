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
    
    /* Style tabel agar muat dan rapi di layar HP */
    .mobile-table-container { width: 100%; overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; font-size: 0.8rem; table-layout: auto; }
    th { background-color: #f8f9fa; padding: 6px 4px; text-align: left; border-bottom: 2px solid #dee2e6; white-space: nowrap; }
    td { padding: 6px 4px; border-bottom: 1px solid #dee2e6; word-break: break-word; }
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

    for c in [c_sales, c_shrink, c_qty_s, c_qty_r]:
        clean_and_convert_numeric(df_target, c)

    pembant_hari = 30.0

    # Histori Logic
    target_idx = sheets.index(target_sheet)
    hist_sheets = sheets[max(0, target_idx - range_val) : target_idx]
    avg_hist = {"sales": 0.0, "shrink": 0.0, "dept_sales": {}, "dept_shrink": {}, "item_sales": {}, "item_shrink": {}}
    
    if hist_sheets:
        num_h = len(hist_sheets)
        for s in hist_sheets:
            df_h = process_sheet(excel_obj, s)
            h_s = find_col(df_h, ['SALES', 'VALUE']) or [col for col in df_h.columns if 'SALES VALUE' in str(col).upper()][0]
            h_r = find_col(df_h, ['SHRINK', 'VALUE']) or [col for col in df_h.columns if 'SHRINK VALUE' in str(col).upper()][0]
            h_d = find_col(df_h, ['DEPT', 'NAME'])
            h_qs = find_col(df_h, ['SALES', 'QTY'])
            h_qr = find_col(df_h, ['SHRINK', 'QTY'])
            
            for col_h in [h_s, h_r, h_qs, h_qr]:
                clean_and_convert_numeric(df_h, col_h)

            if h_s and h_r:
                avg_hist["sales"] += df_h[h_s].sum() / num_h
                avg_hist["shrink"] += df_h[h_r].sum() / num_h
                for _, row in df_h.iterrows():
                    item = str(row[c_desc])
                    avg_hist["item_sales"][item] = avg_hist["item_sales"].get(item, 0) + (row[h_s] / num_h)
                    avg_hist["item_shrink"][item] = avg_hist["item_shrink"].get(item, 0) + (row[h_r] / num_h)
                if h_d:
                    d_s, d_r = df_h.groupby(h_d)[h_s].sum().to_dict(), df_h.groupby(h_d)[h_r].sum().to_dict()
                    for k, v in d_s.items(): avg_hist["dept_sales"][str(k)] = avg_hist["dept_sales"].get(str(k), 0) + (v / num_h)
                    for k, v in d_r.items(): avg_hist["dept_shrink"][str(k)] = avg_hist["dept_shrink"].get(str(k), 0) + (v / num_h)

    if page == "Dashboard Utama":
        ts, tr = df_target[c_sales].sum(), df_target[c_shrink].sum()
        
        curr_ss = (tr / ts * 100) if ts > 0 else 0
        past_ss = (avg_hist["shrink"] / avg_hist["sales"] * 100) if avg_hist["sales"] > 0 else 0
        
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("AVG. SALES / DAY", format_rupiah(ts/pembant_hari), delta=f"{get_delta_val(ts/pembant_hari, avg_hist['sales']/pembant_hari):.1f}%" if avg_hist['sales']>0 else None)
        m2.metric("AVG. SHRINKAGE / DAY", format_rupiah(tr/pembant_hari), delta=f"{get_delta_val(tr/pembant_hari, avg_hist['shrink']/pembant_hari):.1f}%" if avg_hist['shrink']/pembant_hari>0 else None, delta_color="inverse")
        m3.metric("TOTAL SALES", format_rupiah(ts), delta=f"{get_delta_val(ts, avg_hist['sales']):.1f}%" if avg_hist['sales']>0 else None)
        m4.metric("TOTAL SHRINK", format_rupiah(tr), delta=f"{get_delta_val(tr, avg_hist['shrink']):.1f}%" if avg_hist['shrink']/pembant_hari>0 else None, delta_color="inverse")
        m5.metric("% S/S", f"{curr_ss:.2f}%", delta=f"{get_delta_val(curr_ss, past_ss):.1f}%" if past_ss > 0 else None, delta_color="inverse")

        st.divider()
        c_main, c_side = st.columns([1.6, 1.4])
        with c_main:
            custom_colors = {
                '015-POULTRY': '#FFD166',
                '016-BEEF': '#EF476F',
                '021-SEAFOOD': '#118AB2',
                '018-PORK': '#8B5A2B',
                '020-WHOLE CHEESE DELI': '#FFF3B0',
                '017-LAMB': '#000000',
                '019-OTHER': '#000000'
            }

            g1, g2 = st.columns(2)
            with g1:
                st.write("**KONTRIBUSI SALES PER DEPT**")
                s_grp = df_target.groupby(c_dept)[c_sales].sum().nlargest(top_n).reset_index()
                fig = px.pie(s_grp, values=c_sales, names=c_dept, color=c_dept, color_discrete_map=custom_colors, hole=0.6)
                fig.update_traces(textinfo='percent+label', textposition='outside')
                fig.update_layout(showlegend=False, height=380, margin=dict(t=30,b=30,l=0,r=0))
                st.plotly_chart(fig, use_container_width=True)
            with g2:
                st.write("**KONTRIBUSI SHRINKAGE PER DEPT**")
                r_grp = df_target.groupby(c_dept)[c_shrink].sum().nlargest(top_n).reset_index()
                fig2 = px.pie(r_grp, values=c_shrink, names=c_dept, color=c_dept, color_discrete_map=custom_colors, hole=0.6)
                fig2.update_traces(textinfo='percent+label', textposition='outside')
                fig2.update_layout(showlegend=False, height=380, margin=dict(t=30,b=30,l=0,r=0))
                st.plotly_chart(fig2, use_container_width=True)
            
            st.divider()
            t1, t2 = st.columns(2)
            with t1:
                st.write("**Rincian Sales Dept**")
                s_dept_data = df_target.groupby(c_dept).agg({c_qty_s: 'sum', c_sales: 'sum'}).reset_index()
                s_dept_data = s_dept_data.nlargest(top_n, c_sales)
                s_dept_data.insert(0, 'RANK', range(1, len(s_dept_data) + 1))
                s_dept_data['AVG QTY/DAY'] = s_dept_data[c_qty_s] / pembant_hari
                
                s_tbl = s_dept_data.rename(columns={c_dept: 'NAMA DEPARTEMEN', c_qty_s: 'TOTAL QTY', c_sales: 'TOTAL VALUE'})
                s_tbl['GROWTH'] = s_tbl['NAMA DEPARTEMEN'].apply(lambda x: format_growth_html(get_delta_val(s_tbl[s_tbl['NAMA DEPARTEMEN']==x]['TOTAL VALUE'].sum(), avg_hist["dept_sales"].get(str(x), 0))))
                s_tbl['AVG QTY/DAY'] = s_tbl['AVG QTY/DAY'].apply(format_qty)
                s_tbl['TOTAL QTY'] = s_tbl['TOTAL QTY'].apply(format_qty)
                s_tbl['TOTAL VALUE'] = s_tbl['TOTAL VALUE'].apply(format_rupiah)
                
                st.write(f'<div class="mobile-table-container">{s_tbl[["RANK", "NAMA DEPARTEMEN", "AVG QTY/DAY", "TOTAL QTY", "TOTAL VALUE", "GROWTH"]].to_html(escape=False, index=False)}</div>', unsafe_allow_html=True)
                
            with t2:
                st.write("**Rincian Shrink Dept**")
                sh_dept_data = df_target.groupby(c_dept).agg({c_qty_r: 'sum', c_shrink: 'sum'}).reset_index()
                sh_dept_data = sh_dept_data.nlargest(top_n, c_shrink)
                sh_dept_data.insert(0, 'RANK', range(1, len(sh_dept_data) + 1))
                sh_dept_data['AVG QTY/DAY'] = sh_dept_data[c_qty_r] / pembant_hari
                
                r_tbl = sh_dept_data.rename(columns={c_dept: 'NAMA DEPARTEMEN', c_qty_r: 'TOTAL QTY', c_shrink: 'TOTAL VALUE'})
                r_tbl['GROWTH'] = r_tbl['NAMA DEPARTEMEN'].apply(lambda x: format_growth_html(get_delta_val(r_tbl[r_tbl['NAMA DEPARTEMEN']==x]['TOTAL VALUE'].sum(), avg_hist["dept_shrink"].get(str(x), 0)), inverse=True))
                r_tbl['AVG QTY/DAY'] = r_tbl['AVG QTY/DAY'].apply(format_qty)
                r_tbl['TOTAL QTY'] = r_tbl['TOTAL QTY'].apply(format_qty)
                r_tbl['TOTAL VALUE'] = r_tbl['TOTAL VALUE'].apply(format_rupiah)
                
                st.write(f'<div class="mobile-table-container">{r_tbl[["RANK", "NAMA DEPARTEMEN", "AVG QTY/DAY", "TOTAL QTY", "TOTAL VALUE", "GROWTH"]].to_html(escape=False, index=False)}</div>', unsafe_allow_html=True)

        with c_side:
            st.write(f"**Top {top_n} Sales Items**")
            top_s = df_target[[c_desc, c_qty_s, c_sales]].nlargest(top_n, c_sales).copy()
            top_s.insert(0, 'RANK', range(1, len(top_s) + 1))
            top_s['AVG QTY/DAY'] = top_s[c_qty_s] / pembant_hari
            top_s['GROWTH'] = top_s[c_desc].apply(lambda x: format_growth_html(get_delta_val(top_s[top_s[c_desc]==x][c_sales].sum(), avg_hist["item_sales"].get(str(x), 0))))
            top_s[c_sales] = top_s[c_sales].apply(format_rupiah)
            top_s[c_qty_s] = top_s[c_qty_s].apply(format_qty)
            top_s['AVG QTY/DAY'] = top_s['AVG QTY/DAY'].apply(format_qty)
            
            st.write(f'<div class="mobile-table-container">{top_s[["RANK", c_desc, "AVG QTY/DAY", c_qty_s, c_sales, "GROWTH"]].to_html(escape=False, index=False)}</div>', unsafe_allow_html=True)
            st.divider()
            
            st.write(f"**Top {top_n} Shrink Items**")
            top_r = df_target[[c_desc, c_qty_r, c_shrink]].nlargest(top_n, c_shrink).copy()
            top_r.insert(0, 'RANK', range(1, len(top_r) + 1))
            top_r['AVG QTY/DAY'] = top_r[c_qty_r] / pembant_hari
            top_r['GROWTH'] = top_r[c_desc].apply(lambda x: format_growth_html(get_delta_val(top_r[top_r[c_desc]==x][c_shrink].sum(), avg_hist["item_shrink"].get(str(x), 0)), inverse=True))
            top_r[c_shrink] = top_r[c_shrink].apply(format_rupiah)
            top_r[c_qty_r] = top_r[c_qty_r].apply(format_qty)
            top_r['AVG QTY/DAY'] = top_r['AVG QTY/DAY'].apply(format_qty)
            
            st.write(f'<div class="mobile-table-container">{top_r[["RANK", c_desc, "AVG QTY/DAY", c_qty_r, c_shrink, "GROWTH"]].to_html(escape=False, index=False)}</div>', unsafe_allow_html=True)

    # --- PERBAIKAN DI HALAMAN ANALISA BY DEPT ---
    elif page == "Analisa By Dept":
        st.markdown(f'<div class="main-header">ANALISA BY DEPT</div>', unsafe_allow_html=True)
        sel_dept = st.selectbox("Pilih Departemen:", sorted(df_target[c_dept].unique()))
        df_f = df_target[df_target[c_dept] == sel_dept]
        
        b1, b2 = st.columns(2)
        with b1:
            st.write(f"**Top Sales Items di {sel_dept}**")
            df_temp_s = df_f[[c_desc, c_qty_s, c_sales]].nlargest(top_n, c_sales).copy()
            df_temp_s.insert(0, 'RANK', range(1, len(df_temp_s) + 1))
            df_temp_s['AVG QTY/DAY'] = df_temp_s[c_qty_s] / pembant_hari
            
            # Format tampilan data
            df_temp_s['AVG QTY/DAY'] = df_temp_s['AVG QTY/DAY'].apply(format_qty)
            df_temp_s[c_qty_s] = df_temp_s[c_qty_s].apply(format_qty)
            df_temp_s[c_sales] = df_temp_s[c_sales].apply(format_rupiah)
            
            # Tampilkan sebagai HTML table agar lebar kolom kompak untuk tampilan HP
            st.write(f'<div class="mobile-table-container">{df_temp_s[["RANK", c_desc, "AVG QTY/DAY", c_qty_s, c_sales]].to_html(escape=False, index=False)}</div>', unsafe_allow_html=True)
            
        with b2:
            st.write(f"**Top Shrinkage Items di {sel_dept}**")
            df_temp_r = df_f[[c_desc, c_qty_r, c_shrink]].nlargest(top_n, c_shrink).copy()
            df_temp_r.insert(0, 'RANK', range(1, len(df_temp_r) + 1))
            df_temp_r['AVG QTY/DAY'] = df_temp_r[c_qty_r] / pembant_hari
            
            # Format tampilan data
            df_temp_r['AVG QTY/DAY'] = df_temp_r['AVG QTY/DAY'].apply(format_qty)
            df_temp_r[c_qty_r] = df_temp_r[c_qty_r].apply(format_qty)
            df_temp_r[c_shrink] = df_temp_r[c_shrink].apply(format_rupiah)
            
            # Tampilkan sebagai HTML table agar lebar kolom kompak untuk tampilan HP
            st.write(f'<div class="mobile-table-container">{df_temp_r[["RANK", c_desc, "AVG QTY/DAY", c_qty_r, c_shrink]].to_html(escape=False, index=False)}</div>', unsafe_allow_html=True)
