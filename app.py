import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import pandas as pd
import datetime
import qrcode
import re
from io import BytesIO

# ==========================================
# 1. KONFIGURASI HALAMAN & TEMA
# ==========================================
st.set_page_config(
    page_title="SI-PINTU 56 - SMKN 56 Jakarta",
    page_icon="🏫",
    layout="wide"
)

BASE_URL = "https://sipintu-smkn56jakarta.streamlit.app/"

# ===================================================================
# ⚠️ WAJIB PAKAI GOOGLE SHARED DRIVE (bukan folder biasa)
# ===================================================================
GOOGLE_DRIVE_FOLDER_ID = "1jPhL66Q2a0JSFDyiEeB9tOk0cPjxiZ82"

# ==========================================
# 2. KONEKSI GOOGLE SHEETS & GOOGLE DRIVE API
# ==========================================
@st.cache_resource
def get_services():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    if "gcp_service_account" in st.secrets:
        creds_dict = dict(st.secrets["gcp_service_account"])
    else:
        st.error("❌ Secrets 'gcp_service_account' belum diisi di Streamlit Cloud!")
        st.stop()

    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client_gspread = gspread.authorize(creds)
    drive_service = build('drive', 'v3', credentials=creds)
    
    ss = client_gspread.open_by_key("1SXyAvphA5ivL70UVzD49nHfkGBlUGLqiCPaxuDQlGAg")
    
    def get_or_create(title, headers):
        try:
            return ss.worksheet(title)
        except:
            ws = ss.add_worksheet(title=title, rows="1000", cols="35")
            ws.append_row(headers)
            return ws

    s_users = get_or_create("Users", ["Username", "Password"])
    s_arsip = get_or_create("Data_Arsip", [
        "Nama Komponen", "Kategori", "Kode Komponen", "Harga Satuan", "Quantity", 
        "Jumlah Total", "Tanggal Perolehan", "Asal perolehan", "Sub Perolehan", "Kondisi", 
        "Merk", "Type", "Spesifikasi", "BAST", "Tanggal BAST", "Penyedia", 
        "Tahun Pengadaan", "Semester", "Triwulan", "Alokasi Barang", "Bahan", 
        "No. Seri / Pabrik", "Foto Aset (Gambar - Gabungan)", "Dokumen Pendukung (PDF)", 
        "Petugas", "Foto Aset Satuan (Siera / Perwakilan)", "Timestamp"
    ])
    s_sensus = get_or_create("Data_Sensus", [
        "Timestamp Sensus", "ID Aset", "Nama Komponen", "Periode Sensus", 
        "Kondisi Terkini", "Lokasi Terkini", "Catatan Sensus", "Link Foto Sensus", "Petugas Sensus"
    ])
    s_lapor = get_or_create("Data_Laporan_Rusak", [
        "Timestamp Laporan", "ID Aset", "Nama Komponen", "Barang Ke-", 
        "Lokasi Spesifik", "Deskripsi Kerusakan", "Nama Pelapor", "NIP / NIKKI", 
        "Link Foto Bukti", "Status Tindakan", "Dipindahkan ke Gudang ARB"
    ])
    
    return s_users, s_arsip, s_sensus, s_lapor, drive_service

try:
    sheet_users, sheet_arsip, sheet_sensus, sheet_lapor, drive_service = get_services()
except Exception as e:
    st.error(f"❌ Gagal Terhubung ke Google API: {e}")
    st.stop()

# ==========================================
# FUNGSI KOMPRES GAMBAR (MEMpercepat upload)
# ==========================================
def compress_image_if_needed(uploaded_file, max_size=1200, quality=75):
    """Kompres gambar JPG/PNG agar upload ke Drive lebih cepat."""
    try:
        from PIL import Image
        img = Image.open(uploaded_file)
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        img.thumbnail((max_size, max_size))
        buf = BytesIO()
        img.save(buf, format='JPEG', quality=quality, optimize=True)
        buf.seek(0)
        
        class CompressedFile:
            def __init__(self, name, buffer):
                self.name = name
                self.type = 'image/jpeg'
                self._buffer = buffer
            def getvalue(self):
                return self._buffer.getvalue()
        
        return CompressedFile(uploaded_file.name, buf)
    except Exception:
        return uploaded_file

