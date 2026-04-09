import streamlit as st
import os
import json
import pandas as pd
from io import BytesIO
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
from pydrive2.auth import ServiceAccountCredentials
from datetime import datetime

# --- 1. FUNGSI LOGIN GOOGLE DRIVE ---
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

# --- 2. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Sensus Aset SMKN 56", layout="wide")

with st.sidebar:
    st.title("📌 MENU UTAMA")
    menu = st.radio("Pilih Kegiatan:", ["Input Aset Baru", "Sensus Barang (Feedback)"])
    st.divider()
    st.info("Aplikasi terhubung ke Google Drive SMKN 56")

# --- 3. MODUL 1: INPUT ASET BARU (TAMPILAN LENGKAP) ---
if menu == "Input Aset Baru":
    st.title("🏫 Sistem Informasi Aset SMKN 56 Jakarta")
    st.subheader("📍 Kategori & Periode Anggaran")
    col_a, col_b, col_c, col_d = st.columns(4)
    with col_a: kat = st.selectbox("Kategori", ["BELANJA MODAL BOS", "BELANJA MODAL BOP", "KAPITALISASI", "HIBAH"])
    with col_b: thn = st.selectbox("Tahun", ["2024", "2025", "2026", "2027"])
    with col_c: sem = st.selectbox("Semester", ["Semester 1", "Semester 2"])
    with col_d: tri = st.selectbox("Triwulan", ["Triwulan 1", "Triwulan 2", "Triwulan 3", "Triwulan 4"])

    st.divider()
    st.subheader("📦 Detail Spesifikasi")
    col1, col2, col3 = st.columns(3)
    with col1:
        kode_brg = st.text_input("Kode Barang")
        nama_brg = st.text_input("Nama Barang")
    with col2:
        spek = st.text_area("Spesifikasi", height=68)
        kib = st.selectbox("KIB", ["KIB A", "KIB B", "KIB C", "KIB D", "KIB E", "KIB F"])
    with col3:
        tgl_bast = st.date_input("Tanggal BAST")
        lokasi_awal = st.text_area("Alokasi Awal", height=68)

    if st.button("✅ SIMPAN KE DRIVE"):
        st.info("Fitur simpan aset baru dalam pengembangan koneksi.")

# --- 4. MODUL 2: SENSUS BARANG (FIX INDENTASI & EXCEL) ---
elif menu == "Sensus Barang (Feedback)":
    st.title("🔍 Sensus & Feedback Kondisi Fisik")
    
    with st.form("form_sensus"):
        st.subheader("📋 Data Identitas Barang")
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            s_anggaran = st.selectbox("Sumber Anggaran", ["DANA BOS", "DANA BOP", "HIBAH", "KAPITALISASI"])
            s_nama = st.text_input("Nama Barang (Sesuai Label)")
        with col_s2:
            s_jumlah = st.number_input("Jumlah Barang Fisik", min_value=1, value=1)
            s_kondisi = st.radio("Kondisi Fisik Dominan:", ["BAIK", "RUSAK RINGAN", "RUSAK BERAT"], horizontal=True)

        st.divider()
        st.subheader("📍 Lokasi Fisik Terkini (Deskripsi Per Unit)")
        c_lok1, c_lok2 = st.columns(2)
        with c_lok1:
            l1 = st.text_input("Lokasi Barang 1")
            l2 = st.text_input("Lokasi Barang 2")
            l3 = st.text_input("Lokasi Barang 3")
        with c_lok2:
            l4 = st.text_input("Lokasi Barang 4")
            l5 = st.text_input("Lokasi Barang 5")
            s_foto = st.file_uploader("Upload Foto Fisik", type=["jpg", "png", "jpeg"])

        s_catatan = st.text_area("Feedback Tambahan")
        submit_sensus = st.form_submit_button("📤 KIRIM LAPORAN SENSUS")

    if submit_sensus:
        if not s_nama or not s_foto:
            st.error("Nama Barang dan Foto Fisik wajib diisi!")
        else:
            with st.spinner("Memproses Laporan & Excel..."):
                drive = login_gdrive()
                if drive:
                    # Tentukan Folder
                    root_id = st.secrets["FOLDER_UTAMA_ID"]
                    f_sensus = get_or_create_folder(drive, "HASIL_SENSUS_2026", root_id)
                    f_kat = get_or_create_folder(drive, s_anggaran, f_sensus)
                    tgl_jam = datetime.now().strftime("%Y%m%d_%H%M")

                    # 1. Buat File Excel
                    data_ex = {
                        "Waktu": [datetime.now().strftime("%Y-%m-%d %H:%M")],
                        "Barang": [s_nama], "Jumlah": [s_jumlah], "Kondisi": [s_kondisi],
                        "Loc 1": [l1], "Loc 2": [l2], "Loc 3": [l3], "Loc 4": [l4], "Loc 5": [l5],
                        "Catatan": [s_catatan]
                    }
                    df = pd.DataFrame(data_ex)
                    output_ex = BytesIO()
                    with pd.ExcelWriter(output_ex, engine='openpyxl') as writer:
                        df.to_excel(writer, index=False)
                    
                    # 2. Upload Excel ke Drive
                    ex_file = drive.CreateFile({'title': f"REKAP_{s_nama}_{tgl_jam}.xlsx", 'parents': [{'id': f_kat}]})
                    ex_file.SetContentString(output_ex.getvalue().decode('latin1'), encoding='latin1')
                    ex_file.Upload()

                    # 3. Upload Foto ke Drive
                    nama_foto = f"FOTO_{s_nama}_{tgl_jam}.jpg"
                    with open(nama_foto, "wb") as f: f.write(s_foto.getbuffer())
                    f_drive = drive.CreateFile({'title': nama_foto, 'parents': [{'id': f_kat}]})
                    f_drive.SetContentFile(nama_foto)
                    f_drive.Upload()
                    os.remove(nama_foto)

                    st.balloons()
                    st.success("Laporan Berhasil Terkirim ke Drive!")
                    st.download_button("📥 Download Excel Hasil Sensus", output_ex.getvalue(), f"Sensus_{s_nama}.xlsx")
