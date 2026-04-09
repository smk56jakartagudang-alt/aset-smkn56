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
with st.sidebar:
    st.title("📌 MENU UTAMA")
    menu = st.radio("Pilih Kegiatan:", ["Input Aset Baru", "Sensus Barang (3 Bulanan)"])
    st.divider()
    st.info("Aplikasi ini terhubung ke Google Drive SMKN 56")

# --- MODUL 1: INPUT ASET BARU ---
if menu == "Input Aset Baru":
    st.title("🏫 Pendataan Aset Baru SMKN 56")
    st.info("Gunakan menu ini untuk memasukkan barang yang baru dibeli/diterima.")
    
    col_a, col_b = st.columns(2)
    with col_a:
        kategori = st.selectbox("Kategori", ["BELANJA MODAL BOS", "BELANJA MODAL BOP", "KAPITALISASI", "HIBAH"])
        tahun = st.selectbox("Tahun", ["2024", "2025", "2026"])
    with col_b:
        nama_barang = st.text_input("Nama Barang")
        uploaded_files = st.file_uploader("Upload Dokumen SPJ (PDF)", type="pdf", accept_multiple_files=True)

    if st.button("🚀 SIMPAN KE DRIVE"):
        if not nama_barang or not uploaded_files:
            st.warning("Lengkapi Nama Barang dan File!")
        else:
            with st.spinner("Mengunggah..."):
                drive = login_gdrive()
                root_id = st.secrets["FOLDER_UTAMA_ID"]
                kat_id = get_or_create_folder(drive, kategori, root_id)
                thn_id = get_or_create_folder(drive, tahun, kat_id)
                for f in uploaded_files:
                    f_drive = drive.CreateFile({'title': f.name, 'parents': [{'id': thn_id}]})
                    f_drive.SetContentString(f.read()) # Simplified for example
                    f_drive.Upload()
                st.success("Berhasil!")

# --- MODUL 2: SENSUS BARANG ---
elif menu == "Sensus Barang (3 Bulanan)":
    st.title("🔍 Sensus Kondisi Fisik Barang")
    st.subheader("Laporan Triwulan Rekonsiliasi Aset")

    with st.form("form_sensus"):
        col1, col2 = st.columns(2)
        with col1:
            s_nama = st.text_input("Nama Barang yang Disensus", placeholder="Contoh: Laptop Acer Lab Multimedia")
            s_kode = st.text_input("Kode Barang / No. Register")
            s_lokasi = st.text_input("Lokasi Barang Saat Ini", placeholder="Contoh: Ruang TU / Lab Komputer")
        
        with col2:
            s_kondisi = st.radio("Kondisi Fisik Barang:", ["Baik", "Rusak Ringan", "Rusak Berat"])
            s_tgl = st.date_input("Tanggal Pengecekan")
            s_foto = st.file_uploader("Upload Foto Fisik Barang (JPG/PNG)", type=["jpg", "png", "jpeg"])
        
        s_catatan = st.text_area("Catatan Tambahan (Feedback Responden)")
        
        submit_sensus = st.form_submit_with_button("📤 KIRIM LAPORAN SENSUS")

    if submit_sensus:
        if not s_nama or not s_foto:
            st.error("Nama barang dan Foto fisik wajib ada untuk validasi!")
        else:
            with st.spinner("Mengirim data sensus ke Drive..."):
                drive = login_gdrive()
                if drive:
                    # Folder khusus Sensus
                    root_id = st.secrets["FOLDER_UTAMA_ID"]
                    sensus_root_id = get_or_create_folder(drive, "LAPORAN_SENSUS_2026", root_id)
                    
                    # Simpan Foto
                    temp_foto = f"SENSUS_{s_nama}_{s_tgl}.jpg"
                    with open(temp_foto, "wb") as f:
                        f.write(s_foto.getbuffer())
                    
                    foto_drive = drive.CreateFile({'title': temp_foto, 'parents': [{'id': sensus_root_id}]})
                    foto_drive.SetContentFile(temp_foto)
                    foto_drive.Upload()
                    os.remove(temp_foto)

                    # Simpan Data Teks
                    laporan_teks = f"--- LAPORAN SENSUS ---\nTanggal: {s_tgl}\nBarang: {s_nama}\nKondisi: {s_kondisi}\nLokasi: {s_lokasi}\nCatatan: {s_catatan}"
                    teks_drive = drive.CreateFile({'title': f"Data_Sensus_{s_nama}.txt", 'parents': [{'id': sensus_root_id}]})
                    teks_drive.SetContentString(laporan_teks)
                    teks_drive.Upload()

                    st.balloons()
                    st.success(f"Laporan Sensus '{s_nama}' telah diterima. Terima kasih atas feedback-nya!")
