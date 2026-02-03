import pandas as pd
import os
import glob
import warnings

# Matikan warning style openpyxl agar output bersih
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

# ================= KONFIGURASI UTAMA =================
# 1. Folder Sumber Data (Raw Data)
root_folder = r"\\?\C:\Users\ACER\Documents\Dokumen\Magang Ramayana\2026_06_01_Dashboard Kartu\raw_data"

# 2. Nama File Output
output_file = "DETAIL_PAKET_TRANSAKSI_GABUNGAN_V2.xlsx"

# 3. Mapping Angka -> Nama Bulan
map_angka_ke_bulan = {
    '01': 'Januari', '02': 'Februari', '03': 'Maret', '04': 'April',
    '05': 'Mei', '06': 'Juni', '07': 'Juli', '08': 'Agustus',
    '09': 'September', '10': 'Oktober', '11': 'November', '12': 'Desember'
}
# =====================================================

def safe_float(val):
    """Mengubah value menjadi float dengan aman."""
    try:
        if pd.isna(val) or str(val).strip() == '-' or str(val).strip() == '':
            return 0.0
        return float(val)
    except:
        return 0.0

def get_col_safe(row, index):
    """Mengambil data kolom dengan aman. Jika index melebihi panjang baris, return 0."""
    if index < len(row):
        return row[index]
    return 0

def get_existing_signatures(file_path):
    """Cek database lama untuk incremental load."""
    if not os.path.exists(file_path):
        return set(), None
    try:
        print(f"📖 Membaca database eksisting: {file_path}")
        df_exist = pd.read_excel(file_path)
        for col in ['Folder_Asal', 'Tahun', 'Bulan']:
            if col in df_exist.columns:
                df_exist[col] = df_exist[col].astype(str)
        signatures = set(
            df_exist['Folder_Asal'] + "_" + df_exist['Tahun'] + "_" + df_exist['Bulan']
        )
        return signatures, df_exist
    except Exception as e:
        print(f"⚠️ Gagal membaca database lama: {e}. Membuat baru...")
        return set(), None

def proses_detail_paket(file_path):
    try:
        filename = os.path.basename(file_path)
        if filename.startswith("~$"): return [] 

        parts = filename.split('_')
        if len(parts) >= 2:
            tahun, bulan_angka = parts[0], parts[1]
        else:
            tahun, bulan_angka = "Unknown", "Unknown"

        folder_asal = os.path.basename(os.path.dirname(file_path))
        
        try:
            df = pd.read_excel(file_path, header=None, engine='calamine')
        except:
            try:
                df = pd.read_excel(file_path, header=None)
            except Exception as e:
                print(f"   [!] Gagal baca excel {filename}: {e}")
                return []

        try:
            nama_toko_internal = df.iloc[4, 5]
            if pd.isna(nama_toko_internal): 
                nama_toko_internal = "Unknown"
        except:
            nama_toko_internal = "Unknown"

        extracted_data = []
        current_section = "Unknown" 

        for i, row in df.iterrows():
            # Validasi Dasar
            col_0 = str(get_col_safe(row, 0)).strip() 
            col_2 = str(get_col_safe(row, 2)).strip()
            
            # --- 1. DETEKSI SECTION ---
            if "Kiddie Land" in col_0 and len(col_0) < 50: 
                current_section = "Kiddie Land"
                continue 
            elif "Zone" in col_0 and "2000" in col_0:
                current_section = "Zone 2000"
                continue
            elif ("Staf" in col_0 or "Staff" in col_0) and len(col_0) < 50:
                current_section = "Staf"
                continue

            # --- 2. VALIDASI DATA ---
            # Kita butuh minimal sampai index 8 (Qty) untuk tahu ini baris data
            if len(row) < 9: continue

            # --- 3. AMBIL DATA (INDEX DIPERBAIKI SESUAI DUMMY) ---
            val_qty    = get_col_safe(row, 8)   # Kolom I (Index 8)
            val_biaya  = get_col_safe(row, 15)  # Kolom P (Index 15) <--- FIX
            val_kredit = get_col_safe(row, 17)  # Kolom R (Index 17)
            val_bonus  = get_col_safe(row, 20)  # Kolom U (Index 20) <--- FIX
            
            # Validasi Baris Paket: Harus punya nama paket dan Qty berupa angka
            is_valid_row = False
            if col_0 and col_0.lower() != "paket" and "total" not in col_2.lower():
                try:
                    float_qty = float(val_qty)
                    # Kita ambil jika Qty ada isinya (bisa 0 atau lebih)
                    if pd.notna(float_qty):
                        is_valid_row = True
                except:
                    is_valid_row = False

            if is_valid_row:
                extracted_data.append({
                    'Folder_Asal': str(folder_asal),
                    'Nama_Toko_Internal': str(nama_toko_internal),
                    'Tahun': str(tahun),
                    'Bulan': str(bulan_angka), 
                    'Tipe_Kartu': current_section,
                    'Paket': col_0,              
                    'Jumlah_Dibeli': safe_float(val_qty),
                    'Biaya': safe_float(val_biaya),        
                    'Masuk_Kredit': safe_float(val_kredit),
                    'Masuk_Bonus': safe_float(val_bonus)
                })

        return extracted_data

    except Exception as e:
        print(f"❌ Error script pada file {os.path.basename(file_path)}: {e}")
        return []

