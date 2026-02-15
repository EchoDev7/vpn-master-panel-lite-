# 📘 راهنمای آپلود پروژه به GitHub

این راهنما به شما کمک می‌کند پروژه VPN Master Panel را در GitHub قرار دهید.

---

## 📋 مرحله 1: آماده‌سازی (قبل از آپلود)

### ✅ چک‌لیست فایل‌هایی که باید باشند:

```
vpn-master-panel/
├── backend/                  ✅ کد Backend
├── frontend/                 ✅ کد Frontend
├── scripts/                  ✅ اسکریپت‌های نصب
├── monitoring/               ✅ کانفیگ Monitoring
├── docker-compose.yml        ✅ Docker setup
├── .env.example             ✅ نمونه تنظیمات
├── .gitignore              ✅ فایل‌های ignore
├── README.md                ✅ مستندات اصلی
├── FEATURES.md              ✅ لیست ویژگی‌ها
├── QUICKSTART_FA.md         ✅ راهنمای سریع فارسی
├── CONTRIBUTING.md          ✅ راهنمای مشارکت
├── LICENSE                  ✅ مجوز MIT
└── install.sh              ✅ اسکریپت نصب
```

### ❌ چه فایل‌هایی نباید آپلود شوند:

این فایل‌ها توسط `.gitignore` حذف می‌شوند:
- ❌ `.env` (تنظیمات خصوصی)
- ❌ `__pycache__/` (فایل‌های کامپایل شده)
- ❌ `node_modules/` (کتابخانه‌های Node.js)
- ❌ `venv/` (محیط مجازی Python)
- ❌ `*.db` (دیتابیس محلی)
- ❌ `*.log` (فایل‌های لاگ)
- ❌ `*.pyc` (فایل‌های کامپایل Python)

---

## 🚀 مرحله 2: ساخت Repository در GitHub

### گام به گام:

1. **وارد GitHub شوید**
   - برو به: https://github.com
   - Login کن

2. **ساخت Repository جدید**
   - کلیک روی `+` در گوشه بالا
   - انتخاب `New repository`

3. **تنظیمات Repository:**
   ```
   Repository name: vpn-master-panel
   Description: Advanced Multi-Protocol VPN Management Panel with Anti-Censorship Features
   
   ☑️ Public (برای عموم قابل مشاهده)
   یا
   ☐ Private (فقط برای شما)
   
   ☐ Add a README file (چون خودمون داریم)
   ☐ Add .gitignore (چون خودمون داریم)
   ☑️ Choose a license: MIT License
   ```

4. **کلیک روی `Create repository`**

---

## 💻 مرحله 3: آپلود کدها (2 روش)

### روش 1: استفاده از Git Command Line (توصیه می‌شود)

#### نصب Git (اگر ندارید):

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install git
```

**macOS:**
```bash
brew install git
```

**Windows:**
- دانلود از: https://git-scm.com/download/win

#### کانفیگ Git (اولین بار):

```bash
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

#### آپلود کدها:

```bash
# 1. رفتن به پوشه پروژه
cd /path/to/vpn-master-panel

# 2. Initialize Git
git init

# 3. اضافه کردن همه فایل‌ها
git add .

# 4. اولین Commit
git commit -m "Initial commit: VPN Master Panel v1.0.0"

# 5. اضافه کردن Remote (GitHub URL خودتون رو بذارید)
git remote add origin https://github.com/YOUR_USERNAME/vpn-master-panel.git

# 6. Push به GitHub
git branch -M main
git push -u origin main
```

**⚠️ نکته مهم:** جای `YOUR_USERNAME` نام کاربری GitHub خودتون رو بذارید!

#### اگر خطا دادن (Authentication):

**روش 1: Personal Access Token (توصیه می‌شود)**

1. برو به GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
2. کلیک `Generate new token` (classic)
3. دسترسی‌ها: انتخاب `repo` (تمام موارد)
4. کپی Token (فقط یک بار نمایش داده می‌شود!)
5. هنگام push از این Token به جای password استفاده کنید

**روش 2: SSH Key**

```bash
# تولید SSH Key
ssh-keygen -t ed25519 -C "your.email@example.com"

# کپی Public Key
cat ~/.ssh/id_ed25519.pub

# اضافه کردن به GitHub:
# Settings → SSH and GPG keys → New SSH key
# Paste کردن public key

# استفاده از SSH URL
git remote set-url origin git@github.com:YOUR_USERNAME/vpn-master-panel.git
git push -u origin main
```

---

### روش 2: استفاده از GitHub Desktop (آسان‌تر)

1. **دانلود GitHub Desktop**
   - https://desktop.github.com/

2. **نصب و Login**

3. **Add Repository:**
   - File → Add Local Repository
   - انتخاب پوشه `vpn-master-panel`

4. **Commit:**
   - در قسمت چپ تمام فایل‌ها لیست می‌شوند
   - یک پیام بنویسید: "Initial commit"
   - کلیک `Commit to main`

5. **Publish:**
   - کلیک `Publish repository`
   - تایید `Push to GitHub`

---

## 📝 مرحله 4: بهبود Repository

### اضافه کردن Topics (Tags):

1. برو به صفحه Repository در GitHub
2. کلیک روی ⚙️ در بخش About
3. Topics اضافه کن:
   ```
   vpn, wireguard, openvpn, fastapi, react, docker, 
   iran, anti-censorship, tunnel, privacy, security
   ```

### ویرایش Description:

```
🛡️ Advanced Multi-Protocol VPN Management Panel | 
OpenVPN, WireGuard, L2TP, Cisco AnyConnect | 
PersianShield™ Anti-Censorship Technology | 
FastAPI + React + Docker
```

