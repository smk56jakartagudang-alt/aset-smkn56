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
GOOGLE_DRIVE_FOLDER_ID = "1qsgab2n8wN0NYDCzel4nHlc1nKAieyjU"

# ==========================================
# 2. KONEKSI GOOGLE API
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

# ==========================================
# OPTIMASI: CACHE DI SESSION STATE
# ==========================================
def get_cached_records(sheet_name, force_refresh=False):
    cache_key = f"records_{sheet_name}"
    if force_refresh or cache_key not in st.session_state:
        with st.spinner(f"🔄 Memuat data {sheet_name}..."):
            s_users, s_arsip, s_sensus, s_lapor, _ = get_services()
            if sheet_name == "Users":
                st.session_state[cache_key] = s_users.get_all_records()
            elif sheet_name == "Data_Arsip":
                st.session_state[cache_key] = s_arsip.get_all_records()
            elif sheet_name == "Data_Sensus":
                st.session_state[cache_key] = s_sensus.get_all_records()
            elif sheet_name == "Data_Laporan_Rusak":
                st.session_state[cache_key] = s_lapor.get_all_records()
    return st.session_state.get(cache_key, [])

def clear_records_cache(sheet_names=None):
    if sheet_names is None:
        for key in list(st.session_state.keys()):
            if key.startswith("records_"):
                del st.session_state[key]
    else:
        for name in sheet_names:
            key = f"records_{name}"
            if key in st.session_state:
                del st.session_state[key]

def get_sheet_object(sheet_name):
    s_users, s_arsip, s_sensus, s_lapor, _ = get_services()
    if sheet_name == "Users":
        return s_users
    elif sheet_name == "Data_Arsip":
        return s_arsip
    elif sheet_name == "Data_Sensus":
        return s_sensus
    elif sheet_name == "Data_Laporan_Rusak":
        return s_lapor
    return None

def get_drive_service():
    return get_services()[4]

# ==========================================
# FUNGSI UPLOAD KE GOOGLE DRIVE
# ==========================================
def upload_file_to_drive(file_uploaded, custom_filename, folder_id):
    try:
        ext = file_uploaded.name.split('.')[-1]
        final_filename = f"{custom_filename}.{ext}"
        final_filename = re.sub(r'[/\\:*?"<>|]', '_', final_filename)
        
        file_metadata = {'name': final_filename, 'parents': [folder_id]}
        media = MediaIoBaseUpload(BytesIO(file_uploaded.getvalue()), mimetype=file_uploaded.type, resumable=True)
        
        drive_service = get_drive_service()
        uploaded_file = drive_service.files().create(
            body=file_metadata, media_body=media, fields='id, webViewLink', supportsAllDrives=True
        ).execute()
        
        try:
            drive_service.permissions().create(
                fileId=uploaded_file.get('id'), body={'role': 'reader', 'type': 'anyone'}, supportsAllDrives=True
            ).execute()
        except Exception:
            pass
        
        return uploaded_file.get('webViewLink')
        
    except Exception as e:
        error_str = str(e)
        if "storageQuotaExceeded" in error_str:
            return "ERROR::KUOTA_PENUH"
        elif "notFound" in error_str and "parents" in error_str:
            return "ERROR::FOLDER_SALAH"
        else:
            return f"ERROR::{error_str[:120]}"

def render_file_display(url_or_name, label="Lihat Berkas"):
    val_str = str(url_or_name).strip()
    if val_str.startswith("http://") or val_str.startswith("https://"):
        st.markdown(f'<a href="{val_str}" target="_blank" style="text-decoration:none;"><button style="background-color:#007BFF;color:white;border:none;padding:6px 14px;border-radius:6px;cursor:pointer;font-size:13px;font-weight:bold;">🔗 {label}</button></a>', unsafe_allow_html=True)
    elif val_str and val_str != "Tidak ada file":
        st.info(f"📄 Berkas Terdaftar: **{val_str}**")
    else:
        st.caption("🔴 Belum ada file fisiknya")

# ==========================================
# 3. DETEKSI AKSES PUBLIC SCAN QR CODE
# ==========================================
query_params = st.query_params
id_public = query_params.get("id", None)