# ==========================================
# FUNGSI UPLOAD DOKUMEN/FOTO KE GOOGLE DRIVE
# ==========================================
def upload_file_to_drive(file_uploaded, custom_filename, folder_id):
    try:
        ext = file_uploaded.name.split('.')[-1]
        final_filename = f"{custom_filename}.{ext}"
        final_filename = re.sub(r'[/\\:*?"<>|]', '_', final_filename)
        
        file_metadata = {
            'name': final_filename,
            'parents': [folder_id]
        }
        
        media = MediaIoBaseUpload(
            BytesIO(file_uploaded.getvalue()),
            mimetype=file_uploaded.type,
            resumable=True
        )
        
        uploaded_file = drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webViewLink',
            supportsAllDrives=True
        ).execute()
        
        try:
            drive_service.permissions().create(
                fileId=uploaded_file.get('id'),
                body={'role': 'reader', 'type': 'anyone'},
                supportsAllDrives=True
            ).execute()
        except Exception:
            pass
        
        return uploaded_file.get('webViewLink')
    except Exception as e:
        return f"ERROR::{str(e)}"

# ==========================================
# FUNGSI CACHING DATA
# ==========================================
@st.cache_data(ttl=120)
def fetch_records(sheet_name):
    if sheet_name == "Users":
        return sheet_users.get_all_records()
    elif sheet_name == "Data_Arsip":
        return sheet_arsip.get_all_records()
    elif sheet_name == "Data_Sensus":
        return sheet_sensus.get_all_records()
    elif sheet_name == "Data_Laporan_Rusak":
        return sheet_lapor.get_all_records()
    return []

def render_file_display(url_or_name, label="Lihat Berkas"):
    val_str = str(url_or_name).strip()
    if val_str.startswith("http://") or val_str.startswith("https://"):
        st.markdown(f'<a href="{val_str}" target="_blank" style="text-decoration:none;"><button style="background-color:#007BFF;color:white;border:none;padding:6px 14px;border-radius:6px;cursor:pointer;font-size:13px;font-weight:bold;">🔗 {label}</button></a>', unsafe_allow_html=True)
    elif val_str and val_str != "Tidak ada file":
        st.info(f"📄 Berkas: **{val_str}**")
    else:
        st.caption("🔴 Belum ada file")

# ==========================================
# 3. DETEKSI AKSES PUBLIC SCAN QR CODE
# ==========================================
query_params = st.query_params
id_public = query_params.get("id", None)

