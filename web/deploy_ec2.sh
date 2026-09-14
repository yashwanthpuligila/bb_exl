#!/bin/bash
# AWS EC2 Deployment Script for Invoice Generator Web App
set -e

echo "🚀 Starting deployment setup..."

# 1. Update system packages
echo "📦 Updating system packages..."
sudo apt update
sudo apt install -y python3 python3-pip python3-venv build-essential nginx

# 2. Configure 1GB Swap (Crucial for t2.micro / 1GB RAM instances to prevent OOM crash)
if [ $(swapon --show | wc -l) -le 1 ]; then
    echo "💾 Setting up 1GB swap space for memory stability..."
    sudo fallocate -l 1G /swapfile 2>/dev/null || sudo dd if=/dev/zero of=/swapfile bs=1M count=1024
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    if ! grep -q '/swapfile' /etc/fstab; then
        echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
    fi
fi

# 3. Setup application directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="/home/ubuntu/invoice-app"

if [ "$SCRIPT_DIR" != "$APP_DIR" ]; then
    echo "📁 Copying files to $APP_DIR..."
    mkdir -p "$APP_DIR"
    cp -r "$SCRIPT_DIR"/* "$APP_DIR/"
fi

cd "$APP_DIR"

# 4. Create virtual environment & install requirements
echo "🔧 Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

echo "📚 Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn

# Ensure Invoice Storage directory exists
mkdir -p "$APP_DIR/Invoice Storage"
sudo chown -R ubuntu:www-data "$APP_DIR"
sudo chmod -R 775 "$APP_DIR"

# 5. Create systemd service file (optimized for t2.micro / t2.small)
echo "⚙️ Creating systemd service..."
sudo tee /etc/systemd/system/invoice-app.service > /dev/null <<EOF
[Unit]
Description=Invoice Generator Web Application
After=network.target

[Service]
User=ubuntu
Group=www-data
WorkingDirectory=$APP_DIR
Environment="PATH=$APP_DIR/venv/bin"
ExecStart=$APP_DIR/venv/bin/gunicorn --workers 2 --threads 2 --timeout 120 --bind 127.0.0.1:5000 app:app
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

# 6. Create Nginx configuration
echo "🔧 Configuring Nginx..."
sudo tee /etc/nginx/sites-available/invoice-app > /dev/null <<EOF
server {
    listen 80;
    server_name _;

    client_max_body_size 50M;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # Timeout settings for report / invoice generation
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }
}
EOF

# Enable the site
sudo ln -sf /etc/nginx/sites-available/invoice-app /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Test Nginx configuration
sudo nginx -t

# 7. Reload systemd and start services
echo "🔄 Starting services..."
sudo systemctl daemon-reload
sudo systemctl enable invoice-app
sudo systemctl restart invoice-app
sudo systemctl restart nginx

# 8. Configure firewall
echo "🔥 Configuring firewall..."
sudo ufw allow 22
sudo ufw allow 80
sudo ufw allow 443
echo "y" | sudo ufw enable || true

echo "✅ Deployment complete!"
echo ""
echo "📊 Service Status:"
sudo systemctl status invoice-app --no-pager
echo ""
echo "🌐 Your application should now be accessible at: http://YOUR_EC2_PUBLIC_IP"
