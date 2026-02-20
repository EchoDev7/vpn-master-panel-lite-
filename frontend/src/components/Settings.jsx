import React, { useState, useEffect, useCallback } from 'react';
import { Save, Settings as SettingsIcon, Shield, Globe, Server, Lock, Wifi, Route, Clock, Wrench, FileText, AlertTriangle, Eye, Activity, RefreshCw, Terminal, Link, MessageSquare, Zap, Key } from 'lucide-react';
import { apiService } from '../services/api';
import { InputField, SelectField, CheckboxField, TextareaField, MultiSelectField, SectionTitle, IranBadge } from './SettingsFields';
import ConfirmationModal from './ConfirmationModal';
import Toast from './Toast';

// ===== Protocol Logos (inline SVG) =====
const OpenVPNLogo = () => (
    <svg viewBox="0 0 24 24" className="w-7 h-7" fill="none">
        <circle cx="12" cy="12" r="10" stroke="#EA7E20" strokeWidth="2" fill="#EA7E20" fillOpacity="0.15" />
        <path d="M12 6v4m0 4v4m-3-9l3-3 3 3m-6 4l3 3 3-3" stroke="#EA7E20" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        <circle cx="12" cy="12" r="2" fill="#EA7E20" />
    </svg>
);

const WireGuardLogo = () => (
    <svg viewBox="0 0 24 24" className="w-7 h-7" fill="none">
        <circle cx="12" cy="12" r="10" stroke="#88C0D0" strokeWidth="2" fill="#88C0D0" fillOpacity="0.15" />
        <path d="M12 7c-2.8 0-5 2.2-5 5s2.2 5 5 5 5-2.2 5-5-2.2-5-5-5zm0 2a3 3 0 110 6 3 3 0 010-6z" fill="#88C0D0" />
        <circle cx="12" cy="12" r="1.5" fill="#88C0D0" />
    </svg>
);

// ===== Tab Definitions =====
const OPENVPN_TABS = [
    { id: 'ovpn_network', label: '🌐 Network' },
    { id: 'ovpn_security', label: '🔒 Security' },
    { id: 'ovpn_anticensorship', label: '🛡️ Anti-Censorship' },
    { id: 'ovpn_routing', label: '🔀 Routing & DNS' },
    { id: 'ovpn_connection', label: '⏱️ Connection' },
    { id: 'ovpn_advanced', label: '🔧 Advanced' },
    { id: 'ovpn_certificates', label: '📜 Certificates' },
];

const WIREGUARD_TABS = [
    { id: 'wg_network', label: '🌐 Network' },
    { id: 'wg_security', label: '🔒 Security' },
    { id: 'wg_anticensorship', label: '🛡️ Anti-Censorship' },
    { id: 'wg_routing', label: '🔀 Routing & DNS' },
    { id: 'wg_connection', label: '⏱️ Connection' },
    { id: 'wg_advanced', label: '🔧 Advanced' },
    { id: 'wg_status', label: '📊 Status' },
];

const GENERAL_TABS = [
    { id: 'gen_domain_ssl', label: '🔒 Domain & SSL' },
    { id: 'gen_subscription', label: '🔗 Subscription' },
    { id: 'gen_telegram', label: '📱 Telegram Bot' },
    { id: 'gen_smartproxy', label: '🎯 Smart Proxy' },
    { id: 'gen_traffic', label: '📊 Traffic Limits' },
];

// ===== Helper: setting field wrappers =====
const S_Input = ({ settings, onChange, settingKey, ...props }) => (
    <InputField value={settings[settingKey]} onChange={(v) => onChange(settingKey, v)} {...props} />
);
const S_Select = ({ settings, onChange, settingKey, ...props }) => (
    <SelectField value={settings[settingKey]} onChange={(v) => onChange(settingKey, v)} {...props} />
);
const S_Check = ({ settings, onChange, settingKey, ...props }) => (
    <CheckboxField id={settingKey} checked={settings[settingKey] === '1'} onChange={(v) => onChange(settingKey, v ? '1' : '0')} {...props} />
);
const S_Textarea = ({ settings, onChange, settingKey, ...props }) => (
    <TextareaField value={settings[settingKey]} onChange={(v) => onChange(settingKey, v)} {...props} />
);


