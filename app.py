import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import datetime
import qrcode
from io import BytesIO

# ==========================================
# 1. KONFIGURASI HALAMAN & TEMA
# ==========================================
st.set_page_config(
    page_title="SI-PINTU 56 - SMKN 56 Jakarta",
    page_icon="🏫",
    layout="wide"
)

# ==========================================
# 2. KONEKSI GOOGLE SHEETS
# ==========================================
@st.cache_resource
def init_gspread():
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
    return client

try:
    client = init_gspread()
    # PENTING: Ganti tulisan "Database_SiPintu_56" di bawah jika nama file Google Sheets Anda berbeda
    # Buka Spreadsheet menggunakan ID Unik (Lebih stabil dan pasti ketemu)
ss = client.open_by_key("PASTE_KODE_ID_SPREADSHEET_ANDA_DI_SINI") 
except Exception as e:
    st.error(f"❌ Gagal Terhubung ke Google Sheets: {e}")
    st.caption("Pastikan nama spreadsheet sudah sama dan email 'sipintu-bot@si-pintu-56.iam.gserviceaccount.com' sudah dijadikan Editor pada Google Sheets Anda.")
    st.stop()

# Helper untuk membuka / membuat Sheet otomatis
def get_or_create_sheet(sheet_name, headers):
    try:
        return ss.worksheet(sheet_name)
    except:
        ws = ss.add_worksheet(title=sheet_name, rows="1000", cols="30")
        ws.append_row(headers)
        return ws

sheet_users = get_or_create_sheet("Users", ["Username", "Password"])
sheet_arsip = get_or_create_sheet("Data_Arsip", [
    "Timestamp","Nama Komponen", "Klasifikasi", "Kode Barang", "Harga Satuan", 
    "Qty", "Total", "Tgl Perolehan", "Asal", "Sub Asal", "Kondisi", "Merk", 
    "Type", "Spesifikasi", "No BAST", "Tgl BAST", "Penyedia", "Tahun Pengadaan", 
    "Semester", "TW", "Keterangan", "Bahan", "No Seri", "Link Foto", "Link PDF", 
    "Uploader", "Link Foto Satuan"
])
sheet_sensus = get_or_create_sheet("Data_Sensus", [
    "Timestamp Sensus", "ID Aset", "Nama Komponen", "Periode Sensus", 
    "Kondisi Terkini", "Lokasi Terkini", "Catatan Sensus", "Link Foto Sensus", "Petugas Sensus"
])
sheet_lapor = get_or_create_sheet("Data_Laporan_Rusak", [
    "Timestamp Laporan", "ID Aset", "Nama Komponen", "Barang Ke-", 
    "Lokasi Spesifik", "Deskripsi Kerusakan", "Nama Pelapor", "NIP / NIKKI", 
    "Link Foto Bukti", "Status Tindakan", "Dipindahkan ke Gudang ARB"
])

# ==========================================
# 3. DETEKSI AKSES PUBLIC SCAN QR CODE
# ==========================================
query_params = st.query_params
id_public = query_params.get("id", None)

