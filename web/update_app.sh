#!/bin/bash
# Quick update script for pushing changes to production
set -e

echo "🔄 Updating Invoice Generator App on EC2..."

# Auto-detect directory
if [ -d "/home/ubuntu/invoice-app" ]; then
    cd /home/ubuntu/invoice-app
fi

if [ -d ".git" ]; then
    echo "📥 Pulling latest git changes..."
    git pull
fi

source venv/bin/activate

echo "📚 Updating dependencies..."
pip install -r requirements.txt

echo "🔄 Restarting application service..."
sudo systemctl restart invoice-app
sudo systemctl restart nginx

echo "✅ Application updated and running!"
sudo systemctl status invoice-app --no-pager
