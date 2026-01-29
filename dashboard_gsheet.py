import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import os
import io 
import datetime
from dateutil.relativedelta import relativedelta # Penting untuk hitung akhir bulan
from dotenv import load_dotenv
import gspread
from google.oauth2.service_account import Credentials

# ================= 1. KONFIGURASI HALAMAN =================
st.set_page_config(
    page_title="Dashboard Transaksi 2024-2025",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ================= 2. LOGIN & AUTH =================
if "DASHBOARD_USER" in st.secrets:
    ENV_USER = st.secrets["DASHBOARD_USER"]
    ENV_PASS = st.secrets["DASHBOARD_PASS"]
else:
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

def format_label_chart(nilai):
    if nilai >= 1_000_000_000:
        return f"{nilai/1_000_000_000:.1f}M"
    elif nilai >= 1_000_000:
        return f"{nilai/1_000_000:.0f}jt"
    else:
        return f"{nilai/1_000:.0f}rb"

def create_sidebar_filter(df, label, col_name, key_prefix):
    if col_name not in df.columns: 
        return None
    options = sorted(df[col_name].dropna().unique())
    container = st.sidebar.container()
    all_selected = container.checkbox(f"Semua {label}", value=True, key=f"all_{key_prefix}_{col_name}")
    if all_selected:
        return None
    else:
        return container.multiselect(f"Pilih {label}", options, default=options[:1], key=f"sel_{key_prefix}_{col_name}")

# ================= 4. LOAD DATA (LOGIKA CORRECT DATA 2024-2025) =================

try:
    URL_KARTU = st.secrets["spreadsheet_links"]["url_kartu"]
    URL_MESIN = st.secrets["spreadsheet_links"]["url_mesin"]
except Exception as e:
    st.error("Gagal membaca Link Spreadsheet.")
    st.stop()

@st.cache_resource
def get_gspread_client():
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    credentials = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scope
    )
    return gspread.authorize(credentials)

@st.cache_data(ttl=600)
def load_data_kartu():
    try:
        client = get_gspread_client()
        sh = client.open_by_url(URL_KARTU)
        worksheet = sh.get_worksheet(0)
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)

        df.drop_duplicates(inplace=True)

        if 'tOmset_Paket' in df.columns:
            df.rename(columns={'tOmset_Paket': 'Omset_Paket'}, inplace=True)
            
        df['Tanggal'] = pd.to_datetime(df['Tanggal'], errors='coerce')
        df = df.dropna(subset=['Tanggal'])
        
        for col in ['Omset_Paket', 'Frekuensi']:
            if col in df.columns:
                if df[col].dtype == object:
                    df[col] = df[col].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            else:
                df[col] = 0
        
        df['Tahun'] = df['Tanggal'].dt.year.astype(str)
        df = df[df['Tahun'].isin(['2024', '2025'])] # Filter Strict
        
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
    try:
        client = get_gspread_client()
        sh = client.open_by_url(URL_MESIN)
        worksheet = sh.get_worksheet(0)
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)
        
        df.drop_duplicates(inplace=True)

        if 'Center_MAPPED' in df.columns:
            df.rename(columns={'Center_MAPPED': 'Center'}, inplace=True)
            
        if 'Tanggal' in df.columns:
            df = df[df['Tanggal'] != '']
            df['Tanggal'] = pd.to_datetime(df['Tanggal'], errors='coerce')
            df = df.dropna(subset=['Tanggal'])
        else:
            return None
        
        for col in ['Jumlah Diaktifkan', 'Kredit yg Digunakan']:
            if col in df.columns:
                if df[col].dtype == object:
                    df[col] = df[col].astype(str).str.replace('.', '').str.replace(',', '.')
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            else:
                df[col] = 0
        
        df['Tahun'] = df['Tanggal'].dt.year.astype(str)
        df = df[df['Tahun'].isin(['2024', '2025'])] # Filter Strict
        
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

        exclusions = ['KIDDIE LAND', 'KIDDIE LAND 1 JAM', 'KIDDIELAND MINI', 'KIDDIELAND SEPUASNYA', 'KIDDIE ZONE 1 JAM']
        if 'GT_FINAL' in df.columns:
            df = df[~df['GT_FINAL'].isin(exclusions)]

        return df
    except Exception as e:
        st.error(f"Error Loading Data Mesin: {e}")
        return None

df_raw = load_data_kartu()
df_mesin = load_data_mesin()