// ===== Main Settings Component =====
const Settings = () => {
    const [settings, setSettings] = useState({});
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [protocol, setProtocol] = useState('openvpn');
    const [activeTab, setActiveTab] = useState('ovpn_network');
    const [serverConfigPreview, setServerConfigPreview] = useState(null);
    const [showServerConfig, setShowServerConfig] = useState(false);
    const [pkiInfo, setPkiInfo] = useState(null);
    const [wgServerConfigPreview, setWgServerConfigPreview] = useState(null);
    const [showWgServerConfig, setShowWgServerConfig] = useState(false);
    const [wgStatus, setWgStatus] = useState(null);
    const [wgObfsScript, setWgObfsScript] = useState(null);
    const [showWgObfsScript, setShowWgObfsScript] = useState(false);
    const [ovpnVersion, setOvpnVersion] = useState(null);

    const [confirmation, setConfirmation] = useState({ isOpen: false, title: '', message: '', onConfirm: () => { }, confirmText: 'Confirm', confirmColor: 'blue' });
    const [sslStream, setSslStream] = useState({ isOpen: false, logs: '', loading: false });
    const [toast, setToast] = useState(null); // { message, type }

    useEffect(() => { loadSettings(); loadVersions(); }, []);

    const loadSettings = async () => {
        try {
            const response = await apiService.getSettings();
            setSettings(response.data);
        } catch (error) {
            console.error("Failed to load settings:", error);
        } finally {
            setLoading(false);
        }
    };

    const loadVersions = async () => {
        try {
            const res = await apiService.getOpenVPNVersion();
            setOvpnVersion(res.data.version);
        } catch (e) { console.error(e); }
    };

    const handleChange = useCallback((key, value) => {
        setSettings(prev => ({ ...prev, [key]: value }));
    }, []);

    const showToast = (message, type = 'success') => setToast({ message, type });
    const closeToast = () => setToast(null);

    const confirmAction = (title, message, onConfirm, confirmText = 'Confirm', confirmColor = 'blue') => {
        setConfirmation({ isOpen: true, title, message, onConfirm, confirmText, confirmColor });
    };

    const handleSave = async () => {
        setSaving(true);
        try {
            await apiService.updateSettings(settings);
            showToast("Settings saved successfully!");
        } catch (error) {
            showToast("Failed to save settings", "error");
        } finally {
            setSaving(false);
        }
    };

    const switchProtocol = (p) => {
        setProtocol(p);
        if (p === 'openvpn') setActiveTab('ovpn_network');
        else if (p === 'wireguard') setActiveTab('wg_network');
        else setActiveTab('gen_subscription');
    };

    if (loading) return <div className="p-8 text-center text-gray-400">Loading settings...</div>;

    const sp = { settings, onChange: handleChange };

    // ===== OpenVPN Tabs =====
    const ECDH_CURVES = [
        { value: 'secp384r1', label: 'secp384r1 (Strong — Recommended)' },
        { value: 'prime256v1', label: 'prime256v1 (NIST P-256)' },
        { value: 'secp256k1', label: 'secp256k1 (Bitcoin Curve)' },
    ];

    const DEV_TYPES = [
        { value: 'tun', label: 'TUN (L3 IP Tunnel — Recommended)' },
        { value: 'tap', label: 'TAP (L2 Ethernet Bridge)' },
    ];

    const CERT_PROFILES = [
        { value: 'preferred', label: 'Preferred (Modern)' },
        { value: 'legacy', label: 'Legacy (High Compatibility)' },
        { value: 'suiteb', label: 'Suite B (NSA Standard)' },
    ];

    const renderOvpnNetwork = () => (
        <div className="space-y-6">
            <SectionTitle>Connection Settings</SectionTitle>
            <div className="grid grid-cols-2 gap-4">
                <S_Select {...sp} settingKey="ovpn_protocol" label="Protocol" iranBadge tip="TCP on port 443 mimics HTTPS traffic, harder for DPI to detect." options={[
                    { value: 'tcp', label: 'TCP (Stealth — Recommended for Iran)' },
                    { value: 'udp', label: 'UDP (Faster)' },
                    { value: 'both', label: 'Both' },
                ]} />
                <S_Input {...sp} settingKey="ovpn_port" label="Port" placeholder="443" iranBadge tip="Port 443 makes VPN look like normal HTTPS." />
                <S_Input {...sp} settingKey="ovpn_mtu" label="MTU" placeholder="1400" type="number" iranBadge tip="Lower MTU (1400) works better with Iran ISPs." />
                <S_Select {...sp} settingKey="ovpn_topology" label="Topology" tip="Subnet is recommended for modern setups." options={[
                    { value: 'subnet', label: 'Subnet (Recommended)' },
                    { value: 'net30', label: 'Net30 (Legacy)' },
                ]} />
            </div>
            <S_Select {...sp} settingKey="ovpn_dev_type" label="Device Type" options={DEV_TYPES} tip="TUN is for IP routing (Android/iOS). TAP is for bridging." />
            <SectionTitle>Server Network</SectionTitle>
            <div className="grid grid-cols-2 gap-4 mb-4">
                <S_Input {...sp} settingKey="ovpn_server_subnet" label="VPN Subnet" placeholder="10.8.0.0" tip="IP range for VPN clients." />
                <S_Input {...sp} settingKey="ovpn_server_netmask" label="Subnet Mask" placeholder="255.255.255.0" />
                <S_Input {...sp} settingKey="ovpn_max_clients" label="Max Clients" placeholder="100" type="number" />
            </div>

            <SectionTitle>Client Connection Address</SectionTitle>
            <div className="grid grid-cols-2 gap-4">
                <S_Select {...sp} settingKey="ovpn_remote_address_type" label="Address Type" tip="How clients will connect to the server." options={[
                    { value: 'auto', label: 'Auto-detect Server IP' },
                    { value: 'custom_ip', label: 'Custom Server IP' },
                    { value: 'domain', label: 'Custom Domain (e.g., Cloudflare)' }
                ]} />
                {(!settings.ovpn_remote_address_type || settings.ovpn_remote_address_type === 'auto') && (
                    <div className="flex items-center text-gray-500 text-sm mt-6 bg-gray-800/50 px-3 rounded border border-gray-700">
                        The server's public IP will be auto-detected.
                    </div>
                )}
                {settings.ovpn_remote_address_type === 'custom_ip' && (
                    <S_Input {...sp} settingKey="ovpn_server_ip" label="Server IP Address" placeholder="1.2.3.4" />
                )}
                {settings.ovpn_remote_address_type === 'domain' && (
                    <S_Input {...sp} settingKey="ovpn_remote_domain" label="Domain Name" placeholder="vpn.yourdomain.com" />
                )}
            </div>
            <div className="grid grid-cols-1 gap-4">
                <div className="flex gap-4">
                    <S_Check {...sp} settingKey="ovpn_float" label="Allow IP Change (Float)" tip="Essential for mobile users." />
                    <S_Check {...sp} settingKey="ovpn_duplicate_cn" label="Allow Multiple Devices" tip="Same user from multiple devices." />
                    <S_Check {...sp} settingKey="ovpn_explicit_exit_notify" label="Explicit Exit Notify" tip="Notify server on disconnect (UDP only). Faster reconnection." />
                </div>
            </div>
        </div>
    );

    const DATA_CIPHERS = [
        { value: 'AES-256-GCM', label: 'AES-256-GCM (Recommended)' },
        { value: 'AES-128-GCM', label: 'AES-128-GCM' },
        { value: 'CHACHA20-POLY1305', label: 'CHACHA20-POLY1305 (Mobile Friendly)' },
        { value: 'AES-256-CBC', label: 'AES-256-CBC (Legacy)' },
        { value: 'AES-128-CBC', label: 'AES-128-CBC (Legacy)' },
        { value: 'none', label: 'none (No Encryption - Dangerous!)' },
    ];

    const TLS12_CIPHERS = [
        { value: 'TLS-ECDHE-ECDSA-WITH-AES-256-GCM-SHA384', label: 'ECDHE-ECDSA-AES-256-GCM-SHA384' },
        { value: 'TLS-ECDHE-RSA-WITH-AES-256-GCM-SHA384', label: 'ECDHE-RSA-AES-256-GCM-SHA384' },
        { value: 'TLS-DHE-RSA-WITH-AES-256-GCM-SHA384', label: 'DHE-RSA-AES-256-GCM-SHA384' },
        { value: 'TLS-ECDHE-ECDSA-WITH-CHACHA20-POLY1305-SHA256', label: 'ECDHE-ECDSA-CHACHA20-POLY1305' },
        { value: 'TLS-ECDHE-RSA-WITH-CHACHA20-POLY1305-SHA256', label: 'ECDHE-RSA-CHACHA20-POLY1305' },
    ];

    const TLS13_SUITES = [
        { value: 'TLS_AES_256_GCM_SHA384', label: 'TLS_AES_256_GCM_SHA384' },
        { value: 'TLS_CHACHA20_POLY1305_SHA256', label: 'TLS_CHACHA20_POLY1305_SHA256' },
        { value: 'TLS_AES_128_GCM_SHA256', label: 'TLS_AES_128_GCM_SHA256' },
    ];

    const S_MultiSelect = ({ settings, onChange, settingKey, ...props }) => (
        <MultiSelectField value={settings[settingKey]} onChange={(v) => onChange(settingKey, v)} {...props} />
    );

    const renderOvpnSecurity = () => (
        <div className="space-y-6">
            <SectionTitle>TLS Control Channel Security</SectionTitle>
            <S_Select {...sp} settingKey="ovpn_tls_control_channel" label="TLS Control Channel Mode" iranBadge tip="tls-crypt encrypts the ENTIRE control channel, invisible to DPI." options={[
                { value: 'tls-crypt', label: 'tls-crypt (Encrypt — Recommended)' },
                { value: 'tls-crypt-v2', label: 'tls-crypt-v2 (Per-client, 2.5+)' },
                { value: 'tls-auth', label: 'tls-auth (Sign & Verify)' },
                { value: 'none', label: 'None (Not Recommended)' },
            ]} />
            <SectionTitle>Data Channel Encryption</SectionTitle>
            <div className="grid grid-cols-1 gap-4">
                <S_MultiSelect {...sp} settingKey="ovpn_data_ciphers" label="Data Ciphers" options={DATA_CIPHERS} tip="Allowed data channel ciphers. Client tries them in order." />
                <S_Select {...sp} settingKey="ovpn_data_ciphers_fallback" label="Fallback Cipher" options={DATA_CIPHERS} tip="Cipher used if negotiation fails (older clients)." />
            </div>
            <SectionTitle>Authentication & TLS</SectionTitle>
            <S_Select {...sp} settingKey="ovpn_auth_mode" label="Authentication Mode" iranBadge tip="Choose how clients authenticate." options={[
                { value: 'password', label: 'Password Only (Standard)' },
                { value: 'cert', label: 'Certificate Only (No Password)' },
                { value: '2fa', label: 'Password + Certificate (High Security)' },
            ]} />
            <div className="grid grid-cols-2 gap-4">
                <S_Select {...sp} settingKey="ovpn_auth_digest" label="Auth Digest (HMAC)" options={[
                    { value: 'SHA256', label: 'SHA256 (Recommended)' },
                    { value: 'SHA384', label: 'SHA384' },
                    { value: 'SHA512', label: 'SHA512 (Strongest)' },
                    { value: 'none', label: 'none (No Auth - Dangerous!)' },
                ]} />
                <S_Select {...sp} settingKey="ovpn_tls_version_min" label="Minimum TLS Version" options={[
                    { value: '1.2', label: 'TLS 1.2 (Recommended)' },
                    { value: '1.3', label: 'TLS 1.3 (Newest)' },
                ]} />
            </div>
            <S_Select {...sp} settingKey="ovpn_tls_cert_profile" label="Certificate Profile" options={CERT_PROFILES} tip="Security level for certificates." />
            <S_MultiSelect {...sp} settingKey="ovpn_tls_ciphers" label="TLS 1.2 Cipher Suites" options={TLS12_CIPHERS} tip="Allowed ciphers for TLS 1.2 control channel." />
            <S_MultiSelect {...sp} settingKey="ovpn_tls_cipher_suites" label="TLS 1.3 Cipher Suites" options={TLS13_SUITES} tip="Allowed ciphers for TLS 1.3 control channel." />
            <div className="grid grid-cols-2 gap-4">
                <S_Select {...sp} settingKey="ovpn_ecdh_curve" label="ECDH Curve" options={ECDH_CURVES} tip="Elliptic curve for key exchange." />
                <S_Input {...sp} settingKey="ovpn_reneg_sec" label="Renegotiation Interval (sec)" placeholder="3600" type="number" />
            </div>
            <div className="grid grid-cols-3 gap-4">
                <S_Input {...sp} settingKey="ovpn_tls_timeout" label="TLS Timeout" placeholder="2" type="number" />
                <S_Input {...sp} settingKey="ovpn_hand_window" label="Handshake Window" placeholder="60" type="number" />
                <S_Input {...sp} settingKey="ovpn_tran_window" label="Transition Window" placeholder="3600" type="number" />
            </div>
        </div>
    );

    const renderOvpnAntiCensorship = () => (
        <div className="space-y-6">
            <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-4">
                <div className="flex items-start gap-3">
                    <AlertTriangle className="w-5 h-5 text-amber-400 mt-0.5 flex-shrink-0" />
                    <div>
                        <p className="text-amber-300 font-semibold text-sm">Official Client DPI Evasion (Native)</p>
                        <p className="text-gray-400 text-xs mt-1">These settings are 100% supported natively by official OpenVPN Connect apps on iOS/Android/Windows, without needing 3rd-party obfuscators like Stunnel or HTTP custom apps.</p>
                    </div>
                </div>
            </div>

            <SectionTitle>Native HTTP Proxy Payload (Domain Fronting)</SectionTitle>
            <S_Check {...sp} settingKey="ovpn_http_proxy_enabled" label="Enable HTTP Proxy SNI Payload" iranBadge tip="Injects a custom Host header over an HTTP proxy connection to deceive DPI." />
            <div className="grid grid-cols-2 gap-4">
                <S_Input {...sp} settingKey="ovpn_http_proxy_host" label="Proxy IP / CDN Edge IP" placeholder="e.g. 104.16.x.x" tip="IP address of the proxy routing the traffic." />
                <S_Input {...sp} settingKey="ovpn_http_proxy_port" label="Proxy Port" placeholder="80" type="number" />
            </div>
            <S_Input {...sp} settingKey="ovpn_http_proxy_custom_header" label="Spoofed Host Domain (SNI Payload)" placeholder="www.shaparack.ir" iranBadge tip="The domain inserted into the HTTP Host header. DPI assumes traffic is going to this local site." />
            <SectionTitle>Packet Fragmentation</SectionTitle>
            <S_Input {...sp} settingKey="ovpn_fragment" label="Fragment Size (0 = disabled)" placeholder="0" type="number" tip="Split packets to evade DPI (UDP only). Common: 1200." />

            <SectionTitle>HTTPS Camouflage (Port Sharing)</SectionTitle>
            <S_Input {...sp} settingKey="ovpn_port_share" label="Port Share (Forward non-VPN to Web Server)" placeholder="127.0.0.1 8443" tip="If DPI probes your port 443 with normal HTTPS requests, OpenVPN proxies them back to a real web server (e.g. Nginx on 8443)." />
            <SectionTitle>Block Iranian IPs (Server-Side)</SectionTitle>
            <S_Check {...sp} settingKey="ovpn_block_iran_ips" label="Block outgoing connections to Iranian IPs" iranBadge tip="Prevents server from initiating connections to Iran, which DPI monitors as suspicious behavior for a foreign web server." />
            <SectionTitle>Multi-Server Failover</SectionTitle>
            <S_Input {...sp} settingKey="ovpn_remote_servers" label="Remote Servers (comma-separated)" placeholder="1.2.3.4:443:tcp,5.6.7.8:443:tcp" tip="Backup servers if main is blocked." />
        </div>
    );

    const renderOvpnRouting = () => (
        <div className="space-y-6">
            <SectionTitle>Traffic Routing</SectionTitle>
            <S_Select {...sp} settingKey="ovpn_redirect_gateway" label="Redirect Gateway" tip="Force ALL traffic through VPN or split tunnel." options={[
                { value: '1', label: 'Yes — Route All Traffic (Full Tunnel)' },
                { value: '0', label: 'No — Split Tunneling' },
            ]} />
            <S_Check {...sp} settingKey="ovpn_inter_client" label="Allow Client-to-Client" tip="VPN clients can communicate with each other." />
            <SectionTitle>DNS Settings</SectionTitle>
            <S_Input {...sp} settingKey="ovpn_dns" label="DNS Servers (comma-separated)" placeholder="1.1.1.1, 8.8.8.8" />
            <S_Check {...sp} settingKey="ovpn_block_outside_dns" label="Block Outside DNS (Prevent DNS Leaks)" iranBadge tip="Prevents DNS leaks to ISP." />
            <SectionTitle>Push Routes</SectionTitle>
            <S_Textarea {...sp} settingKey="ovpn_push_routes" label="Push Routes" placeholder={"192.168.1.0 255.255.255.0\n10.0.0.0 255.0.0.0"} tip="One route per line (Network Netmask). Pushed to client." rows={3} />
            <S_Textarea {...sp} settingKey="ovpn_push_remove_routes" label="Remove Routes" placeholder={"0.0.0.0/0"} tip="Remove specific routes from client." rows={2} />
        </div>
    );

    const renderOvpnConnection = () => (
        <div className="space-y-6">
            <SectionTitle>Keepalive</SectionTitle>
            <div className="grid grid-cols-2 gap-4">
                <S_Input {...sp} settingKey="ovpn_keepalive_interval" label="Ping Interval (sec)" placeholder="10" type="number" />
                <S_Input {...sp} settingKey="ovpn_keepalive_timeout" label="Ping Timeout (sec)" placeholder="60" type="number" />
            </div>
            <SectionTitle>Retry & Timeout</SectionTitle>
            <div className="grid grid-cols-3 gap-4">
                <S_Input {...sp} settingKey="ovpn_connect_retry" label="Connect Retry (sec)" placeholder="5" type="number" />
                <S_Input {...sp} settingKey="ovpn_connect_retry_max" label="Max Retry (0=infinite)" placeholder="0" type="number" />
                <S_Input {...sp} settingKey="ovpn_server_poll_timeout" label="Server Poll Timeout" placeholder="10" type="number" />
            </div>
            <SectionTitle>Logging & Compression</SectionTitle>
            <div className="grid grid-cols-2 gap-4">
                <S_Select {...sp} settingKey="ovpn_verb" label="Log Verbosity" options={[
                    { value: '1', label: '1 — Minimal' },
                    { value: '3', label: '3 — Normal' },
                    { value: '4', label: '4 — Debug' },
                    { value: '6', label: '6 — Verbose' },
                ]} />
                <S_Select {...sp} settingKey="ovpn_compress" label="Compression" tip="Disabled is recommended for stealth (VORACLE attack)." options={[
                    { value: '', label: 'Disabled (Recommended)' },
                    { value: 'lz4-v2', label: 'LZ4-v2 (New)' },
                    { value: 'lzo', label: 'LZO (Legacy)' },
                ]} />
                <S_Check {...sp} settingKey="ovpn_allow_compression" label="Allow Compression (Asym)" tip="Allow clients to use compression even if pushed no." />
            </div>
        </div>
    );

    const renderOvpnAdvanced = () => (
        <div className="space-y-6">
            <SectionTitle>Custom OpenVPN Directives</SectionTitle>
            <S_Textarea {...sp} settingKey="ovpn_custom_client_config" label="Client Config Directives" placeholder={"# Additional directives for .ovpn files"} tip="Raw directives added to client configs." rows={4} />
            <S_Textarea {...sp} settingKey="ovpn_custom_server_config" label="Server Config Directives" placeholder={"# Additional directives for server.conf"} tip="Raw directives for server config." rows={4} />
            <SectionTitle>Daemon Management</SectionTitle>
            <div className="grid grid-cols-2 gap-4">
                <S_Input {...sp} settingKey="ovpn_management" label="Management Interface" placeholder="127.0.0.1 7505" tip="IP Port for telnet management." />
                <S_Input {...sp} settingKey="ovpn_status_log" label="Status Log Path" placeholder="/var/log/openvpn/openvpn-status.log" />
            </div>
            <div className="grid grid-cols-4 gap-4">
                <S_Input {...sp} settingKey="ovpn_user" label="User" placeholder="nobody" />
                <S_Input {...sp} settingKey="ovpn_group" label="Group" placeholder="nogroup" />
                <S_Check {...sp} settingKey="ovpn_pers_tun" label="Persist Tun" />
                <S_Check {...sp} settingKey="ovpn_pers_key" label="Persist Key" />
            </div>
            <SectionTitle>Server Configuration</SectionTitle>
            <div className="flex gap-3">
                <button onClick={async () => {
                    try { const res = await apiService.getServerConfigPreview(); setServerConfigPreview(res.data.content); setShowServerConfig(true); } catch { showToast("Failed to load preview", "error"); }
                }} className="flex-1 bg-gray-700 hover:bg-gray-600 text-white px-4 py-3 rounded-lg text-sm font-medium flex items-center justify-center gap-2 border border-gray-600 transition-colors">
                    <Eye className="w-4 h-4" /> Preview server.conf
                </button>
                <button onClick={() => confirmAction(
                    "Generate Configuration",
                    "Generate server.conf based on current settings?",
                    async () => {
                        try {
                            const res = await apiService.applyServerConfig();
                            const d = res.data;
                            if (d.system_written) {
                                showToast(`Written to: ${d.system_path}`, "success");
                            } else {
                                showToast(`Saved to: ${d.backup_path}`, "success");
                            }
                        } catch { showToast("Failed to generate config", "error"); }
                    },
                    "Generate & Apply",
                    "orange"
                )} className="flex-1 bg-orange-600 hover:bg-orange-700 text-white px-4 py-3 rounded-lg text-sm font-medium flex items-center justify-center gap-2 transition-colors">
                    <Server className="w-4 h-4" /> Generate & Apply
                </button>
            </div>
            {showServerConfig && serverConfigPreview && (
                <div className="bg-gray-900 rounded-lg border border-gray-600 overflow-hidden">
                    <div className="flex justify-between items-center p-3 bg-gray-800 border-b border-gray-700">
                        <span className="text-sm font-medium text-gray-300">server.conf Preview</span>
                        <button onClick={() => setShowServerConfig(false)} className="text-gray-400 hover:text-white text-sm">✕</button>
                    </div>
                    <textarea readOnly value={serverConfigPreview} className="w-full h-64 bg-transparent text-gray-300 p-4 font-mono text-xs resize-none focus:outline-none" />
                </div>
            )}
        </div>
    );

    const renderOvpnCertificates = () => (
        <div className="space-y-6">
            <SectionTitle>Certificate Authority (CA)</SectionTitle>
            {pkiInfo ? (
                <div className="bg-gray-900 rounded-lg p-4 border border-gray-700 space-y-2">
                    <div className="flex items-center gap-2">
                        <span className={`w-2 h-2 rounded-full ${pkiInfo.exists ? 'bg-green-500' : 'bg-red-500'}`}></span>
                        <span className="text-sm text-gray-300">{pkiInfo.exists ? 'CA Certificate Found' : 'No CA Certificate'}</span>
                    </div>
                    {pkiInfo.subject && <p className="text-xs text-gray-400">Subject: {pkiInfo.subject}</p>}
                    {pkiInfo.not_before && <p className="text-xs text-gray-400">Valid From: {pkiInfo.not_before}</p>}
                    {pkiInfo.not_after && <p className="text-xs text-gray-400">Valid Until: {pkiInfo.not_after}</p>}
                    {pkiInfo.serial && <p className="text-xs text-gray-400">Serial: {pkiInfo.serial}</p>}
                </div>
            ) : (
                <button onClick={async () => { try { const r = await apiService.getPKIInfo(); setPkiInfo(r.data); } catch { console.error('PKI load failed'); } }} className="w-full bg-gray-700 hover:bg-gray-600 text-white px-4 py-2 rounded-lg text-sm border border-gray-600 transition-colors">Load CA Info</button>
            )}
            <button onClick={() => confirmAction(
                "Regenerate Certificates",
                "⚠️ WARNING: This replaces existing certificates.\nAll users must download new .ovpn files.\n\nContinue?",
                async () => {
                    try { await apiService.regeneratePKI(); showToast("Certificates regenerated."); setPkiInfo(null); } catch { showToast("Failed to regenerate PKI", "error"); }
                },
                "Regenerate All",
                "red"
            )} className="w-full bg-red-600/20 hover:bg-red-600/30 text-red-400 px-4 py-3 rounded-lg text-sm font-medium border border-red-600/30 transition-colors">🔄 Regenerate All Certificates</button>
            <p className="text-xs text-gray-500">Warning: Regenerating invalidates all existing client configs.</p>

            <div className="mt-6 pt-6 border-t border-gray-700">
                <button onClick={() => confirmAction(
                    "Generate Configuration",
                    "Generate server.conf based on current settings?",
                    async () => {
                        try {
                            const res = await apiService.applyServerConfig();
                            const d = res.data;
                            if (d.system_written) {
                                showToast(`Written to: ${d.system_path}`, "success");
                            } else {
                                showToast(`Saved to: ${d.backup_path}`, "success");
                            }
                        } catch { showToast("Failed to generate config", "error"); }
                    },
                    "Generate & Apply",
                    "orange"
                )} className="w-full bg-orange-600 hover:bg-orange-700 text-white px-4 py-3 rounded-lg text-sm font-medium flex items-center justify-center gap-2 transition-colors">
                    <Server className="w-4 h-4" /> Generate & Apply Config (After Regeneration)
                </button>
            </div>
        </div>
    );

    // ===== WireGuard Tabs =====
    const renderWgNetwork = () => (
        <div className="space-y-6">
            <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-4">
                <div className="flex items-start gap-3">
                    <AlertTriangle className="w-5 h-5 text-amber-400 mt-0.5 flex-shrink-0" />
                    <div>
                        <p className="text-amber-300 font-semibold text-sm">WireGuard Anti-Censorship Notice</p>
                        <p className="text-gray-400 text-xs mt-1">WireGuard uses UDP with a distinct fingerprint. Enable obfuscation in Anti-Censorship tab to bypass Iran's DPI.</p>
                    </div>
                </div>
            </div>
            <SectionTitle>Network</SectionTitle>
            <div className="grid grid-cols-2 gap-4">
                <S_Input {...sp} settingKey="wg_port" label="Port" placeholder="51820" tip="WireGuard listen port (UDP)." />
                <S_Input {...sp} settingKey="wg_mtu" label="MTU" placeholder="1380" type="number" iranBadge tip="Lower MTU (1280-1380) for Iran ISPs." />
                <S_Input {...sp} settingKey="wg_interface" label="Interface" placeholder="wg0" />
                <S_Input {...sp} settingKey="wg_endpoint_ip" label="Endpoint IP" placeholder="Auto-detect" tip="Set manually if behind NAT or using a domain." />
            </div>
            <div className="grid grid-cols-2 gap-4">
                <S_Input {...sp} settingKey="wg_subnet" label="Subnet" placeholder="10.66.66.0" />
                <S_Input {...sp} settingKey="wg_subnet_mask" label="Subnet Mask (CIDR)" placeholder="24" />
            </div>
        </div>
    );

    const renderWgSecurity = () => (
        <div className="space-y-6">
            <SectionTitle>Security</SectionTitle>
            <S_Check {...sp} settingKey="wg_preshared_key_enabled" label="Enable PresharedKey (Post-Quantum)" iranBadge tip="Extra symmetric-key crypto on top of Curve25519." />
            <S_Input {...sp} settingKey="wg_fwmark" label="FwMark (Firewall Mark)" placeholder="0 (disabled)" tip="32-bit fwmark for outgoing packets." />
        </div>
    );

    const renderWgAntiCensorship = () => (
        <div className="space-y-6">
            <SectionTitle>Obfuscation</SectionTitle>
            <S_Select {...sp} settingKey="wg_obfuscation_type" label="Obfuscation Method" iranBadge tip="Wrap WireGuard to evade DPI." options={[
                { value: 'none', label: 'None (Direct UDP)' },
                { value: 'wstunnel', label: 'wstunnel (WebSocket/HTTPS — Recommended)' },
                { value: 'udp2raw', label: 'udp2raw (FakeTCP)' },
            ]} />
            {settings.wg_obfuscation_type && settings.wg_obfuscation_type !== 'none' && (
                <>
                    <div className="grid grid-cols-2 gap-4">
                        <S_Input {...sp} settingKey="wg_obfuscation_port" label="Obfuscation Port" placeholder="443" iranBadge />
                        <S_Input {...sp} settingKey="wg_obfuscation_domain" label="Domain (wstunnel)" placeholder="your-domain.com" />
                    </div>
                    <button onClick={async () => {
                        try { const res = await apiService.getObfuscationScript(); setWgObfsScript(res.data.content); setShowWgObfsScript(true); } catch { showToast('Failed to load script', 'error'); }
                    }} className="w-full bg-gray-700 hover:bg-gray-600 text-white px-4 py-2.5 rounded-lg text-sm border border-gray-600 flex items-center justify-center gap-2 transition-colors">
                        <Terminal className="w-4 h-4" /> View Server Setup Script
                    </button>
                </>
            )}
            {showWgObfsScript && wgObfsScript && (
                <div className="bg-gray-900 rounded-lg border border-gray-600 overflow-hidden">
                    <div className="flex justify-between items-center p-3 bg-gray-800 border-b border-gray-700">
                        <span className="text-sm font-medium text-gray-300">Obfuscation Setup Script</span>
                        <button onClick={() => setShowWgObfsScript(false)} className="text-gray-400 hover:text-white text-sm">✕</button>
                    </div>
                    <textarea readOnly value={wgObfsScript} className="w-full h-48 bg-transparent text-gray-300 p-4 font-mono text-xs resize-none focus:outline-none" />
                </div>
            )}
            <SectionTitle>WARP Integration</SectionTitle>
            <S_Check {...sp} settingKey="wg_warp_enabled" label="Enable Cloudflare WARP" iranBadge tip="Route traffic through Cloudflare WARP proxy for additional censorship bypass." />
            <S_Select {...sp} settingKey="wg_warp_mode" label="WARP Mode" options={[
                { value: 'proxy', label: 'Proxy Mode (Selective routing)' },
                { value: 'full', label: 'Full Mode (All traffic)' },
            ]} />
            <SectionTitle>Block Iranian IPs</SectionTitle>
            <S_Check {...sp} settingKey="wg_block_iran_ips" label="Block outgoing connections to Iranian IPs" iranBadge tip="Prevents server from connecting to Iran, avoiding DPI suspicion." />
        </div>
    );

    const renderWgRouting = () => (
        <div className="space-y-6">
            <SectionTitle>Routing & DNS</SectionTitle>
            <S_Input {...sp} settingKey="wg_dns" label="DNS Servers" placeholder="1.1.1.1,8.8.8.8" />
            <S_Input {...sp} settingKey="wg_allowed_ips" label="Allowed IPs" placeholder="0.0.0.0/0,::/0" tip="0.0.0.0/0 routes ALL traffic. Specific CIDRs for split tunneling." />
            <S_Select {...sp} settingKey="wg_table" label="Routing Table" options={[
                { value: 'auto', label: 'Auto (Recommended)' },
                { value: 'off', label: 'Off (Manual routing)' },
            ]} />
        </div>
    );

    const renderWgConnection = () => (
        <div className="space-y-6">
            <SectionTitle>Connection</SectionTitle>
            <div className="grid grid-cols-2 gap-4">
                <S_Input {...sp} settingKey="wg_persistent_keepalive" label="Persistent Keepalive (sec)" placeholder="25" type="number" iranBadge tip="Essential for Iran NAT/firewalls." />
                <S_Check {...sp} settingKey="wg_save_config" label="Save Config on Changes" />
            </div>
        </div>
    );

    const renderWgAdvanced = () => (
        <div className="space-y-6">
            <SectionTitle>Scripts & Custom Config</SectionTitle>
            <S_Textarea {...sp} settingKey="wg_post_up" label="PostUp Script" placeholder="iptables -t nat -A POSTROUTING ..." rows={2} />
            <S_Textarea {...sp} settingKey="wg_post_down" label="PostDown Script" placeholder="iptables -t nat -D POSTROUTING ..." rows={2} />
            <S_Textarea {...sp} settingKey="wg_custom_client_config" label="Custom Client Config" placeholder="# Extra lines in client .conf" rows={3} />
            <S_Textarea {...sp} settingKey="wg_custom_server_config" label="Custom Server Config" placeholder="# Extra lines in wg0.conf" rows={3} />
            <SectionTitle>Server Configuration</SectionTitle>
            <div className="flex gap-3">
                <button onClick={async () => {
                    try { const res = await apiService.getWGServerConfigPreview(); setWgServerConfigPreview(res.data.content); setShowWgServerConfig(true); } catch { showToast('Failed to load preview', 'error'); }
                }} className="flex-1 bg-gray-700 hover:bg-gray-600 text-white px-4 py-3 rounded-lg text-sm font-medium flex items-center justify-center gap-2 border border-gray-600 transition-colors">
                    <Eye className="w-4 h-4" /> Preview wg0.conf
                </button>
                <button onClick={() => confirmAction(
                    "Generate WireGuard Config",
                    "Generate and write wg0.conf?",
                    async () => {
                        try {
                            const res = await apiService.applyWGServerConfig();
                            const d = res.data;
                            if (d.system_written) {
                                showToast(`Written to: ${d.system_path}`, "success");
                            } else {
                                showToast(`Saved to: ${d.backup_path}`, "success");
                            }
                        } catch { showToast('Failed to apply config', 'error'); }
                    },
                    "Generate & Apply",
                    "teal"
                )} className="flex-1 bg-teal-600 hover:bg-teal-700 text-white px-4 py-3 rounded-lg text-sm font-medium flex items-center justify-center gap-2 transition-colors">
                    <Server className="w-4 h-4" /> Generate & Apply
                </button>
            </div>
            {showWgServerConfig && wgServerConfigPreview && (
                <div className="bg-gray-900 rounded-lg border border-gray-600 overflow-hidden">
                    <div className="flex justify-between items-center p-3 bg-gray-800 border-b border-gray-700">
                        <span className="text-sm font-medium text-gray-300">wg0.conf Preview</span>
                        <button onClick={() => setShowWgServerConfig(false)} className="text-gray-400 hover:text-white text-sm">✕</button>
                    </div>
                    <textarea readOnly value={wgServerConfigPreview} className="w-full h-64 bg-transparent text-gray-300 p-4 font-mono text-xs resize-none focus:outline-none" />
                </div>
            )}
            <SectionTitle>Server Keys</SectionTitle>
            <button onClick={() => confirmAction(
                "Regenerate Server Keys",
                "⚠️ Regenerating invalidates ALL client configs.\nContinue?",
                async () => {
                    try { const res = await apiService.regenerateWGKeys(); showToast(`New Key: ${res.data.public_key}`); } catch { showToast('Failed to regenerate keys', 'error'); }
                },
                "Regenerate Keys",
                "red"
            )} className="w-full bg-red-600/20 hover:bg-red-600/30 text-red-400 px-4 py-3 rounded-lg text-sm font-medium border border-red-600/30 transition-colors">🔄 Regenerate Server Keys</button>
        </div>
    );

    const renderWgStatus = () => (
        <div className="space-y-6">
            <SectionTitle>Live Status</SectionTitle>
            <button onClick={async () => {
                try { const res = await apiService.getWGStatus(); setWgStatus(res.data); } catch { showToast('Failed to refresh status', 'error'); }
            }} className="w-full bg-gray-700 hover:bg-gray-600 text-white px-4 py-2.5 rounded-lg text-sm border border-gray-600 flex items-center justify-center gap-2 transition-colors">
                <Activity className="w-4 h-4" /> Refresh WireGuard Status
            </button>
            {wgStatus && (
                <div className="bg-gray-900 rounded-lg p-4 border border-gray-700 space-y-3">
                    <div className="flex items-center gap-2">
                        <span className={`w-2.5 h-2.5 rounded-full ${wgStatus.running ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`}></span>
                        <span className="text-sm text-gray-300 font-medium">{wgStatus.running ? `${wgStatus.interface} Running` : 'Not Running'}</span>
                        {wgStatus.listen_port > 0 && <span className="text-xs text-gray-500">Port: {wgStatus.listen_port}</span>}
                    </div>
                    {wgStatus.total_transfer_rx_human && <p className="text-xs text-gray-400">Total: ↓ {wgStatus.total_transfer_rx_human} / ↑ {wgStatus.total_transfer_tx_human}</p>}
                    {wgStatus.peers && wgStatus.peers.length > 0 && (
                        <div className="space-y-2 mt-2">
                            <p className="text-xs text-gray-500 font-semibold">Connected Peers ({wgStatus.peers.length})</p>
                            {wgStatus.peers.map((peer, i) => (
                                <div key={i} className="bg-gray-800 p-2.5 rounded border border-gray-700">
                                    <div className="flex items-center gap-2">
                                        <span className={`w-2 h-2 rounded-full ${peer.is_online ? 'bg-green-500' : 'bg-gray-600'}`}></span>
                                        <span className="text-xs text-gray-300 font-mono">{peer.public_key?.substring(0, 20)}...</span>
                                        <span className="text-xs text-gray-500">{peer.handshake_ago}</span>
                                    </div>
                                    <p className="text-xs text-gray-500 mt-1">↓ {peer.transfer_rx_human} / ↑ {peer.transfer_tx_human} | {peer.allowed_ips}</p>
                                </div>
                            ))}
                        </div>
                    )}
                    {wgStatus.error && <p className="text-xs text-red-400">{wgStatus.error}</p>}
                </div>
            )}
        </div>
    );

    // ===== General Tabs =====
    const renderDomainSsl = () => (
        <div className="space-y-6">
            <div className="bg-purple-500/10 border border-purple-500/30 rounded-lg p-4">
                <div className="flex items-start gap-3">
                    <Globe className="w-5 h-5 text-purple-400 mt-0.5 flex-shrink-0" />
                    <div>
                        <p className="text-purple-300 font-semibold text-sm">Panel Domain & SSL</p>
                        <p className="text-gray-400 text-xs mt-1">This domain is used strictly for accessing this Admin Panel and Subscription Links. It is securely separated from your VPN connection domains.</p>
                        <p className="text-amber-400 text-xs font-bold mt-2">⚠️ IMPORTANT: Point your domain's DNS to your server IP (Proxy ON for Cloudflare) BEFORE requesting SSL.</p>
                    </div>
                </div>
            </div>

            <SectionTitle>Domain Setup</SectionTitle>
            <S_Input {...sp} settingKey="panel_domain" label="Panel & Subscription Domain" placeholder="panel.yourdomain.com" tip="The domain used to access this dashboard and user subscriptions." />

            <SectionTitle>Let's Encrypt SSL (ZeroSSL / Certbot)</SectionTitle>
            <S_Input {...sp} settingKey="ssl_email" label="Admin Email (For SSL Expiration Alerts)" placeholder="admin@yourdomain.com" />

            <div className="mt-6 pt-6 border-t border-gray-700">
                <button onClick={() => confirmAction(
                    "Request Let's Encrypt SSL",
                    "This will request a certificate for your Panel Domain.\n\nPrerequisites:\n1. Your domain MUST point to this server's IP.\n2. Port 80 must be open.\n\nContinue?",
                    async () => {
                        setConfirmation(prev => ({ ...prev, isOpen: false }));
                        setSslStream({ isOpen: true, logs: 'Initializing Let\'s Encrypt client...\n', loading: true });
                        try {
                            const token = localStorage.getItem('access_token');
                            const baseURL = (import.meta.env.VITE_API_URL || '') + '/api/v1/settings/ssl/request';

                            const response = await fetch(baseURL, {
                                method: 'POST',
                                headers: {
                                    'Content-Type': 'application/json',
                                    'Authorization': `Bearer ${token}`
                                },
                                body: JSON.stringify({
                                    domain: settings.panel_domain,
                                    email: settings.ssl_email || 'admin@example.com'
                                })
                            });

                            if (!response.body) throw new Error('ReadableStream not supported by browser');

                            const reader = response.body.getReader();
                            const decoder = new TextDecoder('utf-8');

                            while (true) {
                                const { done, value } = await reader.read();
                                if (done) break;
                                const chunk = decoder.decode(value, { stream: true });
                                setSslStream(prev => ({ ...prev, logs: prev.logs + chunk }));
                            }
                        } catch (err) {
                            setSslStream(prev => ({ ...prev, logs: prev.logs + `\nHTTP ERROR: ${err.message}` }));
                        } finally {
                            setSslStream(prev => ({ ...prev, loading: false }));
                        }
                    },
                    "Request SSL Certificate",
                    "purple"
                )}
                    disabled={!settings.panel_domain}
                    className={`w-full ${settings.panel_domain ? 'bg-purple-600 hover:bg-purple-700 text-white' : 'bg-gray-700 text-gray-500 cursor-not-allowed'} px-4 py-3 rounded-lg text-sm font-medium flex items-center justify-center gap-2 transition-colors`}>
                    <Shield className="w-4 h-4" /> Issue Let's Encrypt SSL
                </button>
            </div>
        </div>
    );

    const renderSubscription = () => (
        <div className="space-y-6">
            <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-4">
                <div className="flex items-start gap-3">
                    <Link className="w-5 h-5 text-blue-400 mt-0.5 flex-shrink-0" />
                    <div>
                        <p className="text-blue-300 font-semibold text-sm">Subscription Links</p>
                        <p className="text-gray-400 text-xs mt-1">Auto-updating config links for clients. Like 3x-ui, Marzban, and Hiddify panels.</p>
                    </div>
                </div>
            </div>
            <SectionTitle>Subscription Settings</SectionTitle>
            <S_Check {...sp} settingKey="subscription_enabled" label="Enable Subscription Links" tip="Allow users to get auto-updating config URLs." />
            <S_Input {...sp} settingKey="subscription_base_url" label="Base URL" placeholder="https://your-panel.com" tip="Public URL of your panel for subscription links." />
            <S_Select {...sp} settingKey="subscription_format" label="Link Format" options={[
                { value: 'v2ray', label: 'V2Ray/Clash URI' },
                { value: 'base64', label: 'Base64 Encoded' },
                { value: 'json', label: 'JSON Config' },
            ]} />
            <S_Input {...sp} settingKey="subscription_update_interval" label="Auto-Update Interval (hours)" placeholder="24" type="number" tip="How often clients refresh their config." />
            <SectionTitle>Config Export</SectionTitle>
            <S_Check {...sp} settingKey="config_export_qr" label="Include QR Code in Exports" tip="Generate QR codes for easy mobile import." />
            <S_Check {...sp} settingKey="config_export_uri" label="Include URI Links in Exports" tip="Generate one-click import URIs." />
        </div>
    );

    const renderTelegram = () => (
        <div className="space-y-6">
            <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-4">
                <div className="flex items-start gap-3">
                    <MessageSquare className="w-5 h-5 text-blue-400 mt-0.5 flex-shrink-0" />
                    <div>
                        <p className="text-blue-300 font-semibold text-sm">Telegram Bot Integration</p>
                        <p className="text-gray-400 text-xs mt-1">Get alerts, manage users, and receive backups via Telegram. Used by 3x-ui, Marzban, and Hiddify.</p>
                    </div>
                </div>
            </div>
            <SectionTitle>Bot Configuration</SectionTitle>
            <S_Check {...sp} settingKey="telegram_enabled" label="Enable Telegram Bot" tip="Send notifications and allow management via Telegram." />
            <S_Input {...sp} settingKey="telegram_bot_token" label="Bot Token" placeholder="123456:ABC-DEF..." tip="From @BotFather on Telegram." />
            <S_Input {...sp} settingKey="telegram_admin_chat_id" label="Admin Chat ID" placeholder="12345678" tip="Your Telegram chat ID for receiving notifications." />
            <SectionTitle>Notification Events</SectionTitle>
            <div className="grid grid-cols-2 gap-4">
                <S_Check {...sp} settingKey="telegram_notify_user_created" label="User Created" />
                <S_Check {...sp} settingKey="telegram_notify_user_expired" label="User Expired" />
                <S_Check {...sp} settingKey="telegram_notify_traffic_warning" label="Traffic Warning (80%)" />
                <S_Check {...sp} settingKey="telegram_notify_server_down" label="Server Down" />
            </div>
            <SectionTitle>Backup</SectionTitle>
            <S_Check {...sp} settingKey="telegram_auto_backup" label="Send Auto Backup to Telegram" tip="Automatically send database backup every 6 hours." />
        </div>
    );

    const renderSmartProxy = () => (
        <div className="space-y-6">
            <div className="bg-green-500/10 border border-green-500/30 rounded-lg p-4">
                <div className="flex items-start gap-3">
                    <Zap className="w-5 h-5 text-green-400 mt-0.5 flex-shrink-0" />
                    <div>
                        <p className="text-green-300 font-semibold text-sm">Smart Proxy (Hiddify-style)</p>
                        <p className="text-gray-400 text-xs mt-1">Only route filtered/blocked traffic through VPN. Domestic sites go direct for maximum speed.</p>
                    </div>
                </div>
            </div>
            <SectionTitle>Smart Proxy Configuration</SectionTitle>
            <S_Check {...sp} settingKey="smart_proxy_enabled" label="Enable Smart Proxy" iranBadge tip="Bypass VPN for domestic Iranian sites. Saves bandwidth, improves speed." />
            <S_Select {...sp} settingKey="smart_proxy_mode" label="Mode" options={[
                { value: 'bypass_iran', label: 'Bypass Iran Domains & IPs (Recommended)' },
                { value: 'only_blocked', label: 'Only Route Blocked Sites' },
                { value: 'full', label: 'Route Everything (Full Tunnel)' },
            ]} />
            <S_Textarea {...sp} settingKey="smart_proxy_bypass_domains" label="Custom Bypass Domains" placeholder={"digikala.com\nsnapp.ir\naparat.com"} tip="One domain per line. These go direct, not through VPN." rows={4} />
            <S_Textarea {...sp} settingKey="smart_proxy_bypass_ips" label="Custom Bypass IPs/CIDRs" placeholder={"185.143.232.0/22\n5.160.0.0/16"} tip="One CIDR per line. Iranian IP ranges to bypass." rows={4} />
        </div>
    );

    const renderTrafficLimits = () => (
        <div className="space-y-6">
            <SectionTitle>Periodic Traffic Limits (Marzban-style)</SectionTitle>
            <S_Check {...sp} settingKey="periodic_traffic_enabled" label="Enable Periodic Traffic Limits" tip="Reset user traffic counters periodically instead of cumulative." />
            <S_Select {...sp} settingKey="periodic_traffic_type" label="Period Type" options={[
                { value: 'monthly', label: 'Monthly' },
                { value: 'weekly', label: 'Weekly' },
                { value: 'daily', label: 'Daily' },
            ]} />
            <S_Input {...sp} settingKey="periodic_traffic_reset_day" label="Reset Day (for Monthly)" placeholder="1" type="number" tip="Day of month to reset traffic counters." />
            <SectionTitle>Auto Actions</SectionTitle>
            <S_Select {...sp} settingKey="traffic_exceed_action" label="When Traffic Exceeds Limit" options={[
                { value: 'suspend', label: 'Suspend User' },
                { value: 'throttle', label: 'Throttle Speed' },
                { value: 'notify', label: 'Notify Only' },
            ]} />
            <S_Input {...sp} settingKey="traffic_warning_percent" label="Warning Threshold (%)" placeholder="80" type="number" tip="Send warning when usage reaches this percent." />
        </div>
    );

    // ===== Tab Router =====
    const renderTabContent = () => {
        switch (activeTab) {
            case 'ovpn_network': return renderOvpnNetwork();
            case 'ovpn_security': return renderOvpnSecurity();
            case 'ovpn_anticensorship': return renderOvpnAntiCensorship();
            case 'ovpn_routing': return renderOvpnRouting();
            case 'ovpn_connection': return renderOvpnConnection();
            case 'ovpn_advanced': return renderOvpnAdvanced();
            case 'ovpn_certificates': return renderOvpnCertificates();
            case 'wg_network': return renderWgNetwork();
            case 'wg_security': return renderWgSecurity();
            case 'wg_anticensorship': return renderWgAntiCensorship();
            case 'wg_routing': return renderWgRouting();
            case 'wg_connection': return renderWgConnection();
            case 'wg_advanced': return renderWgAdvanced();
            case 'wg_status': return renderWgStatus();
            case 'gen_domain_ssl': return renderDomainSsl();
            case 'gen_subscription': return renderSubscription();
            case 'gen_telegram': return renderTelegram();
            case 'gen_smartproxy': return renderSmartProxy();
            case 'gen_traffic': return renderTrafficLimits();
            default: return renderOvpnNetwork();
        }
    };

    const currentTabs = protocol === 'openvpn' ? OPENVPN_TABS : protocol === 'wireguard' ? WIREGUARD_TABS : GENERAL_TABS;
    const protocolColor = protocol === 'openvpn' ? 'orange' : protocol === 'wireguard' ? 'teal' : 'blue';
    const borderColor = { orange: 'border-orange-500', teal: 'border-teal-500', blue: 'border-blue-500' }[protocolColor];
    const bgActive = { orange: 'bg-orange-600/20 text-orange-400 border-orange-500', teal: 'bg-teal-600/20 text-teal-400 border-teal-500', blue: 'bg-blue-600/20 text-blue-400 border-blue-500' }[protocolColor];

    return (
        <div className="p-6 max-w-6xl mx-auto">
            {/* Header */}
            <div className="flex items-center justify-between mb-6">
                <h1 className="text-3xl font-bold text-gray-100 flex items-center gap-3">
                    <SettingsIcon className="text-blue-400" /> System Settings
                </h1>
                <button onClick={handleSave} disabled={saving} className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2.5 rounded-lg font-bold flex items-center gap-2 shadow-lg transition-colors disabled:opacity-50">
                    <Save className="w-4 h-4" /> {saving ? 'Saving...' : 'Save All Settings'}
                </button>
            </div>

            {/* Protocol Selector */}
            <div className="flex gap-3 mb-6">
                <button onClick={() => switchProtocol('openvpn')} className={`flex items-center gap-2.5 px-5 py-3 rounded-xl text-sm font-semibold transition-all border-2 ${protocol === 'openvpn' ? 'border-orange-500 bg-orange-500/15 text-orange-300 shadow-lg shadow-orange-500/10' : 'border-gray-700 bg-gray-800 text-gray-400 hover:border-gray-600'}`}>
                    <div className="text-left">
                        <div className="flex items-center gap-2">
                            <OpenVPNLogo /> OpenVPN
                        </div>
                        {ovpnVersion && <div className="text-[10px] font-mono text-orange-400/80 mt-1 ml-9">{ovpnVersion}</div>}
                    </div>
                </button>
                <button onClick={() => switchProtocol('wireguard')} className={`flex items-center gap-2.5 px-5 py-3 rounded-xl text-sm font-semibold transition-all border-2 ${protocol === 'wireguard' ? 'border-teal-500 bg-teal-500/15 text-teal-300 shadow-lg shadow-teal-500/10' : 'border-gray-700 bg-gray-800 text-gray-400 hover:border-gray-600'}`}>
                    <WireGuardLogo /> WireGuard
                </button>
                <button onClick={() => switchProtocol('general')} className={`flex items-center gap-2.5 px-5 py-3 rounded-xl text-sm font-semibold transition-all border-2 ${protocol === 'general' ? 'border-blue-500 bg-blue-500/15 text-blue-300 shadow-lg shadow-blue-500/10' : 'border-gray-700 bg-gray-800 text-gray-400 hover:border-gray-600'}`}>
                    <SettingsIcon className="w-6 h-6" /> General
                </button>
            </div>

            {/* Tabbed Layout */}
            <div className="flex gap-6">
                {/* Tab Sidebar */}
                <div className="w-56 flex-shrink-0">
                    <div className={`bg-gray-800 rounded-xl border ${borderColor} overflow-hidden`}>
                        {currentTabs.map((tab) => (
                            <button key={tab.id} onClick={() => setActiveTab(tab.id)} className={`w-full text-left px-4 py-3 text-sm font-medium transition-colors border-l-2 ${activeTab === tab.id ? bgActive : 'text-gray-400 hover:text-white hover:bg-gray-700/50 border-transparent'}`}>
                                {tab.label}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Tab Content */}
                <div className={`flex-1 bg-gray-800 rounded-xl p-6 border ${borderColor} min-h-[500px]`}>
                    {renderTabContent()}
                </div>
            </div>

            {/* Bottom Save */}
            <div className="mt-6 flex justify-end">
                <button onClick={handleSave} disabled={saving} className="bg-blue-600 hover:bg-blue-700 text-white px-8 py-3 rounded-lg font-bold flex items-center gap-2 shadow-lg transition-colors disabled:opacity-50">
                    <Save className="w-4 h-4" /> {saving ? 'Saving...' : 'Save All Settings'}
                </button>
            </div>

            <ConfirmationModal
                isOpen={confirmation.isOpen}
                onClose={() => setConfirmation({ ...confirmation, isOpen: false })}
                onConfirm={confirmation.onConfirm}
                title={confirmation.title}
                message={confirmation.message}
                confirmText={confirmation.confirmText}
                confirmColor={confirmation.confirmColor}
            />

            {/* SSL Streaming Logs Modal */}
            {sslStream.isOpen && (
                <div className="fixed inset-0 bg-black/80 flex items-center justify-center p-4 z-50">
                    <div className="bg-gray-900 rounded-xl border border-purple-500/30 p-6 w-full max-w-3xl shadow-2xl overflow-hidden flex flex-col max-h-[80vh]">
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="text-xl font-bold text-gray-100 flex items-center gap-2">
                                <Shield className="w-5 h-5 text-purple-400" />
                                Let's Encrypt SSL Issuance Log
                            </h3>
                            {!sslStream.loading && (
                                <button onClick={() => setSslStream({ isOpen: false, logs: '', loading: false })} className="text-gray-400 hover:text-white transition-colors">
                                    <X className="w-6 h-6" />
                                </button>
                            )}
                        </div>

                        <div className="flex-1 bg-black rounded-lg border border-gray-700 p-4 font-mono text-xs md:text-sm overflow-y-auto whitespace-pre-wrap flex flex-col">
                            {sslStream.logs.split('\n').filter(l => l.trim()).map((line, i) => {
                                let color = "text-gray-300";
                                if (line.startsWith("ERROR") || line.startsWith("FATAL")) color = "text-red-400 font-bold";
                                else if (line.startsWith("SUCCESS") || line.startsWith("DONE")) color = "text-green-400 font-bold";
                                else if (line.startsWith("EXEC")) color = "text-blue-400";
                                else if (line.startsWith("WARN")) color = "text-amber-400";
                                else if (line.startsWith("CERTBOT")) color = "text-gray-500";
                                else if (line.startsWith("INFO")) color = "text-purple-400";

                                return <div key={i} className={color}>{line}</div>
                            })}

                            {sslStream.loading && (
                                <div className="text-purple-400 mt-2 flex items-center gap-2 animate-pulse font-sans font-medium text-sm">
                                    <span className="w-2 h-2 rounded-full bg-purple-400"></span> Communicating with Let's Encrypt CA...
                                </div>
                            )}
                        </div>

                        {!sslStream.loading && (
                            <div className="mt-4 flex justify-end">
                                <button onClick={() => setSslStream({ isOpen: false, logs: '', loading: false })} className="bg-gray-700 hover:bg-gray-600 text-white px-6 py-2 rounded-lg font-medium transition-colors">
                                    Close Logs
                                </button>
                            </div>
                        )}
                    </div>
                </div>
            )}

            {toast && <Toast message={toast.message} type={toast.type} onClose={closeToast} />}
        </div>
    );
};

export default Settings;
