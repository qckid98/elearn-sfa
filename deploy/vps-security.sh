#!/bin/bash
# =============================================================================
# VPS Security Hardening Script for Ubuntu
# Run as root: sudo bash vps-security.sh
# =============================================================================

set -e

echo "🔒 Starting VPS Security Hardening..."

# -----------------------------------------------------------------------------
# 1. System Updates
# -----------------------------------------------------------------------------
echo "📦 Updating system packages..."
apt update && apt upgrade -y
apt install -y ufw fail2ban unattended-upgrades

# -----------------------------------------------------------------------------
# 2. Configure Firewall (UFW)
# -----------------------------------------------------------------------------
echo "🛡️ Configuring firewall..."

# Reset UFW
ufw --force reset

# Default policies
ufw default deny incoming
ufw default allow outgoing

# Allow SSH (change port if using non-standard)
ufw allow 22/tcp comment 'SSH'

# Allow HTTP and HTTPS
ufw allow 80/tcp comment 'HTTP'
ufw allow 443/tcp comment 'HTTPS'

# Allow Docker internal (if needed)
# ufw allow from 172.16.0.0/12 comment 'Docker'

# Enable UFW
ufw --force enable

echo "✅ Firewall configured"

# -----------------------------------------------------------------------------
# 3. Configure Fail2Ban (Brute Force Protection)
# -----------------------------------------------------------------------------
echo "🚫 Configuring Fail2Ban..."

cat > /etc/fail2ban/jail.local << 'EOF'
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5
backend = systemd
banaction = ufw

