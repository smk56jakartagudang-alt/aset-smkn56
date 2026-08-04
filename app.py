import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import pandas as pd
import datetime
import qrcode
import re
import time
from io import BytesIO

# ==========================================
# KONFIGURASI
# ==========================================
st.set_page_config(
    page_title="SI-PINTU 56 - SMKN 56 Jakarta",
    page_icon="🏫",
    layout="wide"
)

BASE_URL = "https://sipintu-smkn56jakarta.streamlit.app/"
GOOGLE_DRIVE_FOLDER_ID = "1qsgab2n8wN0NYDCzel4nHlc1nKAieyjU"

# ==========================================
# KONEKSI GOOGLE (TANPA CACHE YANG RUSAK)
# ==========================================
def init_services():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    
    if "gcp_service_account" not in st.secrets:
        return None, "Secrets 'gcp_service_account' belum diisi di Streamlit Cloud!"
    
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        if "private_key" in creds_dict and isinstance(creds_dict["private_key"], str):
            creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
        
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client_gspread = gspread.authorize(creds)
        drive_service = build('drive', 'v3', credentials=creds)
        
        ss = client_gspread.open_by_key("1SXyAvphA5ivL70UVzD49nHfkGBlUGLqiCPaxuDQlGAg")
        
        def get_or_create(title, headers):
            try:
                return ss.worksheet(title)
            except Exception:
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
        
        return (s_users, s_arsip, s_sensus, s_lapor, drive_service), None
        
    except Exception as e:
        return None, str(e)

# Inisialisasi sekali per session
if "services" not in st.session_state:
    with st.spinner("🔌 Menghubungkan ke Google Cloud..."):
        svcs, err = init_services()
        if err:
            st.error(f"❌ Gagal terhubung: {err}")
            st.stop()
        st.session_state.services = svcs

def get_sheet(name):
    s_users, s_arsip, s_sensus, s_lapor, _ = st.session_state.services
    if name == "Users": return s_users
    elif name == "Data_Arsip": return s_arsip
    elif name == "Data_Sensus": return s_sensus
    elif name == "Data_Laporan_Rusak": return s_lapor
    return None

def get_drive():
    return st.session_state.services[4]

# ==========================================
# CACHE DATA
# ==========================================
def get_records(sheet_name, refresh=False):
    key = f"rec_{sheet_name}"
    if refresh or key not in st.session_state:
        with st.spinner(f"🔄 Memuat {sheet_name}..."):
            st.session_state[key] = get_sheet(sheet_name).get_all_records()
    return st.session_state[key]

def clear_cache(names=None):
    if names is None:
        for k in list(st.session_state.keys()):
            if k.startswith("rec_"):
                del st.session_state[k]
    else:
        for n in names:
            k = f"rec_{n}"
            if k in st.session_state:
                del st.session_state[k]

# ==========================================
# GOOGLE DRIVE HELPERS
# ==========================================
def get_or_create_folder(folder_name, parent_id):
    try:
        drv = get_drive()
        clean = re.sub(r'[/\\:*?"<>|]', '_', folder_name)
        q = f"'{parent_id}' in parents and name = '{clean}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        res = drv.files().list(q=q, spaces='drive', fields='files(id)', supportsAllDrives=True).execute()
        items = res.get('files', [])
        if items:
            return items[0]['id']
        
        meta = {
            'name': clean,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [parent_id]
        }
        fld = drv.files().create(body=meta, fields='id', supportsAllDrives=True).execute()
        return fld['id']
    except Exception as e:
        st.error(f"Gagal buat folder: {e}")
        return parent_id

def upload_drive(file_obj, filename, folder_id):
    try:
        ext = file_obj.name.split('.')[-1]
        final = f"{filename}.{ext}"
        final = re.sub(r'[/\\:*?"<>|]', '_', final)
        
        meta = {'name': final, 'parents': [folder_id]}
        media = MediaIoBaseUpload(BytesIO(file_obj.getvalue()), mimetype=file_obj.type, resumable=True)
        
        drv = get_drive()
        up = drv.files().create(body=meta, media_body=media, fields='id, webViewLink', supportsAllDrives=True).execute()
        
        try:
            drv.permissions().create(fileId=up['id'], body={'role':'reader','type':'anyone'}, supportsAllDrives=True).execute()
        except Exception:
            pass
        
        return up.get('webViewLink')
    except Exception as e:
        err = str(e)
        if "storageQuotaExceeded" in err or "do not have storage quota" in err:
            return "KUOTA_PENUH"
        return None

