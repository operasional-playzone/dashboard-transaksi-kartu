import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import os
import io 
from dotenv import load_dotenv
# Pastikan library statsmodels terinstall: pip install statsmodels

# ================= 1. KONFIGURASI HALAMAN (WAJIB DI PALING ATAS) =================
st.set_page_config(
    page_title="Dashboard Transaksi Kartu & Mesin",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ================= 2. KONFIGURASI LOGIN & ENV =================
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

# HALAMAN LOGIN
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

def format_angka(nilai):
    return f"{nilai:,.0f}".replace(',', '.')

def format_singkat_id(nilai):
    if nilai >= 1_000_000_000:
        return f"{nilai/1_000_000_000:.1f} M"
    elif nilai >= 1_000_000:
        return f"{nilai/1_000_000:.0f} Jt"
    elif nilai >= 1_000:
        return f"{nilai/1_000:.0f} Rb"
    else:
        return str(nilai)

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

# ================= 4. LOAD DATA =================
@st.cache_data
def load_data_kartu():
    file_path = "CLEAN_DATA_TRANSAKSI_FINAL.xlsx" 
    try:
        df = pd.read_excel(file_path)
        df['Tanggal'] = pd.to_datetime(df['Tanggal'])
        df['Omset_Paket'] = pd.to_numeric(df['Omset_Paket'], errors='coerce').fillna(0)
        df['Frekuensi'] = pd.to_numeric(df['Frekuensi'], errors='coerce').fillna(0)
        
        # Kolom Waktu
        df['Tahun'] = df['Tanggal'].dt.year.astype(str)
        df['Bulan_Urut'] = df['Tanggal'].dt.month
        # Helper untuk Merge (Bulan-Tahun)
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
    except FileNotFoundError:
        return None

@st.cache_data
def load_data_mesin():
    try:
        df = pd.read_excel("CLEAN_DATA_MESIN_FINAL.xlsx")
        df['Tanggal'] = pd.to_datetime(df['Tanggal'])
        df['Jumlah Diaktifkan'] = pd.to_numeric(df['Jumlah Diaktifkan'], errors='coerce').fillna(0)
        df['Kredit yg Digunakan'] = pd.to_numeric(df['Kredit yg Digunakan'], errors='coerce').fillna(0)
        
        # Kolom Waktu & Key
        df['Tahun'] = df['Tanggal'].dt.year.astype(str)
        df['Bulan_Urut'] = df['Tanggal'].dt.month
        df['Bulan_Key'] = df['Tanggal'].dt.to_period('M').astype(str)
        
        map_bulan_indo = {
            1: 'Januari', 2: 'Februari', 3: 'Maret', 4: 'April', 5: 'Mei', 6: 'Juni',
            7: 'Juli', 8: 'Agustus', 9: 'September', 10: 'Oktober', 11: 'November', 12: 'Desember'
        }
        df['Nama_Bulan'] = df['Bulan_Urut'].map(map_bulan_indo)

        # --- CLEANING STRING ---
        for c in ['Center', 'GT_FINAL', 'Kategori Game']:
            if c in df.columns:
                df[c] = df[c].astype(str).str.strip()

        # --- FILTER EXCLUSION (Hapus Data Kiddieland) ---
        # Data ini dihapus sebelum masuk ke proses apapun di dashboard
        exclusions = [
            'KIDDIE LAND', 
            'KIDDIE LAND 1 JAM', 
            'KIDDIELAND MINI', 
            'KIDDIELAND SEPUASNYA',
            'KIDDIE ZONE 1 JAM'
        ]
        df = df[~df['GT_FINAL'].isin(exclusions)]

        return df
    except FileNotFoundError:
        return None

df_raw = load_data_kartu()
df_mesin = load_data_mesin()

# ================= 5. SIDEBAR & GLOBAL FILTERING =================
st.sidebar.header(f"👋 Halo, Admin")
if st.sidebar.button("🚪 Log Out", type="primary"):
    st.session_state['logged_in'] = False
    st.rerun()
st.sidebar.markdown("---")

# --- INISIALISASI DATA FILTERED ---
df_filt = pd.DataFrame()
df_m = pd.DataFrame()

if df_raw is not None and df_mesin is not None:
    # === FILTER KARTU ===
    st.sidebar.header("🎛️ Filter Data (Kartu)")
    min_d = df_raw['Tanggal'].min().date()
    max_d = df_raw['Tanggal'].max().date()
    date_range = st.sidebar.date_input("Rentang Tanggal (Kartu)", [min_d, max_d], min_value=min_d, max_value=max_d)
    
    st.sidebar.caption("--- Filter Spesifik Kartu ---")
    sel_toko = create_sidebar_filter(df_raw, "Toko", "Folder_Asal", "kartu")
    sel_tipe = create_sidebar_filter(df_raw, "Tipe Grup", "Tipe_Grup", "kartu")
    sel_kat = create_sidebar_filter(df_raw, "Kategori", "Kategori_Paket", "kartu")
    
    # Apply Filter Kartu
    df_filt = df_raw.copy()
    if len(date_range) == 2:
        df_filt = df_filt[(df_filt['Tanggal'].dt.date >= date_range[0]) & (df_filt['Tanggal'].dt.date <= date_range[1])]
    if sel_toko: df_filt = df_filt[df_filt['Folder_Asal'].isin(sel_toko)]
    if sel_tipe: df_filt = df_filt[df_filt['Tipe_Grup'].isin(sel_tipe)]
    if sel_kat: df_filt = df_filt[df_filt['Kategori_Paket'].isin(sel_kat)]

    # === FILTER MESIN ===
    st.sidebar.markdown("---")
    st.sidebar.header("🎛️ Filter Data (Mesin)")
    min_dm = df_mesin['Tanggal'].min().date()
    max_dm = df_mesin['Tanggal'].max().date()
    date_range_m = st.sidebar.date_input("Rentang Tanggal (Mesin)", [min_dm, max_dm], min_value=min_dm, max_value=max_dm)
    
    st.sidebar.caption("--- Filter Spesifik Mesin ---")
    sel_center = create_sidebar_filter(df_mesin, "Toko", "Center", "mesin")
    sel_gt = create_sidebar_filter(df_mesin, "Game", "GT_FINAL", "mesin")
    sel_cat_m = create_sidebar_filter(df_mesin, "Kategori", "Kategori Game", "mesin")

    # Apply Filter Mesin
    df_m = df_mesin.copy()
    if len(date_range_m) == 2:
        df_m = df_m[(df_m['Tanggal'].dt.date >= date_range_m[0]) & (df_m['Tanggal'].dt.date <= date_range_m[1])]
    if sel_center: df_m = df_m[df_m['Center'].isin(sel_center)]
    if sel_gt: df_m = df_m[df_m['GT_FINAL'].isin(sel_gt)]
    if sel_cat_m: df_m = df_m[df_m['Kategori Game'].isin(sel_cat_m)]

else:
    st.error("Gagal memuat data. Pastikan file Excel tersedia.")
    st.stop()

# ================= 6. LAYOUT UTAMA =================
st.title("📊 RAMAYANA ANALYTICS DASHBOARD")

# Main Tabs (Updated: Removed Recommendation from Main, moved to Mesin Subtab)
tab_kartu_main, tab_mesin_main, tab_corr_main = st.tabs([
    "💳 Dashboard Omset Kartu",
    "🎮 Dashboard Mesin",
    "🔗 Analisis Korelasi"
])

# ==============================================================================
#                               TAB 1: KARTU
# ==============================================================================
with tab_kartu_main:
    if not df_filt.empty:
        # KPI Cards
        st.markdown("### Ringkasan Transaksi Kartu")
        c1, c2, c3, c4 = st.columns(4)
        omset = df_filt['Omset_Paket'].sum()
        qty = df_filt['Frekuensi'].sum()
        avg = omset / qty if qty > 0 else 0
        tokos = df_filt['Folder_Asal'].nunique()
        
        c1.metric("Total Omset", format_rupiah(omset))
        c2.metric("Total Transaksi", f"{qty:,.0f}".replace(',', '.'))
        c3.metric("Rata-rata Transaksi", format_rupiah(avg))
        c4.metric("Toko Aktif", f"{tokos}")
        st.markdown("---")

        subtab1, subtab2, subtab3, subtab4 = st.tabs(["📈 Tren & Performa", "⚖️ Komparasi 2024 vs 2025", "🏆 Peringkat", "🔎 Detail"])

        with subtab1:
            st.subheader("Analisis Tren Waktu")
            col1, col2 = st.columns([1, 3])
            with col1:
                y_val = st.selectbox("Metrik Y-Axis", ['Omset_Paket', 'Frekuensi'], key="y_val_kartu")
                grp_col = st.selectbox("Grouping", ['Folder_Asal', 'Kategori_Paket', 'Tipe_Grup', 'Nominal_Grup'], index=2, key="grp_kartu")
            
            df_trend = df_filt.groupby([pd.Grouper(key='Tanggal', freq='ME'), grp_col])[y_val].sum().reset_index()
            if y_val == 'Omset_Paket':
                df_trend['Label'] = df_trend[y_val].apply(format_rupiah)
            else:
                df_trend['Label'] = df_trend[y_val].apply(format_angka)

            fig_line = px.line(df_trend, x='Tanggal', y=y_val, color=grp_col, markers=True, title=f"Tren Bulanan", template='plotly_white', custom_data=['Label'])
            fig_line.update_traces(hovertemplate="<b>%{x|%b %Y}</b><br>%{customdata[0]}")
            st.plotly_chart(fig_line, use_container_width=True)
            
            fig_bar = px.bar(df_trend, x='Tanggal', y=y_val, color=grp_col, title=f"Komposisi Bulanan", template='plotly_white', custom_data=['Label'])
            fig_bar.update_traces(hovertemplate="<b>%{x|%b %Y}</b><br>%{customdata[0]}")
            st.plotly_chart(fig_bar, use_container_width=True)

            # Pie Chart Kartu
            st.markdown("### 🍰 Proporsi Omset per Toko")
            df_pie = df_filt.groupby('Folder_Asal')['Omset_Paket'].sum().reset_index()
            if not df_pie.empty:
                fig_pie = px.pie(df_pie, values='Omset_Paket', names='Folder_Asal', title='Kontribusi Omset Kartu per Toko', hole=0.4)
                st.plotly_chart(fig_pie, use_container_width=True)

        with subtab2:
            st.subheader("Analisis Komparasi Tahun")
            df_comp = df_filt[df_filt['Tahun'].isin(['2024', '2025'])].copy()
            if not df_comp.empty:
                c1, c2 = st.columns(2)
                with c1:
                    df_y = df_comp.groupby('Tahun')['Omset_Paket'].sum().reset_index()
                    val24 = df_y[df_y['Tahun']=='2024']['Omset_Paket'].sum()
                    val25 = df_y[df_y['Tahun']=='2025']['Omset_Paket'].sum()
                    growth = ((val25 - val24)/val24)*100 if val24 > 0 else 0
                    
                    df_y['Label'] = df_y['Omset_Paket'].apply(format_singkat_id)
                    fig_tot = px.bar(df_y, x='Tahun', y='Omset_Paket', text='Label', color='Tahun', title=f'Total Omset ({growth:+.2f}%)', color_discrete_map={'2024':'#bdc3c7', '2025':'#27ae60'})
                    st.plotly_chart(fig_tot, use_container_width=True)
                with c2:
                    df_mth = df_comp.groupby(['Tahun','Bulan_Urut','Nama_Bulan'])['Omset_Paket'].sum().reset_index().sort_values(['Tahun','Bulan_Urut'])
                    fig_line_yoy = px.line(df_mth, x='Nama_Bulan', y='Omset_Paket', color='Tahun', markers=True, title='Tren YoY', color_discrete_map={'2024':'gray', '2025':'green'})
                    st.plotly_chart(fig_line_yoy, use_container_width=True)
            else:
                st.info("Data 2024/2025 tidak tersedia.")

       # --- SUBTAB 3 (KARTU) ---
        with subtab3:
            st.subheader("Peringkat Performa")
            
            # 1. Selector Metrik (Omset vs Frekuensi)
            rank_mode = st.radio(
                "Urutkan Peringkat Berdasarkan:",
                ['Total Omset', 'Jumlah Transaksi'],
                horizontal=True,
                key='rank_mode_kartu'
            )

            # Tentukan Kolom & Formatter berdasarkan pilihan
            if rank_mode == 'Total Omset':
                col_rank = 'Omset_Paket'
                fmt_func = format_singkat_id
                color_top = '#2980b9' # Biru
            else:
                col_rank = 'Frekuensi'
                fmt_func = lambda x: f"{x:,.0f}".replace(',', '.')
                color_top = '#8e44ad' # Ungu

            st.markdown("---")

            # --- BAGIAN 1: KATEGORI PAKET ---
            st.markdown(f"#### 📦 Analisis Kategori Paket (by {rank_mode})")
            
            # Agregasi Data Kategori
            df_cat = df_filt.groupby('Kategori_Paket')[col_rank].sum().reset_index()
            
            c1, c2 = st.columns(2)
            
            with c1: # Top Kategori
                top_cat = df_cat.sort_values(col_rank, ascending=True).tail(10)
                top_cat['Label'] = top_cat[col_rank].apply(fmt_func)
                
                fig_p = px.bar(
                    top_cat, x=col_rank, y='Kategori_Paket', 
                    orientation='h', text='Label', 
                    title=f"🔥 Top 10 Kategori Tertinggi",
                    template='plotly_white',
                    color_discrete_sequence=[color_top]
                )
                fig_p.update_traces(textposition='outside')
                fig_p.update_layout(yaxis_title="", xaxis_title="")
                st.plotly_chart(fig_p, use_container_width=True)
            
            with c2: # Worst Kategori
                worst_cat = df_cat.sort_values(col_rank, ascending=True).head(10)
                worst_cat['Label'] = worst_cat[col_rank].apply(fmt_func)
                
                fig_w = px.bar(
                    worst_cat, x=col_rank, y='Kategori_Paket', 
                    orientation='h', text='Label', 
                    title=f"❄️ Bottom 10 Kategori Terendah",
                    template='plotly_white',
                    color_discrete_sequence=['#c0392b'] # Merah
                )
                fig_w.update_traces(textposition='outside')
                fig_w.update_layout(yaxis_title="", xaxis_title="")
                st.plotly_chart(fig_w, use_container_width=True)

            st.markdown("---")

            # --- BAGIAN 2: TOKO ---
            st.markdown(f"#### 🏪 Analisis Toko (by {rank_mode})")
            
            # Agregasi Data Toko
            df_toko = df_filt.groupby('Folder_Asal')[col_rank].sum().reset_index()

            c3, c4 = st.columns(2)

            with c3: # Top Toko
                top_tk = df_toko.sort_values(col_rank, ascending=True).tail(10)
                top_tk['Label'] = top_tk[col_rank].apply(fmt_func)
                
                fig_t = px.bar(
                    top_tk, x=col_rank, y='Folder_Asal', 
                    orientation='h', text='Label', 
                    title=f"🏆 Top 10 Toko Terbaik",
                    template='plotly_white',
                    color_discrete_sequence=['#27ae60'] # Hijau
                )
                fig_t.update_traces(textposition='outside')
                fig_t.update_layout(yaxis_title="Toko", xaxis_title="")
                st.plotly_chart(fig_t, use_container_width=True)

            with c4: # Worst Toko
                worst_tk = df_toko.sort_values(col_rank, ascending=True).head(10)
                worst_tk['Label'] = worst_tk[col_rank].apply(fmt_func)
                
                fig_wt = px.bar(
                    worst_tk, x=col_rank, y='Folder_Asal', 
                    orientation='h', text='Label', 
                    title=f"⚠️ Bottom 10 Toko Terendah",
                    template='plotly_white',
                    color_discrete_sequence=['#e67e22'] # Oranye
                )
                fig_wt.update_traces(textposition='outside')
                fig_wt.update_layout(yaxis_title="Toko", xaxis_title="")
                st.plotly_chart(fig_wt, use_container_width=True)

        with subtab4:
            st.subheader("Detail Data")
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df_filt.to_excel(writer, index=False, sheet_name='Data_Transaksi')
            st.download_button("📥 Download Excel", buffer, "data_transaksi.xlsx")
            st.dataframe(df_filt)
    else:
        st.warning("Data Kartu Kosong (Cek Filter).")

# ==============================================================================
#                               TAB 2: MESIN
# ==============================================================================
with tab_mesin_main:
    if not df_m.empty:
        st.markdown("### 📊 KPI Aktivitas Mesin")
        k1, k2, k3, k4 = st.columns(4)
        total_act = df_m['Jumlah Diaktifkan'].sum()
        total_crd = df_m['Kredit yg Digunakan'].sum()
        avg_crd = total_crd / total_act if total_act > 0 else 0
        mesin_active = df_m['GT_FINAL'].nunique()
        
        k1.metric("Total Aktivasi", format_angka(total_act))
        k2.metric("Total Kredit", format_angka(total_crd))
        k3.metric("Rata-rata Kredit/Aktivasi", f"{avg_crd:,.2f}")
        k4.metric("Mesin Aktif", f"{mesin_active}")
        
        with st.expander("📍 KPI per Center"):
            st.dataframe(df_m.groupby('Center')[['Jumlah Diaktifkan','Kredit yg Digunakan']].sum().reset_index(), use_container_width=True)
        st.markdown("---")

        # UPDATE: Tambahkan Subtab Rekomendasi (Index 5)
        subtab_m1, subtab_m2, subtab_m3, subtab_m4, subtab_m5, subtab_m6 = st.tabs([
            "📈 Tren & Performa", 
            "⚖️ Komparasi 2024 vs 2025", 
            "🏆 Peringkat Mesin", 
            "🔥 Utilitas Mesin",
            "💡 Rekomendasi & Efisiensi",
            "🔎 Detail Data"
        ])

        with subtab_m1:
            st.subheader("Analisis Tren Mesin")
            c1, c2 = st.columns(2)
            with c1: y_metric = st.selectbox("Metrik Mesin", ['Jumlah Diaktifkan', 'Kredit yg Digunakan'], key="y_mesin")
            with c2: 
                map_col = {'Game': 'GT_FINAL', 'Toko': 'Center', 'Kategori': 'Kategori Game'}
                grp_lbl = st.selectbox("Kelompokkan", list(map_col.keys()))
                grp_col = map_col[grp_lbl]
            
            df_plot = df_m.groupby([pd.Grouper(key='Tanggal', freq='ME'), grp_col])[y_metric].sum().reset_index()
            df_plot['Label'] = df_plot[y_metric].apply(format_angka)
            
            fig_m = px.line(df_plot, x='Tanggal', y=y_metric, color=grp_col, markers=True, title=f"Tren {y_metric}", template='plotly_white', custom_data=['Label'])
            fig_m.update_traces(hovertemplate="<b>%{x|%b %Y}</b><br>%{customdata[0]}")
            st.plotly_chart(fig_m, use_container_width=True)
            
            fig_bm = px.bar(df_plot, x='Tanggal', y=y_metric, color=grp_col, title=f"Komposisi {y_metric}", template='plotly_white', custom_data=['Label'])
            fig_bm.update_traces(hovertemplate="<b>%{x|%b %Y}</b><br>%{customdata[0]}")
            st.plotly_chart(fig_bm, use_container_width=True)

            # Pie Chart
            st.markdown("### 🍰 Proporsi Aktivitas Mesin")
            metric_pie = st.radio("Metrik Pie Chart", ['Jumlah Diaktifkan', 'Kredit yg Digunakan'], horizontal=True)
            c_p1, c_p2 = st.columns(2)
            with c_p1:
                df_p1 = df_m.groupby('Center')[metric_pie].sum().reset_index()
                st.plotly_chart(px.pie(df_p1, values=metric_pie, names='Center', title="Kontribusi per Toko", hole=0.4), use_container_width=True)
            with c_p2:
                df_p2 = df_m.groupby('GT_FINAL')[metric_pie].sum().sort_values(ascending=False).head(10).reset_index()
                st.plotly_chart(px.pie(df_p2, values=metric_pie, names='GT_FINAL', title="Top 10 Game", hole=0.4), use_container_width=True)

        with subtab_m2:
            st.subheader("Komparasi Tahun (Mesin)")
            met_comp = st.selectbox("Metrik Komparasi", ['Jumlah Diaktifkan', 'Kredit yg Digunakan'])
            df_mc = df_m[df_m['Tahun'].isin(['2024','2025'])].copy()
            if not df_mc.empty:
                c1, c2 = st.columns(2)
                with c1:
                    df_yc = df_mc.groupby('Tahun')[met_comp].sum().reset_index()
                    val24m = df_yc[df_yc['Tahun']=='2024'][met_comp].sum() if '2024' in df_yc['Tahun'].values else 0
                    val25m = df_yc[df_yc['Tahun']=='2025'][met_comp].sum() if '2025' in df_yc['Tahun'].values else 0
                    growthm = ((val25m-val24m)/val24m)*100 if val24m > 0 else 0
                    df_yc['Label'] = df_yc[met_comp].apply(format_singkat_id)
                    st.plotly_chart(px.bar(df_yc, x='Tahun', y=met_comp, text='Label', color='Tahun', title=f"Total ({growthm:+.2f}%)", color_discrete_map={'2024':'#bdc3c7','2025':'#27ae60'}), use_container_width=True)
                with c2:
                    df_mthm = df_mc.groupby(['Tahun','Bulan_Urut','Nama_Bulan'])[met_comp].sum().reset_index().sort_values(['Tahun','Bulan_Urut'])
                    st.plotly_chart(px.line(df_mthm, x='Nama_Bulan', y=met_comp, color='Tahun', markers=True, title="Tren YoY", color_discrete_map={'2024':'gray','2025':'green'}), use_container_width=True)
            else:
                st.info("Data 2024/2025 Kosong.")

        with subtab_m3:
            st.markdown("### 🏆 Top & Worst 10 Mesin")
            df_rank = df_m.groupby('GT_FINAL')[['Jumlah Diaktifkan', 'Kredit yg Digunakan']].sum().reset_index()
            rank_met = st.radio("Peringkat Berdasarkan", ['Jumlah Diaktifkan', 'Kredit yg Digunakan'], horizontal=True)
            
            top10 = df_rank.sort_values(rank_met, ascending=False).head(10).sort_values(rank_met)
            worst10 = df_rank.sort_values(rank_met, ascending=True).head(10)
            
            c1, c2 = st.columns(2)
            with c1:
                top10['Label'] = top10[rank_met].apply(format_angka)
                fig_t = px.bar(top10, x=rank_met, y='GT_FINAL', orientation='h', text='Label', title=f"🔥 Top 10 Mesin", template='plotly_white')
                fig_t.update_layout(yaxis_title="")
                st.plotly_chart(fig_t, use_container_width=True)
            with c2:
                worst10['Label'] = worst10[rank_met].apply(format_angka)
                fig_w = px.bar(worst10, x=rank_met, y='GT_FINAL', orientation='h', text='Label', title=f"❄️ Worst 10 Mesin", template='plotly_white')
                fig_w.update_layout(yaxis_title="")
                st.plotly_chart(fig_w, use_container_width=True)

        with subtab_m4:
            st.markdown("### 🔥 Heatmap Utilitas Mesin")
            util_met = st.radio("Utilitas berdasarkan", ['Jumlah Diaktifkan', 'Kredit yg Digunakan'], horizontal=True, key="heat_met")
            df_heat = df_m.groupby(['Center', 'GT_FINAL'])[util_met].sum().reset_index()
            heat_mx = df_heat.pivot(index='Center', columns='GT_FINAL', values=util_met).fillna(0)
            
            if st.checkbox("Normalisasi (0-100%)", value=True):
                heat_mx = heat_mx.div(heat_mx.sum(axis=1), axis=0) * 100
                lbl = "Utilitas (%)"
            else:
                lbl = util_met
                
            fig_h = px.imshow(heat_mx, aspect="auto", color_continuous_scale="YlOrRd", labels=dict(color=lbl), title=f"Heatmap - {util_met}")
            fig_h.update_layout(height=600)
            st.plotly_chart(fig_h, use_container_width=True)
            
            if st.checkbox("Fokus 1 Center"):
                cfocus = st.selectbox("Pilih Center", heat_mx.index)
                st.dataframe(heat_mx.loc[[cfocus]].T.sort_values(by=cfocus, ascending=False), use_container_width=True)

        with subtab_m5:
            st.header("💡 Rekomendasi & Efisiensi Mesin")
            st.markdown("""
            Analisis ini menghitung **Index Efisiensi** per mesin dengan rumus:  
            `Total Omset Center / Total Kredit Mesin`.  
            *Semakin rendah kredit yang digunakan mesin di toko ber-omset tinggi, semakin tinggi indexnya (mesin "numpang" di toko bagus).*
            """)

            if not df_filt.empty:
                # 1. Agregasi Data Kartu (Omset) per Center & Bulan
                df_k_agg = df_filt.groupby(['Folder_Asal', 'Bulan_Key'])['Omset_Paket'].sum().reset_index()
                df_k_agg.rename(columns={'Folder_Asal': 'Center'}, inplace=True)

                # 2. Agregasi Data Mesin per Center, Game, Bulan
                df_m_agg = df_m.groupby(['Center', 'GT_FINAL', 'Bulan_Key'])[['Jumlah Diaktifkan', 'Kredit yg Digunakan']].sum().reset_index()

                # 3. Merge (Inner Join)
                df_rec = pd.merge(df_m_agg, df_k_agg, on=['Center', 'Bulan_Key'], how='inner')

                if not df_rec.empty:
                    # 4. Hitung Efisiensi per Game
                    df_eff = (
                        df_rec
                        .groupby(['Center', 'GT_FINAL'])
                        .agg(
                            total_kredit=('Kredit yg Digunakan', 'sum'),
                            total_omset=('Omset_Paket', 'sum'),
                            total_aktivasi=('Jumlah Diaktifkan', 'sum')
                        )
                        .reset_index()
                    )

                    # Hitung Index (Hindari pembagian nol)
                    df_eff = df_eff[df_eff['total_kredit'] > 0]
                    df_eff['Index_Efisiensi'] = (df_eff['total_omset'] / df_eff['total_kredit']).round(2)

                    # 5. Klasifikasi
                    q_low = df_eff['Index_Efisiensi'].quantile(0.33)
                    q_high = df_eff['Index_Efisiensi'].quantile(0.67)

                    def klasifikasi(row):
                        if row['Index_Efisiensi'] >= q_high: return 'REKOMENDASI (High Efficiency)'
                        elif row['Index_Efisiensi'] <= q_low: return 'EVALUASI (Low Efficiency)'
                        else: return 'NORMAL'

                    df_eff['Status'] = df_eff.apply(klasifikasi, axis=1)

                    # 6. UI Filters & Display
                    st.markdown("---")
                    center_sel = st.selectbox("Pilih Center untuk Analisis Detail", sorted(df_eff['Center'].unique()))

                    df_center_rec = df_eff[df_eff['Center'] == center_sel].sort_values('Index_Efisiensi', ascending=False)

                    c_rec1, c_rec2 = st.columns(2)
                    with c_rec1:
                        st.markdown("### ⭐ Mesin Paling Direkomendasikan")
                        st.dataframe(df_center_rec.head(5)[['GT_FINAL', 'total_kredit', 'Index_Efisiensi', 'Status']], use_container_width=True)

                    with c_rec2:
                        st.markdown("### ⚠️ Mesin Perlu Evaluasi")
                        st.dataframe(df_center_rec.tail(5)[['GT_FINAL', 'total_kredit', 'Index_Efisiensi', 'Status']], use_container_width=True)

                    st.markdown("### 🗺️ Peta Sebaran Efisiensi")
                    fig_eff = px.scatter(
                        df_center_rec,
                        x='total_kredit',
                        y='total_omset',
                        size='total_aktivasi',
                        color='Status',
                        hover_name='GT_FINAL',
                        title=f'Matriks Efisiensi — {center_sel}',
                        template='plotly_white',
                        color_discrete_map={
                            'REKOMENDASI (High Efficiency)': '#27ae60',
                            'NORMAL': '#f1c40f',
                            'EVALUASI (Low Efficiency)': '#e74c3c'
                        }
                    )
                    fig_eff.update_layout(xaxis_title='Total Kredit Mesin', yaxis_title='Total Omset Toko')
                    st.plotly_chart(fig_eff, use_container_width=True)
                    
                    with st.expander("Lihat Data Lengkap Efisiensi"):
                        st.dataframe(df_eff)
                else:
                    st.warning("Irisan data (Kartu & Mesin) tidak cukup untuk analisis ini.")
            else:
                st.info("Mohon filter data kartu juga.")

        with subtab_m6:
            st.subheader("Detail Data Mesin")
            buffer_m = io.BytesIO()
            with pd.ExcelWriter(buffer_m, engine='xlsxwriter') as writer:
                df_m.to_excel(writer, index=False, sheet_name='Data_Mesin')
            st.download_button("📥 Download Excel", buffer_m, "data_mesin.xlsx")
            st.dataframe(df_m)
    else:
        st.warning("Data Mesin Kosong (Cek Filter).")

# ==============================================================================
#                               TAB 3: KORELASI
# ==============================================================================
with tab_corr_main:
    st.header("🔗 Korelasi Aktivitas Mesin vs Omset Kartu")
    if not df_filt.empty and not df_m.empty:
        df_k_agg = df_filt.groupby(['Folder_Asal', 'Bulan_Key'])['Omset_Paket'].sum().reset_index()
        df_k_agg.rename(columns={'Folder_Asal': 'Center'}, inplace=True) 
        
        df_m_agg = df_m.groupby(['Center', 'Bulan_Key'])[['Jumlah Diaktifkan', 'Kredit yg Digunakan']].sum().reset_index()
        
        df_corr = pd.merge(df_k_agg, df_m_agg, on=['Center', 'Bulan_Key'], how='inner')
        
        if not df_corr.empty:
            x_metric = st.radio("Pilih Aktivitas Mesin (X)", ['Jumlah Diaktifkan', 'Kredit yg Digunakan'], horizontal=True)
            
            c1, c2 = st.columns([3, 1])
            with c1:
                fig_c = px.scatter(df_corr, x=x_metric, y='Omset_Paket', color='Center', trendline='ols', title=f"Scatter: {x_metric} vs Omset", template='plotly_white')
                st.plotly_chart(fig_c, use_container_width=True)
            with c2:
                corr_val = df_corr[[x_metric, 'Omset_Paket']].corr().iloc[0,1]
                st.metric("Korelasi (Pearson)", f"{corr_val:.2f}")
                st.markdown("### Per Center")
                try:
                    corr_cen = df_corr.groupby('Center').apply(lambda x: x[[x_metric,'Omset_Paket']].corr().iloc[0,1]).reset_index(name='Corr').sort_values('Corr', ascending=False)
                    st.dataframe(corr_cen, use_container_width=True)
                except:
                    st.info("Data tidak cukup.")
        else:
            st.warning("Irisan data tidak ditemukan.")
    else:
        st.info("Data belum lengkap.")