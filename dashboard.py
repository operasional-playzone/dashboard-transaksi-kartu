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

# Helper Filter Lokal (Non-Sidebar)
def create_local_filter(df, label, col_name, key_prefix):
    if col_name not in df.columns: return []
    options = sorted(df[col_name].dropna().unique())
    return st.multiselect(f"Filter {label}", options, default=[], key=f"loc_{key_prefix}_{col_name}", placeholder="Semua (Kosongkan untuk memilih semua)")

def create_sidebar_filter(df, label, col_name, key_prefix):
    if col_name not in df.columns: return None
    options = sorted(df[col_name].dropna().unique())
    
    pilih_semua = st.checkbox(f"✅ Pilih Semua {label}", value=False, key=f"all_{key_prefix}_{col_name}")
    
    if pilih_semua:
        st.multiselect(f"Filter {label}", options, default=options, disabled=True, key=f"dis_{key_prefix}_{col_name}")
        return [] 
    else:
        return st.multiselect(f"Filter {label}", options, default=options[:1], key=f"sel_{key_prefix}_{col_name}")

# ================= 4. LOAD DATA =================
@st.cache_data(ttl=600)
def load_data_kartu():
    file_path = os.path.join("output", "CLEAN_DATA_TRANSAKSI_FINAL_V3.xlsx")
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
    file_path = os.path.join("output", "dashboard_in_scope_compact_v2.xlsx")
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

        # --- EXCLUSION FILTER ---
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

# ================= 5. SIDEBAR (GLOBAL FILTER) =================
st.sidebar.header(f"👋 Halo, Admin")
if st.sidebar.button("🚪 Log Out", type="primary"):
    st.session_state['logged_in'] = False
    st.rerun()
st.sidebar.markdown("---")

df_filt = pd.DataFrame()
df_m = pd.DataFrame()

if df_raw is not None and df_mesin is not None:
    with st.sidebar.form("filter_form"):
        st.header("🎛️ Filter Global")
        st.caption("Filter ini berlaku untuk SEMUA Dashboard.")
        
        # 1. Filter Tanggal
        all_dates = pd.concat([df_raw['Tanggal'], df_mesin['Tanggal']])
        min_date = all_dates.min()
        max_date = all_dates.max()
        month_range = pd.date_range(start=min_date, end=max_date, freq='MS')
        month_labels = [d.strftime('%b %Y') for d in month_range]
        
        selected_range = st.select_slider(
            "🗓️ Pilih Rentang Bulan:",
            options=month_labels,
            value=(month_labels[0], month_labels[-1])
        )
        
        st.markdown("---")
        # 2. Filter Toko
        toko_kartu = set(df_raw['Folder_Asal'].unique())
        toko_mesin = set(df_mesin['Center'].unique())
        all_tokos = sorted(list(toko_kartu.union(toko_mesin)))
        
        pilih_semua_toko = st.checkbox("✅ Pilih Semua Toko", value=False)
        if pilih_semua_toko:
            sel_toko_global = [] 
            st.multiselect("Pilih Toko", all_tokos, default=all_tokos, disabled=True)
        else:
            sel_toko_global = st.multiselect("Pilih Toko", all_tokos, default=all_tokos[:1])

        submitted = st.form_submit_button("🚀 Terapkan Filter Global")

    # LOGIKA FILTERING
    start_label, end_label = selected_range
    start_date_filter = month_range[month_labels.index(start_label)]
    end_date_start = month_range[month_labels.index(end_label)]
    end_date_filter = end_date_start + relativedelta(months=1, days=-1)

    # Filter Kartu
    df_filt = df_raw[
        (df_raw['Tanggal'] >= start_date_filter) & 
        (df_raw['Tanggal'] <= end_date_filter)
    ].copy()
    if sel_toko_global:
        df_filt = df_filt[df_filt['Folder_Asal'].isin(sel_toko_global)]

    # Filter Mesin
    df_m = df_mesin[
        (df_mesin['Tanggal'] >= start_date_filter) & 
        (df_mesin['Tanggal'] <= end_date_filter)
    ].copy()
    if sel_toko_global:
        df_m = df_m[df_m['Center'].isin(sel_toko_global)]

    st.sidebar.info(f"📅 Data: {start_label} - {end_label}")

