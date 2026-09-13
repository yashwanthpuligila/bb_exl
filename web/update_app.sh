#!/bin/bash
# Quick update script for pushing changes to production

echo "🔄 Updating Invoice Generator App on EC2..."

# Update application
cd /home/ubuntu/invoice-app
source venv/bin/activate

# If using git
# git pull

# Install any new dependencies
pip install -r requirements.txt

# Restart the service
sudo systemctl restart invoice-app

echo "✅ Application updated and restarted!"
echo "🌐 Check status at: http://YOUR_EC2_PUBLIC_IP"
sudo systemctl status invoice-app --no-pager