if id_public:
    st.title("📋 SI-PINTU 56 - Detail Inventaris")
    st.caption("Sistem Informasi Manajemen Pelacakan BMD Internal SMK Negeri 56 Jakarta")
    
    data_arsip = get_cached_records("Data_Arsip")
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
                    sheet_lapor = get_sheet_object("Data_Laporan_Rusak")
                    sheet_lapor.append_row([
                        timestamp_now, id_public, aset_terpilih.get('Nama Komponen', '-'),
                        barang_ke, lokasi_spesifik, deskripsi_rusak, nama_pelapor,
                        nip_pelapor, "Foto Bukti Terlampir", "Menunggu Tindakan", "Tidak"
                    ])
                    clear_records_cache(["Data_Laporan_Rusak"])
                    st.success("✅ Laporan kerusakan berhasil terkirim ke Pengurus Barang!")
    else:
        st.error("❌ Kode Registrasi Inventaris BMD Tidak Valid.")
        st.info("💡 Petunjuk: Pastikan data aset ini sudah tersimpan di database sebelum membuat/men-scan QR Code.")
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
                users_data = get_cached_records("Users")
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
# 5. DASHBOARD UTAMA
# ==========================================
st.sidebar.title("SI-PINTU 56")
st.sidebar.write(f"👤 User: **{st.session_state.username}**")

menu = st.sidebar.radio(
    "Navigasi Menu:",
    ["📥 Input Data Aset", "📋 Daftar Output & QR", "📊 Sensus Berkala", "🚨 Laporan Kerusakan (CRM)"]
)

st.sidebar.divider()
if st.sidebar.button("🔄 Refresh Data"):
    clear_records_cache()
    st.success("Cache dibersihkan! Data akan di-fetch ulang.")
    st.rerun()

