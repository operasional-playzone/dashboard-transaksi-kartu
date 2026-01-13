import pandas as pd
import os

# ================= KONFIGURASI =================
FOLDER_PATH = r"C:\Users\ACER\Documents\Dokumen\Magang Ramayana\2026_06_01_Dashboard Kartu\data-mesin"
OUTPUT_FILENAME = "REKAP_DATA_MESIN_FULL.xlsx"

def gabung_file_mesin(folder_path):
    print(f"📂 Membaca file dari: {folder_path}")
    
    all_data = []

    if not os.path.exists(folder_path):
        print(f"❌ Error: Folder tidak ditemukan: {folder_path}")
        return

    nama_folder_asal = os.path.basename(os.path.normpath(folder_path))

    for filename in os.listdir(folder_path):

        # ================= FILTER FILE =================
        if not filename.lower().endswith(('.xlsx', '.xls')):
            continue
        if filename.startswith('~$'):
            continue

        file_full_path = os.path.join(folder_path, filename)
        print(f"\n📄 Memproses: {filename}")

        try:
            # ================= PARSING BULAN & TAHUN =================
            nama_bersih = os.path.splitext(filename)[0]
            parts = nama_bersih.split('_')

            print(f"   🔎 parts filename: {parts}")

            if len(parts) >= 3:
                bulan = parts[1].title()
                tahun = parts[2]
            else:
                print("   ⚠️ Format nama file tidak standar → FILE DI-SKIP")
                continue  # ❗ LEBIH AMAN SKIP DARIPADA SALAH

            # ================= BACA EXCEL =================
            df = pd.read_excel(file_full_path)

            # ================= KUNCI KOLOM NUMERIK =================
            if 'Jumlah Diaktifkan' in df.columns:
                df['Jumlah Diaktifkan'] = pd.to_numeric(
                    df['Jumlah Diaktifkan'], errors='coerce'
                )

            if 'Kredit yg Digunakan' in df.columns:
                df['Kredit yg Digunakan'] = pd.to_numeric(
                    df['Kredit yg Digunakan'], errors='coerce'
                )

            # ================= TAMBAH METADATA =================
            df['Bulan'] = bulan
            df['Tahun'] = tahun
            df['Asal_Folder'] = nama_folder_asal
            df['Nama_File_Asal'] = filename

            all_data.append(df)
            print("   ✅ OK")

        except Exception as e:
            print(f"   ❌ Gagal proses file ini: {e}")

    # ================= GABUNGKAN =================
    if all_data:
        print("\n🔄 Menggabungkan semua data...")
        final_df = pd.concat(all_data, ignore_index=True)

        final_df.to_excel(OUTPUT_FILENAME, index=False)

        print(f"\n🎉 SUKSES! Data tersimpan di: {OUTPUT_FILENAME}")
        print(f"📊 Total Baris Data: {len(final_df)}")
        print("📅 Bulan:", final_df['Bulan'].unique())
        print("📅 Tahun:", final_df['Tahun'].unique())

    else:
        print("\n⚠️ Tidak ada file yang berhasil diproses.")

if __name__ == "__main__":
    gabung_file_mesin(FOLDER_PATH)
