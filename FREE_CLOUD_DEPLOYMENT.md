# 🚀 Free Cloud Deployment Guide (Render / Railway)

This guide walks you through deploying your **Invoice ERP Web App** to **Render** or **Railway** for free with automatic **HTTPS / SSL** and instant **PWA App Installation** on PC, Android, and iOS.

---

## 🌟 Method 1: Deploy on Render (Recommended - 100% Free)

Render provides a completely free tier with automatic HTTPS and continuous deployment directly from your GitHub repository.

### Step 1: Commit and Push your Code to GitHub
Run these commands in PowerShell from `d:\bb_exl`:
```powershell
cd d:\bb_exl
git add -A
git commit -m "Configure free cloud deployment and PWA"
git push origin main
```

### Step 2: Create a Free Account on Render
1. Open [render.com](https://render.com) in your browser.
2. Click **Get Started** and sign in with your **GitHub** account.

### Step 3: Connect your Repository
1. In your Render Dashboard, click the blue **New +** button in the top right.
2. Select **Web Service**.
3. Choose **Build and deploy from a Git repository** ➡️ click **Next**.
4. In the repository list, find and connect **`bb_exl`** (or `yashwanthpuligila/bb_exl`).
   *(If not listed, click "Configure account" to grant Render access to your GitHub repo).*

### Step 4: Configure Settings
Render will load the setup form. Enter the following:

| Setting | Value |
| :--- | :--- |
| **Name** | `invoice-erp` *(or any name you like)* |
| **Region** | Singapore / Oregon / Frankfurt *(choose closest to you)* |
| **Branch** | `main` |
| **Root Directory** | *(leave blank)* |
| **Runtime** | `Python 3` |
| **Build Command** | `pip install -r web/requirements.txt` |
| **Start Command** | `gunicorn --chdir web --workers 2 --threads 2 --timeout 120 app:app` |
| **Instance Type** | **Free** ($0 / month) |

### Step 5: Deploy!
1. Click **Create Web Service** at the bottom.
2. Render will pull your repository, install packages, and deploy the application.
3. Within 2–3 minutes, you will see a green checkmark: **`Live`**!
4. Your free public URL will be visible at the top:
   ```
   https://invoice-erp-xxxx.onrender.com
   ```

---

## 📲 Installing as an App from your Live URL

Because Render provides a real, secure **`https://`** certificate:
- **On Android**: Open your Render URL in Chrome ➡️ tap **"Install App"** or the 3 dots ➡️ **Add to Home screen**.
- **On iPhone / iPad**: Open in Safari ➡️ tap **Share** ➡️ **Add to Home Screen**.
- **On Windows / Mac**: Open in Chrome or Edge ➡️ click the **Install App** icon in the address bar (or click **📲 Install App** in the left sidebar).

---

## 🚂 Method 2: Deploy on Railway (Alternative)

1. Open [railway.app](https://railway.app) and sign in with GitHub.
2. Click **New Project** ➡️ **Deploy from GitHub repo**.
3. Select **`bb_exl`**.
4. Click **Deploy Now**. Railway automatically reads the included `Procfile` and deploys your app.
5. In your service settings under **Networking**, click **Generate Domain** to get your public `https://...up.railway.app` URL.

---

## 🔄 Automatic Updates
Whenever you make changes to your code in the future and push them:
```powershell
git add -A
git commit -m "Update feature"
git push origin main
```
Render and Railway will **automatically rebuild and redeploy** your live app without you touching anything!
