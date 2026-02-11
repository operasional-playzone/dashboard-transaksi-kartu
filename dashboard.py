import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import os
import io 
import re 
from dotenv import load_dotenv
from dateutil.relativedelta import relativedelta

# ================= 1. KONFIGURASI HALAMAN =================
st.set_page_config(
    page_title="Dashboard Transaksi 2024-2025 (Local)",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ================= 2. LOGIN & AUTH =================
load_dotenv()
ENV_USER = os.getenv("DASHBOARD_USER", "admin")
ENV_PASS = os.getenv("DASHBOARD_PASS", "admin123")

USERS = {ENV_USER: ENV_PASS}

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

def check_login(username, password):
    if username in USERS and USERS[username] == password:
        st.session_state['logged_in'] = True
        st.success("Login Berhasil!")
        st.rerun() 
    else:
        st.error("Username atau Password salah!")

if not st.session_state['logged_in']:
    st.markdown("<h1 style='text-align: center;'>🔐 Login Dashboard</h1>", unsafe_allow_html=True)
    st.markdown("---")
    c1, c2, c3 = st.columns([1, 1, 1])
    with c2:
        with st.form("login_form"):
            user = st.text_input("Username")
            pwd = st.text_input("Password", type="password")
            if st.form_submit_button("Masuk"):
                check_login(user, pwd)
    st.stop()

# ================= 3. HELPER FUNCTIONS =================
def format_rupiah(nilai):
    return f"Rp {nilai:,.0f}".replace(',', '.')

def format_id(x):
    return f"{int(x):,}".replace(",", ".")

def format_angka(nilai):
    return f"{nilai:,.0f}".replace(',', '.')

def format_label_chart(nilai):
    if nilai >= 1_000_000_000:
        val = f"{nilai/1_000_000_000:.1f}".replace('.', ',')
        if val.endswith(",0"): val = val[:-2]
        return f"{val} M"
    elif nilai >= 1_000_000:
        val = f"{nilai/1_000_000:.1f}".replace('.', ',')
        if val.endswith(",0"): val = val[:-2]
        return f"{val} Jt"
    elif nilai >= 1_000:
        val = f"{nilai/1_000:.0f}".replace('.', ',')
        return f"{val} Rb"
    else:
        return str(int(nilai))

# Helper Filter Lokal
def create_local_filter(df, label, col_name, key_prefix):
    if col_name not in df.columns: return []
    options = sorted(df[col_name].dropna().unique())
    return st.multiselect(f"Filter {label}", options, default=[], key=f"loc_{key_prefix}_{col_name}", placeholder="Semua (Kosongkan untuk memilih semua)")

def create_sidebar_filter_options(df, col_name):
    if col_name not in df.columns: return []
    return sorted(df[col_name].dropna().unique())

# ================= 4. LOAD DATA =================
@st.cache_data(ttl=600)
def load_data_kartu():
    file_path = os.path.join("output", "CLEAN_DATA_TRANSAKSI_FINAL_V4.xlsx")
    try:
        df = pd.read_excel(file_path)
        if 'Tanggal' in df.columns:
            df['Tanggal'] = pd.to_datetime(df['Tanggal'], errors='coerce')
            df = df.dropna(subset=['Tanggal'])
        else:
            return None

        for col in ['Total_Sales', 'Jumlah_Dibeli', 'Biaya', 'Masuk_Kredit', 'Masuk_Bonus']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            else:
                df[col] = 0
        
        df['Tahun'] = df['Tanggal'].dt.year.astype(str)
        df['Bulan_Urut'] = df['Tanggal'].dt.month
        df['Bulan_Key'] = df['Tanggal'].dt.to_period('M').astype(str)
        
        map_bulan_indo = {
            1: 'Januari', 2: 'Februari', 3: 'Maret', 4: 'April', 5: 'Mei', 6: 'Juni',
            7: 'Juli', 8: 'Agustus', 9: 'September', 10: 'Oktober', 11: 'November', 12: 'Desember'
        }
        df['Nama_Bulan'] = df['Bulan_Urut'].map(map_bulan_indo)

        str_cols = ['Folder_Asal', 'Nama_Toko_Internal', 'Tipe_Grup', 'Kategori_Paket', 'Nominal_Grup', 'Paket']
        for c in str_cols:
            if c in df.columns:
                df[c] = df[c].astype(str).str.strip()
        return df
    except Exception as e:
        st.error(f"Error Loading Data Kartu: {e}")
        return None

@st.cache_data(ttl=600)
def load_data_mesin():
    file_path = os.path.join("output", "dashboard_in_scope_compact_v3.xlsx")
    try:
        df = pd.read_excel(file_path)
        if 'Center_MAPPED' in df.columns:
            df.rename(columns={'Center_MAPPED': 'Center'}, inplace=True)
        if 'Tanggal' in df.columns:
            df['Tanggal'] = pd.to_datetime(df['Tanggal'], errors='coerce')
            df = df.dropna(subset=['Tanggal'])
        else:
            return None
        
        for col in ['Jumlah Diaktifkan', 'Kredit yg Digunakan', 'Bonus yg Digunakan', 'Total']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            else:
                df[col] = 0
        
        df['Tahun'] = df['Tanggal'].dt.year.astype(str)
        df['Bulan_Urut'] = df['Tanggal'].dt.month
        df['Bulan_Key'] = df['Tanggal'].dt.to_period('M').astype(str)
        
        map_bulan_indo = {
            1: 'Januari', 2: 'Februari', 3: 'Maret', 4: 'April', 5: 'Mei', 6: 'Juni',
            7: 'Juli', 8: 'Agustus', 9: 'September', 10: 'Oktober', 11: 'November', 12: 'Desember'
        }
        df['Nama_Bulan'] = df['Bulan_Urut'].map(map_bulan_indo)

        for c in ['Center', 'GT_FINAL', 'Kategori Game']:
            if c in df.columns:
                df[c] = df[c].astype(str).str.strip()

        exclusions = [
            'KIDDIE LAND', 'KIDDIE LAND 1 JAM', 'KIDDIELAND MINI', 'KIDDIELAND SEPUASNYA', 'KIDDIE ZONE 1 JAM',
            'Cek Saldo', 'E-TICKET', 'E-Ticket', 'CEK SALDO'
        ]
        if 'GT_FINAL' in df.columns:
            pattern = '|'.join([re.escape(x) for x in exclusions])
            df = df[~df['GT_FINAL'].str.contains(pattern, case=False, na=False)]
        return df
    except Exception as e:
        st.error(f"Error Loading Data Mesin: {e}")
        return None

df_raw = load_data_kartu()
df_mesin = load_data_mesin()

# ================= 5. SIDEBAR NAVIGATION =================
st.sidebar.header(f"👋 Halo, Admin")
st.sidebar.markdown("---")

selected_page = st.sidebar.radio(
    "📂 PILIH DASHBOARD",
    ["Dashboard Kartu", "Dashboard Mesin", "Penjelasan Tambahan"],
    index=0,
    key="nav_radio"
)
st.sidebar.markdown("---")

# ==============================================================================
#                               DASHBOARD KARTU
# ==============================================================================
if selected_page == "Dashboard Kartu":
    if df_raw is None:
        st.error("Gagal memuat Data Kartu.")
        st.stop()

    # --- SIDEBAR FILTER GLOBAL (KARTU) ---
    with st.sidebar.form("filter_kartu_global"):
        st.header("🎛️ Filter Kartu")
        
        min_date = df_raw['Tanggal'].min().date()
        max_date = df_raw['Tanggal'].max().date()
        month_range = pd.date_range(start=min_date, end=max_date, freq='MS')
        month_labels = [d.strftime('%b %Y') for d in month_range]
        
        def_date = st.session_state.get('k_date', (month_labels[0], month_labels[-1]))
        sel_range = st.select_slider("Rentang Bulan:", options=month_labels, value=def_date, key='k_date')
        
        tokos = create_sidebar_filter_options(df_raw, "Folder_Asal")
        def_toko = st.session_state.get('k_toko', [])
        def_toko = [t for t in def_toko if t in tokos]
        sel_toko = st.multiselect("Pilih Toko (Kosong = Semua)", tokos, default=def_toko, key="k_toko")
            
        submitted = st.form_submit_button("🚀 Terapkan Filter")

    # --- PROCESSING ---
    start_label, end_label = sel_range
    start_date = month_range[month_labels.index(start_label)]
    end_date = month_range[month_labels.index(end_label)] + relativedelta(months=1, days=-1)
    
    df_filt = df_raw[(df_raw['Tanggal'] >= start_date) & (df_raw['Tanggal'] <= end_date)].copy()
    if sel_toko:
        df_filt = df_filt[df_filt['Folder_Asal'].isin(sel_toko)]

    st.title("💳 Dashboard Kartu")
    st.caption(f"Periode Data: {start_label} - {end_label}")

    if not df_filt.empty:
        # --- PENGATURAN ANALISIS ---
        with st.expander("⚙️ Pengaturan Analisis & Filter Spesifik", expanded=True):
            with st.form("form_analisis_kartu"):
                c_set1, c_set2 = st.columns([1, 2])
                with c_set1:
                    metric_map_k = {
                        'Total Sales': 'Total_Sales',
                        'Jumlah Transaksi': 'Jumlah_Dibeli',
                        'Biaya Kartu': 'Biaya',
                        'Top Up Murni (Kredit)': 'Masuk_Kredit',
                        'Bonus Top Up': 'Masuk_Bonus'
                    }
                    def_met = st.session_state.get('k_metric', 'Total Sales')
                    pilih_metrik_k_label = st.selectbox("Pilih Metrik Analisis:", list(metric_map_k.keys()), index=list(metric_map_k.keys()).index(def_met), key='k_metric')
                    pilih_metrik_k = metric_map_k[pilih_metrik_k_label]
                
                with c_set2:
                    st.markdown("**Filter Data Spesifik**")
                    c_f1, c_f2 = st.columns(2)
                    with c_f1:
                        f_tipe = create_local_filter(df_filt, "Tipe Grup", "Tipe_Grup", "k_tipe")
                    with c_f2:
                        f_kat = create_local_filter(df_filt, "Kategori Paket", "Kategori_Paket", "k_kat")
                
                submitted_kartu = st.form_submit_button("🔄 Update Analisis")

            if f_tipe: df_filt = df_filt[df_filt['Tipe_Grup'].isin(f_tipe)]
            if f_kat: df_filt = df_filt[df_filt['Kategori_Paket'].isin(f_kat)]

        # --- FORMATTING & KPI ---
        if pilih_metrik_k == 'Jumlah_Dibeli':
            fmt_chart_k = format_id
            fmt_kpi_k = format_id
        else:
            fmt_chart_k = format_label_chart
            fmt_kpi_k = format_rupiah

        c1, c2, c3, c4 = st.columns(4)
        val_kpi = df_filt[pilih_metrik_k].sum()
        qty_tx = df_filt['Jumlah_Dibeli'].sum()
        
        c1.metric(f"Total {pilih_metrik_k_label}", fmt_kpi_k(val_kpi))
        c2.metric("Total Transaksi", format_id(qty_tx))
        c3.metric("Toko Aktif", f"{df_filt['Folder_Asal'].nunique()}")
        c4.metric("Kategori Aktif", f"{df_filt['Tipe_Grup'].nunique()}")
        st.markdown("---")

        subtab1, subtab2, subtab3, subtab4 = st.tabs(["📈 Analisis Tren & YoY", "📊 Tren Spesifik", "🏆 Peringkat & Detail", "🔎 Data Mentah"])

        with subtab1:
            st.subheader("📊 Komparasi Komponen Pendapatan")
            st.caption("Grafik ini menampilkan perbandingan komponen pendapatan berdasarkan filter aktif, **TANPA** dipengaruhi oleh 'Pilih Metrik Analisis'.")
            
            comp_cols = ['Total_Sales', 'Biaya', 'Masuk_Kredit', 'Masuk_Bonus']
            df_comp = df_filt[comp_cols].sum().reset_index()
            df_comp.columns = ['Komponen', 'Nilai']
            
            label_map = {'Total_Sales': 'Total Sales', 'Biaya': 'Biaya Kartu', 'Masuk_Kredit': 'Top Up Kredit', 'Masuk_Bonus': 'Bonus Top Up'}
            df_comp['Komponen'] = df_comp['Komponen'].map(label_map)
            df_comp['Label_Nilai'] = df_comp['Nilai'].apply(format_label_chart)
            
            fig_comp = px.bar(df_comp, x='Komponen', y='Nilai', text='Label_Nilai', color='Komponen', title="Perbandingan Komponen Pendapatan", color_discrete_sequence=px.colors.qualitative.Pastel)
            fig_comp.update_yaxes(showticklabels=False, visible=False)
            fig_comp.update_layout(separators=',.', showlegend=False)
            st.plotly_chart(fig_comp, use_container_width=True)
            st.markdown("---")

            urutan_bulan = ['Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni','Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember']
            c_left, c_right = st.columns(2)
            
            with c_left:
                st.subheader(f"Total {pilih_metrik_k_label} Tahunan")
                df_yearly = df_filt.groupby('Tahun')[pilih_metrik_k].sum().reset_index()
                v24 = df_yearly[df_yearly['Tahun']=='2024'][pilih_metrik_k].sum() if '2024' in df_yearly['Tahun'].values else 0
                v25 = df_yearly[df_yearly['Tahun']=='2025'][pilih_metrik_k].sum() if '2025' in df_yearly['Tahun'].values else 0
                gr = ((v25 - v24) / v24) * 100 if v24 > 0 else 0
                
                df_yearly['Label'] = df_yearly[pilih_metrik_k].apply(fmt_chart_k)
                fig_total = px.bar(df_yearly, x='Tahun', y=pilih_metrik_k, text='Label', title=f'Growth: {gr:.2f}%', color='Tahun', color_discrete_map={'2024': '#bdc3c7', '2025': '#27ae60'})
                fig_total.update_yaxes(showticklabels=False, visible=False)
                fig_total.update_layout(separators=',.')
                st.plotly_chart(fig_total, use_container_width=True)

            with c_right:
                st.subheader(f"Tren {pilih_metrik_k_label} Bulanan (YoY)")
                df_trend = df_filt.groupby(['Tahun', 'Bulan_Urut', 'Nama_Bulan'])[pilih_metrik_k].sum().reset_index().sort_values(['Tahun', 'Bulan_Urut'])
                df_trend['Label'] = df_trend[pilih_metrik_k].apply(fmt_chart_k)
                fig_trend = px.line(df_trend, x='Nama_Bulan', y=pilih_metrik_k, color='Tahun', markers=True, text='Label', color_discrete_map={'2024': 'gray', '2025': 'green'}, category_orders={"Nama_Bulan": urutan_bulan})
                fig_trend.update_traces(textposition="top center")
                fig_trend.update_yaxes(showticklabels=False, visible=False)
                fig_trend.update_layout(separators=',.')
                st.plotly_chart(fig_trend, use_container_width=True)

            st.markdown("---")
            st.subheader(f"📈 Tren {pilih_metrik_k_label} Jangka Panjang")
            df_cont = df_filt.groupby('Tanggal')[pilih_metrik_k].sum().reset_index().sort_values('Tanggal')
            fig_cont = px.line(df_cont, x='Tanggal', y=pilih_metrik_k, markers=True, title=f"Pergerakan {pilih_metrik_k_label}", line_shape='linear')
            fig_cont.update_xaxes(dtick="M1", tickformat="%b %Y", tickangle=-45)
            fig_cont.update_traces(line_color='#2ecc71', line_width=3)
            fig_cont.update_yaxes(tickformat=',.0f') 
            fig_cont.update_layout(separators=',.')
            st.plotly_chart(fig_cont, use_container_width=True)

            st.markdown("---")
            st.markdown(f"### 🍰 Proporsi {pilih_metrik_k_label} per Toko")
            df_pie = df_filt.groupby('Folder_Asal')[pilih_metrik_k].sum().reset_index()
            fig_pie = px.pie(df_pie, values=pilih_metrik_k, names='Folder_Asal', hole=0.4)
            fig_pie.update_layout(separators=',.')
            st.plotly_chart(fig_pie, use_container_width=True)

        # --- SUBTAB 2: TREN SPESIFIK (DENGAN FORM) ---
        with subtab2:
            st.subheader("📊 Analisis Tren Spesifik (Multi-Variable)")
            st.caption("Eksplorasi tren mendalam. **Klik tombol 'Terapkan Tren' untuk memperbarui grafik.**")
            
            with st.form("form_tren_spesifik_kartu"):
                c_spec1, c_spec2 = st.columns(2)
                with c_spec1:
                    x_breakdown_label = st.selectbox("Pecah Data Berdasarkan:", ["Tipe Grup", "Kategori Paket"], key="k_spec_x")
                with c_spec2:
                    y_spec_label = st.selectbox("Pilih Metrik untuk Tren:", list(metric_map_k.keys()), key="k_spec_y")
                
                submitted_tren_k = st.form_submit_button("🚀 Terapkan Tren")

            x_breakdown_col = "Tipe_Grup" if x_breakdown_label == "Tipe Grup" else "Kategori_Paket"
            y_spec_col = metric_map_k[y_spec_label]

            df_spec = df_filt.groupby(['Tanggal', x_breakdown_col])[y_spec_col].sum().reset_index()
            
            if y_spec_col == 'Jumlah_Dibeli':
                df_spec['Label'] = df_spec[y_spec_col].apply(format_id)
            else:
                df_spec['Label'] = df_spec[y_spec_col].apply(format_label_chart)

            fig_spec = px.line(
                df_spec, x='Tanggal', y=y_spec_col, color=x_breakdown_col, markers=True,
                title=f"Tren {y_spec_label} per {x_breakdown_label}", template='plotly_white'
            )
            fig_spec.update_xaxes(dtick="M1", tickformat="%b %Y", tickangle=-45)
            fig_spec.update_yaxes(tickformat=',.0f')
            fig_spec.update_layout(separators=',.', legend_title_text=x_breakdown_label)
            st.plotly_chart(fig_spec, use_container_width=True)

        with subtab3:
            st.subheader(f"Peringkat Berdasarkan: {pilih_metrik_k_label}")
            
            c1, c2 = st.columns(2)
            df_cat = df_filt.groupby('Tipe_Grup')[pilih_metrik_k].sum().reset_index()
            with c1:
                df_cat_top = df_cat.sort_values(pilih_metrik_k, ascending=True).tail(10)
                df_cat_top['Label'] = df_cat_top[pilih_metrik_k].apply(fmt_chart_k)
                fig_cat_t = px.bar(df_cat_top, x=pilih_metrik_k, y='Tipe_Grup', orientation='h', text='Label', title="🏆 Top Kategori (Tipe Grup)", color_discrete_sequence=['#2980b9'])
                fig_cat_t.update_xaxes(showticklabels=False)
                st.plotly_chart(fig_cat_t, use_container_width=True)
            with c2:
                df_cat_worst = df_cat.sort_values(pilih_metrik_k, ascending=False).tail(10)
                df_cat_worst['Label'] = df_cat_worst[pilih_metrik_k].apply(fmt_chart_k)
                fig_cat_w = px.bar(df_cat_worst, x=pilih_metrik_k, y='Tipe_Grup', orientation='h', text='Label', title="⚠️ Bottom Kategori (Tipe Grup)", color_discrete_sequence=['#c0392b'])
                fig_cat_w.update_xaxes(showticklabels=False)
                st.plotly_chart(fig_cat_w, use_container_width=True)

            c3, c4 = st.columns(2)
            df_toko = df_filt.groupby('Folder_Asal')[pilih_metrik_k].sum().reset_index()
            with c3:
                df_toko_top = df_toko.sort_values(pilih_metrik_k, ascending=True).tail(10)
                df_toko_top['Label'] = df_toko_top[pilih_metrik_k].apply(fmt_chart_k)
                fig_toko_t = px.bar(df_toko_top, x=pilih_metrik_k, y='Folder_Asal', orientation='h', text='Label', title="🏆 Top 10 Toko", color_discrete_sequence=['#27ae60'])
                fig_toko_t.update_xaxes(showticklabels=False)
                st.plotly_chart(fig_toko_t, use_container_width=True)
            with c4:
                df_toko_worst = df_toko.sort_values(pilih_metrik_k, ascending=False).tail(10)
                df_toko_worst['Label'] = df_toko_worst[pilih_metrik_k].apply(fmt_chart_k)
                fig_toko_w = px.bar(df_toko_worst, x=pilih_metrik_k, y='Folder_Asal', orientation='h', text='Label', title="⚠️ Worst 10 Toko", color_discrete_sequence=['#e67e22'])
                fig_toko_w.update_xaxes(showticklabels=False)
                st.plotly_chart(fig_toko_w, use_container_width=True)

        with subtab4:
            st.subheader(f"Detail Data Transaksi Kartu (FULL DATA - NO FILTER)")
            df_raw_sorted = df_raw.sort_values('Tanggal', ascending=False)
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df_raw_sorted.to_excel(writer, index=False, sheet_name='Data_Kartu')
            st.download_button(label="📥 Download Excel (.xlsx)", data=buffer, file_name="data_transaksi_kartu_full.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            st.dataframe(df_raw_sorted, use_container_width=True)
    else:
        st.warning("Data Kartu Kosong untuk periode/filter ini.")

# ==============================================================================
#                               DASHBOARD MESIN
# ==============================================================================
elif selected_page == "Dashboard Mesin":
    if df_mesin is None:
        st.error("Gagal memuat Data Mesin.")
        st.stop()

    # --- SIDEBAR FILTER MESIN ---
    with st.sidebar.form("filter_mesin_global"):
        st.header("🎛️ Filter Mesin")
        
        min_date = df_mesin['Tanggal'].min().date()
        max_date = df_mesin['Tanggal'].max().date()
        month_range = pd.date_range(start=min_date, end=max_date, freq='MS')
        month_labels = [d.strftime('%b %Y') for d in month_range]
        
        def_date_m = st.session_state.get('m_date', (month_labels[0], month_labels[-1]))
        sel_range = st.select_slider("Rentang Bulan:", options=month_labels, value=def_date_m, key='m_date')
        
        tokos = create_sidebar_filter_options(df_mesin, "Center")
        def_toko_m = st.session_state.get('m_toko', [])
        def_toko_m = [t for t in def_toko_m if t in tokos]
        sel_toko = st.multiselect("Pilih Toko (Kosong = Semua)", tokos, default=def_toko_m, key="m_toko")
            
        submitted = st.form_submit_button("🚀 Terapkan Filter")

    # --- PROCESSING ---
    start_label, end_label = sel_range
    start_date = month_range[month_labels.index(start_label)]
    end_date = month_range[month_labels.index(end_label)] + relativedelta(months=1, days=-1)
    
    df_m = df_mesin[(df_mesin['Tanggal'] >= start_date) & (df_mesin['Tanggal'] <= end_date)].copy()
    
    if sel_toko:
        df_m = df_m[df_m['Center'].isin(sel_toko)]

    st.title("🎮 Dashboard Mesin")
    st.caption(f"Periode Data: {start_label} - {end_label}")

    if not df_m.empty:
        # --- PENGATURAN ANALISIS ---
        with st.expander("⚙️ Pengaturan Analisis & Filter Spesifik", expanded=True):
            with st.form("form_analisis_mesin"):
                c_set_m1, c_set_m2 = st.columns([1, 2])
                with c_set_m1:
                    metric_map_m = {
                        'Total Sales': 'Total',
                        'Jumlah Aktivasi': 'Jumlah Diaktifkan',
                        'Kredit Terpakai': 'Kredit yg Digunakan',
                        'Bonus Terpakai': 'Bonus yg Digunakan'
                    }
                    def_met_m = st.session_state.get('m_metric', 'Total Sales')
                    y_metric_label = st.selectbox("Pilih Metrik Analisis:", list(metric_map_m.keys()), index=list(metric_map_m.keys()).index(def_met_m), key='m_metric')
                    y_metric = metric_map_m[y_metric_label]
                
                with c_set_m2:
                    st.markdown("**Filter Spesifik**")
                    c_mf1, c_mf2 = st.columns(2)
                    with c_mf1:
                        f_cat_m = create_local_filter(df_m, "Kategori Game", "Kategori Game", "m_cat")
                    with c_mf2:
                        f_gt = create_local_filter(df_m, "Game Title", "GT_FINAL", "m_gt")
                
                submitted_mesin = st.form_submit_button("🔄 Update Analisis")
            
            if f_cat_m: df_m = df_m[df_m['Kategori Game'].isin(f_cat_m)]
            if f_gt: df_m = df_m[df_m['GT_FINAL'].isin(f_gt)]

        # LOGIKA FORMATTING
        if y_metric == 'Jumlah Diaktifkan':
            fmt_chart_m = format_id
            fmt_kpi_m = format_id
        else:
            fmt_chart_m = format_label_chart
            fmt_kpi_m = format_rupiah

        k1, k2, k3, k4 = st.columns(4)
        val_kpi_m = df_m[y_metric].sum()
        total_act = df_m['Jumlah Diaktifkan'].sum()
        mesin_active = df_m['GT_FINAL'].nunique()
        
        k1.metric(f"Total {y_metric_label}", fmt_kpi_m(val_kpi_m))
        k2.metric("Total Aktivasi", format_id(total_act))
        k3.metric("Mesin Aktif", f"{mesin_active}")
        k4.metric("Toko Aktif", f"{df_m['Center'].nunique()}")
        st.markdown("---")
        
        sub_m1, sub_m2, sub_m3, sub_m4 = st.tabs(["📈 Tren & Performa", "📊 Tren Spesifik", "🏆 Peringkat", "🔎 Data Mentah"])

        with sub_m1:
            st.subheader("📊 Komparasi Komponen Pendapatan (Kredit vs Bonus)")
            st.caption("Grafik ini menampilkan proporsi Kredit vs Bonus yang digunakan berdasarkan filter aktif, **TANPA** dipengaruhi oleh 'Pilih Metrik Analisis'.")
            
            comp_cols_m = ['Kredit yg Digunakan', 'Bonus yg Digunakan']
            df_comp_m = df_m[comp_cols_m].sum().reset_index()
            df_comp_m.columns = ['Komponen', 'Nilai']
            
            fig_pie_comp_m = px.pie(
                df_comp_m, values='Nilai', names='Komponen',
                title="Proporsi Total Sales (Kredit + Bonus)", hole=0.4,
                color_discrete_sequence=['#2980b9', '#27ae60'] 
            )
            fig_pie_comp_m.update_layout(separators=',.')
            st.plotly_chart(fig_pie_comp_m, use_container_width=True)
            st.markdown("---")

            urutan_bulan = ['Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni', 'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember']
            st.subheader(f"Tren & Komparasi: {y_metric_label}")
            
            c_left, c_right = st.columns(2)
            with c_left:
                st.markdown(f"**Total {y_metric_label} Tahunan**")
                df_yearly_m = df_m.groupby('Tahun')[y_metric].sum().reset_index()
                val24_m = df_yearly_m[df_yearly_m['Tahun']=='2024'][y_metric].sum() if '2024' in df_yearly_m['Tahun'].values else 0
                val25_m = df_yearly_m[df_yearly_m['Tahun']=='2025'][y_metric].sum() if '2025' in df_yearly_m['Tahun'].values else 0
                growth_m = ((val25_m - val24_m) / val24_m) * 100 if val24_m > 0 else 0
                
                df_yearly_m['Label'] = df_yearly_m[y_metric].apply(fmt_chart_m)
                fig_total_m = px.bar(df_yearly_m, x='Tahun', y=y_metric, text='Label', title=f'Growth: {growth_m:.2f}%', color='Tahun', color_discrete_map={'2024': '#bdc3c7', '2025': '#2980b9'})
                fig_total_m.update_yaxes(showticklabels=False)
                fig_total_m.update_layout(separators=',.')
                st.plotly_chart(fig_total_m, use_container_width=True)

            with c_right:
                st.markdown(f"**Tren {y_metric_label} Bulanan (YoY)**")
                df_tm = df_m.groupby(['Tahun', 'Bulan_Urut', 'Nama_Bulan'])[y_metric].sum().reset_index().sort_values(['Tahun','Bulan_Urut'])
                df_tm['Label'] = df_tm[y_metric].apply(fmt_chart_m)
                fig_tm = px.line(df_tm, x='Nama_Bulan', y=y_metric, color='Tahun', markers=True, text='Label', color_discrete_map={'2024':'gray','2025':'blue'}, category_orders={"Nama_Bulan": urutan_bulan})
                fig_tm.update_traces(textposition="top center")
                fig_tm.update_yaxes(showticklabels=False)
                fig_tm.update_layout(separators=',.')
                st.plotly_chart(fig_tm, use_container_width=True)

            st.markdown("---")
            st.subheader(f"📈 Tren {y_metric_label} Jangka Panjang")
            df_cont_m = df_m.groupby('Tanggal')[y_metric].sum().reset_index().sort_values('Tanggal')
            fig_cont_m = px.line(df_cont_m, x='Tanggal', y=y_metric, markers=True, title=f"Pergerakan {y_metric_label} (Timeline Lengkap)", line_shape='linear')
            fig_cont_m.update_xaxes(dtick="M1", tickformat="%b %Y", tickangle=-45)
            fig_cont_m.update_traces(line_color='#3498db', line_width=3) 
            fig_cont_m.update_yaxes(tickformat=',.0f')
            fig_cont_m.update_layout(separators=',.')
            st.plotly_chart(fig_cont_m, use_container_width=True)

            st.markdown("---")
            st.markdown(f"### 🍰 Proporsi {y_metric_label} per Center")
            df_pie_m = df_m.groupby('Center')[y_metric].sum().reset_index()
            fig_pie_m = px.pie(df_pie_m, values=y_metric, names='Center', hole=0.4)
            fig_pie_m.update_layout(separators=',.')
            st.plotly_chart(fig_pie_m, use_container_width=True)

        with sub_m2:
            st.subheader("📊 Analisis Tren Spesifik (Multi-Variable)")
            st.caption("Eksplorasi tren mendalam. **Klik tombol 'Terapkan Tren' untuk memperbarui grafik.**")
            
            with st.form("form_tren_spesifik_mesin"):
                c_mf1, c_mf2 = st.columns(2)
                with c_mf1:
                    x_m_breakdown_label = st.selectbox("Pecah Data Berdasarkan:", ["Kategori Game", "Game Title"], key="m_spec_x")
                with c_mf2:
                    y_m_spec_label = st.selectbox("Pilih Metrik untuk Tren:", list(metric_map_m.keys()), key="m_spec_y")
                submitted_tren_m = st.form_submit_button("🚀 Terapkan Tren")

            x_m_breakdown_col = "Kategori Game" if x_m_breakdown_label == "Kategori Game" else "GT_FINAL"
            y_m_spec_col = metric_map_m[y_m_spec_label]

            df_m_spec = df_m.groupby(['Tanggal', x_m_breakdown_col])[y_m_spec_col].sum().reset_index()
            
            if y_m_spec_col == 'Jumlah Diaktifkan':
                df_m_spec['Label'] = df_m_spec[y_m_spec_col].apply(format_id)
            else:
                df_m_spec['Label'] = df_m_spec[y_m_spec_col].apply(format_label_chart)

            fig_m_spec = px.line(
                df_m_spec, x='Tanggal', y=y_m_spec_col, color=x_m_breakdown_col, markers=True,
                title=f"Tren {y_m_spec_label} per {x_m_breakdown_label}", template='plotly_white'
            )
            fig_m_spec.update_xaxes(dtick="M1", tickformat="%b %Y", tickangle=-45)
            fig_m_spec.update_yaxes(tickformat=',.0f')
            fig_m_spec.update_layout(separators=',.', legend_title_text=x_m_breakdown_label)
            st.plotly_chart(fig_m_spec, use_container_width=True)

        with sub_m3:
            st.subheader(f"Peringkat Berdasarkan: {y_metric_label}")
            rank_m_met = y_metric 
            
            c_cat1, c_cat2 = st.columns(2)
            df_rank_cat = df_m.groupby('Kategori Game')[rank_m_met].sum().reset_index()
            with c_cat1:
                df_top_cat = df_rank_cat.sort_values(rank_m_met, ascending=True).tail(10)
                df_top_cat['Label'] = df_top_cat[rank_m_met].apply(fmt_chart_m)
                fig_top_cat = px.bar(df_top_cat, x=rank_m_met, y='Kategori Game', orientation='h', text='Label', title="🔥 Top Kategori", color_discrete_sequence=['#8e44ad'])
                fig_top_cat.update_xaxes(showticklabels=False)
                st.plotly_chart(fig_top_cat, use_container_width=True)
            with c_cat2:
                df_worst_cat = df_rank_cat.sort_values(rank_m_met, ascending=False).tail(10)
                df_worst_cat['Label'] = df_worst_cat[rank_m_met].apply(fmt_chart_m)
                fig_worst_cat = px.bar(df_worst_cat, x=rank_m_met, y='Kategori Game', orientation='h', text='Label', title="❄️ Worst Kategori", color_discrete_sequence=['#c0392b'])
                fig_worst_cat.update_xaxes(showticklabels=False)
                st.plotly_chart(fig_worst_cat, use_container_width=True)

            st.markdown("---")
            c1, c2 = st.columns(2)
            df_rank_m = df_m.groupby('GT_FINAL')[rank_m_met].sum().reset_index()
            with c1:
                df_top_m = df_rank_m.sort_values(rank_m_met, ascending=True).tail(10)
                df_top_m['Label'] = df_top_m[rank_m_met].apply(fmt_chart_m)
                fig_top_m = px.bar(df_top_m, x=rank_m_met, y='GT_FINAL', orientation='h', text='Label', title="🔥 Top 10 Mesin", color_discrete_sequence=['#2980b9'])
                fig_top_m.update_xaxes(showticklabels=False)
                st.plotly_chart(fig_top_m, use_container_width=True)
            with c2:
                df_worst_m = df_rank_m.sort_values(rank_m_met, ascending=False).tail(10)
                df_worst_m['Label'] = df_worst_m[rank_m_met].apply(fmt_chart_m)
                fig_worst_m = px.bar(df_worst_m, x=rank_m_met, y='GT_FINAL', orientation='h', text='Label', title="❄️ Worst 10 Mesin", color_discrete_sequence=['#e74c3c'])
                fig_worst_m.update_xaxes(showticklabels=False)
                st.plotly_chart(fig_worst_m, use_container_width=True)

            st.markdown("---")
            c3, c4 = st.columns(2)
            df_rank_toko = df_m.groupby('Center')[rank_m_met].sum().reset_index()
            with c3:
                df_top_toko = df_rank_toko.sort_values(rank_m_met, ascending=True).tail(10)
                df_top_toko['Label'] = df_top_toko[rank_m_met].apply(fmt_chart_m)
                fig_top_t = px.bar(df_top_toko, x=rank_m_met, y='Center', orientation='h', text='Label', title="🏆 Top 10 Toko", color_discrete_sequence=['#27ae60'])
                fig_top_t.update_xaxes(showticklabels=False)
                st.plotly_chart(fig_top_t, use_container_width=True)
            with c4:
                df_worst_toko = df_rank_toko.sort_values(rank_m_met, ascending=False).tail(10)
                df_worst_toko['Label'] = df_worst_toko[rank_m_met].apply(fmt_chart_m)
                fig_worst_t = px.bar(df_worst_toko, x=rank_m_met, y='Center', orientation='h', text='Label', title="⚠️ Worst 10 Toko", color_discrete_sequence=['#e67e22'])
                fig_worst_t.update_xaxes(showticklabels=False)
                st.plotly_chart(fig_worst_t, use_container_width=True)

        with sub_m4:
            st.subheader("Detail Data Mesin (FULL DATA - NO FILTER)")
            df_mesin_sorted = df_mesin.sort_values('Tanggal', ascending=False)
            buffer_m = io.BytesIO()
            with pd.ExcelWriter(buffer_m, engine='xlsxwriter') as writer:
                df_mesin_sorted.to_excel(writer, index=False, sheet_name='Data_Mesin')
            st.download_button(label="📥 Download Excel Full Data (.xlsx)", data=buffer_m, file_name="data_aktivitas_mesin_full.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            st.dataframe(df_mesin_sorted, use_container_width=True)
    else:
        st.warning("Data Mesin Kosong untuk periode/filter ini.")

# ==============================================================================
#                               PENJELASAN TAMBAHAN
# ==============================================================================
elif selected_page == "Penjelasan Tambahan":
    st.title("ℹ️ Penjelasan Tambahan")
    st.markdown("""
# Penjelasan Metrik Dashboard Transaksi Kartu
* **Jumlah_Dibeli**: Jumlah paket dibeli 
* **Biaya**: Biaya kartu
* **Masuk_Kredit**: Penjualan top up paket murni tanpa bonus
* **Masuk_Bonus**: Jumlah bonus top up paket yang diberi pelanggan
* **Total_Sales**: Masuk_Kredit + Biaya
* **Tipe_Grup**: 
    * Regular Top Up
    * Bundling F&B/Barang
    * Kiddie Land
    * Regular Top Up dengan Bonus
    * Kartu Perdana
    * Top Up Promo Tiket.com
* **Nominal_Grup**: Nominal paket transaksi
* **Kategori_Paket**: Tipe_Grup + Nominal_Grup

---

# Penjelasan Metrik Dashboard Mesin
* **Game**: Game Title mesin playzone
* **Kategori Game**: Kategori game title 
* **Jumlah Diaktifkan**: frekuensi game dimainkan
* **Kredit yg Digunakan**: kredit yang masuk ke mesin
* **Bonus yg Digunakan**: bonus main game untuk customer
* **Total**: kredit + bonus
""")