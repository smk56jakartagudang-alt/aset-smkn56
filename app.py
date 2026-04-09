import streamlit as st
import os
import json
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
from pydrive2.auth import ServiceAccountCredentials

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

# --- FUNGSI MANAJEMEN FOLDER ---
def get_or_create_folder(drive, folder_name, parent_id):
    query = f"'{parent_id}' in parents and title = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    file_list = drive.ListFile({'q': query}).GetList()
    if file_list:
        return file_list[0]['id']
    else:
        folder = drive.CreateFile({
            'title': folder_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [{'id': parent_id}]
        })
        folder.Upload()
        return folder['id']

# --- TAMPILAN APLIKASI LENGKAP ---
st.set_page_config(page_title="Sistem Aset SMKN 56 Jakarta", layout="wide")

st.title("🏫 Sistem Informasi Aset SMKN 56 Jakarta")
st.info("💡 Status: Terhubung ke Google Drive (Data Tersimpan Aman & Permanen)")

# 1. Kategori & Periode
st.subheader("📍 Kategori & Periode Anggaran")
col_a, col_b, col_c, col_d = st.columns(4)
with col_a: kategori = st.selectbox("Kategori Penyimpanan", ["BELANJA MODAL BOS", "BELANJA MODAL BOP", "KAPITALISASI", "HIBAH"])
with col_b: tahun = st.selectbox("Tahun Pembelian", ["2024", "2025", "2026", "2027"])
with col_c: semester = st.selectbox("Semester", ["Semester 1", "Semester 2"])
with col_d: triwulan = st.selectbox("Triwulan", ["Triwulan 1", "Triwulan 2", "Triwulan 3", "Triwulan 4"])

st.divider()

# 2. Detail Spesifikasi
st.subheader("📦 Detail Spesifikasi & Informasi Aset")
col1, col2, col3 = st.columns(3)
with col1:
    kode_barang = st.text_input("Masukan Kode Barang", placeholder="Contoh: 1.3.2.05")
    nama_barang = st.text_input("Nama Barang", placeholder="Contoh: Laptop Asus")
    penyedia = st.text_input("Nama Penyedia / Toko", placeholder="PT. Maju Jaya")
with col2:
    spesifikasi = st.text_area("Spesifikasi Barang", height=68)
    jenis_bahan = st.text_input("Jenis Bahan", placeholder="Besi / Kayu / Plastik")
    kib = st.selectbox("Keterangan Aset (KIB)", ["KIB A", "KIB B", "KIB C", "KIB D", "KIB E", "KIB F"])
with col3:
    tgl_bast = st.date_input("Tanggal BAST")
    alokasi = st.text_area("Deskripsi Penempatan Lokasi", height=68)

st.divider()

# 3. Data Keuangan & Dokumen
st.subheader("📋 Informasi Keuangan & Upload Dokumen")
c_harga, c_upload = st.columns([1, 1])
with c_harga:
    jumlah = st.number_input("Jumlah Barang", min_value=1, value=1)
    harga_sat = st.number_input("Harga Satuan (Rp)", min_value=0, step=1000)
    total = jumlah * harga_sat
    st.success(f"**Total Nominal SPJ: Rp {total:,.0f}**".replace(",", "."))
with c_upload:
    uploaded_files = st.file_uploader("Upload Semua Dokumen PDF (BAST, Kwitansi, dll)", type="pdf", accept_multiple_files=True)

# 4. TOMBOL SIMPAN KE DRIVE
if st.button("🚀 SIMPAN DATA KE SISTEM & GOOGLE DRIVE", use_container_width=True):
    if not nama_barang or not uploaded_files:
        st.error("⚠️ Nama Barang dan File PDF wajib diisi!")
    else:
        with st.spinner("Sedang memproses dan mengunggah ke Google Drive SMKN 56..."):
            drive = login_gdrive()
            if drive:
                # Hirarki Folder: Root > Kategori > Tahun > Semester > Nama_Barang
                root_id = st.secrets["FOLDER_UTAMA_ID"]
                kat_id = get_or_create_folder(drive, kategori, root_id)
                thn_id = get_or_create_folder(drive, tahun, kat_id)
                sem_id = get_or_create_folder(drive, semester, thn_id)
                
                # Buat folder khusus untuk barang tersebut
                nama_folder_final = f"{kode_barang}_{nama_barang}".strip("_")
                brg_id = get_or_create_folder(drive, nama_folder_final, sem_id)
                
                # A. Upload File PDF
                for f in uploaded_files:
                    temp_name = f.name
                    with open(temp_name, "wb") as buffer:
                        buffer.write(f.getbuffer())
                    
                    f_drive = drive.CreateFile({'title': temp_name, 'parents': [{'id': brg_id}]})
                    f_drive.SetContentFile(temp_name)
                    f_drive.Upload()
                    os.remove(temp_name)
                
                # B. Buat Laporan Ringkas (Text) di Drive
                info_text = f"NAMA BARANG: {nama_barang}\nKODE: {kode_barang}\nSPEK: {spesifikasi}\nTOTAL: Rp {total:,.0f}\nLOKASI: {alokasi}"
                info_file = drive.CreateFile({'title': f'RINGKASAN_DATA_{nama_barang}.txt', 'parents': [{'id': brg_id}]})
                info_file.SetContentString(info_text)
                info_file.Upload()

                st.balloons()
                st.success(f"✅ Alhamdulillah! Data '{nama_barang}' berhasil tersimpan permanen di Google Drive.")