### اضافه کردن Social Preview:

1. Settings → Options → Social preview
2. آپلود یک تصویر 1280x640 (اختیاری)

---

## 🎨 مرحله 5: تکمیل Documentation

### ویرایش README.md:

در README خود این موارد را تغییر دهید:

```markdown
# جایگزین کردن URL‌ها
❌ https://github.com/yourusername/vpn-master-panel
✅ https://github.com/YOUR_ACTUAL_USERNAME/vpn-master-panel

# اضافه کردن Badges
![Stars](https://img.shields.io/github/stars/YOUR_USERNAME/vpn-master-panel)
![Forks](https://img.shields.io/github/forks/YOUR_USERNAME/vpn-master-panel)
![License](https://img.shields.io/github/license/YOUR_USERNAME/vpn-master-panel)
```

### ساخت Wiki (اختیاری):

1. Settings → Features → ☑️ Wikis
2. ساخت صفحات:
   - Installation Guide
   - API Documentation
   - Troubleshooting
   - FAQ

---

## 🔄 مرحله 6: بروزرسانی‌های آینده

### هر بار که تغییری دادید:

```bash
# 1. بررسی وضعیت
git status

# 2. اضافه کردن فایل‌های تغییر یافته
git add .

# 3. Commit با پیام مناسب
git commit -m "feat: add new tunnel type"

# 4. Push به GitHub
git push origin main
```

### ساخت Release:

```bash
# 1. ساخت Tag برای نسخه
git tag -a v1.0.0 -m "Release version 1.0.0"

# 2. Push Tag
git push origin v1.0.0

# 3. در GitHub:
# Releases → Create a new release
# انتخاب Tag → نوشتن Release Notes → Publish
```

---

## 🌟 مرحله 7: جذب Contributors

### فایل‌های ضروری برای Open Source:

✅ همه این فایل‌ها در پروژه شما هست:

1. **README.md** - توضیحات کامل
2. **LICENSE** - MIT License
3. **CONTRIBUTING.md** - راهنمای مشارکت
4. **.gitignore** - فایل‌های ignore
5. **CODE_OF_CONDUCT.md** (اختیاری)
6. **SECURITY.md** (اختیاری)

### ایجاد Issue Templates:

```bash
# ساخت پوشه
mkdir -p .github/ISSUE_TEMPLATE

# فایل Bug Report
cat > .github/ISSUE_TEMPLATE/bug_report.md << 'EOF'
---
name: Bug Report
about: Report a bug
title: '[BUG] '
labels: bug
---

## Describe the bug
A clear description

## Steps to reproduce
1. Go to '...'
2. Click on '...'

## Expected behavior
What should happen

## Screenshots
If applicable

## Environment
- OS: [e.g. Ubuntu 22.04]
- Version: [e.g. 1.0.0]
EOF

# Commit و Push
git add .github/
git commit -m "docs: add issue templates"
git push
```

---

## 🔒 مرحله 8: امنیت

### حفاظت از اطلاعات حساس:

**قبل از Push حتماً چک کنید:**

```bash
# جستجوی password‌ها
grep -r "password" . --exclude-dir={venv,node_modules,.git}

# جستجوی API keys
grep -r "api_key\|secret_key" . --exclude-dir={venv,node_modules,.git}

# جستجوی IP‌ها
grep -r "[0-9]\{1,3\}\.[0-9]\{1,3\}\.[0-9]\{1,3\}\.[0-9]\{1,3\}" . --exclude-dir={venv,node_modules,.git}
```

**اگر اشتباهی Password رو Push کردید:**

```bash
# پاک کردن از History (خطرناک!)
git filter-branch --force --index-filter \
  'git rm --cached --ignore-unmatch path/to/sensitive/file' \
  --prune-empty --tag-name-filter cat -- --all

# Force push
git push origin --force --all
```

**بهتر است:** Repository رو حذف کنید و دوباره بسازید!

---

## 📊 مرحله 9: GitHub Actions (CI/CD) - اختیاری

### ساخت فایل Test خودکار:

```bash
mkdir -p .github/workflows

cat > .github/workflows/tests.yml << 'EOF'
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        cd backend
        pip install -r requirements.txt
    
    - name: Run tests
      run: |
        cd backend
        pytest
EOF

git add .github/workflows/
git commit -m "ci: add GitHub Actions tests"
git push
```

---

## ✅ چک‌لیست نهایی

قبل از اعلام عمومی پروژه:

- ☑️ Repository ساخته شد
- ☑️ کدها Push شدند
- ☑️ README کامل است
- ☑️ LICENSE اضافه شد
- ☑️ .gitignore کار می‌کند
- ☑️ .env در Git نیست
- ☑️ Topics اضافه شدند
- ☑️ Description نوشته شد
- ☑️ اطلاعات حساس حذف شدند
- ☑️ لینک‌های README صحیح هستند
- ☑️ Screenshots اضافه شدند (اختیاری)

---

## 🎉 تبریک!

پروژه شما حالا در GitHub قرار دارد! 

**لینک Repository شما:**
```
https://github.com/YOUR_USERNAME/vpn-master-panel
```

### مراحل بعدی:

1. **اشتراک‌گذاری:**
   - توییتر، تلگرام، Reddit
   - هکرنیوز، لابکا
   
2. **ارتقا:**
   - اضافه کردن Screenshots
   - ساخت Demo Video
   - نوشتن Blog Post

3. **بهبود:**
   - گوش دادن به Feedback
   - رفع Bugs
   - اضافه کردن Features

---

**موفق باشید! 🚀**
