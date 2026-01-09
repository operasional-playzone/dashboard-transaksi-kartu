import pandas as pd
import os

# ================= KONFIGURASI =================
# Path folder tempat data mesin berada
# Menggunakan r"" string agar backslash Windows terbaca dengan benar
FOLDER_PATH = r"C:\Users\ACER\Documents\Dokumen\Magang Ramayana\2026_06_01_Dashboard Kartu\data-mesin"
OUTPUT_FILENAME = "REKAP_DATA_MESIN_FULL.xlsx"

def gabung_file_mesin(folder_path):
    print(f"📂 Membaca file dari: {folder_path}")
    
    # List untuk menampung semua data sementara
    all_data = []
    
    # Cek apakah folder ada
    if not os.path.exists(folder_path):
        print(f"❌ Error: Folder tidak ditemukan: {folder_path}")
        return

    # Ambil nama folder paling akhir untuk kolom 'Asal_Folder' (misal: 'data-mesin')
    nama_folder_asal = os.path.basename(os.path.normpath(folder_path))

    # Loop semua file dalam folder
    for filename in os.listdir(folder_path):
        # Hanya proses file Excel (.xlsx atau .xls) dan abaikan file temporary (~$)
        if (filename.endswith('.xlsx') or filename.endswith('.xls')) and not filename.startswith('~$'):
            
            file_full_path = os.path.join(folder_path, filename)
            print(f"   📄 Memproses: {filename} ...", end=" ")

            try:
                # --- 1. EKSTRAK BULAN & TAHUN DARI NAMA FILE ---
                # Format: Laporan_Agustus_2024.xlsx
                # Hapus ekstensi (.xlsx) -> Laporan_Agustus_2024
                nama_bersih = os.path.splitext(filename)[0]
                
                # Pisahkan berdasarkan garis bawah '_'
                parts = nama_bersih.split('_')
                
                # Logika: [0]=Laporan, [1]=Bulan, [2]=Tahun
                if len(parts) >= 3:
                    bulan = parts[1] # Agustus
                    tahun = parts[2] # 2024
                else:
                    # Jika format nama file tidak sesuai standar
                    print("⚠️ (Format nama file tidak standar, skip parsing bulan/tahun)")
                    bulan = "Unknown"
                    tahun = "Unknown"

                # --- 2. BACA EXCEL ---
                df = pd.read_excel(file_full_path)

                # --- 3. TAMBAH KOLOM BARU ---
                df['Bulan'] = bulan
                df['Tahun'] = tahun
                df['Asal_Folder'] = nama_folder_asal
                df['Nama_File_Asal'] = filename # Opsional: buat track error

                # Simpan ke list
                all_data.append(df)
                print("✅ OK")

            except Exception as e:
                print(f"❌ Gagal: {e}")

    # --- 4. GABUNGKAN SEMUA DATA ---
    if all_data:
        print("\n🔄 Menggabungkan semua data...")
        final_df = pd.concat(all_data, ignore_index=True)
        
        # Simpan ke Excel Baru
        final_df.to_excel(OUTPUT_FILENAME, index=False)
        print(f"\n🎉 SUKSES! Data tersimpan di: {OUTPUT_FILENAME}")
        print(f"📊 Total Baris Data: {len(final_df)}")
        print(f"📅 Periode Terdeteksi: {final_df['Bulan'].unique()} {final_df['Tahun'].unique()}")
    else:
        print("\n⚠️ Tidak ada file Excel yang ditemukan atau diproses.")

if __name__ == "__main__":
    gabung_file_mesin(FOLDER_PATH)