#!/bin/bash
set -euo pipefail

# Production Bootstrap Script for Telemetry API
# Installs Docker, Caddy, and configures system security

echo "🚀 Starting production bootstrap..."

# Update system
echo "📦 Updating system packages..."
sudo apt update && sudo apt -y upgrade

# Install required packages
echo "📦 Installing required packages..."
sudo apt -y install curl jq ufw fail2ban

# Install Docker
echo "🐳 Installing Docker..."
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu $(. /etc/os-release; echo $VERSION_CODENAME) stable" \
| sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt -y install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Add user to docker group
sudo usermod -aG docker $USER

# Install Caddy
echo "🌐 Installing Caddy..."
sudo apt -y install debian-keyring debian-archive-keyring
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/caddy-stable-archive-keyring.gpg] \
  https://dl.cloudsmith.io/public/caddy/stable/deb/ubuntu noble main" | \
  sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update && sudo apt -y install caddy

# Configure UFW firewall
echo "🔥 Configuring firewall..."
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable

# Configure fail2ban
echo "🛡️ Configuring fail2ban..."
sudo cp ops/fail2ban.local /etc/fail2ban/jail.local
sudo systemctl enable fail2ban
sudo systemctl start fail2ban

# Create log directories
echo "📝 Creating log directories..."
sudo mkdir -p /var/log/caddy
sudo chown www-data:www-data /var/log/caddy

# Configure logrotate
echo "📋 Configuring logrotate..."
sudo cp ops/logrotate.d/caddy /etc/logrotate.d/caddy

echo "✅ Bootstrap completed successfully!"
echo "🔑 Next steps:"
echo "   1. Copy .env.example to .env and configure"
echo "   2. Add your domain DNS A record pointing to this server"
echo "   3. Run: ./scripts/deploy.sh"
