import streamlit as st
import os
import shutil

# 1. SETUP FOLDER UTAMA
BASE_DIR = "arsip_spj"
if not os.path.exists(BASE_DIR):
    os.makedirs(BASE_DIR)

# Konfigurasi halaman
st.set_page_config(page_title="Sistem Aset SMKN 56 Jakarta", layout="wide")

# SIDEBAR UNTUK DOWNLOAD (Agar tidak mengganggu input)
st.sidebar.title("📥 Menu Admin")
st.sidebar.write("Gunakan menu ini untuk mengambil data yang sudah tersimpan di server.")

if os.path.exists(BASE_DIR) and len(os.listdir(BASE_DIR)) > 0:
    if st.sidebar.button("📦 Siapkan Unduhan Semua Folder"):
        shutil.make_archive("arsip_aset_smkn56", 'zip', BASE_DIR)
        with open("arsip_aset_smkn56.zip", "rb") as f:
            st.sidebar.download_button(
                label="✅ Klik untuk Download (.ZIP)",
                data=f,
                file_name="arsip_aset_smkn56.zip",
                mime="application/zip"
            )
else:
    st.sidebar.info("Belum ada data folder yang tersimpan.")

# 2. TAMPILAN UTAMA APLIKASI
st.title("🏫 Sistem Informasi Data Aset Tetap SMKN 56 Jakarta")
st.write("Portal Internal Pendataan Barang dan Verifikasi Dokumen SPJ.")

st.subheader("📍 Kategori & Periode Anggaran")
col_a, col_b, col_c, col_d = st.columns(4)

with col_a:
    kategori_simpan = st.selectbox("Kategori Penyimpanan", ["BELANJA MODAL BOS", "BELANJA MODAL BOP", "KAPITALISASI", "HIBAH"])
with col_b:
    tahun_beli = st.selectbox("Tahun Pembelian", ["2024", "2025", "2026", "2027"])
with col_c:
    semester = st.selectbox("Semester", ["Semester 1", "Semester 2"])
with col_d:
    triwulan = st.selectbox("Triwulan", ["Triwulan 1", "Triwulan 2", "Triwulan 3", "Triwulan 4"])

st.divider()

# 3. MENU INPUT DATA ASET
st.subheader("📦 Detail Spesifikasi & Informasi Aset")
col1, col2, col3 = st.columns(3)

with col1:
    kode_barang = st.text_input("Masukan Kode Barang", placeholder="Contoh: 1.3.2.05")
    nama_barang = st.text_input("Nama Barang", placeholder="Contoh: Laptop Asus")
    if kategori_simpan == "HIBAH":
        penyedia = st.text_input("Hibah Dari", value="Hibah dari ")
    else:
        penyedia = st.text_input("Nama Penyedia / Toko", placeholder="Contoh: PT. Maju Jaya")

with col2:
    spesifikasi = st.text_area("Spesifikasi Barang", placeholder="Detail spek teknis...", height=68)
    jenis_bahan = st.text_input("Jenis Bahan", placeholder="Contoh: Besi / Kayu")
    kategori_kib = st.selectbox("Keterangan Aset (KIB)", ["KIB A", "KIB B", "KIB C", "KIB D", "KIB E", "KIB F", "KIB G"])

with col3:
    tgl_bast = st.date_input("Tanggal BAST")
    tgl_terima = st.date_input("Tanggal Barang Diterima")
    alokasi_barang = st.text_area("Deskripsi Penempatan Lokasi", placeholder="Tulis detail ruangan...", height=68)

st.divider()

# 4. DATA KEUANGAN
st.subheader("💰 Informasi Harga & Kuantitas")
c_kuantitas, c_harga_satuan, c_total_spj = st.columns([1, 2, 2])
with c_kuantitas:
    jumlah_barang = st.number_input("Jumlah Barang", min_value=1, value=1)
with c_harga_satuan:
    harga_satuan = st.number_input("Harga Satuan (Rp)", min_value=0, step=1000)
with c_total_spj:
    total_otomatis = jumlah_barang * harga_satuan
    st.info(f"**Total Nominal SPJ:**\nRp {total_otomatis:,.0f}".replace(",", "."))

st.divider()

# 5. UPLOAD DOKUMEN
st.subheader("📋 Upload Dokumen SPJ")
daftar_dokumen = ["BAST", "Bukti TF", "Kwitansi", "Faktur", "Surat Jalan", "PBB-Boron"]
uploaded_files_map = {}
for doc in daftar_dokumen:
    c1, c2 = st.columns([1, 1])
    with c1: st.write(f"📄 {doc}")
    with c2:
        file = st.file_uploader(f"Upload_{doc}", type=["pdf"], key=f"file_{doc}", label_visibility="collapsed")
        if file: uploaded_files_map[doc] = file

# 6. TOMBOL SIMPAN
if st.button("✅ SIMPAN DATA KE SISTEM", use_container_width=True):
    if not nama_barang or harga_satuan == 0:
        st.error("⚠️ Nama Barang dan Harga Satuan harus diisi!")
    else:
        # LOGIKA PEMBUATAN FOLDER BERLAPIS
        clean_kode = kode_barang.strip().replace(".", "-") if kode_barang else "TanpaKode"
        nama_folder_barang = f"{clean_kode}_{nama_barang.strip()}"
        
        # Folder: arsip_spj > Kategori > Tahun > Semester > Barang
        path_tujuan = os.path.join(BASE_DIR, kategori_simpan, tahun_beli, semester, nama_folder_barang)
        
        if not os.path.exists(path_tujuan):
            os.makedirs(path_tujuan)

        # Simpan File
        for doc, file_data in uploaded_files_map.items():
            with open(os.path.join(path_tujuan, f"ADA_{doc}.pdf"), "wb") as f:
                f.write(file_data.getbuffer())

        # Buat Laporan Teks di dalam folder yang sama
        with open(os.path.join(path_tujuan, "Laporan_Aset.txt"), "w") as f:
            f.write(f"ASET SMKN 56 - {kategori_simpan}\n")
            f.write(f"Barang: {nama_barang}\nSpek: {spesifikasi}\nTotal: Rp {total_otomatis:,.0f}")

        st.success(f"Berhasil! Data tersimpan di folder: {kategori_simpan}/{tahun_beli}/{semester}")
        st.balloons()
