# AWS EC2 Deployment Guide - Invoice Generator Web App

## 📋 Prerequisites

1. AWS Account with EC2 access
2. Basic knowledge of AWS Console
3. SSH client (PuTTY for Windows or native SSH)

---

## 🚀 Step-by-Step Deployment

### **Step 1: Launch EC2 Instance**

1. **Login to AWS Console**
   - Go to https://aws.amazon.com/console/
   - Navigate to EC2 Dashboard

2. **Launch Instance**
   - Click "Launch Instance"
   - **Name**: `invoice-generator-app`
   - **AMI**: Ubuntu Server 22.04 LTS (Free tier eligible)
   - **Instance Type**: `t2.micro` (1 GB RAM, good for testing) or `t2.small` (2 GB RAM, recommended for production)
   - **Key Pair**: 
     - Create new key pair or use existing
     - Name: `invoice-app-key`
     - Type: RSA
     - Format: `.pem` (for Mac/Linux) or `.ppk` (for PuTTY on Windows)
     - **Download and save securely!**

3. **Network Settings**
   - Create or select a security group with these rules:
     - **SSH**: Port 22, Source: Your IP (for security)
     - **HTTP**: Port 80, Source: Anywhere (0.0.0.0/0)
     - **HTTPS**: Port 443, Source: Anywhere (0.0.0.0/0)

4. **Configure Storage**
   - 8 GB or more (default is fine)
   - Keep gp3 SSD type

5. **Launch Instance**
   - Review and click "Launch"
   - Wait for instance state to be "Running"
   - Note down the **Public IPv4 address**

---

### **Step 2: Connect to EC2 Instance**

#### For Windows (using PuTTY):
```bash
# Convert .pem to .ppk using PuTTYgen if needed
# In PuTTY:
# - Host: ubuntu@YOUR_EC2_PUBLIC_IP
# - Port: 22
# - Auth: Browse to your .ppk file
```

#### For Mac/Linux/Windows PowerShell:
```bash
# Set correct permissions (Mac/Linux only)
chmod 400 invoice-app-key.pem

# Connect via SSH
ssh -i invoice-app-key.pem ubuntu@YOUR_EC2_PUBLIC_IP
```

---

### **Step 3: Transfer Application Files**

#### Option A: Using SCP (Recommended)
```bash
# From your local machine, navigate to the project folder
cd d:\bb_exl\web

# Transfer entire web folder to EC2
scp -i /path/to/invoice-app-key.pem -r ./* ubuntu@YOUR_EC2_PUBLIC_IP:/home/ubuntu/invoice-app/
```

#### Option B: Using Git (Alternative)
```bash
# On EC2 instance
sudo apt update
sudo apt install -y git
git clone YOUR_REPOSITORY_URL
cd YOUR_REPOSITORY/web
```

#### Option C: Manual Upload via FileZilla
1. Download FileZilla
2. Use SFTP protocol
3. Host: `sftp://YOUR_EC2_PUBLIC_IP`
4. User: `ubuntu`
5. Key file: Your `.pem` or `.ppk` file
6. Upload the `web` folder

---

### **Step 4: Run Automated Deployment Script**

```bash
# On EC2 instance, navigate to the app folder
cd /home/ubuntu/invoice-app

# Make deployment script executable
chmod +x deploy_ec2.sh

# Run the deployment script
./deploy_ec2.sh
```

The script will automatically:
- Install Python, Nginx, and dependencies
- Set up virtual environment
- Configure systemd service
- Set up Nginx reverse proxy
- Start the application

---

### **Step 5: Verify Deployment**

1. **Check Application Status**
   ```bash
   sudo systemctl status invoice-app
   ```

2. **Check Nginx Status**
   ```bash
   sudo systemctl status nginx
   ```

3. **View Application Logs**
   ```bash
   sudo journalctl -u invoice-app -f
   ```

4. **Test in Browser**
   - Open: `http://YOUR_EC2_PUBLIC_IP`
   - You should see the Invoice Generator interface

---

## 🔧 Manual Deployment (If Script Fails)