if id_public:
    st.title("📋 SI-PINTU 56 - Detail Inventaris")
    st.caption("Sistem Informasi Manajemen Pelacakan BMD Internal SMK Negeri 56 Jakarta")
    
    data_arsip = fetch_records("Data_Arsip")
    aset_terpilih = None
    
    raw_target = str(id_public).strip()
    clean_target = re.sub(r'[^a-zA-Z0-9]', '', raw_target).lower()
    
    for item in data_arsip:
        val_ts = str(item.get("Timestamp", "")).strip()
        val_kode = str(item.get("Kode Komponen", "")).strip()
        val_nama = str(item.get("Nama Komponen", "")).strip()
        
        clean_ts = re.sub(r'[^a-zA-Z0-9]', '', val_ts).lower()
        clean_kode = re.sub(r'[^a-zA-Z0-9]', '', val_kode).lower()
        clean_nama = re.sub(r'[^a-zA-Z0-9]', '', val_nama).lower()
        
        if raw_target in [val_ts, val_kode, val_nama] or clean_target in [clean_ts, clean_kode, clean_nama]:
            aset_terpilih = item
            break
            
    if aset_terpilih:
        st.subheader(f"📦 {aset_terpilih.get('Nama Komponen', '-')} ({aset_terpilih.get('Kode Komponen', '-')})")
        
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Kategori:** {aset_terpilih.get('Kategori', '-')}")
            st.write(f"**Asal Perolehan:** {aset_terpilih.get('Asal perolehan', '-')} / {aset_terpilih.get('Sub Perolehan', '-')}")
            st.write(f"**Tahun Pengadaan:** {aset_terpilih.get('Tahun Pengadaan', '-')} | {aset_terpilih.get('Semester', '-')} / {aset_terpilih.get('Triwulan', '-')}")
            st.write(f"**Kondisi Fisik:** {aset_terpilih.get('Kondisi', '-')}")
        with col2:
            st.write(f"**Merk / Type:** {aset_terpilih.get('Merk', '-')} / {aset_terpilih.get('Type', '-')}")
            st.write(f"**BAST:** {aset_terpilih.get('BAST', '-')} ({aset_terpilih.get('Tanggal BAST', '-')})")
            st.write(f"**Penyedia:** {aset_terpilih.get('Penyedia', '-')}")
            st.write(f"**Alokasi Penempatan:** {aset_terpilih.get('Alokasi Barang', '-')}")

        st.divider()
        st.subheader("🚨 Laporkan Kerusakan Barang Ini (CRM)")
        
        with st.form("form_lapor_publik"):
            nama_pelapor = st.text_input("Nama Lengkap Pelapor")
            nip_pelapor = st.text_input("NIP / NIKKI")
            qty_raw = aset_terpilih.get("Quantity", 1)
            try:
                qty_total = int(qty_raw)
            except:
                qty_total = 1
                
            barang_ke = st.selectbox("Barang Urutan Ke-", [f"Barang Ke-{i}" for i in range(1, qty_total + 1)])
            lokasi_spesifik = st.text_input("Lokasi Spesifik Saat Ini (Misal: Lab TKJ 2)")
            deskripsi_rusak = st.text_area("Deskripsi Kerusakan Fisik")
            
            btn_kirim = st.form_submit_button("🚨 Kirim Pengaduan Kerusakan")
            
            if btn_kirim:
                if not nama_pelapor or not deskripsi_rusak:
                    st.error("Nama Pelapor dan Deskripsi Kerusakan wajib diisi!")
                else:
                    timestamp_now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    sheet_lapor.append_row([
                        timestamp_now, id_public, aset_terpilih.get('Nama Komponen', '-'),
                        barang_ke, lokasi_spesifik, deskripsi_rusak, nama_pelapor,
                        nip_pelapor, "Foto Bukti Terlampir", "Menunggu Tindakan", "Tidak"
                    ])
                    st.cache_data.clear()
                    st.success("✅ Laporan kerusakan berhasil terkirim ke Pengurus Barang!")
    else:
        st.error("❌ Kode Registrasi Inventaris BMD Tidak Valid.")
        st.info("💡 Pastikan data aset sudah tersimpan di database sebelum scan QR Code.")
    st.stop()

# ==========================================
# 4. HALAMAN LOGIN INTERNAL
# ==========================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""

if not st.session_state.logged_in:
    st.markdown("<h2 style='text-align: center;'>SI-PINTU 56</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Sistem Inventaris Aset Digital - SMKN 56 Jakarta</p>", unsafe_allow_html=True)
    
    col_a, col_b, col_c = st.columns([1, 2, 1])
    with col_b:
        with st.form("login_form"):
            user_input = st.text_input("Username")
            pass_input = st.text_input("Password", type="password")
            submit = st.form_submit_button("Masuk ke Sistem")
            
            if submit:
                users_data = fetch_records("Users")
                is_valid = False
                for u in users_data:
                    if str(u.get("Username")).strip() == user_input.strip() and str(u.get("Password")).strip() == pass_input.strip():
                        is_valid = True
                        break
                
                if is_valid:
                    st.session_state.logged_in = True
                    st.session_state.username = user_input
                    st.rerun()
                else:
                    st.error("Login Gagal. Cek Username & Password!")
    st.stop()

