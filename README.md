# 👗 Fashion School Management System

Sistem manajemen sekolah fashion berbasis web modern yang terintegrasi dengan WhatsApp Gateway. Aplikasi ini dirancang untuk menangani pendaftaran siswa, penjadwalan kelas yang fleksibel (*rolling schedule*), absensi digital, dan notifikasi otomatis.

![Python](https://img.shields.io/badge/Python-3.10-blue?style=flat&logo=python)
![Flask](https://img.shields.io/badge/Flask-3.0-green?style=flat&logo=flask)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue?style=flat&logo=postgresql)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat&logo=docker)
![Bootstrap](https://img.shields.io/badge/Bootstrap-5-purple?style=flat&logo=bootstrap)

---

## 📋 Daftar Isi

- [Fitur Utama](#-fitur-utama)
- [Teknologi yang Digunakan](#️-teknologi-yang-digunakan)
- [Arsitektur Aplikasi](#-arsitektur-aplikasi)
- [Struktur Database](#-struktur-database)
- [Cara Instalasi](#-cara-instalasi-docker)
- [Konfigurasi Environment](#-konfigurasi-environment)
- [Perintah Berguna](#-perintah-berguna)
- [Deployment ke VPS](#-deployment-ke-vps)
- [CI/CD Pipeline](#-cicd-pipeline)
- [Backup & Restore](#-backup--restore)
- [Security](#-security)
- [Lisensi](#-lisensi)

---

## ✨ Fitur Utama

### 👨‍💼 Super Admin (God Mode)
* **Manajemen Siswa:** Invite siswa baru via WhatsApp (kirim link aktivasi otomatis), edit sisa sesi, dan non-aktifkan akun.
* **Batch Invite:** Undang banyak siswa sekaligus dengan CSV atau form batch.
* **Master Data:** Kelola Program Studi (Rolling/Batch), Kelas, dan Subject.
* **Manajemen Pengajar:** Kelola guru, skill, dan availability.
* **Master Schedule:** Monitoring kepadatan kelas (okupansi) secara real-time.
* **Override Jadwal:** Menambahkan atau menghapus jadwal siswa secara manual.
* **Silabus:** Mengatur silabus per kelas dengan urutan topik.
* **Data Tools:** Mengelola peralatan/tools yang dibutuhkan per program.
* **Teacher Recap:** Laporan rekap sesi guru bulanan/tahunan (export Excel/PDF).

### 👩‍🏫 Pengajar (Teacher)
* **Absensi Digital:** Input kehadiran (Hadir/Izin/Alpha) via dashboard.
* **WhatsApp Recap:** Laporan otomatis ke grup WA manajemen setelah submit absensi.
* **Manajemen Jadwal:** Mengatur ketersediaan hari dan jam mengajar.
* **Student Progress:** Melihat progress dan portfolio siswa.

### 👩‍🎓 Siswa (Student)
* **Self-Scheduling:** Memilih jadwal kelas sendiri berdasarkan ketersediaan guru (Wizard Style).
* **Dashboard:** Melihat sisa kuota sesi, riwayat kelas, dan jadwal mendatang.
* **Request Izin:** Mengajukan izin untuk jadwal yang sudah di-booking.
* **Portfolio:** Upload hasil karya ke Google Drive terintegrasi per topik silabus.
* **Notifikasi:** Menerima pengingat dan info akun via WhatsApp.

---

## 🛠️ Teknologi yang Digunakan

| Kategori | Teknologi |
|----------|-----------|
| **Backend** | Python 3.10, Flask 3.0, SQLAlchemy, Flask-Login, Flask-Migrate |
| **Frontend** | Jinja2 Templates, Bootstrap 5 (Custom Fashion Tech Theme), FullCalendar.js |
| **Database** | PostgreSQL 15 |
| **Containerization** | Docker & Docker Compose |
| **Web Server** | Gunicorn (WSGI), Nginx (Reverse Proxy) |
| **WhatsApp Gateway** | [Go WhatsApp Web Multidevice](https://github.com/aldinokemal/go-whatsapp-web-multidevice) |
| **Cloud Storage** | Google Drive API (untuk Portfolio) |
| **Export** | OpenPyXL (Excel), ReportLab (PDF) |
| **CI/CD** | GitHub Actions |

---

## 🏗️ Arsitektur Aplikasi

```
┌─────────────────────────────────────────────────────────────┐
│                         NGINX                                │
│                    (Reverse Proxy + SSL)                     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Docker Compose Network                    │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────────┐    │
│  │   web       │   │     db      │   │     wabot       │    │
│  │  (Flask/    │◄─►│ (PostgreSQL │   │  (WhatsApp Bot) │    │
│  │  Gunicorn)  │   │    15)      │   │                 │    │
│  │  :5000      │   │   :5432     │   │    :3000        │    │
│  └─────────────┘   └─────────────┘   └─────────────────┘    │
│         │                                     ▲              │
│         └─────────────────────────────────────┘              │
│                    (HTTP API calls)                          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  Google Drive   │
                    │   (Portfolio)   │
                    └─────────────────┘
```

---

## 💾 Struktur Database

### Model Utama

| Model | Deskripsi |
|-------|-----------|
| `User` | Pengguna sistem (admin, teacher, student) |
| `Program` | Program studi (Rolling/Batch based) |
| `ProgramClass` | Kelas dalam program dengan total sesi |
| `Subject` | Mata pelajaran/skill |
| `TimeSlot` | Slot waktu yang tersedia |
| `Batch` | Kelompok siswa untuk program batch |
| `Enrollment` | Pendaftaran siswa ke program |
| `ClassEnrollment` | Progress siswa per kelas |
| `StudentSchedule` | Jadwal berulang siswa |
| `Booking` | Jadwal kelas yang sudah di-book |
| `Attendance` | Catatan kehadiran |
| `TeacherSkill` | Skill/mata pelajaran yang dikuasai guru |
| `TeacherAvailability` | Ketersediaan waktu guru |
| `Tool` | Peralatan yang dibutuhkan |
| `ProgramTool` | Relasi tools dengan program |
| `Syllabus` | Silabus per kelas |
| `Portfolio` | Portfolio siswa (link Google Drive) |

### Relasi Database (ERD Simplified)

```
User ─────┬────── Enrollment ────── Program
          │            │               │
          │      ClassEnrollment ── ProgramClass
          │            │               │
          │        Booking ─────── Syllabus
          │            │
          │       Attendance
          │
          ├── TeacherSkill ────── Subject
          │
          └── TeacherAvailability ── TimeSlot
```

---

## 🚀 Cara Instalasi (Docker)

Pastikan **Docker** dan **Git** sudah terinstall di komputer Anda.

### 1. Clone Repository

```bash
git clone https://github.com/qckid98/elearn-sfa.git
cd elearn-sfa
```

### 2. Setup Environment Variables

```bash
# Copy template environment file
cp .env.example .env

# Edit sesuai kebutuhan
nano .env  # atau gunakan editor favorit Anda
```

### 3. Build dan Jalankan dengan Docker Compose

```bash
# Build dan jalankan semua service
docker-compose up -d --build

# Lihat status container
docker-compose ps

# Lihat logs
docker-compose logs -f
```

### 4. Inisialisasi Database

```bash
# Jalankan migrasi database
docker-compose exec web flask db upgrade

# (Opsional) Seed data awal untuk testing
docker-compose exec web python manage.py
```

### 5. Akses Aplikasi

Buka browser dan akses: `http://localhost:8080`

---

## ⚙️ Konfigurasi Environment

Buat file `.env` berdasarkan `.env.example`:

```env
# Flask Settings
FLASK_APP=manage.py
FLASK_ENV=development  # Gunakan 'production' untuk VPS

# Security - WAJIB diganti untuk production!
SECRET_KEY=your-secret-key-here

# Database
DATABASE_URL=postgresql://postgres:postgres@db:5432/fashion_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=fashion_db

# WhatsApp Bot
WA_API_URL=http://wabot:3000

# Google Drive (untuk Portfolio)
GOOGLE_DRIVE_ROOT_FOLDER_ID=your-drive-folder-id
GOOGLE_OAUTH_CLIENT_ID=your-oauth-client-id
GOOGLE_OAUTH_CLIENT_SECRET=your-oauth-client-secret
GOOGLE_OAUTH_REFRESH_TOKEN=your-oauth-refresh-token

# Timezone
TZ=Asia/Jakarta
```

### Generate Secret Key

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## 📝 Perintah Berguna

### Docker Commands

```bash
# Melihat container yang berjalan
docker-compose ps

# Melihat logs
docker-compose logs -f web      # Logs Flask app
docker-compose logs -f db       # Logs PostgreSQL
docker-compose logs -f wabot    # Logs WhatsApp Bot

# Restart service
docker-compose restart web

# Rebuild dan restart
docker-compose down
docker-compose up -d --build

# Masuk ke Flask shell
docker-compose exec web flask shell

# Jalankan migrasi database
docker-compose exec web flask db upgrade
```

### Database Commands

```bash
# Backup database
docker-compose exec db pg_dump -U postgres fashion_db > backup.sql

# Restore database
docker-compose exec -T db psql -U postgres fashion_db < backup.sql

# Akses PostgreSQL CLI
docker-compose exec db psql -U postgres fashion_db
```

### Migrasi Database

```bash
# Buat migrasi baru setelah mengubah models
docker-compose exec web flask db migrate -m "Deskripsi perubahan"

# Terapkan migrasi
docker-compose exec web flask db upgrade

# Rollback migrasi
docker-compose exec web flask db downgrade
```

---

## 🌐 Deployment ke VPS

Untuk deployment ke production VPS, lihat panduan lengkap di:

📁 **[deploy/DEPLOYMENT_GUIDE.md](deploy/DEPLOYMENT_GUIDE.md)**

### Quick Overview

1. **Setup VPS** - Install Docker, Nginx, Certbot
2. **Clone & Configure** - Setup environment variables
3. **Setup Nginx & SSL** - Configure reverse proxy dengan Let's Encrypt
4. **Start Application** - `docker-compose up -d --build`
5. **Setup GitHub Secrets** - Untuk CI/CD otomatis

### VPS Requirements

- Ubuntu 20.04+ (recommended)
- Minimal 2GB RAM
- Domain sudah di-pointing ke IP VPS

---

## 🔄 CI/CD Pipeline

Aplikasi menggunakan **GitHub Actions** untuk Continuous Deployment.

### Workflow

Setiap push ke branch `main`:
1. ✅ Checkout repository
2. 🚀 Deploy ke VPS via SSH
3. 🔄 Pull latest code
4. 🏗️ Rebuild Docker containers
5. 📊 Run migrations

### Setup GitHub Secrets

| Secret | Deskripsi |
|--------|-----------|
| `VPS_HOST` | IP Address VPS |
| `VPS_USER` | SSH Username |
| `VPS_SSH_KEY` | Private SSH Key |
| `VPS_PORT` | SSH Port (default: 22) |

---

## 💾 Backup & Restore

### Automated Backup

Sistem backup otomatis sudah tersedia di folder `deploy/`:

```bash
# Setup backup otomatis
chmod +x deploy/backup.sh deploy/restore.sh
mkdir -p backups/{daily,weekly,monthly}

# Install crontab
crontab deploy/crontab
```

### Backup Policy

| Tipe | Jadwal | Retensi |
|------|--------|---------|
| Daily | Setiap hari 02:00 | 7 hari |
| Weekly | Setiap Minggu | 4 minggu |
| Monthly | Tanggal 1 | 3 bulan |

### Manual Backup

```bash
# Backup manual
./deploy/backup.sh backup

# Cek status backup
./deploy/backup.sh status

# Restore dari backup
./deploy/restore.sh backups/daily/backup_YYYYMMDD_HHMMSS.sql.gz
```

---

## 🔒 Security

### Security Features

- ✅ **Password Hashing** - Werkzeug secure password hashing
- ✅ **CSRF Protection** - Flask-WTF CSRF tokens
- ✅ **Session Security** - HTTP-only, secure cookies
- ✅ **Brute Force Protection** - Login attempt limiting
- ✅ **Input Validation** - SQLAlchemy parameterized queries
- ✅ **Role-Based Access** - Admin, Teacher, Student roles

### VPS Hardening

Jalankan script keamanan untuk mengamankan VPS:

```bash
sudo bash deploy/vps-security.sh
```

Script ini mengkonfigurasi:
- **UFW Firewall** - Hanya port 22, 80, 443
- **Fail2Ban** - Block brute force attacks
- **SSH Hardening** - Disable password auth
- **Auto Updates** - Security patches otomatis

---

## 📁 Struktur Folder

```
elearn-sfa/
├── app/                        # Aplikasi Flask utama
│   ├── __init__.py            # App factory
│   ├── models.py              # Database models
│   ├── security.py            # Security utilities
│   ├── routes/                # Blueprint routes
│   │   ├── admin.py           # Admin routes
│   │   ├── admin_syllabus.py  # Syllabus management
│   │   ├── auth.py            # Authentication
│   │   ├── main.py            # Main/dashboard routes
│   │   ├── teacher.py         # Teacher routes
│   │   ├── attendance.py      # Attendance routes
│   │   ├── onboarding.py      # Student onboarding
│   │   └── portfolio.py       # Portfolio management
│   ├── services/              # External services
│   │   └── google_drive.py    # Google Drive integration
│   ├── templates/             # Jinja2 templates
│   └── utils/                 # Utility functions
│       └── whatsapp.py        # WhatsApp API helper
├── deploy/                    # Deployment files
│   ├── DEPLOYMENT_GUIDE.md    # Panduan deployment
│   ├── nginx.conf             # Nginx configuration
│   ├── backup.sh              # Backup script
│   ├── restore.sh             # Restore script
│   ├── crontab                # Cron jobs
│   └── vps-security.sh        # Security hardening
├── migrations/                # Flask-Migrate files
├── static/                    # Static files (CSS, JS, images)
├── go-whatsapp-web-multidevice/  # WhatsApp Bot source
├── .github/workflows/         # GitHub Actions CI/CD
├── config.py                  # App configuration
├── manage.py                  # Management & seeding script
├── run.py                     # Application entry point
├── requirements.txt           # Python dependencies
├── Dockerfile                 # Docker image definition
├── docker-compose.yaml        # Multi-container setup
├── .env.example               # Environment template
└── README.md                  # Dokumentasi ini
```

---

## 🤝 Kontribusi

1. Fork repository ini
2. Buat branch fitur (`git checkout -b feature/AmazingFeature`)
3. Commit perubahan (`git commit -m 'Add some AmazingFeature'`)
4. Push ke branch (`git push origin feature/AmazingFeature`)
5. Buat Pull Request

---

## 📄 Lisensi

Didistribusikan di bawah Lisensi Apache 2.0. Lihat `LICENSE` untuk informasi lebih lanjut.

---

## 📞 Kontak

**Sparks Fashion Academy**  
🌐 Website: [sparksfashionacademy.co.id](https://sparksfashionacademy.co.id)  
📧 Email: info@sparksfashionacademy.co.id

---

<p align="center">
  Made with ❤️ for Fashion Education
</p>