def render_link(url, label="Lihat"):
    s = str(url).strip()
    if s.startswith("http"):
        st.markdown(f'<a href="{s}" target="_blank"><button style="background:#007BFF;color:white;border:none;padding:6px 14px;border-radius:6px;cursor:pointer;font-size:13px;font-weight:bold;">🔗 {label}</button></a>', unsafe_allow_html=True)
    elif s and s != "Tidak ada file":
        st.info(f"📄 {s}")
    else:
        st.caption("🔴 Belum ada file")

# ==========================================
# PUBLIC QR ACCESS
# ==========================================
qp = st.query_params
id_pub = qp.get("id", None)

if id_pub:
    st.title("📋 SI-PINTU 56 - Detail Inventaris")
    data = get_records("Data_Arsip")
    target = None
    raw = str(id_pub).strip()
    clean_raw = re.sub(r'[^a-zA-Z0-9]', '', raw).lower()
    
    for item in data:
        ts = str(item.get("Timestamp","")).strip()
        kd = str(item.get("Kode Komponen","")).strip()
        nm = str(item.get("Nama Komponen","")).strip()
        if raw in [ts,kd,nm] or clean_raw in [re.sub(r'[^a-zA-Z0-9]','',x).lower() for x in [ts,kd,nm]]:
            target = item
            break
    
    if target:
        st.subheader(f"📦 {target.get('Nama Komponen','-')} ({target.get('Kode Komponen','-')})")
        c1, c2 = st.columns(2)
        with c1:
            st.write(f"**Kategori:** {target.get('Kategori','-')}")
            st.write(f"**Asal:** {target.get('Asal perolehan','-')}")
            st.write(f"**Tahun:** {target.get('Tahun Pengadaan','-')}")
        with c2:
            st.write(f"**Kondisi:** {target.get('Kondisi','-')}")
            st.write(f"**Lokasi:** {target.get('Alokasi Barang','-')}")
        
        st.divider()
        st.subheader("🚨 Laporkan Kerusakan")
        with st.form("lapor"):
            nama = st.text_input("Nama Pelapor")
            nip = st.text_input("NIP/NIKKI")
            q = target.get("Quantity",1)
            try: q = int(q)
            except: q = 1
            brg = st.selectbox("Barang Ke-", [f"Barang Ke-{i}" for i in range(1,q+1)])
            lok = st.text_input("Lokasi Spesifik")
            desk = st.text_area("Deskripsi Kerusakan")
            if st.form_submit_button("Kirim"):
                if not nama or not desk:
                    st.error("Nama & Deskripsi wajib diisi!")
                else:
                    get_sheet("Data_Laporan_Rusak").append_row([
                        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        id_pub, target.get('Nama Komponen','-'), brg, lok, desk, nama, nip,
                        "-", "Menunggu Tindakan", "Tidak"
                    ])
                    clear_cache(["Data_Laporan_Rusak"])
                    st.success("✅ Laporan terkirim!")
    else:
        st.error("❌ Kode tidak valid.")
    st.stop()

# ==========================================
# LOGIN
# ==========================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""

if not st.session_state.logged_in:
    st.markdown("<h2 style='text-align:center'>SI-PINTU 56</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center'>Sistem Inventaris Aset Digital - SMKN 56 Jakarta</p>", unsafe_allow_html=True)
    _, col, _ = st.columns([1,2,1])
    with col:
        with st.form("login"):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Masuk"):
                users = get_records("Users")
                ok = any(str(x.get("Username","")).strip()==u.strip() and str(x.get("Password","")).strip()==p.strip() for x in users)
                if ok:
                    st.session_state.logged_in = True
                    st.session_state.username = u
                    st.rerun()
                else:
                    st.error("Login gagal!")
    st.stop()

