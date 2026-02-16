import React, { useState, useEffect } from 'react';
import { Save, Settings as SettingsIcon, Shield, Globe, Server, Lock, Wifi, Route, Clock, Wrench, FileText, AlertTriangle, Info, Eye } from 'lucide-react';
import { apiService } from '../services/api';

const TABS = [
    { id: 'network', label: '🌐 Network', icon: Globe },
    { id: 'security', label: '🔒 Security', icon: Lock },
    { id: 'anticensorship', label: '🛡️ Anti-Censorship', icon: Shield },
    { id: 'routing', label: '🔀 Routing & DNS', icon: Route },
    { id: 'connection', label: '⏱️ Connection', icon: Clock },
    { id: 'advanced', label: '🔧 Advanced', icon: Wrench },
    { id: 'certificates', label: '📜 Certificates', icon: FileText },
    { id: 'wireguard', label: '🟢 WireGuard', icon: Wifi },
];

// Tooltip component
const Tip = ({ text }) => (
    <div className="group relative inline-block ml-1">
        <Info className="w-3.5 h-3.5 text-gray-500 cursor-help inline" />
        <div className="absolute z-50 invisible group-hover:visible bg-gray-900 text-gray-200 text-xs rounded-lg p-2 w-64 bottom-full left-1/2 -translate-x-1/2 mb-1 border border-gray-600 shadow-xl">
            {text}
            <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-900"></div>
        </div>
    </div>
);

// Iran recommended badge
const IranBadge = () => (
    <span className="ml-2 text-[10px] bg-amber-500/20 text-amber-400 px-1.5 py-0.5 rounded font-bold uppercase tracking-wider">
        🇮🇷 Iran
    </span>
);