if st.sidebar.button("🚪 Keluar Sistem"):
    st.session_state.logged_in = False
    st.session_state.username = ""
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
        sub_asal = st.text_input("Sub Perolehan", placeholder="Contoh: TW ... / SEMESTER ... / TAHUN...")

    with col_top2:
        nama_komponen = st.text_input("Nama Komponen*", placeholder="Contoh: Switch Hub Ruijie 8 Port")
        harga_satuan = st.number_input("Harga Satuan", min_value=0, value=0, step=1000)
        penyedia = st.text_input("Penyedia", placeholder="Masukkan Nama Perusahaan/Penyedia")

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

    st.write("")
    st.markdown("**📍 Alokasi Penempatan Barang Berdasarkan Jumlah Qty**")
    alokasi_list = []
    for i in range(int(qty)):
        loc = st.text_input(f"Barang {i+1}", placeholder=f"Lokasi Penempatan / Ruangan Barang ke-{i+1}", key=f"loc_{i}")
        if loc:
            alokasi_list.append(f"[Brg {i+1}: {loc}]")
    alokasi_combined = " ".join(alokasi_list) if alokasi_list else "-"

    st.divider()

    col_det1, col_det2, col_det3, col_det4 = st.columns(4)
    with col_det1:
        kondisi = st.selectbox("Kondisi", ["Baik", "Kurang Baik", "Rusak Berat"])
    with col_det2:
        merk = st.text_input("Merk")
    with col_det3:
        type_barang = st.text_input("Type")
    with col_det4:
        tgl_perolehan = st.date_input("Tanggal Perolehan")

    col_b1, col_b2 = st.columns(2)
    with col_b1:
        bahan = st.text_input("Bahan", placeholder="Contoh: Kayu, Besi, Plastik, Aluminium, Campuran")
    with col_b2:
        no_seri = st.text_input("No. Seri / Pabrik", placeholder="Masukkan nomor seri pabrikan jika ada")

    col_s1, col_s2 = st.columns(2)
    with col_s1:
        spesifikasi = st.text_area("Spesifikasi", placeholder="Sesuaikan Dengan ERKAS...")
    with col_s2:
        keterangan_utama = st.text_area("Keterangan Utama", placeholder="Tulis catatan tambahan utama di sini jika ada...")

    col_f1, col_f2 = st.columns(2)
    with col_f1:
        no_bast = st.text_input("BAST", placeholder="BAST/STRS-0022")
    with col_f2:
        tgl_bast = st.date_input("Tanggal BAST")

    col_up1, col_up2 = st.columns(2)
    with col_up1:
        foto_gabungan = st.file_uploader("📸 Foto Aset (Gambar - Gabungan)", type=["jpg", "jpeg", "png"])
    with col_up2:
        foto_satuan = st.file_uploader("📸 Foto Aset Satuan (Siera / Perwakilan)", type=["jpg", "jpeg", "png"])

    dokumen_pdf = st.file_uploader("📄 Dokumen Pendukung (PDF SPJ)", type=["pdf"])

    st.write("")
    btn_simpan = st.button("Simpan Data Ke Sistem", type="primary")

    if btn_simpan:
        if not nama_komponen:
            st.error("Nama Komponen wajib diisi!")
        else:
            timestamp_id = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            alokasi_full = f"{alokasi_combined} || KET: {keterangan_utama}" if keterangan_utama else alokasi_combined
            base_auto_filename = f"{tahun_pengadaan}_{asal}_{nama_komponen}_{semester}_{tw}_{no_bast}"
            
            val_fgab = "Tidak ada file"
            val_fsat = "Tidak ada file"
            val_pdf = "Tidak ada file"
            failed_uploads = []
            
            with st.spinner("⏳ Mengunggah file fisik langsung ke Google Drive..."):
                if foto_gabungan:
                    link_gab = upload_file_to_drive(foto_gabungan, f"{base_auto_filename}_FOTO_GABUNGAN", GOOGLE_DRIVE_FOLDER_ID)
                    if link_gab and link_gab.startswith("http"):
                        val_fgab = link_gab
                    elif link_gab == "ERROR::KUOTA_PENUH":
                        failed_uploads.append("Foto Gabungan (Kuota PENUH)")
                    elif link_gab == "ERROR::FOLDER_SALAH":
                        failed_uploads.append("Foto Gabungan (Folder tidak ditemukan)")
                    else:
                        failed_uploads.append("Foto Gabungan")
                        
                if foto_satuan:
                    link_sat = upload_file_to_drive(foto_satuan, f"{base_auto_filename}_FOTO_SATUAN", GOOGLE_DRIVE_FOLDER_ID)
                    if link_sat and link_sat.startswith("http"):
                        val_fsat = link_sat
                    elif link_sat == "ERROR::KUOTA_PENUH":
                        failed_uploads.append("Foto Satuan (Kuota PENUH)")
                    elif link_sat == "ERROR::FOLDER_SALAH":
                        failed_uploads.append("Foto Satuan (Folder tidak ditemukan)")
                    else:
                        failed_uploads.append("Foto Satuan")
                        
                if dokumen_pdf:
                    link_pdf = upload_file_to_drive(dokumen_pdf, f"{base_auto_filename}_DOKUMEN_SPJ", GOOGLE_DRIVE_FOLDER_ID)
                    if link_pdf and link_pdf.startswith("http"):
                        val_pdf = link_pdf
                    elif link_pdf == "ERROR::KUOTA_PENUH":
                        failed_uploads.append("Dokumen PDF (Kuota PENUH)")
                    elif link_pdf == "ERROR::FOLDER_SALAH":
                        failed_uploads.append("Dokumen PDF (Folder tidak ditemukan)")
                    else:
                        failed_uploads.append("Dokumen PDF")

            sheet_arsip = get_sheet_object("Data_Arsip")
            sheet_arsip.append_row([
                nama_komponen, klasifikasi, kode_barang, harga_satuan, qty, total_harga,
                str(tgl_perolehan), asal, sub_asal, kondisi, merk, type_barang,
                spesifikasi, no_bast, str(tgl_bast), penyedia, tahun_pengadaan,
                semester, tw, alokasi_full, bahan, no_seri, val_fgab, val_pdf,
                st.session_state.username, val_fsat, timestamp_id
            ])
            
            clear_records_cache(["Data_Arsip"])
            st.success(f"✅ Data Aset '{nama_komponen}' Berhasil Disimpan!")
            
            if failed_uploads:
                st.error("❌ UPLOAD FILE GAGAL!")
                st.warning(
                    f"File yang gagal: {', '.join(failed_uploads)}.\n\n"
                    "Pastikan akun service account baru sudah di-share ke Google Sheet & Folder Drive."
                )
            
            qr_link = f"{BASE_URL}?id={timestamp_id}"
            qr = qrcode.make(qr_link)
            buf = BytesIO()
            qr.save(buf)
            st.image(buf.getvalue(), caption=f"QR Code untuk {nama_komponen}", width=200)
            st.code(qr_link, language="text")