# ==========================================
# SIDEBAR
# ==========================================
st.sidebar.title("SI-PINTU 56")
st.sidebar.write(f"👤 **{st.session_state.username}**")

menu = st.sidebar.radio("Menu", [
    "📥 Input Data Aset",
    "📋 Daftar Output & QR",
    "📊 Sensus Berkala",
    "🚨 Laporan Kerusakan (CRM)"
])

st.sidebar.divider()

# Diagnostik kuota
with st.sidebar.expander("🔍 Cek Kuota Robot"):
    try:
        drv = get_drive()
        act = drv.files().list(q="trashed=false", pageSize=1000, fields="files(id,size)").execute().get('files',[])
        tr = drv.files().list(q="trashed=true", pageSize=1000, fields="files(id,size)").execute().get('files',[])
        sz = sum(int(f.get('size',0)) for f in act+tr)
        st.sidebar.write(f"File aktif: {len(act)}")
        st.sidebar.write(f"File trash: {len(tr)}")
        st.sidebar.write(f"Total: {sz/(1024*1024):.1f} MB")
    except Exception as e:
        st.sidebar.write(f"Gagal cek: {e}")

if st.sidebar.button("🧹 Hapus Semua File Robot"):
    try:
        drv = get_drive()
        act = drv.files().list(q="trashed=false", pageSize=1000, fields="files(id)").execute().get('files',[])
        tr = drv.files().list(q="trashed=true", pageSize=1000, fields="files(id)").execute().get('files',[])
        n = 0
        for f in act+tr:
            try:
                drv.files().delete(fileId=f['id'], supportsAllDrives=True).execute()
                n += 1
            except: pass
        st.sidebar.success(f"✅ {n} file dihapus!")
    except Exception as e:
        st.sidebar.error(f"Gagal: {e}")

st.sidebar.divider()

if st.sidebar.button("🔄 Refresh Data"):
    clear_cache()
    st.rerun()

if st.sidebar.button("🚪 Keluar"):
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.rerun()