const Settings = () => {
    const [settings, setSettings] = useState({});
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [activeTab, setActiveTab] = useState('network');
    const [serverConfigPreview, setServerConfigPreview] = useState(null);
    const [showServerConfig, setShowServerConfig] = useState(false);
    const [pkiInfo, setPkiInfo] = useState(null);

    useEffect(() => {
        loadSettings();
    }, []);

    const loadSettings = async () => {
        try {
            const response = await apiService.getSettings();
            setSettings(response.data);
            setLoading(false);
        } catch (error) {
            console.error("Failed to load settings:", error);
            setLoading(false);
        }
    };

    const handleChange = (key, value) => {
        setSettings(prev => ({ ...prev, [key]: value }));
    };

    const handleSave = async () => {
        setSaving(true);
        try {
            await apiService.updateSettings(settings);
            alert("✅ Settings saved successfully!");
        } catch (error) {
            alert("❌ Failed to save settings");
        } finally {
            setSaving(false);
        }
    };

    const loadPKIInfo = async () => {
        try {
            const response = await apiService.getPKIInfo();
            setPkiInfo(response.data);
        } catch (e) {
            console.error("Failed to load PKI info", e);
        }
    };

    const loadServerConfigPreview = async () => {
        try {
            const response = await apiService.getServerConfigPreview();
            setServerConfigPreview(response.data.content);
            setShowServerConfig(true);
        } catch (e) {
            alert("Failed to load server config preview");
        }
    };

    if (loading) return <div className="p-8 text-center text-gray-400">Loading settings...</div>;

    // ==================================
    // Input helpers
    // ==================================
    const SelectField = ({ label, settingKey, options, tip, iranBadge }) => (
        <div>
            <label className="block text-gray-400 text-sm mb-1">
                {label}
                {tip && <Tip text={tip} />}
                {iranBadge && <IranBadge />}
            </label>
            <select
                value={settings[settingKey] || options[0]?.value || ''}
                onChange={(e) => handleChange(settingKey, e.target.value)}
                className="w-full bg-gray-700 border border-gray-600 rounded-lg p-2 text-white text-sm focus:border-blue-500 focus:outline-none"
            >
                {options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
        </div>
    );

    const InputField = ({ label, settingKey, placeholder, type = "text", tip, iranBadge, mono }) => (
        <div>
            <label className="block text-gray-400 text-sm mb-1">
                {label}
                {tip && <Tip text={tip} />}
                {iranBadge && <IranBadge />}
            </label>
            <input
                type={type}
                value={settings[settingKey] || ''}
                onChange={(e) => handleChange(settingKey, e.target.value)}
                placeholder={placeholder}
                className={`w-full bg-gray-700 border border-gray-600 rounded-lg p-2 text-white text-sm focus:border-blue-500 focus:outline-none ${mono ? 'font-mono text-xs' : ''}`}
            />
        </div>
    );

    const CheckboxField = ({ label, settingKey, tip, iranBadge }) => (
        <div className="flex items-center gap-3 bg-gray-700/50 p-3 rounded-lg">
            <input
                type="checkbox"
                id={settingKey}
                checked={settings[settingKey] === '1'}
                onChange={(e) => handleChange(settingKey, e.target.checked ? '1' : '0')}
                className="w-5 h-5 rounded border-gray-600 bg-gray-700 text-blue-600 focus:ring-blue-500"
            />
            <label htmlFor={settingKey} className="text-gray-200 font-medium text-sm cursor-pointer">
                {label}
                {tip && <Tip text={tip} />}
                {iranBadge && <IranBadge />}
            </label>
        </div>
    );

    const TextareaField = ({ label, settingKey, placeholder, tip, rows = 4 }) => (
        <div>
            <label className="block text-gray-400 text-sm mb-1">
                {label}
                {tip && <Tip text={tip} />}
            </label>
            <textarea
                value={settings[settingKey] || ''}
                onChange={(e) => handleChange(settingKey, e.target.value)}
                placeholder={placeholder}
                rows={rows}
                className="w-full bg-gray-900 border border-gray-600 rounded-lg p-3 text-gray-300 font-mono text-xs resize-none focus:border-blue-500 focus:outline-none"
            />
        </div>
    );

    const SectionTitle = ({ children }) => (
        <h3 className="text-gray-300 font-bold mb-3 text-sm uppercase tracking-wider border-b border-gray-700 pb-2">
            {children}
        </h3>
    );

    // ==================================
    // Tab Content
    // ==================================

    const renderNetworkTab = () => (
        <div className="space-y-6">
            <SectionTitle>Connection Settings</SectionTitle>
            <div className="grid grid-cols-2 gap-4">
                <SelectField
                    label="Protocol"
                    settingKey="ovpn_protocol"
                    iranBadge
                    tip="TCP on port 443 mimics HTTPS traffic, making it harder for DPI to detect. UDP is faster but easier to block."
                    options={[
                        { value: 'tcp', label: 'TCP (Stealth — Recommended for Iran)' },
                        { value: 'udp', label: 'UDP (Faster)' },
                        { value: 'both', label: 'Both' },
                    ]}
                />
                <InputField
                    label="Port"
                    settingKey="ovpn_port"
                    placeholder="443"
                    iranBadge
                    tip="Port 443 is HTTPS port. Using it makes VPN traffic look like normal web browsing."
                />
                <InputField
                    label="MTU"
                    settingKey="ovpn_mtu"
                    placeholder="1400"
                    type="number"
                    iranBadge
                    tip="Lower MTU (1400) works better with Iran ISPs. Default 1500 may cause packet drops."
                />
                <SelectField
                    label="Topology"
                    settingKey="ovpn_topology"
                    tip="Subnet is recommended for modern setups. Net30 is legacy."
                    options={[
                        { value: 'subnet', label: 'Subnet (Recommended)' },
                        { value: 'net30', label: 'Net30 (Legacy)' },
                    ]}
                />
            </div>

            <SectionTitle>Server Network</SectionTitle>
            <div className="grid grid-cols-2 gap-4">
                <InputField
                    label="VPN Subnet"
                    settingKey="ovpn_server_subnet"
                    placeholder="10.8.0.0"
                    tip="The IP range assigned to VPN clients."
                />
                <InputField
                    label="Subnet Mask"
                    settingKey="ovpn_server_netmask"
                    placeholder="255.255.255.0"
                />
                <InputField
                    label="Max Clients"
                    settingKey="ovpn_max_clients"
                    placeholder="100"
                    type="number"
                    tip="Maximum simultaneous connections."
                />
                <InputField
                    label="Server IP (Override)"
                    settingKey="ovpn_server_ip"
                    placeholder="Auto-detect"
                    tip="Leave empty to auto-detect. Set if your server is behind NAT or has a domain."
                />
            </div>

            <div className="grid grid-cols-2 gap-4">
                <CheckboxField
                    label="Allow IP Change (Float)"
                    settingKey="ovpn_float"
                    tip="Essential for mobile users whose IP changes frequently."
                />
                <CheckboxField
                    label="Allow Multiple Devices (Duplicate CN)"
                    settingKey="ovpn_duplicate_cn"
                    tip="Allow the same user to connect from multiple devices simultaneously."
                />
            </div>
        </div>
    );

    const renderSecurityTab = () => (
        <div className="space-y-6">
            <SectionTitle>TLS Control Channel Security</SectionTitle>
            <SelectField
                label="TLS Control Channel Mode"
                settingKey="ovpn_tls_control_channel"
                iranBadge
                tip="tls-crypt encrypts the ENTIRE control channel, making the OpenVPN handshake invisible to DPI. This is the most important anti-censorship setting."
                options={[
                    { value: 'tls-crypt', label: 'tls-crypt (Encrypt Control Channel — Recommended)' },
                    { value: 'tls-crypt-v2', label: 'tls-crypt-v2 (Per-client keys, OpenVPN 2.5+)' },
                    { value: 'tls-auth', label: 'tls-auth (Sign & Verify only)' },
                    { value: 'none', label: 'None (Not Recommended)' },
                ]}
            />

            <SectionTitle>Data Channel Encryption</SectionTitle>
            <div className="grid grid-cols-2 gap-4">
                <InputField
                    label="Data Ciphers"
                    settingKey="ovpn_data_ciphers"
                    placeholder="AES-256-GCM:AES-128-GCM:CHACHA20-POLY1305"
                    mono
                    tip="Colon-separated list. Server and client negotiate the best mutually supported cipher."
                />
                <InputField
                    label="Fallback Cipher"
                    settingKey="ovpn_data_ciphers_fallback"
                    placeholder="AES-256-GCM"
                    mono
                    tip="Used when cipher negotiation fails."
                />
            </div>

            <SectionTitle>Authentication & TLS</SectionTitle>
            <div className="grid grid-cols-2 gap-4">
                <SelectField
                    label="Auth Digest (HMAC)"
                    settingKey="ovpn_auth_digest"
                    tip="Hash algorithm for HMAC authentication."
                    options={[
                        { value: 'SHA256', label: 'SHA256 (Recommended)' },
                        { value: 'SHA384', label: 'SHA384' },
                        { value: 'SHA512', label: 'SHA512 (Strongest)' },
                    ]}
                />
                <SelectField
                    label="Minimum TLS Version"
                    settingKey="ovpn_tls_version_min"
                    tip="Minimum TLS version for the control channel."
                    options={[
                        { value: '1.2', label: 'TLS 1.2 (Recommended)' },
                        { value: '1.3', label: 'TLS 1.3 (Newest)' },
                    ]}
                />
            </div>
            <InputField
                label="TLS 1.2 Cipher Suites"
                settingKey="ovpn_tls_ciphers"
                placeholder="TLS-ECDHE-..."
                mono
                tip="Cipher suites for TLS 1.2 control channel."
            />
            <InputField
                label="TLS 1.3 Cipher Suites"
                settingKey="ovpn_tls_cipher_suites"
                placeholder="TLS_AES_256_GCM_SHA384:..."
                mono
                tip="Cipher suites for TLS 1.3 control channel."
            />
            <InputField
                label="Renegotiation Interval (sec)"
                settingKey="ovpn_reneg_sec"
                placeholder="3600"
                type="number"
                tip="How often TLS sessions are renegotiated. Lower values = more security but more overhead."
            />
        </div>
    );

    const renderAntiCensorshipTab = () => (
        <div className="space-y-6">
            <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-4 mb-4">
                <div className="flex items-start gap-3">
                    <AlertTriangle className="w-5 h-5 text-amber-400 mt-0.5 flex-shrink-0" />
                    <div>
                        <p className="text-amber-300 font-semibold text-sm">Iran Anti-Censorship Settings</p>
                        <p className="text-gray-400 text-xs mt-1">
                            These settings are specifically designed to bypass Iran's Deep Packet Inspection (DPI).
                            Settings marked with 🇮🇷 are pre-configured for optimal performance in Iran.
                        </p>
                    </div>
                </div>
            </div>

            <SectionTitle>XOR Scramble Obfuscation</SectionTitle>
            <CheckboxField
                label="Enable XOR Scramble"
                settingKey="ovpn_scramble"
                iranBadge
                tip="XOR obfuscation modifies packet headers to make them unrecognizable by DPI systems. Requires patched OpenVPN server."
            />
            <InputField
                label="Scramble Password"
                settingKey="ovpn_scramble_password"
                placeholder="vpnmaster"
                iranBadge
                tip="The XOR key used for scrambling. Must match between server and client."
            />

            <SectionTitle>Packet Fragmentation</SectionTitle>
            <InputField
                label="Fragment Size (0 = disabled)"
                settingKey="ovpn_fragment"
                placeholder="0"
                type="number"
                iranBadge
                tip="Splits packets into smaller fragments. This makes it harder for DPI to reassemble and inspect packets. Common values: 1200, 1300."
            />

            <SectionTitle>Port Sharing</SectionTitle>
            <InputField
                label="Port Share (e.g. 127.0.0.1 8443)"
                settingKey="ovpn_port_share"
                placeholder="127.0.0.1 8443"
                tip="Share the VPN port with a web server. Non-VPN traffic on port 443 is forwarded to another port, making the VPN invisible."
            />

            <SectionTitle>Proxy Chaining</SectionTitle>
            <div className="grid grid-cols-3 gap-4">
                <SelectField
                    label="Proxy Type"
                    settingKey="ovpn_proxy_type"
                    tip="Route VPN traffic through a proxy for additional stealth."
                    options={[
                        { value: 'none', label: 'None' },
                        { value: 'socks', label: 'SOCKS5 Proxy' },
                        { value: 'http', label: 'HTTP Proxy' },
                    ]}
                />
                <InputField
                    label="Proxy Address"
                    settingKey="ovpn_proxy_address"
                    placeholder="127.0.0.1"
                />
                <InputField
                    label="Proxy Port"
                    settingKey="ovpn_proxy_port"
                    placeholder="1080"
                />
            </div>

            <SectionTitle>Multi-Server Failover</SectionTitle>
            <InputField
                label="Remote Servers (comma-separated)"
                settingKey="ovpn_remote_servers"
                placeholder="1.2.3.4:443:tcp,5.6.7.8:443:tcp"
                tip="If main server is blocked, client automatically tries these backup servers. Format: ip:port:proto"
            />
        </div>
    );

    const renderRoutingTab = () => (
        <div className="space-y-6">
            <SectionTitle>Traffic Routing</SectionTitle>
            <SelectField
                label="Redirect Gateway"
                settingKey="ovpn_redirect_gateway"
                tip="Force ALL client traffic through VPN (full tunnel) or only VPN-destined traffic (split tunnel)."
                options={[
                    { value: '1', label: 'Yes — Route All Traffic (Full Tunnel)' },
                    { value: '0', label: 'No — Split Tunneling' },
                ]}
            />
            <CheckboxField
                label="Allow Client-to-Client Communication"
                settingKey="ovpn_inter_client"
                tip="If enabled, VPN clients can communicate with each other on the VPN network."
            />

            <SectionTitle>DNS Settings</SectionTitle>
            <InputField
                label="DNS Servers (comma-separated)"
                settingKey="ovpn_dns"
                placeholder="1.1.1.1, 8.8.8.8"
                tip="DNS servers pushed to clients. Multiple servers provide fallback."
            />
            <CheckboxField
                label="Block Outside DNS (Prevent DNS Leaks)"
                settingKey="ovpn_block_outside_dns"
                iranBadge
                tip="Prevents Windows clients from using non-VPN DNS, which could leak browsing data to your ISP."
            />
        </div>
    );

    const renderConnectionTab = () => (
        <div className="space-y-6">
            <SectionTitle>Keepalive</SectionTitle>
            <div className="grid grid-cols-2 gap-4">
                <InputField
                    label="Ping Interval (sec)"
                    settingKey="ovpn_keepalive_interval"
                    placeholder="10"
                    type="number"
                    tip="Send a ping every N seconds to check connection is alive."
                />
                <InputField
                    label="Ping Timeout (sec)"
                    settingKey="ovpn_keepalive_timeout"
                    placeholder="60"
                    type="number"
                    tip="If no response in N seconds, consider connection dead and reconnect."
                />
            </div>

            <SectionTitle>Retry & Timeout</SectionTitle>
            <div className="grid grid-cols-3 gap-4">
                <InputField
                    label="Connect Retry (sec)"
                    settingKey="ovpn_connect_retry"
                    placeholder="5"
                    type="number"
                    tip="Wait N seconds between connection attempts."
                />
                <InputField
                    label="Max Retry (0=infinite)"
                    settingKey="ovpn_connect_retry_max"
                    placeholder="0"
                    type="number"
                    tip="0 means keep retrying forever. Important for Iran where connections drop frequently."
                />
                <InputField
                    label="Server Poll Timeout (sec)"
                    settingKey="ovpn_server_poll_timeout"
                    placeholder="10"
                    type="number"
                    tip="Timeout for initial server response."
                />
            </div>

            <SectionTitle>Logging & Compression</SectionTitle>
            <div className="grid grid-cols-2 gap-4">
                <SelectField
                    label="Log Verbosity"
                    settingKey="ovpn_verb"
                    tip="Higher values produce more detailed logs. Use 4+ for debugging."
                    options={[
                        { value: '1', label: '1 — Minimal' },
                        { value: '3', label: '3 — Normal' },
                        { value: '4', label: '4 — Debug' },
                        { value: '6', label: '6 — Verbose' },
                    ]}
                />
                <SelectField
                    label="Compression"
                    settingKey="ovpn_compression"
                    tip="Compression can improve speed but may be detected by DPI. Disabled is recommended for stealth."
                    options={[
                        { value: 'none', label: 'Disabled (Recommended)' },
                        { value: 'lz4-v2', label: 'LZ4-v2' },
                        { value: 'lzo', label: 'LZO' },
                    ]}
                />
            </div>
        </div>
    );

    const renderAdvancedTab = () => (
        <div className="space-y-6">
            <SectionTitle>Custom OpenVPN Directives</SectionTitle>
            <TextareaField
                label="Client Config Directives"
                settingKey="ovpn_custom_client_config"
                placeholder={"# Additional directives injected into .ovpn files\n# Example: push \"route 10.0.0.0 255.0.0.0\""}
                tip="Raw OpenVPN directives added to every generated client config file."
                rows={4}
            />
            <TextareaField
                label="Server Config Directives"
                settingKey="ovpn_custom_server_config"
                placeholder={"# Additional directives for server.conf\n# Example: management 127.0.0.1 7505"}
                tip="Raw OpenVPN directives added to the generated server config."
                rows={4}
            />

            <SectionTitle>Server Configuration</SectionTitle>
            <div className="flex gap-3">
                <button
                    onClick={loadServerConfigPreview}
                    className="flex-1 bg-gray-700 hover:bg-gray-600 text-white px-4 py-3 rounded-lg text-sm font-medium flex items-center justify-center gap-2 border border-gray-600 transition-colors"
                >
                    <Eye className="w-4 h-4" /> Preview server.conf
                </button>
                <button
                    onClick={async () => {
                        if (window.confirm("This will generate server.conf based on current settings. Continue?")) {
                            try {
                                const res = await apiService.applyServerConfig();
                                const data = res.data;
                                if (data.system_written) {
                                    alert(`✅ Server config written to:\n${data.system_path}\n\nRun: sudo systemctl restart openvpn@server`);
                                } else {
                                    alert(`⚠️ Saved to: ${data.backup_path}\n\n${data.hint}`);
                                }
                            } catch (e) {
                                alert("❌ Failed to apply server config");
                            }
                        }
                    }}
                    className="flex-1 bg-blue-600 hover:bg-blue-700 text-white px-4 py-3 rounded-lg text-sm font-medium flex items-center justify-center gap-2 transition-colors"
                >
                    <Server className="w-4 h-4" /> Generate & Apply
                </button>
            </div>

            {/* Server Config Preview Modal */}
            {showServerConfig && serverConfigPreview && (
                <div className="mt-4 bg-gray-900 rounded-lg border border-gray-600 overflow-hidden">
                    <div className="flex justify-between items-center p-3 bg-gray-800 border-b border-gray-700">
                        <span className="text-sm font-medium text-gray-300">server.conf Preview</span>
                        <button onClick={() => setShowServerConfig(false)} className="text-gray-400 hover:text-white text-sm">✕</button>
                    </div>
                    <textarea
                        readOnly
                        value={serverConfigPreview}
                        className="w-full h-64 bg-transparent text-gray-300 p-4 font-mono text-xs resize-none focus:outline-none"
                    />
                </div>
            )}
        </div>
    );

    const renderCertificatesTab = () => (
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
                <button
                    onClick={loadPKIInfo}
                    className="w-full bg-gray-700 hover:bg-gray-600 text-white px-4 py-2 rounded-lg text-sm border border-gray-600 transition-colors"
                >
                    Load CA Info
                </button>
            )}

            <button
                onClick={async () => {
                    if (window.confirm("⚠️ WARNING: This will replace existing certificates.\nAll users must download new .ovpn files.\n\nContinue?")) {
                        try {
                            await apiService.regeneratePKI();
                            alert("✅ Certificates regenerated successfully.");
                            setPkiInfo(null);
                        } catch (e) {
                            alert("❌ Failed to regenerate certificates.");
                        }
                    }
                }}
                className="w-full bg-red-600/20 hover:bg-red-600/30 text-red-400 px-4 py-3 rounded-lg text-sm font-medium border border-red-600/30 transition-colors"
            >
                🔄 Regenerate All Certificates
            </button>
            <p className="text-xs text-gray-500">
                Warning: Regenerating will invalidate all existing client configs. Users must download new .ovpn files.
            </p>

            <SectionTitle>TLS Key Info</SectionTitle>
            <p className="text-xs text-gray-400">
                The TLS key (ta.key) is used for the TLS control channel security mode you selected in the Security tab.
                It is automatically included in generated client configs.
            </p>
        </div>
    );

    const renderWireGuardTab = () => (
        <div className="space-y-6">
            <SectionTitle>WireGuard Configuration</SectionTitle>
            <div className="grid grid-cols-2 gap-4">
                <InputField
                    label="Port"
                    settingKey="wg_port"
                    placeholder="51820"
                />
                <InputField
                    label="MTU"
                    settingKey="wg_mtu"
                    placeholder="1420"
                    tip="Recommended: 1280-1420 for Iran mobile networks."
                    iranBadge
                />
            </div>
            <InputField
                label="Endpoint IP (Public IP)"
                settingKey="wg_endpoint_ip"
                placeholder="Auto-detect"
                tip="Set this if your server is behind NAT or you have a specific domain."
            />
            <InputField
                label="DNS Servers"
                settingKey="wg_dns"
                placeholder="1.1.1.1,8.8.8.8"
            />
        </div>
    );

    const renderTabContent = () => {
        switch (activeTab) {
            case 'network': return renderNetworkTab();
            case 'security': return renderSecurityTab();
            case 'anticensorship': return renderAntiCensorshipTab();
            case 'routing': return renderRoutingTab();
            case 'connection': return renderConnectionTab();
            case 'advanced': return renderAdvancedTab();
            case 'certificates': return renderCertificatesTab();
            case 'wireguard': return renderWireGuardTab();
            default: return renderNetworkTab();
        }
    };

    return (
        <div className="p-6 max-w-6xl mx-auto">
            {/* Header */}
            <div className="flex items-center justify-between mb-8">
                <h1 className="text-3xl font-bold text-gray-100 flex items-center gap-3">
                    <SettingsIcon className="text-blue-400" /> System Settings
                </h1>
                <button
                    onClick={handleSave}
                    disabled={saving}
                    className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2.5 rounded-lg font-bold flex items-center gap-2 shadow-lg transition-colors disabled:opacity-50"
                >
                    <Save className="w-4 h-4" /> {saving ? 'Saving...' : 'Save All Settings'}
                </button>
            </div>

            {/* Tabbed Layout */}
            <div className="flex gap-6">
                {/* Tab Sidebar */}
                <div className="w-56 flex-shrink-0">
                    <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden">
                        {TABS.map((tab) => (
                            <button
                                key={tab.id}
                                onClick={() => setActiveTab(tab.id)}
                                className={`w-full text-left px-4 py-3 text-sm font-medium transition-colors border-l-2 ${activeTab === tab.id
                                        ? 'bg-blue-600/20 text-blue-400 border-blue-500'
                                        : 'text-gray-400 hover:text-white hover:bg-gray-700/50 border-transparent'
                                    }`}
                            >
                                {tab.label}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Tab Content */}
                <div className="flex-1 bg-gray-800 rounded-xl p-6 border border-gray-700 min-h-[500px]">
                    {renderTabContent()}
                </div>
            </div>

            {/* Bottom Save Button */}
            <div className="mt-6 flex justify-end">
                <button
                    onClick={handleSave}
                    disabled={saving}
                    className="bg-blue-600 hover:bg-blue-700 text-white px-8 py-3 rounded-lg font-bold flex items-center gap-2 shadow-lg transition-colors disabled:opacity-50"
                >
                    <Save className="w-4 h-4" /> {saving ? 'Saving...' : 'Save All Settings'}
                </button>
            </div>
        </div>
    );
};

export default Settings;
