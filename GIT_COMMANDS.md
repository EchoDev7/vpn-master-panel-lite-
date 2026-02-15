# 🚀 دستورات سریع Git & GitHub

## ⚡ آپلود سریع (3 دستور)

```bash
# 1. ساخت Repository در GitHub با مرورگر
# https://github.com/new

# 2. اجرای اسکریپت خودکار
cd vpn-master-panel
chmod +x setup-github.sh
./setup-github.sh

# یا دستی:
git init
git add .
git commit -m "Initial commit: VPN Master Panel"
git remote add origin https://github.com/YOUR_USERNAME/vpn-master-panel.git
git branch -M main
git push -u origin main
```

---

## 📚 دستورات پرکاربرد

### نصب و راه‌اندازی اولیه

```bash
# نصب Git
sudo apt install git  # Ubuntu/Debian
brew install git      # macOS

# تنظیمات اولیه
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"

# بررسی تنظیمات
git config --list
```

### شروع پروژه

```bash
# راه‌اندازی در پوشه موجود
cd vpn-master-panel
git init

# Clone کردن پروژه موجود
git clone https://github.com/username/repo.git
```

### مدیریت فایل‌ها

```bash
# بررسی وضعیت
git status

# اضافه کردن همه فایل‌ها
git add .

# اضافه کردن فایل خاص
git add backend/app/main.py

# حذف فایل از staging
git reset HEAD filename.py

# حذف فایل از Git (اما نه از دیسک)
git rm --cached filename.py
```

### Commit کردن

```bash
# ساخت commit
git commit -m "feat: add user authentication"

# تغییر آخرین commit
git commit --amend -m "new message"

# مشاهده تاریخچه
git log
git log --oneline
git log --graph --oneline
```

### کار با Remote

```bash
# اضافه کردن remote
git remote add origin https://github.com/user/repo.git

# مشاهده remote‌ها
git remote -v

# تغییر URL remote
git remote set-url origin NEW_URL

# حذف remote
git remote remove origin
```

### Push و Pull

```bash
# Push به GitHub
git push origin main

# Push اولین بار (set upstream)
git push -u origin main

# Force push (خطرناک!)
git push -f origin main

# Pull از GitHub
git pull origin main
```

### Branch‌ها

```bash
# لیست branch‌ها
git branch

# ساخت branch جدید
git branch feature-new

# تغییر branch
git checkout feature-new

# ساخت و تغییر همزمان
git checkout -b feature-new

# حذف branch
git branch -d feature-new

# Merge کردن
git checkout main
git merge feature-new
```

### مشکلات متداول

```bash
# لغو تغییرات محلی
git checkout -- filename.py

# بازگشت به commit قبلی
git reset --hard HEAD~1

# حذف فایل‌های untracked
git clean -fd

# دیدن تفاوت‌ها
git diff
git diff filename.py
```

---

## 🔐 Authentication

### روش 1: Personal Access Token (PAT)

```bash
# 1. ساخت Token در GitHub:
# Settings → Developer settings → Personal access tokens → Generate new token

# 2. انتخاب دسترسی‌ها:
☑️ repo (full control)
☑️ workflow (if needed)

# 3. کپی Token (فقط یک بار نمایش داده می‌شود!)

# 4. استفاده هنگام Push:
Username: your_github_username
Password: ghp_xxxxxxxxxxxxxxxxxxxx (Token)

# 5. ذخیره Token (اختیاری):
git config --global credential.helper store
# دفعه بعد ذخیره می‌شود
```

### روش 2: SSH Key

```bash
# 1. ساخت SSH Key
ssh-keygen -t ed25519 -C "your.email@example.com"
# یا برای سیستم‌های قدیمی:
ssh-keygen -t rsa -b 4096 -C "your.email@example.com"

# 2. شروع SSH agent
eval "$(ssh-agent -s)"

# 3. اضافه کردن Key
ssh-add ~/.ssh/id_ed25519

# 4. کپی Public Key
cat ~/.ssh/id_ed25519.pub
# یا در macOS:
pbcopy < ~/.ssh/id_ed25519.pub

# 5. اضافه کردن به GitHub:
# Settings → SSH and GPG keys → New SSH key → Paste

# 6. تست اتصال
ssh -T git@github.com

# 7. استفاده
git remote set-url origin git@github.com:username/repo.git
```

---

## 📦 دستورات پروژه VPN Master Panel

### آماده‌سازی برای Commit

```bash
# بررسی فایل‌های تغییر یافته
git status

# بررسی تفاوت‌ها
git diff

# حذف فایل‌های غیرضروری
rm -rf __pycache__/ *.pyc node_modules/

# بررسی .gitignore
cat .gitignore

# اضافه و Commit
git add .
git commit -m "feat: add PersianShield tunnel"
git push
```

