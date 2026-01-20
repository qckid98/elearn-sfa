# 🚀 Deployment Guide - elearn-sfa

Domain: **edu.sparksfashionacademy.co.id** (redirect from lms.sparksfashionacademy.co.id)

## Prerequisites

- VPS dengan Ubuntu 20.04+ (recommended)
- Domain sudah di-pointing ke IP VPS
- SSH access ke VPS

---

## 1️⃣ Setup VPS (First Time Only)

### Install Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt install -y docker-compose

# Install Nginx & Certbot
sudo apt install -y nginx certbot python3-certbot-nginx

# Start services
sudo systemctl enable nginx docker
sudo systemctl start nginx docker
```

### Clone Repository

```bash
sudo mkdir -p /var/www
cd /var/www
git clone https://github.com/YOUR_USERNAME/elearn-sfa.git
cd elearn-sfa
```

### Setup Environment

```bash
# Copy example env and edit
cp .env.example .env
nano .env

# IMPORTANT: Update these values for production:
# - SECRET_KEY (generate random: python -c "import secrets; print(secrets.token_hex(32))")
# - DATABASE_URL (use the Docker internal URL)
# - Any API keys
```

---

## 2️⃣ Setup Nginx & SSL

### Copy Nginx Config

```bash
sudo cp deploy/nginx.conf /etc/nginx/sites-available/elearn-sfa
sudo ln -s /etc/nginx/sites-available/elearn-sfa /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default  # Remove default config
```

### Test & Reload (HTTP only first)

```bash
# Comment out SSL lines in nginx config first, then:
sudo nginx -t
sudo systemctl reload nginx
```

### Get SSL Certificate

```bash
sudo certbot --nginx -d edu.sparksfashionacademy.co.id -d lms.sparksfashionacademy.co.id

# Auto-renewal (should be automatic, but verify)
sudo certbot renew --dry-run
```

---

## 3️⃣ Start Application

```bash
cd /var/www/elearn-sfa

# Build and start containers
docker-compose up -d --build

# Run migrations
docker-compose exec web flask db upgrade

# Seed initial data (if needed)
docker-compose exec web python manage.py seed

# Check logs
docker-compose logs -f
```

---

## 4️⃣ Setup GitHub Secrets for CI/CD

Go to: **GitHub Repo → Settings → Secrets and variables → Actions**

Add these secrets:

| Secret Name | Value |
|-------------|-------|
| `VPS_HOST` | Your VPS IP address (e.g., `123.45.67.89`) |
| `VPS_USER` | SSH username (e.g., `root` or `ubuntu`) |
| `VPS_SSH_KEY` | Your private SSH key (see below) |
| `VPS_PORT` | SSH port (optional, default 22) |

### Generate SSH Key (if needed)

```bash
# On your local machine
ssh-keygen -t ed25519 -C "github-deploy"

# Copy public key to VPS
ssh-copy-id -i ~/.ssh/id_ed25519.pub user@your-vps-ip

# Copy private key content to GitHub secrets (VPS_SSH_KEY)
cat ~/.ssh/id_ed25519
```

---

## 5️⃣ Test Deployment

1. Make a small change in your code
2. Push to `main` branch
3. Check GitHub Actions tab for deployment status
4. Visit https://edu.sparksfashionacademy.co.id

---

## 📝 Useful Commands

```bash
# View running containers
docker-compose ps

# View logs
docker-compose logs -f web
docker-compose logs -f db

# Restart services
docker-compose restart

# Full rebuild
docker-compose down
docker-compose up -d --build

# Access Flask shell
docker-compose exec web flask shell

# Run migrations
docker-compose exec web flask db upgrade

# Backup database
docker-compose exec db pg_dump -U postgres fashion_db > backup.sql
```

---

## 💾 Database Backup

### Setup Automated Backups

```bash
cd /var/www/elearn-sfa

# Make scripts executable
chmod +x deploy/backup.sh deploy/restore.sh

# Create backup directory
mkdir -p backups/{daily,weekly,monthly}

# Install crontab for automated backups (runs daily at 2 AM)
crontab deploy/crontab

# Verify crontab installed
crontab -l
```

### Manual Backup Commands

```bash
# Run backup manually
./deploy/backup.sh backup

# Check backup status
./deploy/backup.sh status

# Restore from backup (CAUTION: replaces current database!)
./deploy/restore.sh backups/daily/backup_20260110_020000.sql.gz
```

### Setup rclone for Google Drive Backup

```bash
# 1. Install rclone
curl https://rclone.org/install.sh | sudo bash

# 2. Configure rclone
rclone config
```

Ikuti langkah konfigurasi:
1. Ketik `n` (new remote)
2. Name: `gdrive`
3. Storage: pilih nomor untuk **Google Drive**
4. Client ID: tekan **Enter** (default)
5. Client Secret: tekan **Enter** (default)
6. Scope: pilih `1` (full access)
7. Root folder ID: tekan **Enter**
8. Service Account: tekan **Enter**
9. Advanced config: `n`
10. Auto config: `n` (karena di server tanpa GUI)

#### Mendapatkan Token (Headless Server)

Karena VPS tidak memiliki browser, jalankan di **komputer lokal**:

```bash
# Di Windows/Mac/Linux dengan browser:
rclone authorize "drive" "eyJzY29wZSI6ImRyaXZlIn0"
```

Browser akan terbuka, login Google, izinkan akses, lalu copy token JSON yang muncul.
Paste token tersebut ke VPS di prompt `config_token>`.

Lanjutkan konfigurasi:
11. Team Drive: `n`
12. Confirm: `y`

#### Verifikasi Setup

```bash
# Test koneksi ke Google Drive
rclone lsd gdrive:

# Test backup ke cloud
./deploy/backup.sh backup
```

### Backup Retention Policy

| Type | Schedule | Retention |
|------|----------|-----------|
| Daily | Every day at 2 AM | 7 days |
| Weekly | Every Sunday | 4 weeks |
| Monthly | 1st of month | 3 months |

---

## 🔒 Security Hardening

### Run VPS Security Script

```bash
cd /var/www/elearn-sfa
sudo bash deploy/vps-security.sh
```

This script configures:
- **UFW Firewall** - Only allows ports 22, 80, 443
- **Fail2Ban** - Blocks brute force attacks on SSH and Nginx
- **SSH Hardening** - Disables password auth, limits attempts
- **Auto Updates** - Security patches applied automatically
- **Kernel Hardening** - Network security parameters

### Verify Security Status

```bash
# Check firewall
sudo ufw status

# Check Fail2Ban
sudo fail2ban-client status
sudo fail2ban-client status sshd

# Check blocked IPs
sudo fail2ban-client status nginx-botsearch
```

---

## 🔧 Troubleshooting

### Container won't start
```bash
docker-compose logs web
docker-compose down && docker-compose up -d --build
```

### Database connection error
```bash
# Check if db container is running
docker-compose ps db
docker-compose restart db
```

### 502 Bad Gateway
```bash
# Check if Flask is running
docker-compose ps web
docker-compose logs web

# Check nginx config
sudo nginx -t
```

### SSL Certificate Issues
```bash
sudo certbot renew
sudo systemctl reload nginx
```