# ==========================================
# MENU 1: INPUT
# ==========================================
if menu == "📥 Input Data Aset":
    st.header("Input Deskripsi Aset Baru")
    st.divider()

    c1, c2, c3 = st.columns(3)
    with c1:
        klas = st.selectbox("Klasifikasi", ["KIB B - Peralatan & Mesin", "KIB C - Gedung & Bangunan", "KIB E - Aset Tetap Lainnya"])
        asal = st.selectbox("Asal Perolehan", ["BOS", "BOP", "KAPITALISASI BOS", "KAPITALISASI BOP", "Hibah", "Lainnya"])
        sub = st.text_input("Sub Perolehan", placeholder="TW ... / SEMESTER ...")
    with c2:
        nama = st.text_input("Nama Komponen*", placeholder="Contoh: Switch Hub Ruijie 8 Port")
        harga = st.number_input("Harga Satuan", min_value=0, value=0, step=1000)
        penyedia = st.text_input("Penyedia")
    with c3:
        kode = st.text_input("Kode Komponen", placeholder="132100203003...")
        qty = st.number_input("Quantity", min_value=1, value=1, step=1)
        total = harga * qty
        st.text_input("Jumlah Total", value=f"Rp {total:,.0f}", disabled=True)

    c1, c2, c3 = st.columns(3)
    with c1: thn = st.text_input("Tahun Pengadaan", value="2026")
    with c2: sem = st.selectbox("Semester", ["SEMESTER I", "SEMESTER II"])
    with c3: tw = st.selectbox("Triwulan", ["TW I", "TW II", "TW III", "TW IV"])

    st.markdown("**📍 Alokasi Penempatan**")
    alok = []
    for i in range(int(qty)):
        loc = st.text_input(f"Barang {i+1}", key=f"loc{i}")
        if loc: alok.append(f"[Brg {i+1}: {loc}]")
    alok_str = " ".join(alok) if alok else "-"

    st.divider()
    c1, c2, c3, c4 = st.columns(4)
    with c1: kondisi = st.selectbox("Kondisi", ["Baik", "Kurang Baik", "Rusak Berat"])
    with c2: merk = st.text_input("Merk")
    with c3: tipe = st.text_input("Type")
    with c4: tgl = st.date_input("Tanggal Perolehan")

    c1, c2 = st.columns(2)
    with c1: bahan = st.text_input("Bahan")
    with c2: seri = st.text_input("No. Seri / Pabrik")

    c1, c2 = st.columns(2)
    with c1: spek = st.text_area("Spesifikasi")
    with c2: ket = st.text_area("Keterangan Utama")

    c1, c2 = st.columns(2)
    with c1: bast = st.text_input("BAST", placeholder="BAST/STRS-0022")
    with c2: tgl_bast = st.date_input("Tanggal BAST")

    c1, c2 = st.columns(2)
    with c1: fgab = st.file_uploader("📸 Foto Gabungan", type=["jpg","jpeg","png"])
    with c2: fsat = st.file_uploader("📸 Foto Satuan", type=["jpg","jpeg","png"])
    pdf = st.file_uploader("📄 Dokumen PDF", type=["pdf"])

    if st.button("Simpan Data Ke Sistem", type="primary"):
        if not nama:
            st.error("Nama Komponen wajib diisi!")
        else:
            ts = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            alok_full = f"{alok_str} || KET: {ket}" if ket else alok_str
            folder_name = f"{thn}_{asal}_{nama}_{sem}_{tw}_{bast}_{kode}"
            base = f"{thn}_{asal}_{nama}_{sem}_{tw}_{bast}"
            
            v_fgab = "Tidak ada file"
            v_fsat = "Tidak ada file"
            v_pdf = "Tidak ada file"
            gagal = []
            
            with st.spinner("⏳ Mengunggah ke Google Drive..."):
                fid = get_or_create_folder(folder_name, GOOGLE_DRIVE_FOLDER_ID)
                
                if fgab:
                    r = upload_drive(fgab, f"{base}_FOTO_GABUNGAN", fid)
                    if r and r.startswith("http"): v_fgab = r
                    else: gagal.append("Foto Gabungan")
                if fsat:
                    r = upload_drive(fsat, f"{base}_FOTO_SATUAN", fid)
                    if r and r.startswith("http"): v_fsat = r
                    else: gagal.append("Foto Satuan")
                if pdf:
                    r = upload_drive(pdf, f"{base}_DOKUMEN_SPJ", fid)
                    if r and r.startswith("http"): v_pdf = r
                    else: gagal.append("Dokumen PDF")
            
            get_sheet("Data_Arsip").append_row([
                nama, klas, kode, harga, qty, total, str(tgl), asal, sub, kondisi,
                merk, tipe, spek, bast, str(tgl_bast), penyedia, thn, sem, tw,
                alok_full, bahan, seri, v_fgab, v_pdf, st.session_state.username, v_fsat, ts
            ])
            
            clear_cache(["Data_Arsip"])
            st.success(f"✅ Data '{nama}' berhasil disimpan!")
            
            if gagal:
                st.error("❌ Upload gagal — KUOTA ROBOT PENUH!")
                st.info("Klik **🧹 Hapus Semua File Robot** di sidebar untuk bersihkan kuota.")
            
            qr = f"{BASE_URL}?id={ts}"
            img = qrcode.make(qr)
            buf = BytesIO()
            img.save(buf)
            st.image(buf.getvalue(), caption=f"QR Code {nama}", width=200)
            st.code(qr)