# ================= MAIN EXECUTION =================
existing_signatures, df_old = get_existing_signatures(output_file)

print(f"🚀 Memulai proses scanning di folder:\n   {root_folder}")
print("-" * 50)

search_pattern = os.path.join(root_folder, "**", "*.xlsx")
files = glob.glob(search_pattern, recursive=True)

print(f"📦 Total file ditemukan: {len(files)}")
print("🔍 Memilah file baru vs file lama...\n")

new_data = []
processed_count = 0
skipped_count = 0
long_path_prefix = "\\\\?\\"

for i, file in enumerate(files):
    if not file.startswith(long_path_prefix) and ":" in file:
         file = long_path_prefix + os.path.abspath(file)
    
    filename = os.path.basename(file)
    if filename.startswith("~$"): continue 

    folder_name = os.path.basename(os.path.dirname(file))
    parts = filename.split('_')
    
    if len(parts) >= 2:
        thn, bln_angka = parts[0], parts[1]
        bln_nama = map_angka_ke_bulan.get(bln_angka, bln_angka)
        
        current_signature = f"{folder_name}_{thn}_{bln_nama}"
        
        if current_signature in existing_signatures:
            skipped_count += 1
            continue
    
    processed_count += 1
    if processed_count % 10 == 0:
        print(f"   ...Sedang memproses Data Baru ke-{processed_count} ({filename})")

    res = proses_detail_paket(file)
    if res:
        new_data.append(res)

print("\n" + "="*40)
print(f"📊 LAPORAN AKHIR:")
print(f"⏩ File Di-skip (Sudah ada): {skipped_count}")
print(f"✅ File Baru Diproses     : {processed_count}")
print("="*40)

if new_data:
    print("\n💾 Sedang menggabungkan dan menyimpan data...")
    flat_data = [item for sublist in new_data for item in sublist]
    df_new = pd.DataFrame(flat_data)
    
    df_new['Bulan'] = df_new['Bulan'].map(map_angka_ke_bulan).fillna(df_new['Bulan'])
    
    cols_order = [
        'Folder_Asal', 'Nama_Toko_Internal', 'Tahun', 'Bulan', 
        'Tipe_Kartu', 'Paket', 'Jumlah_Dibeli', 'Biaya', 'Masuk_Kredit', 'Masuk_Bonus'
    ]
    
    for col in cols_order:
        if col not in df_new.columns:
            df_new[col] = None
            
    if df_old is not None:
        for col in cols_order:
            if col not in df_old.columns:
                df_old[col] = None
        final_df = pd.concat([df_old[cols_order], df_new[cols_order]], ignore_index=True)
    else:
        final_df = df_new[cols_order]
        
    final_df.dropna(how='all', inplace=True)
    
    try:
        final_df.to_excel(output_file, index=False)
        print(f"✅ SUKSES! File tersimpan sebagai: {output_file}")
        print(f"   Total Baris Data: {len(final_df)}")
        
        # --- DIAGNOSTIK UNTUK MEMASTIKAN DATA ADA ---
        if 'Biaya' in final_df.columns:
            print(f"   💰 Total Biaya Terdeteksi: {final_df['Biaya'].sum():,.0f}")
        if 'Masuk_Bonus' in final_df.columns:
            print(f"   🎁 Total Bonus Terdeteksi: {final_df['Masuk_Bonus'].sum():,.0f}")
            
    except Exception as e:
        print(f"❌ Gagal menyimpan file: {e}")
        backup_name = "BACKUP_" + output_file
        final_df.to_excel(backup_name, index=False)
        print(f"   -> Data diselamatkan ke: {backup_name}")

else:
    print("\n💤 Tidak ada data baru yang perlu ditambahkan.")