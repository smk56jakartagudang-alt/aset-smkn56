import streamlit as st
import os
import json
import pandas as pd
from io import BytesIO
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
from pydrive2.auth import ServiceAccountCredentials
from datetime import datetime

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Sensus Aset SMKN 56", layout="wide")

# --- 2. FUNGSI LOGIN & UTILITY GOOGLE DRIVE ---
def login_gdrive():
    try:
        scope = ['https://www.googleapis.com/auth/drive']
        # Pastikan gdrive_service_account sudah ada di Streamlit Secrets
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
        folder = drive.CreateFile({
            'title': folder_name, 
            'mimeType': 'application/vnd.google-apps.folder', 
            'parents': [{'id': parent_id}]
        })
        folder.Upload()
        return folder['id']

def upload_file_to_drive(drive, parent_id, file_obj, custom_name):
    try:
        # Simpan sementara secara lokal untuk diupload pydrive
        with open(custom_name, "wb") as f:
            f.write(file_obj.getbuffer())
        
        file_drive = drive.CreateFile({'title': custom_name, 'parents': [{'id': parent_id}]})
        file_drive.SetContentFile(custom_name)
        file_drive.Upload()
        
        # Hapus file sementara
        os.remove(custom_name)
        return True
    except Exception as e:
        st.error(f"Gagal mengunggah {custom_name}: {e}")
        return False

# --- 3. SIDEBAR NAVIGASI ---
with st.sidebar:
    st.title("📌 MENU UTAMA")
    menu = st.radio("Pilih Kegiatan:", ["Input Aset Baru", "Sensus Barang (Feedback)"])
    st.divider()
    st.info("Aplikasi terhubung ke Google Drive SMKN 56")

# --- 4. MODUL 1: INPUT ASET BARU ---
if menu == "Input Aset Baru":
    st.title("🏫 Sistem Pendataan Aset Internal SMKN 56 Jakarta")
    st.write("Portal Internal Pendataan Barang dan Verifikasi Dokumen SPJ.")

    # A. Kategori & Periode
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

    # B. Detail Spesifikasi
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

    # C. Data Keuangan
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

    # D. Upload Dokumen SPJ
    st.subheader("📋 Upload Dokumen SPJ (Format PDF)")
    daftar_dokumen = ["BAST", "Bukti TF", "Kwitansi", "Faktur-Invoice", "Surat Jalan", "PBB-Boron"]
    uploaded_files_map = {}
    
    for doc in daftar_dokumen:
        cx, cy = st.columns([1, 1])
        with cx: st.write(f"📄 {doc}")
        with cy:
            file = st.file_uploader(f"Upload_{doc}", type=["pdf"], key=f"file_{doc}", label_visibility="collapsed")
            if file: uploaded_files_map[doc] = file

    # E. Tombol Simpan Modul 1
    if st.button("✅ SIMPAN DATA KE ARSIP SMKN 56", use_container_width=True):
        if not nama_barang or harga_satuan == 0:
            st.error("Nama Barang dan Harga tidak boleh kosong!")
        elif not uploaded_files_map:
            st.warning("Silakan unggah minimal satu dokumen SPJ.")
        else:
            with st.spinner("Sedang membuat folder dan mengunggah dokumen ke Drive..."):
                drive = login_gdrive()
                if drive:
                    root_id = st.secrets["FOLDER_UTAMA_ID"]
                    
                    # Buat struktur folder: Kategori > Tahun > Semester > Nama Barang
                    f_kat = get_or_create_folder(drive, kategori_simpan, root_id)
                    f_thn = get_or_create_folder(drive, tahun_beli, f_kat)
                    f_sem = get_or_create_folder(drive, semester, f_thn)
                    
                    clean_kode = kode_barang.strip().replace(".", "-") if kode_barang else "TanpaKode"
                    folder_aset_name = f"{clean_kode}_{nama_barang.strip()}"
                    f_aset = get_or_create_folder(drive, folder_aset_name, f_sem)
                    
                    success_count = 0
                    for doc_type, file_obj in uploaded_files_map.items():
                        nama_file_drive = f"{doc_type}_{nama_barang.strip()}_{tahun_beli}.pdf"
                        if upload_file_to_drive(drive, f_aset, file_obj, nama_file_drive):
                            success_count += 1
                    
                    st.balloons()
                    st.success(f"Berhasil! {success_count} dokumen tersimpan di Drive.")
                    st.info(f"Lokasi: {kategori_simpan} / {tahun_beli} / {semester} / {folder_aset_name}")

# --- 5. MODUL 2: SENSUS BARANG ---
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
            with st.spinner("Memproses Laporan & Sinkronisasi Drive..."):
                drive = login_gdrive()
                if drive:
                    root_id = st.secrets["FOLDER_UTAMA_ID"]
                    f_sensus_root = get_or_create_folder(drive, "HASIL_SENSUS_2026", root_id)
                    f_kat_sensus = get_or_create_folder(drive, s_anggaran, f_sensus_root)
                    tgl_jam = datetime.now().strftime("%Y%m%d_%H%M")

                    # 1. Proses Excel di Memori
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
                    nama_file_excel = f"REKAP_{s_nama}_{tgl_jam}.xlsx"
                    ex_drive = drive.CreateFile({'title': nama_file_excel, 'parents': [{'id': f_kat_sensus}]})
                    # Gunakan buffer langsung
                    output_ex.seek(0)
                    ex_drive.SetContentString(output_ex.getvalue().decode('latin1'), encoding='latin1')
                    ex_drive.Upload()

                    # 3. Upload Foto ke Drive
                    nama_foto = f"FOTO_{s_nama}_{tgl_jam}.jpg"
                    if upload_file_to_drive(drive, f_kat_sensus, s_foto, nama_foto):
                        st.balloons()
                        st.success("Laporan Sensus dan Foto Berhasil Terkirim ke Drive!")
                        st.download_button("📥 Download Excel Hasil Sensus", output_ex.getvalue(), f"Sensus_{s_nama}.xlsx")
