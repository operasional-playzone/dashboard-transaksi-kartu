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
output_file = "DETAIL_PAKET_TRANSAKSI_GABUNGAN.xlsx"

# 3. Mapping Angka -> Nama Bulan
map_angka_ke_bulan = {
    '01': 'Januari', '02': 'Februari', '03': 'Maret', '04': 'April',
    '05': 'Mei', '06': 'Juni', '07': 'Juli', '08': 'Agustus',
    '09': 'September', '10': 'Oktober', '11': 'November', '12': 'Desember'
}
# =====================================================

def safe_float(val):
    """Mengubah value menjadi float dengan aman (handle string/strip/-)."""
    try:
        if pd.isna(val) or str(val).strip() == '-' or str(val).strip() == '':
            return 0.0
        return float(val)
    except:
        return 0.0

def get_existing_signatures(file_path):
    """Cek database lama untuk incremental load."""
    if not os.path.exists(file_path):
        return set(), None
    try:
        print(f"📖 Membaca database eksisting: {file_path}")
        df_exist = pd.read_excel(file_path)
        
        # Pastikan kolom kunci bertipe string untuk comparison
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

        # Ambil Tahun & Bulan dari nama file (Format: YYYY_MM_...)
        parts = filename.split('_')
        if len(parts) >= 2:
            tahun, bulan_angka = parts[0], parts[1]
        else:
            tahun, bulan_angka = "Unknown", "Unknown"

        # Ambil nama folder parent sebagai Folder_Asal
        folder_asal = os.path.basename(os.path.dirname(file_path))
        
        # --- BACA EXCEL ---
        # Prioritas pakai calamine (cepat), fallback ke default (openpyxl/xlrd)
        try:
            df = pd.read_excel(file_path, header=None, engine='calamine')
        except:
            try:
                df = pd.read_excel(file_path, header=None)
            except Exception as e:
                print(f"   [!] Gagal baca excel {filename}: {e}")
                return []

        # Ambil Nama Toko Internal (Biasanya di cell F5 -> index [4, 5])
        try:
            nama_toko_internal = df.iloc[4, 5]
            if pd.isna(nama_toko_internal): 
                nama_toko_internal = "Unknown"
        except:
            nama_toko_internal = "Unknown"

        extracted_data = []
        current_section = "Unknown" 

        for i, row in df.iterrows():
            col_0 = str(row[0]).strip() if pd.notna(row[0]) else "" 
            col_2 = str(row[2]).strip() if pd.notna(row[2]) else "" 
            
            # --- 1. DETEKSI SECTION (KATEGORI) ---
            # Logic: Jika kolom 0 mengandung kata kunci tertentu, set section baru
            if "Kiddie Land" in col_0 and len(col_0) < 50: 
                current_section = "Kiddie Land"
                continue 
            elif "Zone" in col_0 and "2000" in col_0:
                current_section = "Zone 2000"
                continue
            elif ("Staf" in col_0 or "Staff" in col_0) and len(col_0) < 50:
                current_section = "Staf"
                continue

            # --- 2. AMBIL DATA ---
            # Pastikan row memiliki cukup kolom sebelum akses index
            if len(row) < 18: continue

            val_qty    = row[8]  # Kolom I
            val_sales  = row[9]  # Kolom J
            val_kredit = row[17] # Kolom R
            
            # Validasi Baris Paket:
            # 1. Kolom 0 tidak kosong
            # 2. Bukan header "Paket"
            # 3. Bukan baris "Total"
            # 4. Qty harus angka dan tidak NaN/Kosong
            
            is_valid_row = False
            if col_0 and col_0.lower() != "paket" and "total" not in col_2.lower():
                # Cek apakah qty bisa dikonversi ke float
                try:
                    float_qty = float(val_qty)
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
                    'Frekuensi': safe_float(val_qty),        
                    'Total_Sales': safe_float(val_sales),   
                    'Masuk_Kredit': safe_float(val_kredit)  
                })

        return extracted_data

    except Exception as e:
        print(f"❌ Error script pada file {os.path.basename(file_path)}: {e}")
        return []