# ================= 5. SIDEBAR & FILTER (TRANSFORMASI DATE -> MONTH) =================
st.sidebar.header(f"👋 Halo, Admin")
if st.sidebar.button("🚪 Log Out", type="primary"):
    st.session_state['logged_in'] = False
    st.rerun()
st.sidebar.markdown("---")

df_filt = pd.DataFrame()
df_m = pd.DataFrame()

if df_raw is not None and df_mesin is not None:
    # --- 1. FILTER BULAN (FITUR BARU) ---
    st.sidebar.header("🗓️ Filter Periode (Bulan)")
    
    # Gabungkan tanggal dari kedua dataset untuk mendapatkan rentang penuh
    all_dates = pd.concat([df_raw['Tanggal'], df_mesin['Tanggal']])
    min_date = all_dates.min()
    max_date = all_dates.max()

    # Buat list bulan (YYYY-MM-01) untuk Slider
    # Kita buat range bulanan dari Min sampai Max
    month_range = pd.date_range(start=min_date, end=max_date, freq='MS')
    
    # Label Slider (Jan 2024, Feb 2024, ...)
    month_labels = [d.strftime('%b %Y') for d in month_range]
    
    # Slider UI
    selected_range = st.sidebar.select_slider(
        "Pilih Rentang Bulan:",
        options=month_labels,
        value=(month_labels[0], month_labels[-1]) # Default: Semua bulan
    )
    
    # Konversi Label Slider Kembali ke Tanggal untuk Filtering
    start_label, end_label = selected_range
    
    # Ambil tanggal awal (tgl 1 bulan tersebut)
    start_date_filter = month_range[month_labels.index(start_label)]
    
    # Ambil tanggal akhir (tgl terakhir bulan tersebut)
    end_date_start = month_range[month_labels.index(end_label)]
    # Tambah 1 bulan lalu kurangi 1 hari untuk dapat tanggal terakhir
    end_date_filter = end_date_start + relativedelta(months=1, days=-1)

    # --- 2. TERAPKAN FILTER TANGGAL (GLOBAL) ---
    df_filt = df_raw[
        (df_raw['Tanggal'] >= start_date_filter) & 
        (df_raw['Tanggal'] <= end_date_filter)
    ].copy()
    
    df_m = df_mesin[
        (df_mesin['Tanggal'] >= start_date_filter) & 
        (df_mesin['Tanggal'] <= end_date_filter)
    ].copy()

    st.sidebar.caption(f"📅 Data: {start_label} s/d {end_label}")
    st.sidebar.markdown("---")

    # --- 3. FILTER KATEGORI (KARTU) ---
    st.sidebar.header("🎛️ Filter Spesifik (Kartu)")
    sel_toko = create_sidebar_filter(df_raw, "Toko", "Folder_Asal", "kartu")
    sel_tipe = create_sidebar_filter(df_raw, "Tipe Grup", "Tipe_Grup", "kartu")
    sel_kat = create_sidebar_filter(df_raw, "Kategori", "Kategori_Paket", "kartu")
    
    if sel_toko: df_filt = df_filt[df_filt['Folder_Asal'].isin(sel_toko)]
    if sel_tipe: df_filt = df_filt[df_filt['Tipe_Grup'].isin(sel_tipe)]
    if sel_kat: df_filt = df_filt[df_filt['Kategori_Paket'].isin(sel_kat)]

    st.sidebar.markdown("---")
    
    # --- 4. FILTER KATEGORI (MESIN) ---
    st.sidebar.header("🎛️ Filter Spesifik (Mesin)")
    sel_center = create_sidebar_filter(df_mesin, "Toko", "Center", "mesin")
    sel_gt = create_sidebar_filter(df_mesin, "Game", "GT_FINAL", "mesin")
    sel_cat_m = create_sidebar_filter(df_mesin, "Kategori", "Kategori Game", "mesin")
    
    if sel_center: df_m = df_m[df_m['Center'].isin(sel_center)]
    if sel_gt: df_m = df_m[df_m['GT_FINAL'].isin(sel_gt)]
    if sel_cat_m: df_m = df_m[df_m['Kategori Game'].isin(sel_cat_m)]

else:
    st.error("Gagal memuat data.")
    st.stop()

# ================= 6. LAYOUT UTAMA =================
st.title("📊 RAMAYANA ANALYTICS DASHBOARD")

