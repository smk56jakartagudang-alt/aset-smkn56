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
# 1. SETUP FOLDER UTAMA
BASE_DIR = "arsip_spj"
if not os.path.exists(BASE_DIR):
    os.makedirs(BASE_DIR)

# Konfigurasi halaman khusus SMKN 56 Jakarta
st.set_page_config(page_title="Sistem Aset SMKN 56 Jakarta", layout="wide")

st.title("🏫 Sistem Informasi Aset SMKN 56 Jakarta")
st.write("Portal Internal Pendataan Barang dan Verifikasi Dokumen SPJ.")

# 2. INPUT KATEGORI & WAKTU (Penambahan Semester)
st.subheader("📍 Kategori & Periode Anggaran")
col_a, col_b, col_c, col_d = st.columns(4)

with col_a:
    kategori_simpan = st.selectbox("Kategori Penyimpanan", [
        "BELANJA MODAL BOS", 
        "BELANJA MODAL BOP", 
        "KAPITALISASI", 
        "HIBAH"
    ])
with col_b:
    tahun_beli = st.selectbox("Tahun Pembelian", ["2024", "2025", "2026", "2027"])
with col_c:
    # FITUR BARU: Semester untuk struktur folder
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
    kategori_kib = st.selectbox("Keterangan Aset (KIB)", [
        "KIB A (Tanah)", "KIB B (Peralatan & Mesin)", "KIB C (Gedung & Bangunan)",
        "KIB D (Jalan, Irigasi & Jaringan)", "KIB E (Aset Tetap Lainnya)",
        "KIB F (Konstruksi dalam Pengerjaan)", "KIB G (Aset Tak Berwujud)"
    ])

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

# 5. DAFTAR DOKUMEN WAJIB
daftar_dokumen = ["BAST (Berita Acara Serah Terima)", "Bukti TF (Transfer)", "Kwitansi", "Faktur / Invoice", "Surat Jalan", "PBB / Boron"]

st.subheader("📋 Upload Dokumen SPJ")
uploaded_files_map = {}
for doc in daftar_dokumen:
    c1, c2 = st.columns([1, 1])
    with c1: st.write(f"📄 {doc}")
    with c2:
        file = st.file_uploader(f"Upload_{doc}", type=["pdf"], key=f"file_{doc}", label_visibility="collapsed")
        if file: uploaded_files_map[doc] = file

st.divider()

# 6. TOMBOL SELESAI
if st.button("✅ SIMPAN DATA KE ARSIP SMKN 56", use_container_width=True):
    if not nama_barang or harga_satuan == 0:
        st.error("⚠️ Nama Barang dan Harga Satuan tidak boleh kosong!")
    else:
        # LOGIKA FOLDER: arsip_spj > Kategori > Tahun > Semester > Kode_NamaBarang
        clean_kode = kode_barang.strip().replace(".", "-") if kode_barang else "TanpaKode"
        nama_folder_barang = f"{clean_kode}_{nama_barang.strip()}"
        
        # Path tujuan hirarkis
        path_tujuan = os.path.join(BASE_DIR, kategori_simpan, tahun_beli, semester, nama_folder_barang)
        
        if not os.path.exists(path_tujuan):
            os.makedirs(path_tujuan)

        # Simpan PDF
        list_ada, list_tidak_ada = [], []
        for doc in daftar_dokumen:
            if doc in uploaded_files_map:
                with open(os.path.join(path_tujuan, f"ADA_{doc}.pdf"), "wb") as f:
                    f.write(uploaded_files_map[doc].getbuffer())
                list_ada.append(doc)
            else:
                list_tidak_ada.append(doc)

        # BUAT LAPORAN LENGKAP
        with open(os.path.join(path_tujuan, "Laporan_Aset_Lengkap.txt"), "w") as f:
            f.write("DOKUMEN INTERNAL ASET SMKN 56 JAKARTA\n")
            f.write("=====================================\n\n")
            f.write(f"Sumber Dana    : {kategori_simpan}\n")
            f.write(f"Tahun Anggaran : {tahun_beli}\n")
            f.write(f"Periode        : {semester} ({triwulan})\n")
            f.write(f"Nama Barang    : {nama_barang}\n")
            f.write(f"Kode Barang    : {kode_barang}\n")
            f.write(f"Kategori KIB   : {kategori_kib}\n")
            f.write(f"Jumlah Barang  : {jumlah_barang}\n")
            f.write(f"Penyedia       : {penyedia}\n")
            f.write(f"Jenis Bahan    : {jenis_bahan}\n")
            f.write(f"Tanggal BAST   : {tgl_bast}\n")
            f.write(f"Tanggal Terima : {tgl_terima}\n")
            f.write(f"Total Nominal  : Rp {total_otomatis:,.0f}\n\n".replace(",", "."))
            
            f.write("SPESIFIKASI BARANG:\n")
            f.write(f"{spesifikasi if spesifikasi else '-'}\n\n")
            
            f.write("ALOKASI PENEMPATAN:\n")
            f.write(f"{alokasi_barang if alokasi_barang else '-'}\n\n")
            
            f.write("VERIFIKASI DOKUMEN:\n")
            for item in list_ada: f.write(f" [v] {item}\n")
            for item in list_tidak_ada: f.write(f" [X] {item}\n")

        st.balloons()
        st.success(f"Berhasil! Data disimpan di: {kategori_simpan} > {tahun_beli} > {semester}")

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