# ------------------------------------------
# MENU 2: DAFTAR OUTPUT & QR CODE
# ------------------------------------------
elif menu == "📋 Daftar Output & QR":
    st.header("📋 Hasil Rekonsiliasi & Output Data Inventaris")
    st.caption("Menampilkan ringkasan data inventaris aset SMKN 56 Jakarta beserta akses langsung berkas foto/PDF & QR Code.")
    st.divider()
    
    records = get_cached_records("Data_Arsip")
    if records:
        df = pd.DataFrame(records)
        st.dataframe(df, use_container_width=True, height=300)
        st.divider()

        st.subheader("🔎 Detail Aset, QR Code & Berkas Terkait")
        
        id_options = []
        for idx, r in enumerate(records):
            id_val = str(r.get("Timestamp", "")).strip() or str(r.get("Kode Komponen", "")).strip()
            if id_val:
                id_options.append(f"{idx+2} | {r.get('Nama Komponen', '')} ({id_val})")
                
        if id_options:
            selected_option = st.selectbox("📌 Pilih Aset untuk Melihat Detail, QR Code, dan Mengelola Berkas Fisik:", id_options)
            row_num = int(selected_option.split(" | ")[0])
            target_item = records[row_num - 2]
            selected_id = str(target_item.get("Timestamp", "")).strip() or str(target_item.get("Kode Komponen", "")).strip()
            
            c_qr, c_media, c_up = st.columns([1, 1.3, 1.3])
            
            with c_qr:
                st.markdown("##### 📱 QR Code Inventaris")
                qr_link = f"{BASE_URL}?id={selected_id}"
                qr = qrcode.make(qr_link)
                buf = BytesIO()
                qr.save(buf)
                st.image(buf.getvalue(), width=160)
                st.markdown(f"Direct Link: [{qr_link}]({qr_link})")

            with c_media:
                st.markdown("##### 📂 Berkas & Dokumen Terlampir")
                fgab = target_item.get('Foto Aset (Gambar - Gabungan)', '')
                fsat = target_item.get('Foto Aset Satuan (Siera / Perwakilan)', '')
                fpdf = target_item.get('Dokumen Pendukung (PDF)', '')

                st.write("**Foto Aset Gabungan:**")
                render_file_display(fgab, "Buka Foto Gabungan")
                st.write("")
                
                st.write("**Foto Aset Satuan:**")
                render_file_display(fsat, "Buka Foto Satuan")
                st.write("")
                
                st.write("**Dokumen PDF / SPJ:**")
                render_file_display(fpdf, "Buka Dokumen PDF/SPJ")

            with c_up:
                st.markdown("##### 🔄 Update Berkas / SPJ Aset Ke Drive")
                with st.form("form_update_media_links"):
                    file_upload_gab = st.file_uploader("Upload Foto Gabungan Baru", type=["jpg", "jpeg", "png"], key="up_file_gab")
                    file_upload_sat = st.file_uploader("Upload Foto Satuan Baru", type=["jpg", "jpeg", "png"], key="up_file_sat")
                    file_upload_pdf = st.file_uploader("Upload File PDF SPJ Baru", type=["pdf"], key="up_file_pdf")
                    
                    btn_update_file = st.form_submit_button("💾 Simpan Berkas Baru ke Drive")
                    
                    if btn_update_file:
                        base_auto_filename = f"{target_item.get('Tahun Pengadaan')}_{target_item.get('Asal perolehan')}_{target_item.get('Nama Komponen')}_{target_item.get('Semester')}_{target_item.get('Triwulan')}_{target_item.get('BAST')}"
                        update_errors = []
                        
                        with st.spinner("⏳ Mengunggah file ke Google Drive..."):
                            sheet_arsip = get_sheet_object("Data_Arsip")
                            
                            if file_upload_gab:
                                link_gab = upload_file_to_drive(file_upload_gab, f"{base_auto_filename}_FOTO_GABUNGAN", GOOGLE_DRIVE_FOLDER_ID)
                                if link_gab and link_gab.startswith("http"):
                                    sheet_arsip.update_cell(row_num, 23, link_gab)
                                else:
                                    update_errors.append("Foto Gabungan")
                                    
                            if file_upload_pdf:
                                link_pdf = upload_file_to_drive(file_upload_pdf, f"{base_auto_filename}_DOKUMEN_SPJ", GOOGLE_DRIVE_FOLDER_ID)
                                if link_pdf and link_pdf.startswith("http"):
                                    sheet_arsip.update_cell(row_num, 24, link_pdf)
                                else:
                                    update_errors.append("Dokumen PDF")
                                    
                            if file_upload_sat:
                                link_sat = upload_file_to_drive(file_upload_sat, f"{base_auto_filename}_FOTO_SATUAN", GOOGLE_DRIVE_FOLDER_ID)
                                if link_sat and link_sat.startswith("http"):
                                    sheet_arsip.update_cell(row_num, 26, link_sat)
                                else:
                                    update_errors.append("Foto Satuan")
                                    
                        clear_records_cache(["Data_Arsip"])
                        
                        if update_errors:
                            st.error("❌ Upload gagal: " + ", ".join(update_errors))
                            st.warning("Pastikan akun service account baru sudah di-share ke Google Sheet & Folder Drive.")
                        else:
                            st.success("✅ Berkas berhasil diunggah ke Google Drive dan link tersimpan!")
                        st.rerun()
    else:
        st.info("Belum ada data rekon aset.")

