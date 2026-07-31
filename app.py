import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
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

# Domain Resmi Aplikasi SI-PINTU 56
BASE_URL = "https://sipintu-smkn56jakarta.streamlit.app/"

# ==========================================
# 2. KONEKSI GOOGLE SHEETS (CACHED RESOURCE)
# ==========================================
@st.cache_resource
def get_sheets():
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
    client = gspread.authorize(creds)
    
    # ID Spreadsheet Utama
    ss = client.open_by_key("1SXyAvphA5ivL70UVzD49nHfkGBlUGLqiCPaxuDQlGAg")
    
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
    
    return s_users, s_arsip, s_sensus, s_lapor

try:
    sheet_users, sheet_arsip, sheet_sensus, sheet_lapor = get_sheets()
except Exception as e:
    st.error(f"❌ Gagal Terhubung ke Google Sheets: {e}")
    st.caption("Pastikan email 'sipintu-bot@si-pintu-56.iam.gserviceaccount.com' sudah dijadikan Editor pada Google Sheets Anda.")
    st.stop()

# ==========================================
# FUNGSI CACHING DATA UNTUK HEMAT QUOTA
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

# Helper untuk menampilkan fisik berkas & tombol link
def render_file_display(url_or_name, label="Lihat Berkas"):
    val_str = str(url_or_name).strip()
    if val_str.startswith("http://") or val_str.startswith("https://"):
        st.markdown(f'<a href="{val_str}" target="_blank" style="text-decoration:none;"><button style="background-color:#007BFF;color:white;border:none;padding:6px 14px;border-radius:6px;cursor:pointer;font-size:13px;font-weight:bold;">🔗 {label}</button></a>', unsafe_allow_html=True)
        # Jika link berupa direktori gambar
        if any(ext in val_str.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']):
            st.image(val_str, width=220)
    elif val_str and val_str != "Tidak ada file":
        st.info(f"📄 Berkas Terdaftar: **{val_str}**")
        st.caption("💡 Petunjuk: Masukkan link URL Google Drive/Imgur file pada menu update di samping agar fisik foto/PDF muncul langsung.")
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
        st.subheader(f"📦 {aset_terpilih.get('Nama Komponen', '-')}")
        
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Kategori:** {aset_terpilih.get('Kategori', '-')}")
            st.write(f"**Kode Komponen:** `{aset_terpilih.get('Kode Komponen', '-')}`")
            st.write(f"**Asal Perolehan:** {aset_terpilih.get('Asal perolehan', '-')}")
            st.write(f"**Tahun Pengadaan:** {aset_terpilih.get('Tahun Pengadaan', '-')}")
            st.write(f"**Kondisi Fisik:** {aset_terpilih.get('Kondisi', '-')}")
        with col2:
            st.write(f"**Semester / Triwulan:** {aset_terpilih.get('Semester', '-')} / {aset_terpilih.get('Triwulan', '-')}")
            st.write(f"**BAST:** {aset_terpilih.get('BAST', '-')}")
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
# 5. DASHBOARD UTAMA (SETELAH LOGIN)
# ==========================================
st.sidebar.title("SI-PINTU 56")
st.sidebar.write(f"👤 User: **{st.session_state.username}**")

menu = st.sidebar.radio(
    "Navigasi Menu:",
    ["📥 Input Data Aset", "📋 Daftar Output & QR", "📊 Sensus Berkala", "🚨 Laporan Kerusakan (CRM)"]
)

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
        nama_komponen = st.text_input("Nama Komponen*", placeholder="Contoh: PC DELL / Meja Siswa")
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
        tahun_pengadaan = st.text_input("📅 Tahun Pengadaan", placeholder="Contoh: 2026")
    with col_mid2:
        semester = st.selectbox("🌖 Semester", ["-- Pilih Semester --", "SEMESTER I", "SEMESTER II"])
    with col_mid3:
        tw = st.selectbox("⏱️ Triwulan", ["-- Pilih Triwulan --", "TW I", "TW II", "TW III", "TW IV"])

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
        no_bast = st.text_input("BAST")
    with col_f2:
        tgl_bast = st.date_input("Tanggal BAST")

    st.markdown("##### 🔗 Tautan Link Berkas Fisik (Google Drive / Imgur)")
    st.caption("Tempelkan link share Google Drive atau URL gambar publik agar fisik foto & PDF langsung muncul di menu output.")
    
    col_up1, col_up2 = st.columns(2)
    with col_up1:
        link_foto_gab = st.text_input("🔗 Link Foto Aset Gabungan (URL / Google Drive)")
    with col_up2:
        link_foto_sat = st.text_input("🔗 Link Foto Aset Satuan (URL / Google Drive)")

    link_doc_pdf = st.text_input("🔗 Link Dokumen Pendukung SPJ (PDF Drive)")

    st.write("")
    btn_simpan = st.button("Simpan Data Ke Sistem", type="primary")

    if btn_simpan:
        if not nama_komponen:
            st.error("Nama Komponen wajib diisi!")
        else:
            timestamp_id = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            alokasi_full = f"{alokasi_combined} || KET: {keterangan_utama}" if keterangan_utama else alokasi_combined
            
            val_fgab = link_foto_gab if link_foto_gab else "Tidak ada file"
            val_fsat = link_foto_sat if link_foto_sat else "Tidak ada file"
            val_pdf = link_doc_pdf if link_doc_pdf else "Tidak ada file"

            sheet_arsip.append_row([
                nama_komponen,          # A
                klasifikasi,            # B
                kode_barang,            # C
                harga_satuan,           # D
                qty,                    # E
                total_harga,            # F
                str(tgl_perolehan),     # G
                asal,                   # H
                sub_asal,               # I
                kondisi,                # J
                merk,                   # K
                type_barang,            # L
                spesifikasi,            # M
                no_bast,                # N
                str(tgl_bast),          # O
                penyedia,               # P
                tahun_pengadaan,        # Q
                semester,               # R
                tw,                     # S
                alokasi_full,           # T
                bahan,                  # U
                no_seri,                # V
                val_fgab,               # W
                val_pdf,                # X
                st.session_state.username, # Y
                val_fsat,               # Z
                timestamp_id            # AA
            ])
            
            st.cache_data.clear()
            st.success(f"✅ Data Aset '{nama_komponen}' Berhasil Disimpan Ke Spreadsheet!")
            
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
    
    records = fetch_records("Data_Arsip")
    if records:
        df = pd.DataFrame(records)
        
        # 1. TABEL ELEGAN DENGAN LEBAR KONTAINER RAPI
        st.dataframe(df, use_container_width=True, height=300)
        st.divider()

        # 2. PANEL DETAIL & PRATINJAU DENGAN CARD VIEW 3 KOLOM
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
            
            # KOLOM 1: QR CODE
            with c_qr:
                st.markdown("##### 📱 QR Code Inventaris")
                qr_link = f"{BASE_URL}?id={selected_id}"
                qr = qrcode.make(qr_link)
                buf = BytesIO()
                qr.save(buf)
                st.image(buf.getvalue(), width=160)
                st.markdown(f"Direct Link: [{qr_link}]({qr_link})")

            # KOLOM 2: BERKAS FOTO & PDF (DENGAN PEMERIKSAAN FISIK)
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

            # KOLOM 3: FORM UPDATE/GANTI LINK BERKAS/FILE
            with c_up:
                st.markdown("##### 🔄 Update Berkas / Link Drive SPJ")
                st.caption("Masukkan link Google Drive / URL file baru untuk memperbarui file fisik tanpa menginput ulang data aset.")
                
                with st.form("form_update_media_links"):
                    new_link_gab = st.text_input("Link Foto Gabungan Baru (URL Drive)", value=str(fgab) if str(fgab).startswith("http") else "")
                    new_link_sat = st.text_input("Link Foto Satuan Baru (URL Drive)", value=str(fsat) if str(fsat).startswith("http") else "")
                    new_link_pdf = st.text_input("Link Dokumen PDF SPJ Baru (URL Drive)", value=str(fpdf) if str(fpdf).startswith("http") else "")
                    
                    file_upload_gab = st.file_uploader("Atau Upload File Foto Gabungan Baru", type=["jpg", "jpeg", "png"], key="up_file_gab")
                    file_upload_pdf = st.file_uploader("Atau Upload File PDF SPJ Baru", type=["pdf"], key="up_file_pdf")
                    
                    btn_update_file = st.form_submit_button("💾 Simpan Berkas / Link Baru")
                    
                    if btn_update_file:
                        val_to_save_gab = file_upload_gab.name if file_upload_gab else new_link_gab
                        val_to_save_pdf = file_upload_pdf.name if file_upload_pdf else new_link_pdf
                        val_to_save_sat = new_link_sat
                        
                        if val_to_save_gab:
                            sheet_arsip.update_cell(row_num, 23, val_to_save_gab) # Kolom W
                        if val_to_save_pdf:
                            sheet_arsip.update_cell(row_num, 24, val_to_save_pdf) # Kolom X
                        if val_to_save_sat:
                            sheet_arsip.update_cell(row_num, 26, val_to_save_sat) # Kolom Z
                            
                        st.cache_data.clear()
                        st.success("✅ Berkas berhasil diperbarui!")
                        st.rerun()
    else:
        st.info("Belum ada data rekon aset.")

# ------------------------------------------
# MENU 3: SENSUS BERKALA
# ------------------------------------------
elif menu == "📊 Sensus Berkala":
    st.title("📊 Monitoring & Sensus Berkala Kondisi Aset")
    
    records_arsip = fetch_records("Data_Arsip")
    records_sensus = fetch_records("Data_Sensus")
    
    f_col1, f_col2, f_col3 = st.columns(3)
    with f_col1:
        f_tahun_sensus = st.selectbox("📅 Filter Tahun Sensus:", [2026, 2025, 2024, 2027])
    with f_col2:
        f_periode_sensus = st.selectbox("⏱️ Filter Periode / Triwulan / Semester:", ["Triwulan I (Q1)", "Triwulan II (Q2)", "Triwulan III (Q3)", "Triwulan IV (Q4)", "Semester I", "Semester II", "Sensus Tahunan"])
    with f_col3:
        tahun_aset_options = ["Semua Tahun"]
        if records_arsip:
            tahun_set = sorted(list(set([str(r.get("Tahun Pengadaan", "")).strip() for r in records_arsip if r.get("Tahun Pengadaan")])))
            tahun_aset_options.extend(tahun_set)
        f_tahun_pengadaan = st.selectbox("📦 Filter Tahun Pengadaan Aset (Rekon):", tahun_aset_options)

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
    st.subheader("📑 Tabel Pelaksanaan Sensus Komponen (Berdasarkan Filter)")

    if not filtered_arsip:
        st.info("Tidak ada data aset yang sesuai dengan filter tahun pengadaan ini.")
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
                st.subheader(f"📝 Form Verifikasi Sensus: {target_aset.get('Nama Komponen', '-')}")
                st.caption(f"ID Aset: {st.session_state.selected_sensus_id} | Periode Sensus Target: {label_periode_filter}")

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
                        nama_foto = foto_sensus.name if foto_sensus else "Tanpa Foto"
                        
                        sheet_sensus.append_row([
                            timestamp_now, 
                            st.session_state.selected_sensus_id, 
                            target_aset.get('Nama Komponen', '-'), 
                            label_periode_filter,
                            kondisi_terkini, 
                            lokasi_terkini, 
                            catatan_sensus, 
                            nama_foto, 
                            st.session_state.username
                        ])
                        
                        st.cache_data.clear()
                        st.session_state.selected_sensus_id = None
                        st.success("✅ Verifikasi Sensus Lapangan Berhasil Disimpan!")
                        st.rerun()

# ------------------------------------------
# MENU 4: LAPORAN KERUSAKAN (CRM)
# ------------------------------------------
elif menu == "🚨 Laporan Kerusakan (CRM)":
    st.header("🚨 Rekap Laporan Kerusakan dari Lapangan")
    
    lapor_data = fetch_records("Data_Laporan_Rusak")
    if lapor_data:
        df_lapor = pd.DataFrame(lapor_data)
        st.dataframe(df_lapor, use_container_width=True)
    else:
        st.info("Belum ada laporan kerusakan yang masuk.")
