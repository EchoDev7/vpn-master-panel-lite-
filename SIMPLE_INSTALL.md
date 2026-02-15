# 🚀 نصب آسان و بدون Docker

این روش **ساده‌ترین** راه برای نصب VPN Master Panel است - بدون نیاز به Docker!

---

## ⚡ نصب سریع (یک دستور!)

### برای Ubuntu 22.04:

```bash
wget -O install.sh https://raw.githubusercontent.com/EchoDev7/vpn-master-panel/main/install-simple.sh && chmod +x install.sh && sudo bash install.sh
```

**همین!** فقط چند سوال ساده جواب بده و صبر کن.

---

## 📖 نصب گام به گام

### مرحله 1: اتصال به سرور

```bash
ssh root@YOUR_SERVER_IP
```

### مرحله 2: دانلود و اجرا

```bash
# دانلود
wget https://raw.githubusercontent.com/EchoDev7/vpn-master-panel/main/install-simple.sh

# اجازه اجرا
chmod +x install-simple.sh

# نصب
sudo bash install-simple.sh
```

### مرحله 3: پاسخ به سوالات

```
نام کاربری ادمین: [Enter برای admin]
رمز عبور: [رمز قوی بزن]
پورت: [Enter برای 8080]
ایمیل: [Enter]
```

### مرحله 4: منتظر بمان

نصب 5-10 دقیقه طول می‌کشه.

### مرحله 5: دسترسی

```
http://YOUR_SERVER_IP:8080
```

---

## 🎯 پس از نصب

### بررسی وضعیت:
```bash
systemctl status vpnmaster
```

### راه‌اندازی مجدد:
```bash
systemctl restart vpnmaster
```

### مشاهده لاگ:
```bash
journalctl -u vpnmaster -f
```

---

## 🔧 تنظیمات Firewall

اگر پنل باز نمی‌شود:

```bash
# باز کردن پورت
ufw allow 8080/tcp
ufw enable
```

---

## 🆚 مقایسه: Docker vs بدون Docker

| ویژگی | با Docker | بدون Docker |
|-------|-----------|-------------|
| نصب | پیچیده‌تر | ✅ آسان |
| حجم | 500MB+ | ✅ 100MB |
| سرعت | کندتر | ✅ سریع‌تر |
| مناسب | Production بزرگ | ✅ شروع سریع |

---

## 📁 فایل‌های نصب شده

```
/opt/vpn-master-panel/
├── backend/
│   ├── main.py
│   ├── requirements.txt
│   └── venv/
└── logs/
```

---

## 🐛 مشکلات متداول

### پنل باز نمی‌شود؟
```bash
# چک کردن
curl http://localhost:8080

# اگر کار کرد، مشکل از firewall است
ufw allow 8080/tcp
```

### خطای Permission?
```bash
# با sudo اجرا کنید
sudo bash install-simple.sh
```

### چطور پاک کنم?
```bash
systemctl stop vpnmaster
systemctl disable vpnmaster
rm -rf /opt/vpn-master-panel
rm /etc/systemd/system/vpnmaster.service
```

---

## 🎓 راهنمای کامل

برای راهنمای تصویری و مبتدی:

[📘 راهنمای کامل مبتدی](INSTALL_GUIDE_BEGINNER_FA.md)

---

## ✅ موفق بودی!

اگر پنل رو دیدی، تبریک! حالا می‌تونی:

1. ساخت کاربر VPN
2. تنظیم تونل‌ها
3. مانیتور ترافیک
4. مدیریت سرورها

**خوش اومدی به دنیای VPN Management! 🎉**
