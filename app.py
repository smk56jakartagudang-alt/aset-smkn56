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

# --- KONFIGURASI HALAMAN & SIDEBAR ---
st.set_page_config(page_title="Sistem Aset SMKN 56", layout="wide")

with st.sidebar:
    st.title("📌 MENU UTAMA")
    menu = st.radio("Pilih Kegiatan:", ["Input Aset Baru", "Sensus Barang (Feedback)"])
    st.divider()
    st.info("Aplikasi terhubung ke Google Drive SMKN 56 Jakarta")

# --- MODUL 1: INPUT ASET BARU ---
if menu == "Input Aset Baru":
    st.title("🏫 Pendataan Aset Baru SMKN 56 Jakarta")
    st.subheader("📍 Kategori & Periode Anggaran")
    
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        kategori = st.selectbox("Kategori", ["BELANJA MODAL BOS", "BELANJA MODAL BOP", "KAPITALISASI", "HIBAH"])
    with col_b:
        tahun = st.selectbox("Tahun", ["2024", "2025", "2026", "2027"])
    with col_c:
        semester = st.selectbox("Semester", ["Semester 1", "Semester 2"])

    st.divider()
    st.subheader("📦 Detail Barang")
    c1, c2 = st.columns(2)
    with c1:
        nama_barang = st.text_input("Nama Barang")
        kode_barang = st.text_input("Kode Barang")
    with c2:
        uploaded_files = st.file_uploader("Upload Dokumen PDF", type="pdf", accept_multiple_files=True)

    if st.button("✅ SIMPAN KE DRIVE"):
        if not nama_barang or not uploaded_files:
            st.warning("Mohon isi Nama Barang dan Upload Dokumen!")
        else:
            with st.spinner("Mengunggah data..."):
                drive = login_gdrive()
                if drive:
                    root_id = st.secrets["FOLDER_UTAMA_ID"]
                    kat_id = get_or_create_folder(drive, kategori, root_id)
                    thn_id = get_or_create_folder(drive, tahun, kat_id)
                    sem_id = get_or_create_folder(drive, semester, thn_id)
                    
                    for f in uploaded_files:
                        temp_name = f.name
                        with open(temp_name, "wb") as buffer:
                            buffer.write(f.getbuffer())
                        f_drive = drive.CreateFile({'title': f.name, 'parents': [{'id': sem_id}]})
                        f_drive.SetContentFile(temp_name)
                        f_drive.Upload()
                        os.remove(temp_name)
                    st.success("Data Berhasil Disimpan!")

# --- MODUL 2: SENSUS BARANG (HANYA KONDISI & ANGGARAN) ---
elif menu == "Sensus Barang (Feedback)":
    st.title("🔍 Sensus & Feedback Kondisi Barang")
    st.write("Silakan isi kondisi fisik barang berdasarkan anggaran dan kategori terkait.")

    with st.form("form_sensus"):
        st.subheader("📋 Informasi Dasar")
        col1, col2 = st.columns(2)
        with col1:
            s_anggaran = st.selectbox("Sumber Anggaran", ["DANA BOS", "DANA BOP", "HIBAH", "LAINNYA"])
            s_kategori = st.selectbox("Kategori Barang", ["Elektronik", "Mebel", "Alat Praktik", "Bangunan", "Lain-lain"])
        with col2:
            s_nama = st.text_input("Nama Barang", placeholder="Contoh: Laptop Acer i5")
            s_lokasi = st.text_input("Lokasi / Ruangan", placeholder="Contoh: Ruang TU")

        st.divider()
        st.subheader("🛠️ Kondisi Fisik & Bukti Foto")
        c3, c4 = st.columns(2)
        with c3:
            s_kondisi = st.radio("Kondisi Fisik Saat Ini:", ["BAIK", "RUSAK RINGAN", "RUSAK BERAT"])
        with c4:
            s_foto = st.file_uploader("Ambil Foto Fisik (JPG/PNG)", type=["jpg", "png", "jpeg"])

        s_feedback = st.text_area("Feedback / Catatan Responden")
        
        submit_sensus = st.form_submit_with_button("📤 KIRIM LAPORAN SENSUS")

    if submit_sensus:
        if not s_nama or not s_foto:
            st.error("Nama Barang dan Foto Fisik wajib dilampirkan!")
        else:
            with st.spinner("Mengirim ke Drive..."):
                drive = login_gdrive()
                if drive:
                    root_id = st.secrets["FOLDER_UTAMA_ID"]
                    # Buat folder pusat sensus
                    sensus_root = get_or_create_folder(drive, "HASIL_SENSUS_2026", root_id)
                    # Buat sub-folder berdasarkan anggaran agar rapi
                    folder_anggaran = get_or_create_folder(drive, s_anggaran, sensus_root)
                    
                    tgl_skrg = datetime.now().strftime("%Y-%m-%d_%H-%M")
                    
                    # 1. Simpan Foto ke Drive
                    nama_file_foto = f"FOTO_{s_nama}_{tgl_skrg}.jpg"
                    with open(nama_file_foto, "wb") as f:
                        f.write(s_foto.getbuffer())
                    
                    f_drive = drive.CreateFile({'title': nama_file_foto, 'parents': [{'id': folder_anggaran}]})
                    f_drive.SetContentFile(nama_file_foto)
                    f_drive.Upload()
                    os.remove(nama_file_foto)

                    # 2. Simpan Data Teks Feedback
                    data_teks = (f"=== LAPORAN SENSUS ===\n"
                                 f"Waktu: {tgl_skrg}\n"
                                 f"Anggaran: {s_anggaran}\n"
                                 f"Kategori: {s_kategori}\n"
                                 f"Nama Barang: {s_nama}\n"
                                 f"Lokasi: {s_lokasi}\n"
                                 f"Kondisi: {s_kondisi}\n"
                                 f"Feedback: {s_feedback}")
                    
                    txt_drive = drive.CreateFile({'title': f"DATA_{s_nama}_{tgl_skrg}.txt", 'parents': [{'id': folder_anggaran}]})
                    txt_drive.SetContentString(data_teks)
                    txt_drive.Upload()

                    st.balloons()
                    st.success(f"Terima kasih Pak Indra! Laporan sensus '{s_nama}' sudah masuk ke Google Drive.")