else:
    st.error("Gagal memuat data.")
    st.stop()

# ================= 6. LAYOUT UTAMA =================
st.title("📊 RAMAYANA ANALYTICS DASHBOARD")

tab_kartu_main, tab_mesin_main, tab_help_main = st.tabs([
    "💳 Pendapatan Kartu",
    "🎮 Dashboard Mesin",
    "ℹ️ Penjelasan Tambahan"
])

# --- TAB 1: KARTU ---
with tab_kartu_main:
    if not df_filt.empty:
        # FILTER LOKAL
        with st.expander("🔎 Filter Spesifik Kartu (Tipe & Kategori)", expanded=False):
            with st.form("form_filter_kartu"):
                st.caption("Pilih filter di bawah, lalu klik 'Terapkan Filter Kartu'")
                c_f1, c_f2 = st.columns(2)
                with c_f1:
                    f_tipe = create_local_filter(df_filt, "Tipe Grup", "Tipe_Grup", "kartu_loc")
                with c_f2:
                    f_kat = create_local_filter(df_filt, "Kategori Paket", "Kategori_Paket", "kartu_loc")
                
                submitted_kartu = st.form_submit_button("🚀 Terapkan Filter Kartu")
            
            if f_tipe: df_filt = df_filt[df_filt['Tipe_Grup'].isin(f_tipe)]
            if f_kat: df_filt = df_filt[df_filt['Kategori_Paket'].isin(f_kat)]

        # KPI
        c1, c2, c3, c4 = st.columns(4)
        omset = df_filt['Total_Sales'].sum()
        qty = df_filt['Jumlah_Dibeli'].sum()
        avg = omset / qty if qty > 0 else 0
        tokos = df_filt['Folder_Asal'].nunique()
        
        c1.metric("Total Sales", format_rupiah(omset))
        c2.metric("Total Transaksi", format_id(qty))
        c3.metric("Rata-rata", format_rupiah(avg))
        c4.metric("Toko Aktif", f"{tokos}")
        st.markdown("---")

        subtab1, subtab2, subtab3 = st.tabs(["📈 Analisis Tren & YoY", "🏆 Peringkat & Detail", "🔎 Data Mentah"])

        with subtab1:
            urutan_bulan = ['Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni','Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember']
            c_left, c_right = st.columns(2)
            
            with c_left:
                st.subheader("Total Pendapatan Tahunan")
                df_yearly = df_filt.groupby('Tahun')['Total_Sales'].sum().reset_index()
                val24 = df_yearly[df_yearly['Tahun']=='2024']['Total_Sales'].sum() if '2024' in df_yearly['Tahun'].values else 0
                val25 = df_yearly[df_yearly['Tahun']=='2025']['Total_Sales'].sum() if '2025' in df_yearly['Tahun'].values else 0
                growth = ((val25 - val24) / val24) * 100 if val24 > 0 else 0
                
                df_yearly['Label'] = df_yearly['Total_Sales'].apply(format_label_chart)
                
                fig_total = px.bar(
                    df_yearly, x='Tahun', y='Total_Sales', text='Label', 
                    title=f'Growth: {growth:.2f}%', 
                    color='Tahun', color_discrete_map={'2024': '#bdc3c7', '2025': '#27ae60'}
                )
                fig_total.update_yaxes(showticklabels=False, visible=False)
                fig_total.update_layout(separators=',.')
                st.plotly_chart(fig_total, use_container_width=True)

            with c_right:
                st.subheader("Tren Pendapatan Bulanan (YoY)")
                df_trend = df_filt.groupby(['Tahun', 'Bulan_Urut', 'Nama_Bulan'])['Total_Sales'].sum().reset_index().sort_values(['Tahun', 'Bulan_Urut'])
                df_trend['Label_Text'] = df_trend['Total_Sales'].apply(format_label_chart)
                
                fig_trend = px.line(
                    df_trend, x='Nama_Bulan', y='Total_Sales', color='Tahun', 
                    markers=True, text='Label_Text', 
                    color_discrete_map={'2024': 'gray', '2025': 'green'}, 
                    category_orders={"Nama_Bulan": urutan_bulan}
                )
                fig_trend.update_traces(textposition="top center")
                fig_trend.update_yaxes(showticklabels=False, visible=False)
                fig_trend.update_layout(separators=',.')
                st.plotly_chart(fig_trend, use_container_width=True)

            st.markdown("---")
            st.subheader("📈 Tren Pendapatan Jangka Panjang")
            df_cont = df_filt.groupby('Tanggal')['Total_Sales'].sum().reset_index().sort_values('Tanggal')
            
            fig_cont = px.line(
                df_cont, x='Tanggal', y='Total_Sales', markers=True, 
                title="Pergerakan Pendapatan (Timeline Lengkap)", line_shape='linear'
            )
            fig_cont.update_xaxes(dtick="M1", tickformat="%b %Y", tickangle=-45)
            fig_cont.update_traces(line_color='#2ecc71', line_width=3)
            fig_cont.update_yaxes(tickformat=',.0f') 
            fig_cont.update_layout(separators=',.')
            st.plotly_chart(fig_cont, use_container_width=True)

            st.markdown("---")
            st.markdown("### 🍰 Proporsi Pendapatan per Toko")
            df_pie = df_filt.groupby('Folder_Asal')['Total_Sales'].sum().reset_index()
            fig_pie = px.pie(df_pie, values='Total_Sales', names='Folder_Asal', hole=0.4, title="Kontribusi Pendapatan Kartu per Toko")
            fig_pie.update_layout(separators=',.')
            st.plotly_chart(fig_pie, use_container_width=True)

        with subtab2:
            st.subheader("Peringkat Performa: Top & Worst")
            rank_mode = st.radio("Urutkan Berdasarkan:", ['Total Sales', 'Jumlah Transaksi'], horizontal=True)
            col_rank = 'Total_Sales' if rank_mode == 'Total Sales' else 'Jumlah_Dibeli'
            fmt_func = format_label_chart if rank_mode == 'Total Sales' else format_id

            c1, c2 = st.columns(2)
            # GROUP BY TIPE GRUP (SESUAI REQUEST)
            df_cat = df_filt.groupby('Tipe_Grup')[col_rank].sum().reset_index()
            
            with c1:
                df_cat_top = df_cat.sort_values(col_rank, ascending=True).tail(10)
                df_cat_top['Label'] = df_cat_top[col_rank].apply(fmt_func)
                fig_cat_t = px.bar(df_cat_top, x=col_rank, y='Tipe_Grup', orientation='h', text='Label', title="🏆 Top Kategori (Tipe Grup)", color_discrete_sequence=['#2980b9'])
                fig_cat_t.update_xaxes(showticklabels=False)
                st.plotly_chart(fig_cat_t, use_container_width=True)
            with c2:
                df_cat_worst = df_cat.sort_values(col_rank, ascending=False).tail(10)
                df_cat_worst['Label'] = df_cat_worst[col_rank].apply(fmt_func)
                fig_cat_w = px.bar(df_cat_worst, x=col_rank, y='Tipe_Grup', orientation='h', text='Label', title="⚠️ Bottom Kategori (Tipe Grup)", color_discrete_sequence=['#c0392b'])
                fig_cat_w.update_xaxes(showticklabels=False)
                st.plotly_chart(fig_cat_w, use_container_width=True)

            c3, c4 = st.columns(2)
            df_toko = df_filt.groupby('Folder_Asal')[col_rank].sum().reset_index()
            with c3:
                df_toko_top = df_toko.sort_values(col_rank, ascending=True).tail(10)
                df_toko_top['Label'] = df_toko_top[col_rank].apply(fmt_func)
                fig_toko_t = px.bar(df_toko_top, x=col_rank, y='Folder_Asal', orientation='h', text='Label', title="🏆 Top 10 Toko", color_discrete_sequence=['#27ae60'])
                fig_toko_t.update_xaxes(showticklabels=False)
                st.plotly_chart(fig_toko_t, use_container_width=True)
            with c4:
                df_toko_worst = df_toko.sort_values(col_rank, ascending=False).tail(10)
                df_toko_worst['Label'] = df_toko_worst[col_rank].apply(fmt_func)
                fig_toko_w = px.bar(df_toko_worst, x=col_rank, y='Folder_Asal', orientation='h', text='Label', title="⚠️ Worst 10 Toko", color_discrete_sequence=['#e67e22'])
                fig_toko_w.update_xaxes(showticklabels=False)
                st.plotly_chart(fig_toko_w, use_container_width=True)

        with subtab3:
            st.subheader("Detail Data Transaksi Kartu")
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df_filt.to_excel(writer, index=False, sheet_name='Data_Kartu')
            st.download_button(label="📥 Download Excel (.xlsx)", data=buffer, file_name="data_transaksi_kartu.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            st.dataframe(df_filt, use_container_width=True)
    else:
        st.warning("Data Kartu Kosong untuk periode ini.")

# --- TAB 2: MESIN ---
with tab_mesin_main:
    if not df_m.empty:
        # FILTER LOKAL
        with st.expander("🔎 Filter Spesifik Mesin (Kategori Game & Game)", expanded=False):
            with st.form("form_filter_mesin"):
                st.caption("Pilih filter di bawah, lalu klik 'Terapkan Filter Mesin'")
                c_mf1, c_mf2 = st.columns(2)
                with c_mf1:
                    f_cat_m = create_local_filter(df_m, "Kategori Game", "Kategori Game", "mesin_loc")
                with c_mf2:
                    f_gt = create_local_filter(df_m, "Game Title", "GT_FINAL", "mesin_loc")
                
                submitted_mesin = st.form_submit_button("🚀 Terapkan Filter Mesin")
            
            if f_cat_m: df_m = df_m[df_m['Kategori Game'].isin(f_cat_m)]
            if f_gt: df_m = df_m[df_m['GT_FINAL'].isin(f_gt)]

        # KPI
        k1, k2, k3, k4 = st.columns(4)
        total_act = df_m['Jumlah Diaktifkan'].sum()
        total_sales_mesin = df_m['Total'].sum() 
        avg_sales = total_sales_mesin / total_act if total_act > 0 else 0
        mesin_active = df_m['GT_FINAL'].nunique()
        
        k1.metric("Total Aktivasi", format_id(total_act))
        k2.metric("Total Sales", format_rupiah(total_sales_mesin)) 
        k3.metric("Rata-rata Sales/Main", format_rupiah(avg_sales))
        k4.metric("Mesin Aktif", f"{mesin_active}")
        st.markdown("---")
        
        # GLOBAL SELECTOR METRIC MESIN
        st.markdown("### ⚙️ Pengaturan Analisis")
        c_sel, _ = st.columns([1, 2])
        with c_sel:
            y_metric = st.selectbox("Pilih Metrik Analisis (Berlaku untuk Tren & Peringkat)", ['Total', 'Jumlah Diaktifkan', 'Kredit yg Digunakan', 'Bonus yg Digunakan'])

        sub_m1, sub_m2, sub_m3 = st.tabs(["📈 Tren & Performa", "🏆 Peringkat", "🔎 Data Mentah"])

        with sub_m1:
            urutan_bulan = ['Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni', 'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember']
            st.subheader("Tren & Komparasi Aktivitas")
            
            c_left, c_right = st.columns(2)
            with c_left:
                st.markdown(f"**Total {y_metric} Tahunan**")
                df_yearly_m = df_m.groupby('Tahun')[y_metric].sum().reset_index()
                val24_m = df_yearly_m[df_yearly_m['Tahun']=='2024'][y_metric].sum() if '2024' in df_yearly_m['Tahun'].values else 0
                val25_m = df_yearly_m[df_yearly_m['Tahun']=='2025'][y_metric].sum() if '2025' in df_yearly_m['Tahun'].values else 0
                growth_m = ((val25_m - val24_m) / val24_m) * 100 if val24_m > 0 else 0
                
                # Format label dynamic based on metric type
                if y_metric in ['Total', 'Kredit yg Digunakan', 'Bonus yg Digunakan']:
                    df_yearly_m['Label'] = df_yearly_m[y_metric].apply(format_label_chart)
                else:
                    df_yearly_m['Label'] = df_yearly_m[y_metric].apply(format_id)

                fig_total_m = px.bar(df_yearly_m, x='Tahun', y=y_metric, text='Label', title=f'Growth: {growth_m:.2f}%', color='Tahun', color_discrete_map={'2024': '#bdc3c7', '2025': '#2980b9'})
                fig_total_m.update_yaxes(showticklabels=False)
                fig_total_m.update_layout(separators=',.')
                st.plotly_chart(fig_total_m, use_container_width=True)

            with c_right:
                st.markdown(f"**Tren {y_metric} Bulanan (YoY)**")
                df_tm = df_m.groupby(['Tahun', 'Bulan_Urut', 'Nama_Bulan'])[y_metric].sum().reset_index().sort_values(['Tahun','Bulan_Urut'])
                
                if y_metric in ['Total', 'Kredit yg Digunakan', 'Bonus yg Digunakan']:
                    df_tm['Label'] = df_tm[y_metric].apply(format_label_chart)
                else:
                    df_tm['Label'] = df_tm[y_metric].apply(format_id)

                fig_tm = px.line(df_tm, x='Nama_Bulan', y=y_metric, color='Tahun', markers=True, text='Label', color_discrete_map={'2024':'gray','2025':'blue'}, category_orders={"Nama_Bulan": urutan_bulan})
                fig_tm.update_traces(textposition="top center")
                fig_tm.update_yaxes(showticklabels=False)
                fig_tm.update_layout(separators=',.')
                st.plotly_chart(fig_tm, use_container_width=True)

            st.markdown("---")
            st.subheader(f"📈 Tren {y_metric} Jangka Panjang")
            df_cont_m = df_m.groupby('Tanggal')[y_metric].sum().reset_index().sort_values('Tanggal')
            fig_cont_m = px.line(df_cont_m, x='Tanggal', y=y_metric, markers=True, title=f"Pergerakan {y_metric} (Timeline Lengkap)", line_shape='linear')
            fig_cont_m.update_xaxes(dtick="M1", tickformat="%b %Y", tickangle=-45)
            fig_cont_m.update_traces(line_color='#3498db', line_width=3) 
            fig_cont_m.update_yaxes(tickformat=',.0f')
            fig_cont_m.update_layout(separators=',.')
            st.plotly_chart(fig_cont_m, use_container_width=True)

            st.markdown("---")
            st.markdown(f"### 🍰 Proporsi {y_metric} per Center")
            df_pie_m = df_m.groupby('Center')[y_metric].sum().reset_index()
            fig_pie_m = px.pie(df_pie_m, values=y_metric, names='Center', hole=0.4)
            fig_pie_m.update_layout(separators=',.')
            st.plotly_chart(fig_pie_m, use_container_width=True)

        with sub_m2:
            st.markdown(f"### 📂 Analisis Kategori Game (by {y_metric})")
            
            # Formatter Func for Ranking
            if y_metric in ['Total', 'Kredit yg Digunakan', 'Bonus yg Digunakan']:
                fmt_func_m = format_label_chart
            else:
                fmt_func_m = format_id

            c_cat1, c_cat2 = st.columns(2)
            df_rank_cat = df_m.groupby('Kategori Game')[y_metric].sum().reset_index()
            with c_cat1:
                df_top_cat = df_rank_cat.sort_values(y_metric, ascending=True).tail(10)
                df_top_cat['Label'] = df_top_cat[y_metric].apply(fmt_func_m)
                fig_top_cat = px.bar(df_top_cat, x=y_metric, y='Kategori Game', orientation='h', text='Label', title="🔥 Top Kategori", color_discrete_sequence=['#8e44ad'])
                fig_top_cat.update_xaxes(showticklabels=False)
                st.plotly_chart(fig_top_cat, use_container_width=True)
            with c_cat2:
                df_worst_cat = df_rank_cat.sort_values(y_metric, ascending=False).tail(10)
                df_worst_cat['Label'] = df_worst_cat[y_metric].apply(fmt_func_m)
                fig_worst_cat = px.bar(df_worst_cat, x=y_metric, y='Kategori Game', orientation='h', text='Label', title="❄️ Worst Kategori", color_discrete_sequence=['#c0392b'])
                fig_worst_cat.update_xaxes(showticklabels=False)
                st.plotly_chart(fig_worst_cat, use_container_width=True)

            st.markdown("---")
            st.markdown(f"### 🎮 Analisis Mesin (Game) (by {y_metric})")
            c1, c2 = st.columns(2)
            df_rank_m = df_m.groupby('GT_FINAL')[y_metric].sum().reset_index()
            with c1:
                df_top_m = df_rank_m.sort_values(y_metric, ascending=True).tail(10)
                df_top_m['Label'] = df_top_m[y_metric].apply(fmt_func_m)
                fig_top_m = px.bar(df_top_m, x=y_metric, y='GT_FINAL', orientation='h', text='Label', title="🔥 Top 10 Mesin", color_discrete_sequence=['#2980b9'])
                fig_top_m.update_xaxes(showticklabels=False)
                st.plotly_chart(fig_top_m, use_container_width=True)
            with c2:
                df_worst_m = df_rank_m.sort_values(y_metric, ascending=False).tail(10)
                df_worst_m['Label'] = df_worst_m[y_metric].apply(fmt_func_m)
                fig_worst_m = px.bar(df_worst_m, x=y_metric, y='GT_FINAL', orientation='h', text='Label', title="❄️ Worst 10 Mesin", color_discrete_sequence=['#e74c3c'])
                fig_worst_m.update_xaxes(showticklabels=False)
                st.plotly_chart(fig_worst_m, use_container_width=True)

            st.markdown("---")
            st.markdown(f"### 🏪 Analisis Toko (by {y_metric})")
            c3, c4 = st.columns(2)
            df_rank_toko = df_m.groupby('Center')[y_metric].sum().reset_index()
            with c3:
                df_top_toko = df_rank_toko.sort_values(y_metric, ascending=True).tail(10)
                df_top_toko['Label'] = df_top_toko[y_metric].apply(fmt_func_m)
                fig_top_t = px.bar(df_top_toko, x=y_metric, y='Center', orientation='h', text='Label', title="🏆 Top 10 Toko", color_discrete_sequence=['#27ae60'])
                fig_top_t.update_xaxes(showticklabels=False)
                st.plotly_chart(fig_top_t, use_container_width=True)
            with c4:
                df_worst_toko = df_rank_toko.sort_values(y_metric, ascending=False).tail(10)
                df_worst_toko['Label'] = df_worst_toko[y_metric].apply(fmt_func_m)
                fig_worst_t = px.bar(df_worst_toko, x=y_metric, y='Center', orientation='h', text='Label', title="⚠️ Worst 10 Toko", color_discrete_sequence=['#e67e22'])
                fig_worst_t.update_xaxes(showticklabels=False)
                st.plotly_chart(fig_worst_t, use_container_width=True)

        with sub_m3:
            st.subheader("Detail Data Mesin")
            buffer_m = io.BytesIO()
            with pd.ExcelWriter(buffer_m, engine='xlsxwriter') as writer:
                df_m.to_excel(writer, index=False, sheet_name='Data_Mesin')
            st.download_button(label="📥 Download Excel (.xlsx)", data=buffer_m, file_name="data_aktivitas_mesin.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            st.dataframe(df_m, use_container_width=True)
    else:
        st.warning("Data Mesin Kosong (Cek Filter).")

# --- TAB 3: PENJELASAN ---
with tab_help_main:
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