[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
bantime = 86400

[nginx-http-auth]
enabled = true
filter = nginx-http-auth
port = http,https
logpath = /var/log/nginx/error.log
maxretry = 5

[nginx-limit-req]
enabled = true
port = http,https
filter = nginx-limit-req
logpath = /var/log/nginx/error.log
maxretry = 10

[nginx-botsearch]
enabled = true
port = http,https
filter = nginx-botsearch
logpath = /var/log/nginx/access.log
maxretry = 2
EOF

# Create nginx-botsearch filter
cat > /etc/fail2ban/filter.d/nginx-botsearch.local << 'EOF'
[Definition]
failregex = ^<HOST> .* "(GET|POST|HEAD) .*(wp-login|wp-admin|phpmyadmin|\.php|\.asp|\.env|\.git).*" (400|403|404)
ignoreregex =
EOF

systemctl enable fail2ban
systemctl restart fail2ban

echo "✅ Fail2Ban configured"

# -----------------------------------------------------------------------------
# 4. SSH Hardening
# -----------------------------------------------------------------------------
echo "🔐 Hardening SSH..."

# Backup original config
cp /etc/ssh/sshd_config /etc/ssh/sshd_config.backup

# Apply secure settings (uncomment and modify as needed)
cat >> /etc/ssh/sshd_config << 'EOF'

# Security hardening
PermitRootLogin prohibit-password
PasswordAuthentication no
PubkeyAuthentication yes
PermitEmptyPasswords no
X11Forwarding no
MaxAuthTries 3
ClientAliveInterval 300
ClientAliveCountMax 2
AllowAgentForwarding no
AllowTcpForwarding no
EOF

# Note: Uncomment PasswordAuthentication no ONLY after setting up SSH keys!
echo "⚠️  WARNING: Set up SSH keys before disabling password authentication!"

# Test SSH config
sshd -t && systemctl restart sshd

echo "✅ SSH hardened"

# -----------------------------------------------------------------------------
# 5. Enable Automatic Security Updates
# -----------------------------------------------------------------------------
echo "🔄 Enabling automatic security updates..."

cat > /etc/apt/apt.conf.d/50unattended-upgrades << 'EOF'
Unattended-Upgrade::Allowed-Origins {
    "${distro_id}:${distro_codename}";
    "${distro_id}:${distro_codename}-security";
    "${distro_id}ESMApps:${distro_codename}-apps-security";
    "${distro_id}ESM:${distro_codename}-infra-security";
};
Unattended-Upgrade::Package-Blacklist {
};
Unattended-Upgrade::AutoFixInterruptedDpkg "true";
Unattended-Upgrade::MinimalSteps "true";
Unattended-Upgrade::Remove-Unused-Kernel-Packages "true";
Unattended-Upgrade::Remove-Unused-Dependencies "true";
Unattended-Upgrade::Automatic-Reboot "false";
EOF

cat > /etc/apt/apt.conf.d/20auto-upgrades << 'EOF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
APT::Periodic::AutocleanInterval "7";
EOF

echo "✅ Automatic updates enabled"

# -----------------------------------------------------------------------------
# 6. Kernel Security Parameters
# -----------------------------------------------------------------------------
echo "🧠 Applying kernel security parameters..."

cat > /etc/sysctl.d/99-security.conf << 'EOF'
# IP Spoofing protection
net.ipv4.conf.all.rp_filter = 1
net.ipv4.conf.default.rp_filter = 1

# Ignore ICMP broadcast requests
net.ipv4.icmp_echo_ignore_broadcasts = 1

# Disable source packet routing
net.ipv4.conf.all.accept_source_route = 0
net.ipv6.conf.all.accept_source_route = 0
net.ipv4.conf.default.accept_source_route = 0
net.ipv6.conf.default.accept_source_route = 0

# Ignore send redirects
net.ipv4.conf.all.send_redirects = 0
net.ipv4.conf.default.send_redirects = 0

# Block SYN attacks
net.ipv4.tcp_syncookies = 1
net.ipv4.tcp_max_syn_backlog = 2048
net.ipv4.tcp_synack_retries = 2
net.ipv4.tcp_syn_retries = 5

# Log Martians
net.ipv4.conf.all.log_martians = 1
net.ipv4.icmp_ignore_bogus_error_responses = 1

# Disable IPv6 if not needed (uncomment if desired)
# net.ipv6.conf.all.disable_ipv6 = 1
# net.ipv6.conf.default.disable_ipv6 = 1
EOF

sysctl -p /etc/sysctl.d/99-security.conf

echo "✅ Kernel parameters applied"

# -----------------------------------------------------------------------------
# 7. Docker Security
# -----------------------------------------------------------------------------
echo "🐳 Applying Docker security settings..."

# Limit Docker container resources (example in docker-compose)
# Create docker daemon config for security
mkdir -p /etc/docker
cat > /etc/docker/daemon.json << 'EOF'
{
    "log-driver": "json-file",
    "log-opts": {
        "max-size": "10m",
        "max-file": "3"
    },
    "no-new-privileges": true,
    "live-restore": true
}
EOF

systemctl restart docker

echo "✅ Docker security applied"

# -----------------------------------------------------------------------------
# 8. Create non-root deploy user (optional)
# -----------------------------------------------------------------------------
echo "👤 Creating deploy user..."

if ! id "deploy" &>/dev/null; then
    useradd -m -s /bin/bash deploy
    usermod -aG docker deploy
    usermod -aG sudo deploy
    
    # Copy SSH keys from root
    mkdir -p /home/deploy/.ssh
    cp /root/.ssh/authorized_keys /home/deploy/.ssh/ 2>/dev/null || true
    chown -R deploy:deploy /home/deploy/.ssh
    chmod 700 /home/deploy/.ssh
    chmod 600 /home/deploy/.ssh/authorized_keys 2>/dev/null || true
    
    echo "✅ Deploy user created"
else
    echo "ℹ️  Deploy user already exists"
fi

# -----------------------------------------------------------------------------
# Summary
# -----------------------------------------------------------------------------
echo ""
echo "=============================================="
echo "🎉 VPS Security Hardening Complete!"
echo "=============================================="
echo ""
echo "What was configured:"
echo "  ✅ UFW Firewall (ports 22, 80, 443)"
echo "  ✅ Fail2Ban (SSH & Nginx protection)"
echo "  ✅ SSH Hardening"
echo "  ✅ Automatic Security Updates"
echo "  ✅ Kernel Security Parameters"
echo "  ✅ Docker Security Settings"
echo "  ✅ Deploy user created"
echo ""
echo "⚠️  IMPORTANT NEXT STEPS:"
echo "  1. Test SSH access before closing this session"
echo "  2. Set up SSH key authentication"
echo "  3. After SSH keys work, edit /etc/ssh/sshd_config:"
echo "     - Set 'PasswordAuthentication no'"
echo "     - Set 'PermitRootLogin no'"
echo "  4. Run: sudo systemctl restart sshd"
echo ""
echo "📊 Check status with:"
echo "  - sudo ufw status"
echo "  - sudo fail2ban-client status"
echo "  - sudo systemctl status fail2ban"
echo ""