### ساخت Tag برای Release

```bash
# ساخت Tag
git tag -a v1.0.0 -m "Release version 1.0.0"

# Push Tag
git push origin v1.0.0

# Push همه Tags
git push --tags

# لیست Tags
git tag

# حذف Tag (محلی)
git tag -d v1.0.0

# حذف Tag (remote)
git push origin :refs/tags/v1.0.0
```

### کار با Submodule (اگر نیاز باشد)

```bash
# اضافه کردن Submodule
git submodule add https://github.com/user/repo.git path/to/submodule

# Clone با Submodule
git clone --recursive https://github.com/user/repo.git

# بروزرسانی Submodules
git submodule update --init --recursive
```

---

## 🐛 رفع مشکلات

### خطای Authentication

```bash
# حذف credential ذخیره شده
git credential reject
protocol=https
host=github.com

# یا
rm ~/.git-credentials

# استفاده از Token جدید
```

### خطای "remote origin already exists"

```bash
# حذف و اضافه مجدد
git remote remove origin
git remote add origin https://github.com/user/repo.git
```

### اشتباهی فایل حساس Commit شد

```bash
# روش 1: حذف از آخرین commit (اگر هنوز Push نشده)
git reset --soft HEAD~1
# حذف فایل
rm .env
# Commit دوباره
git add .
git commit -m "fix: remove sensitive file"

# روش 2: اگر Push شده (خطرناک!)
git filter-branch --force --index-filter \
  'git rm --cached --ignore-unmatch .env' \
  --prune-empty --tag-name-filter cat -- --all

git push origin --force --all

# روش 3: بهترین راه
# حذف Repository و ساخت دوباره با فایل‌های تمیز
```

### Merge Conflict

```bash
# وقتی conflict داشتید
git status  # فایل‌های conflict دار را نشان می‌دهد

# ویرایش فایل‌ها و حذف markers:
<<<<<<< HEAD
=======
>>>>>>> branch-name

# بعد از حل conflict:
git add .
git commit -m "fix: resolve merge conflict"
```

---

## 📝 Commit Message Guidelines

```bash
# فرمت:
<type>(<scope>): <subject>

# Types:
feat:     New feature
fix:      Bug fix
docs:     Documentation
style:    Formatting
refactor: Code restructuring
test:     Tests
chore:    Maintenance

# مثال‌ها:
git commit -m "feat(api): add user search endpoint"
git commit -m "fix(tunnel): resolve connection timeout"
git commit -m "docs(readme): update installation guide"
git commit -m "refactor(auth): simplify JWT logic"
```

---

## 🔄 Workflow توسعه

```bash
# 1. ساخت branch برای feature
git checkout -b feature/new-tunnel

# 2. کار روی feature
# ... edit files ...

# 3. Commit تغییرات
git add .
git commit -m "feat: add new tunnel type"

# 4. Push branch
git push -u origin feature/new-tunnel

# 5. ساخت Pull Request در GitHub

# 6. بعد از Merge، حذف branch
git checkout main
git pull
git branch -d feature/new-tunnel
```

---

## 🎯 Git Aliases (میانبرها)

```bash
# تنظیم aliases
git config --global alias.st status
git config --global alias.co checkout
git config --global alias.br branch
git config --global alias.ci commit
git config --global alias.unstage 'reset HEAD --'
git config --global alias.last 'log -1 HEAD'
git config --global alias.visual 'log --graph --oneline --all'

# استفاده:
git st      # به جای git status
git co main # به جای git checkout main
git visual  # نمایش گراف
```

---

## 📊 بررسی پروژه

```bash
# تعداد commits
git rev-list --count HEAD

# آمار contributor
git shortlog -sn

# تغییرات هر فایل
git log --follow -p -- filename.py

# فایل‌های پرتغییر
git log --pretty=format: --name-only | sort | uniq -c | sort -rg | head -10

# اندازه repository
git count-objects -vH
```

---

## 💡 نکات مفید

```bash
# Stash کردن تغییرات موقت
git stash
git stash list
git stash pop

# Cherry-pick (انتخاب commit خاص)
git cherry-pick <commit-hash>

# Rebase (تاریخچه تمیز)
git rebase main

# Reset soft (حفظ تغییرات)
git reset --soft HEAD~1

# Reset hard (حذف تغییرات)
git reset --hard HEAD~1

# بررسی کی چه خطی را نوشته
git blame filename.py

# جستجو در commits
git log --all --grep='keyword'
```

---

**این فایل را برای مراجعه سریع نگه دارید! 🚀**