if id_public:
    st.title("📋 SI-PINTU 56 - Detail Inventaris")
    st.caption("Sistem Informasi Manajemen Pelacakan BMD Internal SMK Negeri 56 Jakarta")
    
    data_arsip = sheet_arsip.get_all_records()
    aset_terpilih = None
    
    for item in data_arsip:
        if str(item.get("Timestamp", "")).strip() == str(id_public).strip():
            aset_terpilih = item
            break
            
    if aset_terpilih:
        st.subheader(f"📦 {aset_terpilih.get('Nama Komponen', '-')}")
        
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Klasifikasi:** {aset_terpilih.get('Klasifikasi', '-')}")
            st.write(f"**Kode Barang:** `{aset_terpilih.get('Kode Barang', '-')}`")
            st.write(f"**Asal Perolehan:** {aset_terpilih.get('Asal', '-')}")
            st.write(f"**Tahun Pengadaan:** {aset_terpilih.get('Tahun Pengadaan', '-')}")
        with col2:
            st.write(f"**Semester / TW:** {aset_terpilih.get('Semester', '-')} / {aset_terpilih.get('TW', '-')}")
            st.write(f"**No BAST:** {aset_terpilih.get('No BAST', '-')}")
            st.write(f"**Keterangan / Alokasi:** {aset_terpilih.get('Keterangan', '-')}")

        st.divider()
        st.subheader("🚨 Laporkan Kerusakan Barang Ini (CRM)")
        
        with st.form("form_lapor_publik"):
            nama_pelapor = st.text_input("Nama Lengkap Pelapor")
            nip_pelapor = st.text_input("NIP / NIKKI")
            qty_total = int(aset_terpilih.get("Qty", 1))
            barang_ke = st.selectbox("Barang Urutan Ke-", [f"Barang Ke-{i}" for i in range(1, qty_total + 1)])
            lokasi_spesifik = st.text_input("Lokasi Spesifik Saat Ini (Misal: Lab TKJ 2)")
            deskripsi_rusak = st.text_area("Deskripsi Kerusakan Fisik")
            
            btn_kirim = st.form_submit_button("🚨 Kirim Pengaduan Kerusakan")
            
            if btn_kirim:
                timestamp_now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                sheet_lapor.append_row([
                    timestamp_now, id_public, aset_terpilih.get('Nama Komponen', '-'),
                    barang_ke, lokasi_spesifik, deskripsi_rusak, nama_pelapor,
                    nip_pelapor, "Foto diisi via upload Drive", "Menunggu Tindakan", "Tidak"
                ])
                st.success("✅ Laporan kerusakan berhasil terkirim ke Pengurus Barang!")
    else:
        st.error("❌ Kode Registrasi Inventaris BMD Tidak Valid.")
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
                users_data = sheet_users.get_all_records()
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

BASE_URL = "https://datarekonasetsmkn56jakartapercobaan.streamlit.app/"

# ------------------------------------------
# MENU 1: INPUT DATA ASET
# ------------------------------------------
if menu == "📥 Input Data Aset":
    st.header("Input Deskripsi Aset Baru")
    
    with st.form("form_input_aset"):
        c1, c2, c3 = st.columns(3)
        with c1:
            klasifikasi = st.selectbox("Klasifikasi", ["KIB B - Peralatan & Mesin", "KIB C - Gedung & Bangunan", "KIB E - Aset Tetap Lainnya"])
            nama_komponen = st.text_input("Nama Komponen*", placeholder="PC DELL / Meja Siswa")
            kode_barang = st.text_input("Kode Barang", placeholder="1.3.2.05...")
            asal = st.selectbox("Asal Perolehan", ["BOS", "BOP", "KAPITALISASI BOS", "KAPITALISASI BOP", "Hibah", "Lainnya"])
        
        with c2:
            harga_satuan = st.number_input("Harga Satuan", min_value=0, value=0)
            qty = st.number_input("Quantity", min_value=1, value=1)
            total_harga = harga_satuan * qty
            st.info(f"Total Harga: **Rp {total_harga:,.0f}**")
            sub_asal = st.text_input("Sub Asal", placeholder="TW 1 / SEMESTER 1")
            penyedia = st.text_input("Penyedia / Vendor")

        with c3:
            tahun_pengadaan = st.number_input("Tahun Pengadaan", min_value=2020, max_value=2045, value=2026)
            semester = st.selectbox("Semester", ["SEMESTER I", "SEMESTER II"])
            tw = st.selectbox("Triwulan (TW)", ["TW I", "TW II", "TW III", "TW IV"])
            kondisi = st.selectbox("Kondisi Awal", ["Baik", "Kurang Baik", "Rusak Berat"])

        st.divider()
        st.subheader("Detail Tambahan & Alokasi")
        alokasi_input = st.text_area("Lokasi / Alokasi Penempatan Barang", placeholder="Contoh: [Brg 1: R. Lab 1] [Brg 2: R. Lab 2]")
        keterangan_tambahan = st.text_input("Keterangan Utama")
        
        c4, c5 = st.columns(2)
        with c4:
            merk = st.text_input("Merk")
            type_barang = st.text_input("Type")
            tgl_perolehan = st.date_input("Tanggal Perolehan")
            bahan = st.text_input("Bahan")
        with c5:
            no_seri = st.text_input("No. Seri / Pabrik")
            no_bast = st.text_input("No BAST")
            tgl_bast = st.date_input("Tanggal BAST")
            spesifikasi = st.text_area("Spesifikasi")

        btn_simpan = st.form_submit_button("💾 Simpan Data Ke Sistem")
        
        if btn_simpan:
            if not nama_komponen:
                st.error("Nama Komponen wajib diisi!")
            else:
                timestamp_id = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                gabungan_ket = f"ALOKASI: {alokasi_input} | KET: {keterangan_tambahan}"
                
                sheet_arsip.append_row([
                    timestamp_id, nama_komponen, klasifikasi, kode_barang,
                    harga_satuan, qty, total_harga, str(tgl_perolehan),
                    asal, sub_asal, kondisi, merk, type_barang, spesifikasi,
                    no_bast, str(tgl_bast), penyedia, tahun_pengadaan,
                    semester, tw, gabungan_ket, bahan, no_seri,
                    "Link Foto Auto", "Link PDF Auto", st.session_state.username, "Link Satuan Auto"
                ])
                
                st.success("✅ Data Berhasil Masuk ke Database!")
                
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
    st.header("Daftar Hasil Rekonsiliasi Inventaris")
    
    records = sheet_arsip.get_all_records()
    if records:
        df = pd.DataFrame(records)
        st.dataframe(df, use_container_width=True)
        
        st.divider()
        st.subheader("🖨️ Cetak / Generate QR Code Aset")
        selected_id = st.selectbox("Pilih Aset untuk Dibuat QR Code:", df["Timestamp"].tolist())
        
        if selected_id:
            qr_link = f"{BASE_URL}?id={selected_id}"
            qr = qrcode.make(qr_link)
            buf = BytesIO()
            qr.save(buf)
            st.image(buf.getvalue(), width=200)
            st.write(f"Link Direct: [{qr_link}]({qr_link})")
    else:
        st.info("Belum ada data rekon aset.")