tab_kartu_main, tab_mesin_main, tab_corr_main, tab_help_main = st.tabs([
    "💳 Omset Kartu",
    "🎮 Dashboard Mesin",
    "🔗 Analisis Korelasi",
    "ℹ️ Penjelasan Tambahan"
])

# ================= TAB 1: KARTU =================
with tab_kartu_main:
    if not df_filt.empty:
        # 1. SUMMARY METRICS
        c1, c2, c3, c4 = st.columns(4)
        omset = df_filt['Omset_Paket'].sum()
        qty = df_filt['Frekuensi'].sum()
        avg = omset / qty if qty > 0 else 0
        tokos = df_filt['Folder_Asal'].nunique()
        
        c1.metric("Total Omset", format_rupiah(omset))
        c2.metric("Total Transaksi", format_id(qty))
        c3.metric("Rata-rata", format_rupiah(avg))
        c4.metric("Toko Aktif", f"{tokos}")
        st.markdown("---")

        subtab1, subtab2, subtab3 = st.tabs(["📈 Analisis Tren & YoY", "🏆 Peringkat & Detail", "🔎 Data Mentah"])

      # --- SUBTAB 1: TREN & KOMPARASI YoY + KONTINU (KARTU) ---
        with subtab1:
            # Definisi Urutan Bulan (Agar X-Axis Tidak Berantakan)
            urutan_bulan = [
                'Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni',
                'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember'
            ]

            # BAGIAN ATAS: Komparasi Tahunan & YoY
            c_left, c_right = st.columns(2)
            
            with c_left:
                st.subheader("Total Omset Tahunan")
                df_yearly = df_filt.groupby('Tahun')['Omset_Paket'].sum().reset_index()
                
                val24 = df_yearly[df_yearly['Tahun']=='2024']['Omset_Paket'].sum() if '2024' in df_yearly['Tahun'].values else 0
                val25 = df_yearly[df_yearly['Tahun']=='2025']['Omset_Paket'].sum() if '2025' in df_yearly['Tahun'].values else 0
                growth = ((val25 - val24) / val24) * 100 if val24 > 0 else 0
                
                df_yearly['Label'] = df_yearly['Omset_Paket'].apply(format_label_chart)

                fig_total = px.bar(
                    df_yearly, x='Tahun', y='Omset_Paket', text='Label',
                    title=f'Growth: {growth:.2f}%',
                    color='Tahun', color_discrete_map={'2024': '#bdc3c7', '2025': '#27ae60'}
                )
                st.plotly_chart(fig_total, use_container_width=True)

            with c_right:
                st.subheader("Tren Omset Bulanan (YoY)")
                df_trend = df_filt.groupby(['Tahun', 'Bulan_Urut', 'Nama_Bulan'])['Omset_Paket'].sum().reset_index()
                # Sort berdasarkan urutan bulan agar garis nyambung benar
                df_trend = df_trend.sort_values(['Tahun', 'Bulan_Urut'])
                df_trend['Label_Text'] = df_trend['Omset_Paket'].apply(format_label_chart)
                
                fig_trend = px.line(
                    df_trend, x='Nama_Bulan', y='Omset_Paket', color='Tahun', markers=True, text='Label_Text',
                    color_discrete_map={'2024': 'gray', '2025': 'green'},
                    # --- FIX: MEMAKSA URUTAN BULAN ---
                    category_orders={"Nama_Bulan": urutan_bulan}
                )
                fig_trend.update_traces(textposition="top center")
                st.plotly_chart(fig_trend, use_container_width=True)

            # --- BAGIAN BAWAH: LINE CHART KONTINU ---
            st.markdown("---")
            st.subheader("📈 Tren Omset Jangka Panjang")
            
            df_cont = df_filt.groupby('Tanggal')['Omset_Paket'].sum().reset_index().sort_values('Tanggal')
            
            fig_cont = px.line(
                df_cont, x='Tanggal', y='Omset_Paket', markers=True,
                title="Pergerakan Omset (Timeline Lengkap)",
                line_shape='linear'
            )
            fig_cont.update_xaxes(dtick="M1", tickformat="%b %Y", tickangle=-45)
            fig_cont.update_traces(line_color='#2ecc71', line_width=3) 
            st.plotly_chart(fig_cont, use_container_width=True)

            # Pie Chart
            st.markdown("---")
            st.markdown("### 🍰 Proporsi Omset per Toko")
            df_pie = df_filt.groupby('Folder_Asal')['Omset_Paket'].sum().reset_index()
            fig_pie = px.pie(df_pie, values='Omset_Paket', names='Folder_Asal', hole=0.4)
            st.plotly_chart(fig_pie, use_container_width=True)

        # --- SUBTAB 2: PERINGKAT (DENGAN WORST 10) ---
        with subtab2:
            st.subheader("Peringkat Performa: Top & Worst")
            rank_mode = st.radio("Urutkan Berdasarkan:", ['Total Omset', 'Jumlah Transaksi'], horizontal=True)
            col_rank = 'Omset_Paket' if rank_mode == 'Total Omset' else 'Frekuensi'
            fmt_func = format_label_chart if rank_mode == 'Total Omset' else format_id

            st.markdown("---")
            st.markdown("### 📦 Analisis Kategori Paket")
            c1, c2 = st.columns(2)
            
            df_cat = df_filt.groupby('Kategori_Paket')[col_rank].sum().reset_index()
            
            with c1:
                df_cat_top = df_cat.sort_values(col_rank, ascending=True).tail(10)
                df_cat_top['Label'] = df_cat_top[col_rank].apply(fmt_func)
                fig_cat_t = px.bar(df_cat_top, x=col_rank, y='Kategori_Paket', orientation='h', text='Label', title="🏆 Top 10 Kategori", color_discrete_sequence=['#2980b9'])
                st.plotly_chart(fig_cat_t, use_container_width=True)

            with c2:
                df_cat_worst = df_cat.sort_values(col_rank, ascending=False).tail(10)
                df_cat_worst['Label'] = df_cat_worst[col_rank].apply(fmt_func)
                fig_cat_w = px.bar(df_cat_worst, x=col_rank, y='Kategori_Paket', orientation='h', text='Label', title="⚠️ Worst 10 Kategori", color_discrete_sequence=['#c0392b'])
                st.plotly_chart(fig_cat_w, use_container_width=True)

            st.markdown("---")
            st.markdown("### 🏪 Analisis Toko (Store)")
            c3, c4 = st.columns(2)
            
            df_toko = df_filt.groupby('Folder_Asal')[col_rank].sum().reset_index()

            with c3:
                df_toko_top = df_toko.sort_values(col_rank, ascending=True).tail(10)
                df_toko_top['Label'] = df_toko_top[col_rank].apply(fmt_func)
                fig_toko_t = px.bar(df_toko_top, x=col_rank, y='Folder_Asal', orientation='h', text='Label', title="🏆 Top 10 Toko", color_discrete_sequence=['#27ae60'])
                st.plotly_chart(fig_toko_t, use_container_width=True)

            with c4:
                df_toko_worst = df_toko.sort_values(col_rank, ascending=False).tail(10)
                df_toko_worst['Label'] = df_toko_worst[col_rank].apply(fmt_func)
                fig_toko_w = px.bar(df_toko_worst, x=col_rank, y='Folder_Asal', orientation='h', text='Label', title="⚠️ Worst 10 Toko", color_discrete_sequence=['#e67e22'])
                st.plotly_chart(fig_toko_w, use_container_width=True)

        # --- SUBTAB 3: DATA MENTAH (KARTU) ---
        with subtab3:
            st.subheader("Detail Data Transaksi Kartu")
            
            # Konversi ke Excel
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df_filt.to_excel(writer, index=False, sheet_name='Data_Kartu')
            
            # Tombol Download
            st.download_button(
                label="📥 Download Excel (.xlsx)",
                data=buffer,
                file_name="data_transaksi_kartu.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
            # Tampilkan Tabel
            st.dataframe(df_filt, use_container_width=True)
    else:
        st.warning("Data Kartu Kosong untuk periode ini.")

# ================= TAB 2: MESIN =================
with tab_mesin_main:
    if not df_m.empty:
        # 1. KPI
        k1, k2, k3, k4 = st.columns(4)
        total_act = df_m['Jumlah Diaktifkan'].sum()
        total_crd = df_m['Kredit yg Digunakan'].sum()
        avg_crd = total_crd / total_act if total_act > 0 else 0
        mesin_active = df_m['GT_FINAL'].nunique()
        
        k1.metric("Total Aktivasi", format_id(total_act))
        k2.metric("Total Kredit", format_id(total_crd))
        k3.metric("Rata-rata Kredit", f"{avg_crd:,.2f}")
        k4.metric("Mesin Aktif", f"{mesin_active}")
        st.markdown("---")
        
        # --- UPDATE: MENAMBAHKAN TAB DATA MENTAH ---
        sub_m1, sub_m2, sub_m3, sub_m4, sub_m5 = st.tabs([
            "📈 Tren & Performa", 
            "🏆 Peringkat", 
            "🔥 Heatmap & Utilitas", 
            "💡 Efisiensi",
            "🔎 Data Mentah" # <--- Tab Baru
        ])

        # --- SUBTAB M1: TREN & PERFORMA (MESIN) ---
        # --- SUBTAB M1: TREN & PERFORMA (MESIN) ---
        with sub_m1:
            # Definisi Urutan Bulan
            urutan_bulan = [
                'Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni',
                'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember'
            ]

            st.subheader("Tren & Komparasi Aktivitas")
            y_metric = st.selectbox("Pilih Metrik Analisis:", ['Jumlah Diaktifkan', 'Kredit yg Digunakan'])
            
            c_left, c_right = st.columns(2)

            # KIRI: Bar Chart Tahunan
            with c_left:
                st.markdown(f"**Total {y_metric} Tahunan**")
                df_yearly_m = df_m.groupby('Tahun')[y_metric].sum().reset_index()
                
                val24_m = df_yearly_m[df_yearly_m['Tahun']=='2024'][y_metric].sum() if '2024' in df_yearly_m['Tahun'].values else 0
                val25_m = df_yearly_m[df_yearly_m['Tahun']=='2025'][y_metric].sum() if '2025' in df_yearly_m['Tahun'].values else 0
                growth_m = ((val25_m - val24_m) / val24_m) * 100 if val24_m > 0 else 0
                
                df_yearly_m['Label'] = df_yearly_m[y_metric].apply(format_label_chart)

                fig_total_m = px.bar(
                    df_yearly_m, x='Tahun', y=y_metric, text='Label',
                    title=f'Growth: {growth_m:.2f}%',
                    color='Tahun', 
                    color_discrete_map={'2024': '#bdc3c7', '2025': '#2980b9'} 
                )
                st.plotly_chart(fig_total_m, use_container_width=True)

            # KANAN: Line Chart Bulanan (YoY)
            with c_right:
                st.markdown(f"**Tren {y_metric} Bulanan (YoY)**")
                df_tm = df_m.groupby(['Tahun', 'Bulan_Urut', 'Nama_Bulan'])[y_metric].sum().reset_index().sort_values(['Tahun','Bulan_Urut'])
                df_tm['Label'] = df_tm[y_metric].apply(format_id)
                
                fig_tm = px.line(
                    df_tm, x='Nama_Bulan', y=y_metric, color='Tahun', markers=True, text='Label',
                    color_discrete_map={'2024':'gray','2025':'blue'},
                    # --- FIX: MEMAKSA URUTAN BULAN ---
                    category_orders={"Nama_Bulan": urutan_bulan}
                )
                fig_tm.update_traces(textposition="top center")
                st.plotly_chart(fig_tm, use_container_width=True)

            # --- BAGIAN BAWAH: LINE CHART KONTINU (MESIN) ---
            st.markdown("---")
            st.subheader(f"📈 Tren {y_metric} Jangka Panjang")
            
            df_cont_m = df_m.groupby('Tanggal')[y_metric].sum().reset_index().sort_values('Tanggal')
            
            fig_cont_m = px.line(
                df_cont_m, x='Tanggal', y=y_metric, markers=True,
                title=f"Pergerakan {y_metric} (Timeline Lengkap)",
                line_shape='linear'
            )
            fig_cont_m.update_xaxes(dtick="M1", tickformat="%b %Y", tickangle=-45)
            fig_cont_m.update_traces(line_color='#3498db', line_width=3) 
            st.plotly_chart(fig_cont_m, use_container_width=True)

            # Pie Chart
            st.markdown("---")
            st.markdown(f"### 🍰 Proporsi {y_metric} per Center")
            df_pie_m = df_m.groupby('Center')[y_metric].sum().reset_index()
            fig_pie_m = px.pie(df_pie_m, values=y_metric, names='Center', hole=0.4)
            st.plotly_chart(fig_pie_m, use_container_width=True)
        # --- SUBTAB M2: PERINGKAT (DENGAN KATEGORI, MESIN, & TOKO) ---
        with sub_m2:
            # Selector Metrik untuk semua grafik di tab ini
            rank_m_met = st.radio("Ranking By", ['Jumlah Diaktifkan', 'Kredit yg Digunakan'], horizontal=True)
            
            # --- BAGIAN 1: KATEGORI GAME (BARU) ---
            st.markdown("---")
            st.markdown("### 📂 Analisis Kategori Game")
            c_cat1, c_cat2 = st.columns(2)
            
            # Agregasi Data Kategori
            df_rank_cat = df_m.groupby('Kategori Game')[rank_m_met].sum().reset_index()

            # Top 10 Kategori
            with c_cat1:
                df_top_cat = df_rank_cat.sort_values(rank_m_met, ascending=True).tail(10)
                df_top_cat['Label'] = df_top_cat[rank_m_met].apply(format_id)
                fig_top_cat = px.bar(
                    df_top_cat, x=rank_m_met, y='Kategori Game', orientation='h', text='Label', 
                    title="🔥 Top Kategori", 
                    color_discrete_sequence=['#8e44ad'] # Warna Ungu
                )
                st.plotly_chart(fig_top_cat, use_container_width=True)

            # Worst 10 Kategori
            with c_cat2:
                df_worst_cat = df_rank_cat.sort_values(rank_m_met, ascending=False).tail(10)
                df_worst_cat['Label'] = df_worst_cat[rank_m_met].apply(format_id)
                fig_worst_cat = px.bar(
                    df_worst_cat, x=rank_m_met, y='Kategori Game', orientation='h', text='Label', 
                    title="❄️ Worst Kategori", 
                    color_discrete_sequence=['#c0392b'] # Warna Merah Gelap
                )
                st.plotly_chart(fig_worst_cat, use_container_width=True)

            # --- BAGIAN 2: MESIN SPESIFIK (GT_FINAL) ---
            st.markdown("---")
            st.markdown("### 🎮 Analisis Mesin (Game)")
            c1, c2 = st.columns(2)
            
            df_rank_m = df_m.groupby('GT_FINAL')[rank_m_met].sum().reset_index()

            # Top 10 Mesin
            with c1:
                df_top_m = df_rank_m.sort_values(rank_m_met, ascending=True).tail(10)
                df_top_m['Label'] = df_top_m[rank_m_met].apply(format_id)
                fig_top_m = px.bar(
                    df_top_m, x=rank_m_met, y='GT_FINAL', orientation='h', text='Label', 
                    title="🔥 Top 10 Mesin", 
                    color_discrete_sequence=['#2980b9'] # Warna Biru
                )
                st.plotly_chart(fig_top_m, use_container_width=True)

            # Worst 10 Mesin
            with c2:
                df_worst_m = df_rank_m.sort_values(rank_m_met, ascending=False).tail(10)
                df_worst_m['Label'] = df_worst_m[rank_m_met].apply(format_id)
                fig_worst_m = px.bar(
                    df_worst_m, x=rank_m_met, y='GT_FINAL', orientation='h', text='Label', 
                    title="❄️ Worst 10 Mesin", 
                    color_discrete_sequence=['#e74c3c'] # Warna Merah
                )
                st.plotly_chart(fig_worst_m, use_container_width=True)

            # --- BAGIAN 3: TOKO (CENTER) ---
            st.markdown("---")
            st.markdown("### 🏪 Analisis Toko (Berdasarkan Mesin)")
            c3, c4 = st.columns(2)
            
            df_rank_toko = df_m.groupby('Center')[rank_m_met].sum().reset_index()

            # Top 10 Toko (Mesin)
            with c3:
                df_top_toko = df_rank_toko.sort_values(rank_m_met, ascending=True).tail(10)
                df_top_toko['Label'] = df_top_toko[rank_m_met].apply(format_id)
                fig_top_t = px.bar(
                    df_top_toko, x=rank_m_met, y='Center', orientation='h', text='Label', 
                    title="🏆 Top 10 Toko (Aktivitas Mesin)", 
                    color_discrete_sequence=['#27ae60'] # Warna Hijau
                )
                st.plotly_chart(fig_top_t, use_container_width=True)

            # Worst 10 Toko (Mesin)
            with c4:
                df_worst_toko = df_rank_toko.sort_values(rank_m_met, ascending=False).tail(10)
                df_worst_toko['Label'] = df_worst_toko[rank_m_met].apply(format_id)
                fig_worst_t = px.bar(
                    df_worst_toko, x=rank_m_met, y='Center', orientation='h', text='Label', 
                    title="⚠️ Worst 10 Toko (Aktivitas Mesin)", 
                    color_discrete_sequence=['#e67e22'] # Warna Oranye
                )
                st.plotly_chart(fig_worst_t, use_container_width=True)
        # --- SUBTAB M3: HEATMAP & UTILITAS ---

        with sub_m3:
            st.subheader("🔥 Heatmap Utilitas Mesin")
            hm_metric = st.selectbox("Metrik Heatmap", ['Jumlah Diaktifkan', 'Kredit yg Digunakan'])
            
            df_heat = df_m.groupby(['Center', 'GT_FINAL'])[hm_metric].sum().reset_index()
            heat_mx = df_heat.pivot(index='Center', columns='GT_FINAL', values=hm_metric).fillna(0)
            
            heat_mx_norm = heat_mx.div(heat_mx.sum(axis=1), axis=0) * 100
            
            fig_h = px.imshow(heat_mx_norm, aspect="auto", color_continuous_scale="YlOrRd", labels=dict(color="Utilitas (%)"))
            fig_h.update_layout(height=600)
            st.plotly_chart(fig_h, use_container_width=True)

        with sub_m4:
            st.header("💡 Matriks Efisiensi (Omset Toko vs Kredit Mesin)")
            if not df_filt.empty:
                df_k_agg = df_filt.groupby(['Folder_Asal', 'Bulan_Key'])['Omset_Paket'].sum().reset_index()
                df_k_agg.rename(columns={'Folder_Asal': 'Center'}, inplace=True)
                df_m_agg = df_m.groupby(['Center', 'GT_FINAL', 'Bulan_Key'])[['Jumlah Diaktifkan', 'Kredit yg Digunakan']].sum().reset_index()
                df_rec = pd.merge(df_m_agg, df_k_agg, on=['Center', 'Bulan_Key'], how='inner')
                
                if not df_rec.empty:
                    df_eff = df_rec.groupby(['Center', 'GT_FINAL']).agg({
                        'Kredit yg Digunakan': 'sum',
                        'Omset_Paket': 'sum',
                        'Jumlah Diaktifkan': 'sum'
                    }).reset_index()
                    
                    df_eff['Ratio'] = df_eff['Omset_Paket'] / df_eff['Kredit yg Digunakan']
                    q33 = df_eff['Ratio'].quantile(0.33)
                    q67 = df_eff['Ratio'].quantile(0.67)
                    
                    def classify(x):
                        if x >= q67: return 'HIGH Efficiency'
                        elif x <= q33: return 'LOW Efficiency'
                        else: return 'NORMAL'
                    
                    df_eff['Status'] = df_eff['Ratio'].apply(classify)
                    
                    sel_cen = st.selectbox("Pilih Center", sorted(df_eff['Center'].unique()))
                    df_scat = df_eff[df_eff['Center'] == sel_cen]
                    
                    fig_eff = px.scatter(
                        df_scat, x='Kredit yg Digunakan', y='Omset_Paket', color='Status',
                        size='Jumlah Diaktifkan', hover_name='GT_FINAL',
                        color_discrete_map={'HIGH Efficiency': 'green', 'NORMAL': 'yellow', 'LOW Efficiency': 'red'}
                    )
                    st.plotly_chart(fig_eff, use_container_width=True)
                else:
                    st.warning("Data irisan tidak cukup.")
            else:
                st.warning("Data Kartu Kosong.")

        # --- SUBTAB 5: DATA MENTAH (BARU) ---
        with sub_m5:
            st.subheader("Detail Data Mesin")
            
            # Konversi ke Excel
            buffer_m = io.BytesIO()
            with pd.ExcelWriter(buffer_m, engine='xlsxwriter') as writer:
                df_m.to_excel(writer, index=False, sheet_name='Data_Mesin')
            
            # Tombol Download
            st.download_button(
                label="📥 Download Excel (.xlsx)",
                data=buffer_m,
                file_name="data_aktivitas_mesin.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
            st.dataframe(df_m, use_container_width=True)

    else:
        st.warning("Data Mesin Kosong untuk periode ini.")

# ================= TAB 4: PENJELASAN TAMBAHAN =================
with tab_help_main:
    st.title("📘 Panduan Membaca Analisis Lanjutan")
    st.markdown("---")

    st.subheader("1. 🔥 Heatmap Utilitas Mesin (Peta Persebaran Aktivitas)")
    st.markdown("""
    **Fungsi Utama:** Memvisualisasikan intensitas penggunaan mesin di berbagai lokasi (Center) dalam satu tampilan kisi (grid) warna.

    **Cara Membaca:**
    * **Sumbu Y (Vertikal):** Nama Toko/Center (misal: Cengkareng, Cipanas).
    * **Sumbu X (Horizontal):** Nama Mesin/Game (misal: Danz Base, Maximum Tune).
    * **Warna:**
        * 🟥 **Merah Tua/Gelap:** Aktivitas sangat tinggi (Mesin Primadona).
        * 🟨 **Kuning/Terang:** Aktivitas sedang atau rendah.
    * **Normalisasi (%):** Data dinormalisasi menjadi persentase agar toko kecil dan toko besar bisa dibandingkan secara adil (proporsi).

    **Insight Bisnis:**
    * **Alokasi Aset:** Mengetahui mesin mana yang "mati" di satu toko tapi "ramai" di toko lain, sehingga bisa dilakukan rotasi unit (mutasi).
    * **Preferensi Lokal:** Mengidentifikasi selera pasar per daerah (misal: Daerah A suka game balapan, Daerah B suka game tembak-tembakan).
    """)
    

    st.markdown("---")

    st.subheader("2. 💡 Matriks Efisiensi (Omset Toko vs. Kredit Mesin)")
    st.markdown("""
    **Fungsi Utama:** Mengevaluasi apakah "biaya" (kredit/listrik/maintenance) yang dikeluarkan oleh sebuah mesin sebanding dengan kontribusinya terhadap keramaian/omset toko. Ini menggunakan *Scatter Plot* (Diagram Tebar).

    **Cara Membaca (Kuadran):** Analisis ini membagi mesin ke dalam 3 status berdasarkan rasio `Total Omset Toko / Total Kredit Mesin`:
    * 🟢 **HIGH Efficiency (Rekomendasi):** Mesin yang menggunakan kredit wajar/sedikit, tetapi berada di toko dengan omset tinggi. Ini adalah mesin yang efisien dan menguntungkan.
    * 🟡 **NORMAL:** Mesin dengan performa standar.
    * 🔴 **LOW Efficiency (Evaluasi):** Mesin yang menyedot banyak kredit (banyak dimainkan), tetapi omset tokonya rendah.
        * *Indikasi:* Mungkin harga per kredit terlalu murah, ada kecurangan (free play), atau mesin ramai tapi tidak menghasilkan pembelian kartu baru.

    **Insight Bisnis:**
    * **Optimasi Harga:** Mesin di zona merah mungkin perlu dinaikkan harga per kreditnya (SWIPE price).
    * **Investigasi:** Mendeteksi anomali di mana mesin sangat aktif bekerja tapi uang tidak masuk ke kasir.
    """)
    

    st.markdown("---")

    st.subheader("3. 🔗 Korelasi Aktivitas Mesin vs. Omset Kartu")
    st.markdown("""
    **Fungsi Utama:** Mengukur seberapa kuat hubungan antara **Keramaian Mesin** (Jumlah main/Kredit) dengan **Uang Masuk** (Omset Paket). Menggunakan *Pearson Correlation Coefficient*.

    **Cara Membaca:**
    * **Trendline (Garis Miring):**
        * Jika garis naik ke kanan atas ↗️: **Korelasi Positif**. Artinya, semakin banyak mesin dimainkan, semakin besar omset toko. (Ini kondisi ideal).
        * Jika garis datar atau turun: Tidak ada hubungan atau hubungan terbalik.
    * **Nilai Korelasi (r):**
        * **Mendekati +1.0:** Hubungan sangat kuat. Aktivitas mesin adalah pendorong utama omset.
        * **Mendekati 0:** Tidak ada hubungan. (Misal: Omset tinggi karena jualan makanan/minuman, bukan karena mesin).

    **Insight Bisnis:**
    * **Validasi Model Bisnis:** Membuktikan bahwa strategi memperbanyak mesin atau kredit gratis benar-benar memancing orang untuk *top-up* uang (Omset).
    * **Forecasting:** Jika kita menargetkan kenaikan omset sekian Rupiah, kita bisa memprediksi berapa minimal aktivitas mesin yang harus dicapai.
    """)