# ==========================================
# 5. LOAD DATA KE SESSION STATE (1× SETELAH LOGIN)
# ==========================================
if 'data_arsip' not in st.session_state:
    with st.spinner("⏳ Memuat data inventaris ke memori..."):
        st.session_state.data_arsip = fetch_records("Data_Arsip")
        st.session_state.data_sensus = fetch_records("Data_Sensus")
        st.session_state.data_lapor = fetch_records("Data_Laporan_Rusak")
        st.session_state.data_users = fetch_records("Users")

# ==========================================
# 6. DASHBOARD UTAMA
# ==========================================
st.sidebar.title("SI-PINTU 56")
st.sidebar.write(f"👤 User: **{st.session_state.username}**")

if st.sidebar.button("🔄 Refresh Data"):
    with st.spinner("⏳ Memuat ulang data..."):
        st.session_state.data_arsip = fetch_records("Data_Arsip")
        st.session_state.data_sensus = fetch_records("Data_Sensus")
        st.session_state.data_lapor = fetch_records("Data_Laporan_Rusak")
        st.session_state.data_users = fetch_records("Users")
    st.rerun()

menu = st.sidebar.radio(
    "Navigasi Menu:",
    ["📥 Input Data Aset", "📋 Daftar Output & QR", "📊 Sensus Berkala", "🚨 Laporan Kerusakan (CRM)"]
)

if st.sidebar.button("🚪 Keluar Sistem"):
    st.session_state.logged_in = False
    st.session_state.username = ""
    for key in ['data_arsip', 'data_sensus', 'data_lapor', 'data_users']:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()

# ------------------------------------------
# MENU 1: INPUT DATA ASET
# ------------------------------------------
if menu == "📥 Input Data Aset":
    st.header("Input Deskripsi Aset Baru")
    st.divider()

    col_top1, col_top2, col_top3 = st.columns(3)
    with col_top1:
        klasifikasi = st.selectbox("Klasifikasi / Kategori", ["KIB B - Peralatan & Mesin", "KIB C - Gedung & Bangunan", "KIB E - Aset Tetap Lainnya"])
        asal = st.selectbox("Asal Perolehan", ["BOS", "BOP", "KAPITALISASI BOS", "KAPITALISASI BOP", "Hibah", "Lainnya"])
        sub_asal = st.text_input("Sub Perolehan", placeholder="Contoh: TW ... / SEMESTER ...")

    with col_top2:
        nama_komponen = st.text_input("Nama Komponen*", placeholder="Contoh: Switch Hub Ruijie 8 Port")
        harga_satuan = st.number_input("Harga Satuan", min_value=0, value=0, step=1000)
        penyedia = st.text_input("Penyedia", placeholder="Nama Perusahaan/Penyedia")

    with col_top3:
        kode_barang = st.text_input("Kode Komponen", placeholder="Contoh: 132100203003...")
        qty = st.number_input("Quantity", min_value=1, value=1, step=1)
        total_harga = harga_satuan * qty
        st.text_input("Jumlah Total", value=f"Rp {total_harga:,.0f}", disabled=True)

    st.write("")
    col_mid1, col_mid2, col_mid3 = st.columns(3)
    with col_mid1:
        tahun_pengadaan = st.text_input("📅 Tahun Pengadaan", value="2026")
    with col_mid2:
        semester = st.selectbox("🌖 Semester", ["SEMESTER I", "SEMESTER II"])
    with col_mid3:
        tw = st.selectbox("⏱️ Triwulan", ["TW I", "TW II", "TW III", "TW IV"])
