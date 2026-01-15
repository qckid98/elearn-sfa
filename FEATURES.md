# 📚 Dokumentasi Fitur - elearn-sfa

**Sparks Fashion Academy - Learning Management System**

> Sistem manajemen pembelajaran untuk kursus fashion design dengan fitur lengkap untuk Admin, Teacher, dan Student.

---

## 🔐 Role & Akses

| Role | Deskripsi |
|------|-----------|
| **Admin** | Mengelola seluruh sistem: siswa, guru, program, jadwal, dan laporan |
| **Teacher** | Mengajar siswa, mengisi absensi, melihat progress siswa |
| **Student** | Mengakses jadwal, melihat progress belajar, upload portfolio |

---

## 👨‍💼 FITUR ADMIN

### 📋 Manajemen Data

| Fitur | Deskripsi |
|-------|-----------|
| **Dashboard** | Statistik siswa, guru, program, sesi hari ini, status WhatsApp Bot |
| **Invite Siswa** | Daftarkan siswa baru via WhatsApp (single/batch) |
| **Data Siswa** | Lihat, edit, hapus siswa dengan detail enrollment dan progress |
| **Data Pengajar** | Kelola guru, skill mengajar, dan jadwal availability |
| **Master Schedule** | Monitoring kepadatan kelas dan jadwal seluruh siswa |

### 🎓 Manajemen Akademik

| Fitur | Deskripsi |
|-------|-----------|
| **Program** | Buat dan kelola program pembelajaran (Regular/Batch) |
| **Master Class** | Data master kelas (Fashion Design, Draping, dll) |
| **Program Classes** | Kelas dalam program dengan jumlah sesi dan kuota izin |
| **Silabus** | Kelola topik pembelajaran per kelas |
| **Batch** | Kelola kelas grup dengan kapasitas maksimal |
| **Tools/Alat** | Kelola daftar alat yang dibutuhkan per program |

### 📊 Laporan & Export

| Fitur | Deskripsi |
|-------|-----------|
| **Rekap Pengajar** | Rekap sesi mengajar per guru (bulan/tahun) |
| **Export Excel** | Export rekap ke format spreadsheet |
| **Export PDF** | Export rekap ke format dokumen |
| **Export Semua Guru** | Export rekap semua guru sekaligus |

### ✅ Approval & Override

| Fitur | Deskripsi |
|-------|-----------|
| **Request Absen** | Approve/reject request absen lewat dari guru |
| **Session Override** | Assign guru pengganti untuk sesi tertentu |

---

## 👩‍🏫 FITUR TEACHER

### 📅 Dashboard & Jadwal

| Fitur | Deskripsi |
|-------|-----------|
| **Dashboard** | Kalender jadwal mengajar interaktif (bulanan/mingguan/harian) |
| **Quick Access Absensi** | Akses cepat ke form absensi per sesi (Pagi/Siang/Malam) |
| **Status Jadwal** | Warna: 🔵 Mendatang, 🟢 Selesai, 🔴 Terlewat |

### ✍️ Absensi

| Fitur | Deskripsi |
|-------|-----------|
| **Form Absensi** | Isi absensi siswa (Hadir/Alpha) dengan catatan |
| **Absensi Lewat** | Request absensi untuk sesi yang sudah lewat (H-2) |
| **Riwayat Request** | Lihat status request absensi (pending/approved/rejected) |

### 👥 Progress Siswa

| Fitur | Deskripsi |
|-------|-----------|
| **Daftar Siswa** | Lihat semua siswa yang diajar |
| **Detail Progress** | Progress per kelas, riwayat absensi, statistik lengkap |

### 🔄 Substitusi

| Fitur | Deskripsi |
|-------|-----------|
| **Terima Override** | Otomatis terima sesi dari guru lain yang digantikan |
| **Indikator 🔄** | Tanda sesi substitusi di kalender |

---

## 👨‍🎓 FITUR STUDENT

### 📊 Dashboard

| Fitur | Deskripsi |
|-------|-----------|
| **Sisa Sesi** | Tampilan besar jumlah sesi tersisa |
| **Status Enrollment** | Active, Pending Schedule, Completed |
| **Multi-Program** | Support siswa dengan lebih dari 1 program |

### 📅 Jadwal

| Fitur | Deskripsi |
|-------|-----------|
| **Jadwal Mendatang** | Lihat jadwal kelas yang akan datang (12 sesi) |
| **Detail Jadwal** | Tanggal, waktu, kelas, pengajar |
| **Request Izin** | Ajukan izin minimal H-1 jam sebelum sesi |
| **Kuota Izin** | Lihat sisa kuota izin per kelas |

### 📈 Progress Belajar

| Fitur | Deskripsi |
|-------|-----------|
| **Progress Bar** | Visualisasi persentase progress keseluruhan |
| **Detail per Kelas** | Hadir, Izin, Alpha, Sisa sesi per kelas |
| **Riwayat Sesi** | 10 sesi terakhir dengan status dan catatan |

### 📁 Portfolio

| Fitur | Deskripsi |
|-------|-----------|
| **Upload Portfolio** | Upload hasil karya ke Google Drive |
| **Per Topik Silabus** | Organisasi portfolio per topik pembelajaran |
| **Folder Otomatis** | Struktur: Nama Siswa > Program > Kelas |

### 🧭 Onboarding

| Fitur | Deskripsi |
|-------|-----------|
| **Schedule Wizard** | Atur jadwal rutin setelah aktivasi akun |
| **Pilih Kelas & Slot** | Pilih hari, waktu, dan guru yang tersedia |
| **First Class Date** | Pilih tanggal mulai kelas pertama |

---

## 🔔 Notifikasi WhatsApp

| Notifikasi | Penerima |
|------------|----------|
| Link aktivasi akun | Siswa baru |
| Pengingat jadwal besok | Guru |
| Ringkasan jadwal mingguan | Guru |
| Perubahan jadwal | Guru & Siswa |
| Siswa izin | Guru |

---

## 🛠️ Fitur Teknis

| Fitur | Deskripsi |
|-------|-----------|
| **Dark Mode** | Toggle tema gelap/terang |
| **Responsive** | Tampilan optimal di desktop, tablet, mobile |
| **Google Drive** | Integrasi untuk portfolio dan dokumen |
| **Backup Otomatis** | Database backup harian ke Google Drive (rclone) |
| **SSL/HTTPS** | Keamanan dengan sertifikat Let's Encrypt |
| **Docker** | Deployment containerized untuk konsistensi |
| **CI/CD** | Auto deploy via GitHub Actions |

---

## 📱 Teknologi

- **Backend**: Flask (Python 3.10)
- **Database**: PostgreSQL
- **Frontend**: HTML5, CSS3, JavaScript, Bootstrap 5
- **Calendar**: FullCalendar.js
- **Icons**: Font Awesome
- **Container**: Docker & Docker Compose
- **Bot**: WhatsApp API (Baileys)
- **Storage**: Google Drive API

---

## 🔗 Struktur URL

| Path | Role | Deskripsi |
|------|------|-----------|
| `/` | All | Dashboard (berbeda per role) |
| `/admin/*` | Admin | Semua fitur admin |
| `/teacher/*` | Teacher | Progress siswa |
| `/attendance/*` | Teacher | Form absensi |
| `/onboarding/*` | Student | Setup jadwal |
| `/portfolio/*` | Student | Upload portfolio |
| `/auth/*` | All | Login, logout, aktivasi |

---

*Dokumentasi ini di-generate otomatis dari analisis kode aplikasi.*
*Last updated: Januari 2026*