# ==========================================
# MENU 2: OUTPUT & QR
# ==========================================
elif menu == "📋 Daftar Output & QR":
    st.header("📋 Daftar Inventaris")
    data = get_records("Data_Arsip")
    if data:
        st.dataframe(pd.DataFrame(data), use_container_width=True, height=300)
        st.divider()
        
        opts = []
        for i, r in enumerate(data):
            iv = str(r.get("Timestamp","")).strip() or str(r.get("Kode Komponen","")).strip()
            if iv: opts.append(f"{i+2} | {r.get('Nama Komponen','')} ({iv})")
        
        if opts:
            sel = st.selectbox("Pilih Aset:", opts)
            rn = int(sel.split(" | ")[0])
            item = data[rn-2]
            sid = str(item.get("Timestamp","")).strip() or str(item.get("Kode Komponen","")).strip()
            
            cq, cm, cu = st.columns([1,1.3,1.3])
            with cq:
                st.markdown("##### 📱 QR Code")
                ql = f"{BASE_URL}?id={sid}"
                im = qrcode.make(ql)
                bf = BytesIO()
                im.save(bf)
                st.image(bf.getvalue(), width=160)
                st.markdown(f"[{ql}]({ql})")
            
            with cm:
                st.markdown("##### 📂 Berkas")
                render_link(item.get('Foto Aset (Gambar - Gabungan)',''), "Foto Gabungan")
                render_link(item.get('Foto Aset Satuan (Siera / Perwakilan)',''), "Foto Satuan")
                render_link(item.get('Dokumen Pendukung (PDF)',''), "Dokumen PDF")
            
            with cu:
                st.markdown("##### 🔄 Update Berkas")
                with st.form("up"):
                    ug = st.file_uploader("Foto Gabungan Baru", type=["jpg","jpeg","png"], key="ug")
                    us = st.file_uploader("Foto Satuan Baru", type=["jpg","jpeg","png"], key="us")
                    up = st.file_uploader("PDF Baru", type=["pdf"], key="up")
                    if st.form_submit_button("Simpan"):
                        fn = f"{item.get('Tahun Pengadaan')}_{item.get('Asal perolehan')}_{item.get('Nama Komponen')}_{item.get('Semester')}_{item.get('Triwulan')}_{item.get('BAST')}"
                        fn2 = f"{item.get('Tahun Pengadaan')}_{item.get('Asal perolehan')}_{item.get('Nama Komponen')}_{item.get('Semester')}_{item.get('Triwulan')}_{item.get('BAST')}_{item.get('Kode Komponen')}"
                        fid = get_or_create_folder(fn2, GOOGLE_DRIVE_FOLDER_ID)
                        err = []
                        sht = get_sheet("Data_Arsip")
                        if ug:
                            r = upload_drive(ug, f"{fn}_FOTO_GABUNGAN", fid)
                            if r: sht.update_cell(rn, 23, r)
                            else: err.append("Foto Gabungan")
                        if up:
                            r = upload_drive(up, f"{fn}_DOKUMEN_SPJ", fid)
                            if r: sht.update_cell(rn, 24, r)
                            else: err.append("PDF")
                        if us:
                            r = upload_drive(us, f"{fn}_FOTO_SATUAN", fid)
                            if r: sht.update_cell(rn, 26, r)
                            else: err.append("Foto Satuan")
                        clear_cache(["Data_Arsip"])
                        if err: st.error("Gagal: " + ", ".join(err))
                        else: st.success("✅ Berkas diperbarui!")
                        st.rerun()
    else:
        st.info("Belum ada data.")