### Install Dependencies
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv nginx
```

### Setup Application
```bash
cd /home/ubuntu/invoice-app
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install gunicorn
```

### Create Systemd Service
```bash
sudo nano /etc/systemd/system/invoice-app.service
```

Paste:
```ini
[Unit]
Description=Invoice Generator Web Application
After=network.target

[Service]
User=ubuntu
Group=www-data
WorkingDirectory=/home/ubuntu/invoice-app
Environment="PATH=/home/ubuntu/invoice-app/venv/bin"
ExecStart=/home/ubuntu/invoice-app/venv/bin/gunicorn --workers 3 --bind 127.0.0.1:5000 app:app

[Install]
WantedBy=multi-user.target
```

### Configure Nginx
```bash
sudo nano /etc/nginx/sites-available/invoice-app
```

Paste:
```nginx
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 300s;
    }
}
```

Enable site:
```bash
sudo ln -s /etc/nginx/sites-available/invoice-app /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default
sudo nginx -t
```

### Start Services
```bash
sudo systemctl daemon-reload
sudo systemctl enable invoice-app
sudo systemctl start invoice-app
sudo systemctl restart nginx
```

---

## 🔒 Optional: Setup HTTPS with SSL (Free)

```bash
# Install Certbot
sudo apt install -y certbot python3-certbot-nginx

# Get SSL certificate (requires domain name)
sudo certbot --nginx -d yourdomain.com

# Auto-renew will be configured automatically
```

---

## 🛠️ Useful Management Commands

### Application Management
```bash
# Restart application
sudo systemctl restart invoice-app

# Stop application
sudo systemctl stop invoice-app

# View logs (real-time)
sudo journalctl -u invoice-app -f

# View last 100 lines
sudo journalctl -u invoice-app -n 100
```

### Nginx Management
```bash
# Restart Nginx
sudo systemctl restart nginx

# Test configuration
sudo nginx -t

# View Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### Application Updates
```bash
# On EC2, pull latest code
cd /home/ubuntu/invoice-app
git pull  # if using git

# Or upload new files via SCP

# Restart the service
sudo systemctl restart invoice-app
```

---

## 📊 Monitoring & Maintenance

### Check System Resources
```bash
# CPU and Memory usage
htop  # or 'top'

# Disk usage
df -h

# Application resource usage
ps aux | grep gunicorn
```

### Backup Important Files
```bash
# Backup generated invoices
scp -i invoice-app-key.pem -r ubuntu@YOUR_EC2_IP:/home/ubuntu/invoice-app/*.xlsx ./backups/
```

---

## 🐛 Troubleshooting

### Application Won't Start
```bash
# Check detailed logs
sudo journalctl -u invoice-app -xe

# Check Python errors
cd /home/ubuntu/invoice-app
source venv/bin/activate
python3 app.py  # Run directly to see errors
```

### Can't Access Website
1. Check Security Group rules (port 80 open?)
2. Check if app is running: `sudo systemctl status invoice-app`
3. Check Nginx: `sudo systemctl status nginx`
4. Check firewall: `sudo ufw status`

### Port Already in Use
```bash
# Find what's using port 5000
sudo lsof -i :5000

# Kill the process
sudo kill -9 PID
```

---

## 💰 Cost Optimization

- **Use t2.micro** (Free tier: 750 hours/month for 12 months)
- **Stop instance** when not in use (important!)
- **Use Elastic IP** only if you need static IP (small charge if not attached)
- **Monitor billing** in AWS Console

---

## 🎉 Success Checklist

- [ ] EC2 instance launched and running
- [ ] SSH connection successful
- [ ] Files transferred to EC2
- [ ] Dependencies installed
- [ ] Application service running
- [ ] Nginx configured and running
- [ ] Can access website via public IP
- [ ] Invoices can be generated successfully

---

## 📞 Support

If you encounter issues:
1. Check the troubleshooting section
2. Review application logs: `sudo journalctl -u invoice-app -f`
3. Verify all security group rules
4. Ensure all dependencies are installed

---

**🎊 Congratulations! Your Invoice Generator is now live on AWS EC2!**

Access it at: `http://YOUR_EC2_PUBLIC_IP`
