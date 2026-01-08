import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import os
from dotenv import load_dotenv

# ================= KONFIGURASI ENV =================
# Muat variabel dari file .env
load_dotenv()

# Ambil kredensial dari environment variable
# Jika tidak ada di .env (misal lupa buat), pakai default user/pass dummy agar tidak error
ENV_USER = os.getenv("DASHBOARD_USER", "admin")
ENV_PASS = os.getenv("DASHBOARD_PASS", "admin123")

# ================= KONFIGURASI HALAMAN =================
st.set_page_config(
    page_title="Dashboard Transaksi Kartu",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ================= 0. KONFIGURASI LOGIN =================
# Menggunakan data dari .env
USERS = {
    ENV_USER: ENV_PASS
}

# Inisialisasi State Login
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

def check_login(username, password):
    """Fungsi validasi login"""
    if username in USERS and USERS[username] == password:
        st.session_state['logged_in'] = True
        st.success("Login Berhasil!")
        st.rerun() 
    else:
        st.error("Username atau Password salah!")

# ================= 1. HALAMAN LOGIN =================
if not st.session_state['logged_in']:
    st.markdown("<h1 style='text-align: center;'>🔐 Login Dashboard</h1>", unsafe_allow_html=True)
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Masuk")
            
            if submit:
                check_login(username, password)
    
    st.stop() 

# ================= 2. DASHBOARD (LOGIKA ASLI) =================

# --- HELPER FUNCTIONS ---
def format_rupiah(nilai):
    return f"Rp {nilai:,.0f}".replace(',', '.')

def format_singkat_id(nilai):
    if nilai >= 1_000_000_000:
        return f"{nilai/1_000_000_000:.1f} M"
    elif nilai >= 1_000_000:
        return f"{nilai/1_000_000:.0f} Jt"
    elif nilai >= 1_000:
        return f"{nilai/1_000:.0f} Rb"
    else:
        return str(nilai)

# --- LOAD DATA ---
@st.cache_data
def load_data():
    file_path = "CLEAN_DATA_TRANSAKSI_FINAL.xlsx" 
    try:
        df = pd.read_excel(file_path)
        
        # Konversi Tanggal & Numerik
        df['Tanggal'] = pd.to_datetime(df['Tanggal'])
        df['Omset_Paket'] = pd.to_numeric(df['Omset_Paket'], errors='coerce').fillna(0)
        df['Frekuensi'] = pd.to_numeric(df['Frekuensi'], errors='coerce').fillna(0)
        
        # Bersihkan String
        cat_cols = ['Folder_Asal', 'Nama_Toko_Internal', 'Tipe_Grup', 'Kategori_Paket', 'Nominal_Grup', 'Paket']
        for c in cat_cols:
            if c in df.columns:
                df[c] = df[c].astype(str).str.strip()
            
        return df
    except FileNotFoundError:
        return None

df_raw = load_data()

# --- SIDEBAR & LOGOUT ---
# Menampilkan User yang sedang login
st.sidebar.header(f"👋 Halo, {username if 'username' in locals() else 'User'}")

if st.sidebar.button("🚪 Log Out", type="primary"):
    st.session_state['logged_in'] = False
    st.rerun()

st.sidebar.markdown("---")

# --- VISUALISASI UTAMA ---
if df_raw is not None:
    st.sidebar.header("🎛️ Panel Filter")
    
    # Filter Tanggal
    min_date = df_raw['Tanggal'].min().date()
    max_date = df_raw['Tanggal'].max().date()
    
    date_range = st.sidebar.date_input(
        "Pilih Rentang Tanggal",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )
    
    if len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date, end_date = min_date, max_date

    # Helper Filter
    def create_filter(label, column_name):
        if column_name not in df_raw.columns:
            return None
        options = sorted(df_raw[column_name].unique())
        container = st.sidebar.container()
        all_selected = container.checkbox(f"Semua {label}", value=True, key=f"chk_{column_name}")
        
        if all_selected:
            return None
        else:
            return container.multiselect(f"Pilih {label}", options, default=options[:1], key=f"multi_{column_name}")

    st.sidebar.markdown("---")
    
    sel_toko = create_filter("Toko", "Folder_Asal") 
    sel_tipe = create_filter("Tipe Grup", "Tipe_Grup")
    sel_kat = create_filter("Kategori", "Kategori_Paket")
    sel_nom = create_filter("Nominal", "Nominal_Grup")

    df_filtered = df_raw.copy()
    
    df_filtered = df_filtered[
        (df_filtered['Tanggal'].dt.date >= start_date) & 
        (df_filtered['Tanggal'].dt.date <= end_date)
    ]

    if sel_toko: df_filtered = df_filtered[df_filtered['Folder_Asal'].isin(sel_toko)]
    if sel_tipe: df_filtered = df_filtered[df_filtered['Tipe_Grup'].isin(sel_tipe)]
    if sel_kat: df_filtered = df_filtered[df_filtered['Kategori_Paket'].isin(sel_kat)]
    if sel_nom: df_filtered = df_filtered[df_filtered['Nominal_Grup'].isin(sel_nom)]

    st.sidebar.markdown("---")
    st.sidebar.caption("✅ **Cek Data (Validasi)**")
    st.sidebar.info(f"Total Database: {format_rupiah(df_raw['Omset_Paket'].sum())}")
    st.sidebar.success(f"Total Tampil: {format_rupiah(df_filtered['Omset_Paket'].sum())}")

    # Dashboard Content
    st.title("📊 Dashboard Analisis Transaksi Kartu")
    
    col1, col2, col3, col4 = st.columns(4)
    total_omset = df_filtered['Omset_Paket'].sum()
    total_qty = df_filtered['Frekuensi'].sum()
    avg_ticket = total_omset / total_qty if total_qty > 0 else 0
    toko_active = df_filtered['Folder_Asal'].nunique()
    
    col1.metric("Total Omset", format_rupiah(total_omset))
    col2.metric("Total Transaksi", f"{total_qty:,.0f}".replace(',', '.'))
    col3.metric("Rata-rata per Transaksi", format_rupiah(avg_ticket))
    col4.metric("Jumlah Toko Aktif", f"{toko_active}")
    
    st.markdown("---")

    tab1, tab2, tab3 = st.tabs(["📈 Tren & Performa", "🏆 Peringkat", "🔎 Detail Korelasi"])

    with tab1:
        st.subheader("Analisis Tren Waktu")
        c1, c2 = st.columns([1, 3])
        with c1:
            y_axis_val = st.selectbox("Metrik Y-Axis", ['Omset_Paket', 'Frekuensi'])
            color_by = st.selectbox("Kelompokkan Berdasarkan", 
                                  ['Folder_Asal', 'Kategori_Paket', 'Tipe_Grup', 'Nominal_Grup'], 
                                  index=2)
        
        if not df_filtered.empty:
            df_trend = df_filtered.groupby([pd.Grouper(key='Tanggal', freq='ME'), color_by])[y_axis_val].sum().reset_index()
            
            if y_axis_val == 'Omset_Paket':
                df_trend['Label_Text'] = df_trend[y_axis_val].apply(format_rupiah)
                y_label = "Total Omset (Rp)"
            else:
                df_trend['Label_Text'] = df_trend[y_axis_val].apply(lambda x: f"{x:,.0f}".replace(',', '.'))
                y_label = "Jumlah Transaksi"

            fig_line = px.line(
                df_trend, x='Tanggal', y=y_axis_val, color=color_by, markers=True,
                title=f"Tren {y_label} Bulanan", template='plotly_white',
                custom_data=['Label_Text']
            )
            fig_line.update_traces(hovertemplate="<b>%{x|%b %Y}</b><br>%{customdata[0]}")
            fig_line.update_layout(yaxis_title=y_label)
            st.plotly_chart(fig_line, use_container_width=True)
            
            fig_bar = px.bar(
                df_trend, x='Tanggal', y=y_axis_val, color=color_by,
                title=f"Komposisi {y_label} per Bulan", template='plotly_white',
                custom_data=['Label_Text']
            )
            fig_bar.update_traces(hovertemplate="<b>%{x|%b %Y}</b><br>%{customdata[0]}")
            fig_bar.update_layout(yaxis_title=y_label)
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.warning("Data kosong.")

    with tab2:
        st.subheader("Peringkat Performa")
        col_rank_1, col_rank_2 = st.columns(2)
        if not df_filtered.empty:
            with col_rank_1:
                st.markdown("#### 🏆 Top 10 Paket Terlaris")
                df_top_paket = df_filtered.groupby('Paket')[['Omset_Paket', 'Frekuensi']].sum().reset_index()
                df_top_paket = df_top_paket.sort_values('Omset_Paket', ascending=True).tail(10)
                df_top_paket['Label_Bar'] = df_top_paket['Omset_Paket'].apply(format_singkat_id)
                df_top_paket['Label_Tooltip'] = df_top_paket['Omset_Paket'].apply(format_rupiah)
                fig_top_p = px.bar(df_top_paket, x='Omset_Paket', y='Paket', orientation='h', title="Top 10 Paket by Omset", text='Label_Bar', custom_data=['Label_Tooltip'], color_discrete_sequence=['#3366CC'])
                fig_top_p.update_traces(hovertemplate="<b>%{y}</b><br>Omset: %{customdata[0]}<extra></extra>", textposition='outside')
                fig_top_p.update_layout(yaxis={'title': ''}, xaxis={'title': 'Total Omset (Rupiah)', 'showticklabels': False}, showlegend=False)
                st.plotly_chart(fig_top_p, use_container_width=True)
                
            with col_rank_2:
                st.markdown("#### 🏪 Top 10 Toko Terbaik")
                df_top_toko = df_filtered.groupby('Folder_Asal')[['Omset_Paket']].sum().reset_index()
                df_top_toko = df_top_toko.sort_values('Omset_Paket', ascending=True).tail(10)
                df_top_toko['Label_Bar'] = df_top_toko['Omset_Paket'].apply(format_singkat_id)
                df_top_toko['Label_Tooltip'] = df_top_toko['Omset_Paket'].apply(format_rupiah)
                fig_top_t = px.bar(df_top_toko, x='Omset_Paket', y='Folder_Asal', orientation='h', title="Top 10 Toko by Omset", text='Label_Bar', custom_data=['Label_Tooltip'], color_discrete_sequence=['#109618'])
                fig_top_t.update_traces(hovertemplate="<b>%{y}</b><br>Omset: %{customdata[0]}<extra></extra>", textposition='outside')
                fig_top_t.update_layout(yaxis={'title': ''}, xaxis={'title': 'Total Omset (Rupiah)', 'showticklabels': False}, showlegend=False)
                st.plotly_chart(fig_top_t, use_container_width=True)
        else:
            st.warning("Data kosong.")

    with tab3:
        st.subheader("Scatter Plot: Harga vs Volume")
        if not df_filtered.empty:
            df_scatter = df_filtered.groupby(['Paket', 'Kategori_Paket']).agg({'Omset_Paket': 'sum', 'Frekuensi': 'sum'}).reset_index()
            df_scatter = df_scatter[df_scatter['Frekuensi'] > 0]
            df_scatter['Avg_Price'] = df_scatter['Omset_Paket'] / df_scatter['Frekuensi']
            df_scatter['Label_Omset'] = df_scatter['Omset_Paket'].apply(format_rupiah)
            df_scatter['Label_Harga'] = df_scatter['Avg_Price'].apply(format_rupiah)
            
            fig_scatter = px.scatter(df_scatter, x='Frekuensi', y='Omset_Paket', size='Frekuensi', color='Kategori_Paket', hover_name='Paket', custom_data=['Label_Omset', 'Label_Harga'], log_x=True, log_y=True, title="Sebaran Paket: Frekuensi vs Omset (Log Scale)")
            fig_scatter.update_traces(hovertemplate="<b>%{hovertext}</b><br>Omset: %{customdata[0]}<br>Transaksi: %{x}<br>Rata-rata Harga: %{customdata[1]}")
            st.plotly_chart(fig_scatter, use_container_width=True)
            with st.expander("📄 Lihat Data Mentah"):
                st.dataframe(df_filtered)
else:
    st.error("File 'CLEAN_DATA_TRANSAKSI_FINAL.xlsx' tidak ditemukan.")