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
        # Membaca kunci JSON dari Streamlit Secrets
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

# --- TAMPILAN UTAMA ---
st.set_page_config(page_title="Sistem Aset SMKN 56", layout="wide")
st.title("🏫 Sistem Informasi Aset SMKN 56 Jakarta")
st.info("Status: Penyimpanan Terhubung ke Google Drive (Data Aman)")

# Input Data
col1, col2 = st.columns(2)
with col1:
    kategori = st.selectbox("Kategori", ["BELANJA MODAL BOS", "BELANJA MODAL BOP", "KAPITALISASI", "HIBAH"])
    tahun = st.selectbox("Tahun", ["2024", "2025", "2026"])
    semester = st.selectbox("Semester", ["Semester 1", "Semester 2"])
with col2:
    kode = st.text_input("Kode Barang")
    nama = st.text_input("Nama Barang")
    files = st.file_uploader("Upload Dokumen PDF", type="pdf", accept_multiple_files=True)

# TOMBOL EKSEKUSI
if st.button("🚀 SIMPAN DATA KE GOOGLE DRIVE", use_container_width=True):
    if not nama or not files:
        st.error("Mohon lengkapi Nama Barang dan File PDF!")
    else:
        with st.spinner("Sedang mengamankan data ke Drive..."):
            drive = login_gdrive()
            if drive:
                # 1. Pastikan Struktur Folder Ada
                root_id = st.secrets["FOLDER_UTAMA_ID"]
                kat_id = get_or_create_folder(drive, kategori, root_id)
                thn_id = get_or_create_folder(drive, tahun, kat_id)
                sem_id = get_or_create_folder(drive, semester, thn_id)
                
                # 2. Upload File
                for f in files:
                    temp_name = f.name
                    with open(temp_name, "wb") as buffer:
                        buffer.write(f.getbuffer())
                    
                    f_drive = drive.CreateFile({
                        'title': f"{nama}_{temp_name}",
                        'parents': [{'id': sem_id}]
                    })
                    f_drive.SetContentFile(temp_name)
                    f_drive.Upload()
                    os.remove(temp_name) # Hapus file sementara
                
                st.balloons()
                st.success(f"Alhamdulillah! Dokumen {nama} sudah tersimpan permanen di Google Drive.")
