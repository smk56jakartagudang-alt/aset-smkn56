import streamlit as st
import os
import json
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
from pydrive2.auth import ServiceAccountCredentials
from datetime import datetime

# --- FUNGSI LOGIN GOOGLE DRIVE ---
def login_gdrive():
    try:
        scope = ['https://www.googleapis.com/auth/drive']
        key_dict = json.loads(st.secrets["gdrive_service_account"])
        gauth = GoogleAuth()
        gauth.auth_method = 'service'
        gauth.credentials = ServiceAccountCredentials.from_json_keyfile_dict(key_dict, scope)
        return GoogleDrive(gauth)
    except Exception as e:
        st.error(f"Koneksi Drive Gagal: {e}")
        return None

def get_or_create_folder(drive, folder_name, parent_id):
    query = f"'{parent_id}' in parents and title = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    file_list = drive.ListFile({'q': query}).GetList()
    if file_list:
        return file_list[0]['id']
    else:
        folder = drive.CreateFile({'title': folder_name, 'mimeType': 'application/vnd.google-apps.folder', 'parents': [{'id': parent_id}]})
        folder.Upload()
        return folder['id']

# --- SIDEBAR NAVIGASI ---
st.set_page_config(page_title="Sensus Aset SMKN 56", layout="wide")

BASE_DIR = "arsip_spj"
if not os.path.exists(BASE_DIR):
    os.makedirs(BASE_DIR)

with st.sidebar:
    st.title("📌 MENU UTAMA")
    menu = st.radio("Pilih Kegiatan:", ["Input Aset Baru", "Sensus Barang (Feedback)"])
    st.divider()
    st.info("Aplikasi terhubung ke Google Drive SMKN 56")

# --- MODUL 1: INPUT ASET BARU (TAMPILAN LENGKAP SEPERTI GAMBAR 2) ---
if menu == "Input Aset Baru":
    st.title("🏫 Sistem Informasi Aset SMKN 56 Jakarta")
    st.write("Portal Internal Pendataan Barang dan Verifikasi Dokumen SPJ.")

    # 1. KATEGORI & PERIODE
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

    # 2. DETAIL SPESIFIKASI
    st.subheader("📦 Detail Spesifikasi & Informasi Aset")
    col1, col2, col3 = st.columns(3)
    with col1:
        kode_barang = st.text_input("Masukan Kode Barang", placeholder="Contoh: 1.3.2.05")
        nama_barang = st.text_input("Nama Barang", placeholder="Contoh: Laptop Asus")
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

    # 3. DATA KEUANGAN
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

    # 4. UPLOAD DOKUMEN SPJ (BERJEJER)
    st.subheader("📋 Upload Dokumen SPJ")
    daftar_dokumen = ["BAST", "Bukti TF", "Kwitansi", "Faktur / Invoice", "Surat Jalan", "PBB / Boron"]
    uploaded_files_map = {}
    
    for doc in daftar_dokumen:
        cx, cy = st.columns([1, 1])
        with cx: st.write(f"📄 {doc}")
        with cy:
            file = st.file_uploader(f"Upload_{doc}", type=["pdf"], key=f"file_{doc}", label_visibility="collapsed")
            if file: uploaded_files_map[doc] = file

    # 5. TOMBOL SIMPAN
    if st.button("✅ SIMPAN DATA KE ARSIP SMKN 56", use_container_width=True):
        if not nama_barang or harga_satuan == 0:
            st.error("Nama Barang dan Harga tidak boleh kosong!")
        else:
            with st.spinner("Menyimpan data..."):
                # Logika folder lokal
                clean_kode = kode_barang.strip().replace(".", "-") if kode_barang else "TanpaKode"
                nama_folder_barang = f"{clean_kode}_{nama_barang.strip()}"
                path_tujuan = os.path.join(BASE_DIR, kategori_simpan, tahun_beli, semester, nama_folder_barang)
                if not os.path.exists(path_tujuan): os.makedirs(path_tujuan)
                
                # Simpan File & Kirim Drive (Opsional)
                st.balloons()
                st.success(f"Data Berhasil diarsipkan di folder {semester}")

# --- MODUL 2: SENSUS BARANG (RINGKAS) ---
elif menu == "Sensus Barang (Feedback)":
    st.title("🔍 Sensus Kondisi Fisik Barang")
    with st.form("form_sensus"):
        s_anggaran = st.selectbox("Sumber Anggaran", ["DANA BOS", "DANA BOP", "HIBAH"])
        s_nama = st.text_input("Nama Barang")
        s_kondisi = st.radio("Kondisi Fisik:", ["BAIK", "RUSAK RINGAN", "RUSAK BERAT"])
        s_foto = st.file_uploader("Upload Foto Fisik", type=["jpg", "png", "jpeg"])
        submit = st.form_submit_with_button("Kirim Laporan")
        
        if submit and s_foto:
            st.success("Laporan Sensus Terkirim!")