# ================= MAIN EXECUTION =================
existing_signatures, df_old = get_existing_signatures(output_file)

print(f"🚀 Memulai proses scanning di folder:\n   {root_folder}")
print("-" * 50)

# Pattern pencarian file rekursif
search_pattern = os.path.join(root_folder, "**", "*.xlsx")
files = glob.glob(search_pattern, recursive=True)

print(f"📦 Total file ditemukan: {len(files)}")
print("🔍 Memilah file baru vs file lama...\n")

new_data = []
processed_count = 0
skipped_count = 0
long_path_prefix = "\\\\?\\"

for i, file in enumerate(files):
    # Handle Long Path Windows
    if not file.startswith(long_path_prefix) and ":" in file:
         file = long_path_prefix + os.path.abspath(file)
    
    filename = os.path.basename(file)
    if filename.startswith("~$"): continue 

    folder_name = os.path.basename(os.path.dirname(file))
    parts = filename.split('_')
    
    # Cek Incremental Load
    # Logic: Jika Folder+Tahun+Bulan(Nama) sudah ada di database, skip.
    if len(parts) >= 2:
        thn, bln_angka = parts[0], parts[1]
        # Konversi 01 -> Januari untuk pengecekan signature
        bln_nama = map_angka_ke_bulan.get(bln_angka, bln_angka)
        
        current_signature = f"{folder_name}_{thn}_{bln_nama}"
        
        if current_signature in existing_signatures:
            skipped_count += 1
            # Optional: print(f"Skip: {filename}")
            continue
    
    processed_count += 1
    if processed_count % 10 == 0:
        print(f"   ...Sedang memproses Data Baru ke-{processed_count} ({filename})")

    res = proses_detail_paket(file)
    if res:
        new_data.append(res)

# ================= FINISHING =================
print("\n" + "="*40)
print(f"📊 LAPORAN AKHIR:")
print(f"⏩ File Di-skip (Sudah ada): {skipped_count}")
print(f"✅ File Baru Diproses     : {processed_count}")
print("="*40)

if new_data:
    print("\n💾 Sedang menggabungkan dan menyimpan data...")
    # Flatten list of lists
    flat_data = [item for sublist in new_data for item in sublist]
    df_new = pd.DataFrame(flat_data)
    
    # Mapping Bulan Angka ke Nama (01 -> Januari) untuk df_new
    df_new['Bulan'] = df_new['Bulan'].map(map_angka_ke_bulan).fillna(df_new['Bulan'])
    
    # Definisi Urutan Kolom Final
    cols_order = [
        'Folder_Asal', 'Nama_Toko_Internal', 'Tahun', 'Bulan', 
        'Tipe_Kartu', 'Paket', 'Frekuensi', 'Total_Sales', 'Masuk_Kredit'
    ]
    
    # Pastikan df_new memiliki semua kolom (isi NaN jika tidak ada)
    for col in cols_order:
        if col not in df_new.columns:
            df_new[col] = None
            
    # Gabung Data
    if df_old is not None:
        # Pastikan df_old juga memiliki kolom yang sama untuk mencegah error concat
        for col in cols_order:
            if col not in df_old.columns:
                df_old[col] = None
                
        final_df = pd.concat([df_old[cols_order], df_new[cols_order]], ignore_index=True)
    else:
        final_df = df_new[cols_order]
        
    # Final Cleaning: Drop baris yang benar-benar kosong jika ada
    final_df.dropna(how='all', inplace=True)
    
    # Simpan
    try:
        final_df.to_excel(output_file, index=False)
        print(f"✅ SUKSES! File tersimpan sebagai: {output_file}")
        print(f"   Total Baris Data: {len(final_df)}")
    except Exception as e:
        print(f"❌ Gagal menyimpan file: {e}")
        # Opsi backup jika gagal save
        backup_name = "BACKUP_" + output_file
        final_df.to_excel(backup_name, index=False)
        print(f"   -> Data diselamatkan ke: {backup_name}")

else:
    print("\n💤 Tidak ada data baru yang perlu ditambahkan.")