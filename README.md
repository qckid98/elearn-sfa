# 👗 Fashion School Management System

Sistem manajemen sekolah fashion berbasis web modern yang terintegrasi dengan WhatsApp Gateway. Aplikasi ini dirancang untuk menangani pendaftaran siswa, penjadwalan kelas yang fleksibel (*rolling schedule*), absensi digital, dan notifikasi otomatis.

![Python](https://img.shields.io/badge/Python-3.10-blue?style=flat&logo=python)
![Flask](https://img.shields.io/badge/Flask-3.0-green?style=flat&logo=flask)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue?style=flat&logo=postgresql)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat&logo=docker)
![Bootstrap](https://img.shields.io/badge/Bootstrap-5-purple?style=flat&logo=bootstrap)

## ✨ Fitur Utama

### 👨‍💼 Super Admin (God Mode)
* **Manajemen Siswa:** Invite siswa baru via WhatsApp (kirim link aktivasi otomatis), edit sisa sesi, dan non-aktifkan akun.
* **Master Data:** Kelola Program Studi (Rolling/Batch) dan Manajemen Pengajar (Skill & Availability).
* **Master Schedule:** Monitoring kepadatan kelas (okupansi) secara real-time.
* **Override Jadwal:** Menambahkan atau menghapus jadwal siswa secara manual.

### 👩‍🏫 Pengajar (Teacher)
* **Absensi Digital:** Input kehadiran (Hadir/Izin/Alpha) via dashboard.
* **WhatsApp Recap:** Laporan otomatis ke grup WA manajemen setelah submit absensi.
* **Manajemen Jadwal:** Mengatur ketersediaan hari dan jam mengajar.

### 👩‍🎓 Siswa (Student)
* **Self-Scheduling:** Memilih jadwal kelas sendiri berdasarkan ketersediaan guru (Wizard Style).
* **Dashboard:** Melihat sisa kuota sesi, riwayat kelas, dan jadwal mendatang.
* **Notifikasi:** Menerima pengingat dan info akun via WhatsApp.

---

## 🛠️ Teknologi yang Digunakan

* **Backend:** Python (Flask), SQLAlchemy, Flask-Login, Flask-Migrate.
* **Frontend:** Jinja2 Templates, Bootstrap 5 (Custom Fashion Tech Theme), FullCalendar.js.
* **Database:** PostgreSQL.
* **Containerization:** Docker & Docker Compose.
* **WhatsApp Gateway:** [Go WhatsApp Web Multidevice](https://github.com/aldinokemal/go-whatsapp-web-multidevice).

---

## 🚀 Cara Instalasi (Docker)

Pastikan **Docker** dan **Git** sudah terinstall di komputer Anda.

### 1. Clone Repository
```bash
git clone [https://github.com/qckid98/elearn-sfa.git](https://github.com/qckid98/elearn-sfa.git)
cd fashion-school