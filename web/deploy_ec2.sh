#!/bin/bash
# AWS EC2 Deployment Script for Invoice Generator Web App

echo "🚀 Starting deployment setup..."

# Update system
echo "📦 Updating system packages..."
sudo apt update
sudo apt upgrade -y

# Install Python and pip
echo "🐍 Installing Python 3 and pip..."
sudo apt install -y python3 python3-pip python3-venv

# Install Nginx
echo "🌐 Installing Nginx..."
sudo apt install -y nginx

# Create application directory
echo "📁 Setting up application directory..."
APP_DIR="/home/ubuntu/invoice-app"
mkdir -p $APP_DIR

# Copy application files (assumes you're running this from the web directory)
echo "📋 Copying application files..."
cp -r * $APP_DIR/

# Change to app directory
cd $APP_DIR

# Create virtual environment
echo "🔧 Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo "📚 Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn

# Create systemd service file
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
ExecStart=$APP_DIR/venv/bin/gunicorn --workers 3 --bind 127.0.0.1:5000 app:app

[Install]
WantedBy=multi-user.target
EOF

# Create Nginx configuration
echo "🔧 Configuring Nginx..."
sudo tee /etc/nginx/sites-available/invoice-app > /dev/null <<EOF
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # Increase timeout for large file operations
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }

    # Serve static files directly
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
        proxy_pass http://127.0.0.1:5000;
        expires 1d;
        add_header Cache-Control "public, immutable";
    }
}
EOF

# Enable the site
sudo ln -sf /etc/nginx/sites-available/invoice-app /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Test Nginx configuration
sudo nginx -t

# Reload systemd and start services
echo "🔄 Starting services..."
sudo systemctl daemon-reload
sudo systemctl enable invoice-app
sudo systemctl start invoice-app
sudo systemctl restart nginx

# Configure firewall
echo "🔥 Configuring firewall..."
sudo ufw allow 22
sudo ufw allow 80
sudo ufw allow 443
echo "y" | sudo ufw enable

echo "✅ Deployment complete!"
echo ""
echo "📊 Service Status:"
sudo systemctl status invoice-app --no-pager
echo ""
echo "🌐 Your application should now be accessible at: http://YOUR_EC2_PUBLIC_IP"
echo ""
echo "📝 Useful commands:"
echo "  - View logs: sudo journalctl -u invoice-app -f"
echo "  - Restart app: sudo systemctl restart invoice-app"
echo "  - Check status: sudo systemctl status invoice-app"