# ------------------------------------------
# MENU 3: SENSUS BERKALA
# ------------------------------------------
elif menu == "📊 Sensus Berkala":
    st.title("📊 Monitoring & Sensus Berkala Kondisi Aset")
    
    records_arsip = get_cached_records("Data_Arsip")
    records_sensus = get_cached_records("Data_Sensus")
    
    f_col1, f_col2, f_col3 = st.columns(3)
    with f_col1:
        f_tahun_sensus = st.selectbox("📅 Filter Tahun Sensus:", [2026, 2025, 2024, 2027])
    with f_col2:
        f_periode_sensus = st.selectbox("⏱️ Filter Periode:", ["Triwulan I (Q1)", "Triwulan II (Q2)", "Triwulan III (Q3)", "Triwulan IV (Q4)", "Semester I", "Semester II", "Sensus Tahunan"])
    with f_col3:
        tahun_aset_options = ["Semua Tahun"]
        if records_arsip:
            tahun_set = sorted(list(set([str(r.get("Tahun Pengadaan", "")).strip() for r in records_arsip if r.get("Tahun Pengadaan")])), reverse=True)
            tahun_aset_options.extend(tahun_set)
        f_tahun_pengadaan = st.selectbox("📦 Filter Tahun Pengadaan Aset:", tahun_aset_options)

    label_periode_filter = f"{f_periode_sensus} - {f_tahun_sensus}"

    filtered_arsip = records_arsip
    if f_tahun_pengadaan != "Semua Tahun":
        filtered_arsip = [r for r in records_arsip if str(r.get("Tahun Pengadaan", "")).strip() == f_tahun_pengadaan]

    sensus_done_ids = [str(s.get("ID Aset", "")).strip().lower() for s in records_sensus if str(s.get("Periode Sensus", "")).strip() == label_periode_filter]

    total_komponen = len(filtered_arsip)
    sudah_sensus_count = len([r for r in filtered_arsip if str(r.get("Timestamp", "")).strip().lower() in sensus_done_ids])
    belum_sensus_count = total_komponen - sudah_sensus_count
    capaian_pct = int((sudah_sensus_count / total_komponen) * 100) if total_komponen > 0 else 0

    st.write("")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("TOTAL KOMPONEN ASET", f"{total_komponen} Komponen")
    m2.metric("SUDAH TER-SENSUS", f"{sudah_sensus_count} Item")
    m3.metric("BELUM TER-SENSUS", f"{belum_sensus_count} Item")
    m4.metric("CAPAIAN PROGRESS", f"{capaian_pct}%")

    st.divider()
    st.subheader("📑 Tabel Pelaksanaan Sensus Komponen")

    if not filtered_arsip:
        st.info("Tidak ada data aset yang sesuai dengan filter.")
    else:
        th1, th2, th3, th4, th5, th6, th7 = st.columns([2.5, 2, 2, 1.2, 1.5, 2, 2])
        th1.markdown("**Nama Komponen**")
        th2.markdown("**Kategori**")
        th3.markdown("**Kode Komponen**")
        th4.markdown("**Quantity**")
        th5.markdown("**Thn Pengadaan**")
        th6.markdown("**Status Periode Ini**")
        th7.markdown("**Aksi Sensus**")
        st.divider()

        if "selected_sensus_id" not in st.session_state:
            st.session_state.selected_sensus_id = None

        for item in filtered_arsip:
            item_id = str(item.get("Timestamp", "")).strip() or str(item.get("Kode Komponen", "")).strip()
            is_done = item_id.lower() in sensus_done_ids
            
            tc1, tc2, tc3, tc4, tc5, tc6, tc7 = st.columns([2.5, 2, 2, 1.2, 1.5, 2, 2])
            tc1.write(item.get("Nama Komponen", "-"))
            tc2.write(item.get("Kategori", "-"))
            tc3.write(f"`{item.get('Kode Komponen', '-')}`")
            tc4.write(f"{item.get('Quantity', 1)} Unit")
            tc5.write(str(item.get("Tahun Pengadaan", "-")))
            
            if is_done:
                tc6.success("✅ Sudah Disensus")
            else:
                tc6.error("🔴 Belum Disensus")
                
            if tc7.button("🔍 Mulai Sensus", key=f"btn_sensus_{item_id}"):
                st.session_state.selected_sensus_id = item_id

        if st.session_state.selected_sensus_id:
            target_aset = next((r for r in records_arsip if (str(r.get("Timestamp", "")).strip() == st.session_state.selected_sensus_id or str(r.get("Kode Komponen", "")).strip() == st.session_state.selected_sensus_id)), None)
            
            if target_aset:
                st.divider()
                st.subheader(f"📝 Form Verifikasi Sensus: {target_aset.get('Nama Komponen', '-')} ({target_aset.get('Kode Komponen', '-')})")
                st.caption(f"ID Aset: {st.session_state.selected_sensus_id} | Periode: {label_periode_filter}")

                with st.form("form_sensus_detail"):
                    c_s1, c_s2 = st.columns(2)
                    with c_s1:
                        lokasi_terkini = st.text_input("Lokasi / Ruangan Terkini Lapangan", placeholder="Contoh: Lab Komputer 1 / Ruang Guru")
                        kondisi_terkini = st.selectbox("Kondisi Fisik Terkini", ["Baik", "Kurang Baik", "Rusak Berat"])
                    with c_s2:
                        catatan_sensus = st.text_area("Catatan Pemeriksaan Khusus Sensus", placeholder="Tuliskan temuan pemeriksaan fisik di sini...")
                        foto_sensus = st.file_uploader("📸 Upload Foto Bukti Sensus Lapangan", type=["jpg", "jpeg", "png"])

                    btn_simpan_sensus = st.form_submit_button("💾 Simpan Hasil Verifikasi Sensus Lapangan")

                    if btn_simpan_sensus:
                        timestamp_now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        
                        val_foto_sensus = "Tanpa Foto"
                        if foto_sensus:
                            base_auto_filename = f"SENSUS_{target_aset.get('Tahun Pengadaan')}_{target_aset.get('Nama Komponen')}_{f_periode_sensus}"
                            link_foto_sensus = upload_file_to_drive(foto_sensus, base_auto_filename, GOOGLE_DRIVE_FOLDER_ID)
                            if link_foto_sensus and link_foto_sensus.startswith("http"):
                                val_foto_sensus = link_foto_sensus
                            else:
                                st.warning("⚠️ Foto sensus gagal diupload ke Drive, data sensus tetap disimpan tanpa foto.")

                        sheet_sensus = get_sheet_object("Data_Sensus")
                        sheet_sensus.append_row([
                            timestamp_now, st.session_state.selected_sensus_id, 
                            target_aset.get('Nama Komponen', '-'), label_periode_filter,
                            kondisi_terkini, lokasi_terkini, catatan_sensus, 
                            val_foto_sensus, st.session_state.username
                        ])
                        
                        clear_records_cache(["Data_Sensus", "Data_Arsip"])
                        st.session_state.selected_sensus_id = None
                        st.success("✅ Verifikasi Sensus Lapangan Berhasil Disimpan!")
                        st.rerun()

# ------------------------------------------
# MENU 4: LAPORAN KERUSAKAN (CRM)
# ------------------------------------------
elif menu == "🚨 Laporan Kerusakan (CRM)":
    st.header("🚨 Rekap Laporan Kerusakan dari Lapangan")
    
    lapor_data = get_cached_records("Data_Laporan_Rusak")
    if lapor_data:
        df_lapor = pd.DataFrame(lapor_data)
        st.dataframe(df_lapor, use_container_width=True)
    else:
        st.info("Belum ada laporan kerusakan yang masuk.")