# ==========================================
# MENU 3: SENSUS
# ==========================================
elif menu == "📊 Sensus Berkala":
    st.title("📊 Sensus Berkala")
    arsip = get_records("Data_Arsip")
    sensus = get_records("Data_Sensus")
    
    c1, c2, c3 = st.columns(3)
    with c1: ft = st.selectbox("Tahun Sensus", [2026,2025,2024,2027])
    with c2: fp = st.selectbox("Periode", ["Triwulan I","Triwulan II","Triwulan III","Triwulan IV","Semester I","Semester II","Sensus Tahunan"])
    with c3:
        to = ["Semua Tahun"]
        if arsip: to += sorted({str(r.get("Tahun Pengadaan","")).strip() for r in arsip if r.get("Tahun Pengadaan")}, reverse=True)
        fa = st.selectbox("Tahun Aset", to)
    
    lbl = f"{fp} - {ft}"
    fil = arsip
    if fa != "Semua Tahun": fil = [r for r in arsip if str(r.get("Tahun Pengadaan","")).strip()==fa]
    done = [str(s.get("ID Aset","")).strip().lower() for s in sensus if str(s.get("Periode Sensus","")).strip()==lbl]
    
    t = len(fil)
    s = len([r for r in fil if str(r.get("Timestamp","")).strip().lower() in done])
    b = t-s
    p = int(s/t*100) if t else 0
    
    m1,m2,m3,m4 = st.columns(4)
    m1.metric("TOTAL", f"{t} Komponen")
    m2.metric("SUDAH", f"{s} Item")
    m3.metric("BELUM", f"{b} Item")
    m4.metric("CAPAIAN", f"{p}%")
    
    st.divider()
    if not fil:
        st.info("Tidak ada data.")
    else:
        h1,h2,h3,h4,h5,h6,h7 = st.columns([2.5,2,2,1.2,1.5,2,2])
        h1.markdown("**Nama**"); h2.markdown("**Kategori**"); h3.markdown("**Kode**")
        h4.markdown("**Qty**"); h5.markdown("**Thn**"); h6.markdown("**Status**"); h7.markdown("**Aksi**")
        st.divider()
        
        if "sid" not in st.session_state: st.session_state.sid = None
        
        for it in fil:
            iid = str(it.get("Timestamp","")).strip() or str(it.get("Kode Komponen","")).strip()
            ok = iid.lower() in done
            t1,t2,t3,t4,t5,t6,t7 = st.columns([2.5,2,2,1.2,1.5,2,2])
            t1.write(it.get("Nama Komponen","-"))
            t2.write(it.get("Kategori","-"))
            t3.write(f"`{it.get('Kode Komponen','-')}`")
            t4.write(f"{it.get('Quantity',1)}")
            t5.write(str(it.get("Tahun Pengadaan","-")))
            t6.success("✅") if ok else t6.error("🔴")
            if t7.button("🔍", key=f"bs{iid}"):
                st.session_state.sid = iid
        
        if st.session_state.sid:
            ta = next((r for r in arsip if str(r.get("Timestamp","")).strip()==st.session_state.sid or str(r.get("Kode Komponen","")).strip()==st.session_state.sid), None)
            if ta:
                st.divider()
                st.subheader(f"📝 Sensus: {ta.get('Nama Komponen','-')}")
                with st.form("fs"):
                    c1,c2 = st.columns(2)
                    with c1:
                        lok = st.text_input("Lokasi Terkini")
                        kon = st.selectbox("Kondisi", ["Baik","Kurang Baik","Rusak Berat"])
                    with c2:
                        cat = st.text_area("Catatan")
                        fot = st.file_uploader("📸 Foto Bukti", type=["jpg","jpeg","png"])
                    if st.form_submit_button("💾 Simpan"):
                        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        vf = "Tanpa Foto"
                        if fot:
                            fn = f"SENSUS_{ta.get('Tahun Pengadaan')}_{ta.get('Nama Komponen')}_{fp}"
                            fn2 = f"{ta.get('Tahun Pengadaan')}_{ta.get('Asal perolehan')}_{ta.get('Nama Komponen')}_{ta.get('Semester')}_{ta.get('Triwulan')}_{ta.get('BAST')}_{ta.get('Kode Komponen')}"
                            fid = get_or_create_folder(fn2, GOOGLE_DRIVE_FOLDER_ID)
                            r = upload_drive(fot, fn, fid)
                            if r: vf = r
                        get_sheet("Data_Sensus").append_row([ts, st.session_state.sid, ta.get('Nama Komponen','-'), lbl, kon, lok, cat, vf, st.session_state.username])
                        clear_cache(["Data_Sensus","Data_Arsip"])
                        st.session_state.sid = None
                        st.success("✅ Tersimpan!")
                        st.rerun()

# ==========================================
# MENU 4: LAPORAN
# ==========================================
elif menu == "🚨 Laporan Kerusakan (CRM)":
    st.header("🚨 Rekap Laporan Kerusakan")
    d = get_records("Data_Laporan_Rusak")
    if d:
        st.dataframe(pd.DataFrame(d), use_container_width=True)
    else:
        st.info("Belum ada laporan.")
