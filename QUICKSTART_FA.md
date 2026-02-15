# 🚀 راهنمای سریع نصب - VPN Master Panel

## 📋 پیش‌نیازها

- سرور Ubuntu 22.04 یا بالاتر
- دسترسی root
- حداقل 2GB RAM
- 20GB فضای دیسک

---

## ⚡ نصب سریع با Docker (توصیه می‌شود)

### مرحله 1: نصب Docker

```bash
# نصب Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# نصب Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### مرحله 2: دانلود و راه‌اندازی پنل

```bash
# دانلود پروژه
cd /opt
git clone https://github.com/yourusername/vpn-master-panel.git
cd vpn-master-panel

# کپی و ویرایش تنظیمات
cp .env.example .env
nano .env

# تغییر موارد زیر:
# - SECRET_KEY (یک کلید تصادفی 32 کاراکتری)
# - INITIAL_ADMIN_PASSWORD (رمز عبور ادمین)
# - DB_PASSWORD (رمز عبور دیتابیس)

# راه‌اندازی
docker-compose up -d

# مشاهده لاگ‌ها
docker-compose logs -f backend
```

### مرحله 3: دسترسی به پنل

```
آدرس پنل: http://IP_SERVER:3000
آدرس API: http://IP_SERVER:8000
مستندات API: http://IP_SERVER:8000/docs

یوزرنیم پیش‌فرض: admin
رمز عبور: (آنچه در .env تنظیم کردید)
```

---

## 📝 دستورات مفید

```bash
# مشاهده وضعیت سرویس‌ها
docker-compose ps

# توقف سرویس‌ها
docker-compose stop

# شروع مجدد
docker-compose restart

# مشاهده لاگ‌ها
docker-compose logs -f

# بروزرسانی
docker-compose pull
docker-compose up -d

# پشتیبان‌گیری از دیتابیس
docker-compose exec postgres pg_dump -U vpnmaster vpnmaster > backup.sql

# بازیابی از پشتیبان
docker-compose exec -T postgres psql -U vpnmaster vpnmaster < backup.sql
```

---

## 🔧 تنظیمات اولیه

### 1. تغییر رمز عبور ادمین

```bash
# از طریق API
curl -X PUT http://localhost:8000/api/v1/users/1 \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"password": "new_secure_password"}'
```

### 2. ایجاد اولین کاربر VPN

```bash
curl -X POST http://localhost:8000/api/v1/users/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "user1",
    "password": "user_password",
    "data_limit_gb": 50,
    "expiry_days": 30,
    "openvpn_enabled": true,
    "wireguard_enabled": true
  }'
```

### 3. راه‌اندازی تونل ایران-خارج

```bash
# تونل PersianShield (توصیه می‌شود)
curl -X POST http://localhost:8000/api/v1/tunnels/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "iran-germany",
    "tunnel_type": "persianshield",
    "iran_server_ip": "IP_IRAN",
    "iran_server_port": 443,
    "foreign_server_ip": "IP_FOREIGN",
    "foreign_server_port": 443,
    "domain_fronting_enabled": true,
    "tls_obfuscation": true
  }'
```

---

## 🌐 نصب سرویس‌های VPN

### OpenVPN

```bash
# نصب OpenVPN
sudo apt install -y openvpn

# کپی فایل‌های config (از پنل تولید می‌شود)
sudo cp server.conf /etc/openvpn/
sudo systemctl enable openvpn@server
sudo systemctl start openvpn@server
```

### WireGuard

```bash
# نصب WireGuard
sudo apt install -y wireguard

# تنظیم از طریق پنل انجام می‌شود
sudo systemctl enable wg-quick@wg0
sudo systemctl start wg-quick@wg0
```

---

## 🛡️ تونل PersianShield™

### ویژگی‌های خاص برای عبور از فیلترینگ ایران:

1. **Domain Fronting**: پنهان کردن مقصد اصلی
2. **TLS Obfuscation**: مخفی‌سازی ترافیک
3. **SNI Fragmentation**: تکه‌تکه کردن SNI
4. **Traffic Padding**: تصادفی‌سازی اندازه بسته‌ها
5. **Auto-Switching**: تغییر خودکار استراتژی

### نحوه استفاده:

```python
# تنظیمات تونل
{
  "domain_fronting_enabled": true,
  "fronting_domain": "cloudflare.com",  # یا هر CDN دیگر
  "tls_obfuscation": true,
  "sni": "www.google.com"
}
```

---

## 🔒 امنیت

### تنظیمات ضروری:

```bash
# فایروال
sudo ufw allow 22/tcp
sudo ufw allow 3000/tcp
sudo ufw allow 8000/tcp
sudo ufw allow 1194/udp
sudo ufw allow 51820/udp
sudo ufw enable

# تغییر پورت SSH
sudo nano /etc/ssh/sshd_config
# Port 22 → Port 2222
sudo systemctl restart sshd

# غیرفعال کردن root login
# PermitRootLogin no
```

---

## 📊 مانیتورینگ با Grafana (اختیاری)

```bash
# راه‌اندازی Prometheus + Grafana
docker-compose --profile monitoring up -d

# دسترسی به Grafana
http://IP_SERVER:3001
Username: admin
Password: (از .env)
```

---

## 🐛 عیب‌یابی

### سرویس backend راه‌اندازی نمی‌شود

```bash
# بررسی لاگ
docker-compose logs backend

# بررسی اتصال به دیتابیس
docker-compose exec backend python -c "from app.database import engine; print(engine)"
```

### تونل متصل نمی‌شود

```bash
# بررسی وضعیت تونل
curl http://localhost:8000/api/v1/tunnels/1/status \
  -H "Authorization: Bearer YOUR_TOKEN"

# بررسی پورت‌ها
sudo netstat -tulpn | grep -E '(443|8080)'

# تست اتصال
telnet FOREIGN_IP 443
```

### کاربر نمی‌تواند وصل شود

```bash
# بررسی وضعیت کاربر
docker-compose exec backend python -c "
from app.database import SessionLocal
from app.models.user import User
db = SessionLocal()
user = db.query(User).filter(User.username=='user1').first()
print(f'Status: {user.status}, Active: {user.is_active}')
"

# بررسی محدودیت‌ها
# - Data limit
# - Expiry date
# - Connection limit
```

---

## 📚 منابع بیشتر

- [مستندات کامل](README.md)
- [لیست ویژگی‌ها](FEATURES.md)
- [مستندات API](http://localhost:8000/docs)
- [GitHub Issues](https://github.com/yourusername/vpn-master-panel/issues)

---

## 💡 نکات مهم

1. **همیشه رمز عبور پیش‌فرض را تغییر دهید**
2. **از HTTPS استفاده کنید** (Let's Encrypt)
3. **پشتیبان منظم** از دیتابیس بگیرید
4. **لاگ‌ها را مانیتور کنید**
5. **بروزرسانی‌های امنیتی** را فراموش نکنید

---

**ساخته شده با ❤️ برای اینترنت آزاد**

🌐 شکستن موانع، اتصال مردم