# ------------------------------------------
# MENU 3: SENSUS BERKALA
# ------------------------------------------
elif menu == "📊 Sensus Berkala":
    st.header("📊 Monitoring & Sensus Berkala Kondisi Aset")
    
    records_arsip = sheet_arsip.get_all_records()
    records_sensus = sheet_sensus.get_all_records()
    
    total_aset = len(records_arsip)
    total_sensus = len(records_sensus)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Komponen Aset", f"{total_aset} Item")
    c2.metric("Total Sensus Tercatat", f"{total_sensus} Sensus")
    c3.metric("Capaian Sensus", f"{int((total_sensus/total_aset)*100) if total_aset>0 else 0}%")
    
    st.divider()
    st.subheader("🔍 Form Pengisian Sensus Lapangan")
    
    if records_arsip:
        list_aset = [f"{r['Timestamp']} - {r['Nama Komponen']}" for r in records_arsip]
        pilihan_aset = st.selectbox("Pilih Komponen Aset:", list_aset)
        id_aset_sensus = pilihan_aset.split(" - ")[0]
        nama_aset_sensus = pilihan_aset.split(" - ")[1]
        
        with st.form("form_sensus"):
            tahun_sensus = st.selectbox("Tahun Sensus", [2024, 2025, 2026, 2027])
            periode_sensus = st.selectbox("Periode Sensus", ["Triwulan I (Q1)", "Triwulan II (Q2)", "Triwulan III (Q3)", "Triwulan IV (Q4)", "Semester I", "Semester II", "Sensus Tahunan"])
            lokasi_sensus = st.text_input("Lokasi / Ruangan Saat Ini")
            kondisi_sensus = st.selectbox("Kondisi Fisik Terkini", ["Baik", "Kurang Baik", "Rusak Berat"])
            catatan_sensus = st.text_input("Catatan Pemeriksaan Khusus")
            
            btn_sensus = st.form_submit_button("💾 Simpan Hasil Verifikasi Sensus")
            
            if btn_sensus:
                timestamp_now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                label_periode = f"{periode_sensus} - {tahun_sensus}"
                
                sheet_sensus.append_row([
                    timestamp_now, id_aset_sensus, nama_aset_sensus, label_periode,
                    kondisi_sensus, lokasi_sensus, catatan_sensus, "Foto Sensus", st.session_state.username
                ])
                st.success("✅ Sensus Berhasil Disimpan!")
                st.rerun()

# ------------------------------------------
# MENU 4: LAPORAN KERUSAKAN (CRM)
# ------------------------------------------
elif menu == "🚨 Laporan Kerusakan (CRM)":
    st.header("🚨 Rekap Laporan Kerusakan dari Lapangan")
    
    lapor_data = sheet_lapor.get_all_records()
    if lapor_data:
        df_lapor = pd.DataFrame(lapor_data)
        st.dataframe(df_lapor, use_container_width=True)
    else:
        st.info("Belum ada laporan kerusakan yang masuk.")
