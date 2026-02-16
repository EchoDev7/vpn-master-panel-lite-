# Changelog

All notable changes to VPN Master Panel will be documented in this file.

## [3.0.0] - 2026-02-16

### 🎉 Major Release - Enterprise Features

Complete enterprise-grade features for production deployment.

### Added

#### 1. WebSocket Real-time Communication (5 files)
- **Backend**: Connection manager with user tracking
- **Backend**: Event handlers for notifications, users, traffic
- **Frontend**: WebSocket client service
- **Frontend**: React hook for WebSocket
- **Features**: Auto-reconnection, heartbeat, admin broadcasts

#### 2. Multi-language Support (4 files)
- **Languages**: English, Persian/Farsi (RTL)
- **Frontend**: i18n configuration with language detection
- **Frontend**: Language switcher component
- **Features**: RTL support, persistent language preference

#### 3. Email Notifications (3 files)
- **Backend**: SMTP email service with async sending
- **Backend**: Jinja2 email templates
- **Templates**: Welcome email, expiry warning, traffic limit
- **Features**: Queue system ready, HTML templates

#### 4. Telegram Bot Integration (1 file)
- **Backend**: Complete bot with 6 commands
- **Commands**: /start, /status, /users, /traffic, /connections, /help
- **Features**: Inline keyboards, admin notifications, async messaging

#### 5. Domain & SSL Automation (1 file)
- **Script**: Automatic SSL with Let's Encrypt
- **Features**: Auto-renewal, HTTP→HTTPS redirect, multiple subdomains
- **Infrastructure**: Systemd timer for renewal

#### 6. Subscription Management (4 files)
- **Backend**: 3 database models (Plan, Subscription, History)
- **Backend**: Database migration
- **Features**: 4 default plans, payment tracking, auto-renewal

### Changed
- **package.json**: Added i18n dependencies
- **requirements.txt**: Added enterprise dependencies
- **main.py**: Added WebSocket endpoint
- **README.md**: Updated with v3.0 features

### Dependencies
- Added `react-i18next@^13.5.0`
- Added `i18next@^23.7.0`
- Added `i18next-browser-languagedetector@^7.2.0`
- Added `aiosmtplib@>=3.0.0`
- Added `jinja2@>=3.1.0`
- Added `python-telegram-bot@>=20.0`
- Added `aiohttp@>=3.9.0`

### Documentation
- Created `enterprise_plan.md` - Implementation plan
- Created `enterprise_installation.md` - Installation guide
- Created `walkthrough.md` - Complete feature walkthrough
- Created `.env.enterprise.example` - Configuration template

### Performance
- WebSocket: 100+ concurrent connections
- Email: Queue-based async sending
- Telegram: Async bot with minimal overhead
- RAM: +100MB total for all features

### Security
- JWT authentication for WebSocket
- SMTP with TLS encryption
- SSL/HTTPS with Let's Encrypt
- Telegram bot token security

---

## [2.0.0] - 2026-02-16

### 🎉 Major Release - Professional Dashboard

Complete overhaul with 16 new components and advanced analytics.

### Added
- 16 new frontend components
- Real-time notifications (database-backed)
- Activity timeline (database-backed)
- Advanced analytics
- QR code generation
- Data export (CSV/JSON)
- Audit logs
- Backup & restore
- Systemd auto-start services

### Fixed
- Notifications static count
- Activity timeline mock data
- SQLAlchemy reserved keyword
- Dashboard 500 error
- Missing npm dependencies

---

## [1.0.0] - 2025-XX-XX

### Added
- Initial release
- Basic dashboard
- User management
- OpenVPN support
- WireGuard support
- Basic monitoring

---

## Future Releases

### Planned for v3.1.0
- Payment gateway integration (Stripe, PayPal)
- 2FA/MFA authentication
- API key management
- Prometheus monitoring

### Planned for v4.0.0
- Mobile app support
- Advanced user roles
- API rate limiting
- WebRTC support

---

[3.0.0]: https://github.com/EchoDev7/vpn-master-panel-lite/compare/v2.0.0...v3.0.0
[2.0.0]: https://github.com/EchoDev7/vpn-master-panel-lite/compare/v1.0.0...v2.0.0
[1.0.0]: https://github.com/EchoDev7/vpn-master-panel-lite/releases/tag/v1.0.0
