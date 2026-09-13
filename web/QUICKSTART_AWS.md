# Quick Start Guide for AWS EC2 Deployment

## 🚀 Quick 5-Minute Deploy

### 1. Launch EC2 Instance
- Go to AWS Console → EC2 → Launch Instance
- **AMI**: Ubuntu 22.04 LTS
- **Type**: t2.small (or t2.micro for free tier)
- **Security Group**: Allow ports 22, 80, 443
- **Download key pair** (save as `invoice-app-key.pem`)

### 2. Get Your Public IP
- Wait for instance state: "Running"
- Copy the **Public IPv4 address** (e.g., 54.123.45.67)

### 3. Transfer Files
```powershell
# From PowerShell in d:\bb_exl\web folder
scp -i C:\path\to\invoice-app-key.pem -r * ubuntu@YOUR_EC2_IP:/home/ubuntu/
```

### 4. Connect & Deploy
```bash
# Connect to EC2
ssh -i invoice-app-key.pem ubuntu@YOUR_EC2_IP

# Navigate and run deployment
cd /home/ubuntu
chmod +x deploy_ec2.sh
./deploy_ec2.sh
```

### 5. Access Your App
Open browser: `http://YOUR_EC2_IP`

---

## ✅ That's it! Your app is live!

For detailed instructions, see [AWS_EC2_DEPLOYMENT_GUIDE.md](AWS_EC2_DEPLOYMENT_GUIDE.md)

## 📋 Common Commands

```bash
# View logs
sudo journalctl -u invoice-app -f

# Restart app
sudo systemctl restart invoice-app

# Check status
sudo systemctl status invoice-app
```

## 🔒 Security Tips
- Change SSH port 22 to custom port
- Use Elastic IP for consistent access
- Setup CloudWatch monitoring
- Regular backups of generated invoices
