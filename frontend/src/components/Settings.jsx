import React, { useState, useEffect } from 'react';
import { Save, Settings as SettingsIcon, Shield, Globe, Server } from 'lucide-react';
import { apiService } from '../services/api';

const Settings = () => {
    const [settings, setSettings] = useState({});
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);

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
            alert("Settings saved successfully!");
        } catch (error) {
            alert("Failed to save settings");
        } finally {
            setSaving(false);
        }
    };

    if (loading) return <div className="p-8 text-center text-gray-400">Loading settings...</div>;

    return (
        <div className="p-6">
            <h1 className="text-3xl font-bold text-gray-100 flex items-center gap-2 mb-8">
                <SettingsIcon /> System Settings
            </h1>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                {/* OpenVPN Settings */}
                <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
                    <h2 className="text-xl font-bold text-blue-400 mb-6 flex items-center gap-2">
                        <Shield /> OpenVPN Configuration
                    </h2>
                    <div className="space-y-6">
                        {/* 1. Protocol & Network */}
                        <div className="border-b border-gray-700 pb-4">
                            <h3 className="text-gray-300 font-bold mb-3 text-sm uppercase">Network Strategy</h3>
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-gray-400 text-sm mb-1">Protocol</label>
                                    <select
                                        value={settings.ovpn_protocol || 'udp'}
                                        onChange={(e) => handleChange('ovpn_protocol', e.target.value)}
                                        className="w-full bg-gray-700 border border-gray-600 rounded-lg p-2 text-white"
                                    >
                                        <option value="udp">UDP (Faster)</option>
                                        <option value="tcp">TCP (Reliable)</option>
                                        <option value="both">Both</option>
                                    </select>
                                </div>
                                <div>
                                    <label className="block text-gray-400 text-sm mb-1">Port</label>
                                    <input
                                        type="text"
                                        value={settings.ovpn_port || '1194'}
                                        onChange={(e) => handleChange('ovpn_port', e.target.value)}
                                        className="w-full bg-gray-700 border border-gray-600 rounded-lg p-2 text-white"
                                    />
                                </div>
                                <div>
                                    <label className="block text-gray-400 text-sm mb-1">Topology</label>
                                    <select
                                        value={settings.ovpn_topology || 'subnet'}
                                        onChange={(e) => handleChange('ovpn_topology', e.target.value)}
                                        className="w-full bg-gray-700 border border-gray-600 rounded-lg p-2 text-white"
                                    >
                                        <option value="subnet">Subnet (Recommended)</option>
                                        <option value="net30">Net30 (Legacy)</option>
                                    </select>
                                </div>
                                <div>
                                    <label className="block text-gray-400 text-sm mb-1">Float (Allow IP Change)</label>
                                    <select
                                        value={settings.ovpn_float || '1'}
                                        onChange={(e) => handleChange('ovpn_float', e.target.value)}
                                        className="w-full bg-gray-700 border border-gray-600 rounded-lg p-2 text-white"
                                    >
                                        <option value="1">Enabled (Robust)</option>
                                        <option value="0">Disabled</option>
                                    </select>
                                </div>
                            </div>
                        </div>

                        {/* 2. Routing & DNS */}
                        <div className="border-b border-gray-700 pb-4">
                            <h3 className="text-gray-300 font-bold mb-3 text-sm uppercase">Routing & DNS</h3>
                            <div className="space-y-4">
                                <div>
                                    <label className="block text-gray-400 text-sm mb-1">Redirect Gateway (Force Traffic)</label>
                                    <select
                                        value={settings.ovpn_redirect_gateway || '1'}
                                        onChange={(e) => handleChange('ovpn_redirect_gateway', e.target.value)}
                                        className="w-full bg-gray-700 border border-gray-600 rounded-lg p-2 text-white"
                                    >
                                        <option value="1">Yes (Route All Traffic)</option>
                                        <option value="0">No (Split Tunneling)</option>
                                    </select>
                                </div>
                                <div>
                                    <label className="block text-gray-400 text-sm mb-1">DNS Servers</label>
                                    <input
                                        type="text"
                                        value={settings.ovpn_dns || '8.8.8.8,1.1.1.1'}
                                        onChange={(e) => handleChange('ovpn_dns', e.target.value)}
                                        className="w-full bg-gray-700 border border-gray-600 rounded-lg p-2 text-white"
                                        placeholder="8.8.8.8, 1.1.1.1"
                                    />
                                </div>
                            </div>
                        </div>

                        {/* 3. Security Details */}
                        <div className="border-b border-gray-700 pb-4">
                            <h3 className="text-gray-300 font-bold mb-3 text-sm uppercase">Security & Encryption</h3>
                            <div className="space-y-3">
                                <div>
                                    <label className="block text-gray-400 text-sm mb-1">Data Ciphers</label>
                                    <input
                                        type="text"
                                        value={settings.ovpn_data_ciphers || 'AES-256-GCM:AES-128-GCM:CHACHA20-POLY1305'}
                                        onChange={(e) => handleChange('ovpn_data_ciphers', e.target.value)}
                                        className="w-full bg-gray-700 border border-gray-600 rounded-lg p-2 text-white font-mono text-xs"
                                    />
                                </div>
                                <div className="grid grid-cols-2 gap-4">
                                    <div>
                                        <label className="block text-gray-400 text-sm mb-1">Auth Digest</label>
                                        <select
                                            value={settings.ovpn_auth_digest || 'SHA256'}
                                            onChange={(e) => handleChange('ovpn_auth_digest', e.target.value)}
                                            className="w-full bg-gray-700 border border-gray-600 rounded-lg p-2 text-white"
                                        >
                                            <option value="SHA256">SHA256</option>
                                            <option value="SHA512">SHA512</option>
                                        </select>
                                    </div>
                                    <div>
                                        <label className="block text-gray-400 text-sm mb-1">Min TLS Version</label>
                                        <select
                                            value={settings.ovpn_tls_version_min || '1.2'}
                                            onChange={(e) => handleChange('ovpn_tls_version_min', e.target.value)}
                                            className="w-full bg-gray-700 border border-gray-600 rounded-lg p-2 text-white"
                                        >
                                            <option value="1.2">TLS 1.2</option>
                                            <option value="1.3">TLS 1.3</option>
                                        </select>
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* 4. Timeouts & Logs */}
                        <div className="pb-2">
                            <h3 className="text-gray-300 font-bold mb-3 text-sm uppercase">Timeouts & Operations</h3>
                            <div className="grid grid-cols-3 gap-4">
                                <div>
                                    <label className="block text-gray-400 text-sm mb-1">Keepalive (Sec)</label>
                                    <input
                                        type="number"
                                        value={settings.ovpn_keepalive_interval || '10'}
                                        onChange={(e) => handleChange('ovpn_keepalive_interval', e.target.value)}
                                        className="w-full bg-gray-700 border border-gray-600 rounded-lg p-2 text-white"
                                    />
                                </div>
                                <div>
                                    <label className="block text-gray-400 text-sm mb-1">Verbosity (Log)</label>
                                    <select
                                        value={settings.ovpn_verb || '3'}
                                        onChange={(e) => handleChange('ovpn_verb', e.target.value)}
                                        className="w-full bg-gray-700 border border-gray-600 rounded-lg p-2 text-white"
                                    >
                                        <option value="1">1 (Minimal)</option>
                                        <option value="3">3 (Normal)</option>
                                        <option value="4">4 (Debug)</option>
                                        <option value="6">6 (Verbose)</option>
                                    </select>
                                </div>
                                <div>
                                    <label className="block text-gray-400 text-sm mb-1">Compression</label>
                                    <select
                                        value={settings.ovpn_compression || 'none'}
                                        onChange={(e) => handleChange('ovpn_compression', e.target.value)}
                                        className="w-full bg-gray-700 border border-gray-600 rounded-lg p-2 text-white"
                                    >
                                        <option value="none">Disabled</option>
                                        <option value="lz4-v2">LZ4-v2</option>
                                    </select>
                                </div>
                            </div>
                        </div>

                        <div className="pb-4">
                            <label className="block text-gray-400 text-sm mb-1">Raw Custom Config (Advanced)</label>
                            <textarea
                                value={settings.ovpn_custom_config || ''}
                                onChange={(e) => handleChange('ovpn_custom_config', e.target.value)}
                                placeholder="Paste additional OpenVPN directives here..."
                                className="w-full bg-gray-900 border border-gray-600 rounded-lg p-3 text-gray-300 font-mono text-xs h-24"
                            />
                        </div>

                        <div className="flex items-center gap-3 pt-2 bg-gray-700/50 p-3 rounded-lg">
                            <input
                                type="checkbox"
                                id="scramble"
                                checked={settings.ovpn_scramble === '1'}
                                onChange={(e) => handleChange('ovpn_scramble', e.target.checked ? '1' : '0')}
                                className="w-5 h-5 rounded border-gray-600 bg-gray-700 text-blue-600"
                            />
                            <label htmlFor="scramble" className="text-gray-200 font-medium">Enable XOR Scramble (Anti-Censorship)</label>
                        </div>

                        <div className="border-t border-gray-700 pt-4 mt-4">
                            <h3 className="text-sm font-bold text-gray-300 mb-2">Certificate Authority (CA)</h3>
                            <button
                                onClick={async () => {
                                    if (window.confirm("Are you sure? This will replace existing Server Certificates. Clients might need to download new configs if they rely on the old CA.")) {
                                        try {
                                            await apiService.regeneratePKI();
                                            alert("Certificates regenerated successfully.");
                                        } catch (e) {
                                            alert("Failed to regenerate certs.");
                                        }
                                    }
                                }}
                                className="w-full bg-gray-700 hover:bg-gray-600 text-white px-4 py-2 rounded-lg text-sm border border-gray-600"
                            >
                                Regenerate Server Certificates
                            </button>
                            <p className="text-xs text-gray-500 mt-2">
                                Note: Regenerating will invalidate all old client configs. Users must download new .ovpn files.
                            </p>
                        </div>
                    </div>
                </div>

                {/* WireGuard Settings */}
                <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
                    <h2 className="text-xl font-bold text-green-400 mb-6 flex items-center gap-2">
                        <Globe /> WireGuard Configuration
                    </h2>
                    <div className="space-y-4">
                        <div>
                            <label className="block text-gray-400 text-sm mb-1">Port (default: 51820)</label>
                            <input
                                type="text"
                                value={settings.wg_port || ''}
                                onChange={(e) => handleChange('wg_port', e.target.value)}
                                className="w-full bg-gray-700 border border-gray-600 rounded-lg p-2 text-white"
                            />
                        </div>
                        <div>
                            <label className="block text-gray-400 text-sm mb-1">MTU</label>
                            <input
                                type="text"
                                value={settings.wg_mtu || '1420'}
                                onChange={(e) => handleChange('wg_mtu', e.target.value)}
                                className="w-full bg-gray-700 border border-gray-600 rounded-lg p-2 text-white"
                            />
                            <p className="text-xs text-gray-500 mt-1">Recommended: 1280-1420 for mobile networks in Iran</p>
                        </div>
                        <div>
                            <label className="block text-gray-400 text-sm mb-1">Endpoint IP (Public IP)</label>
                            <input
                                type="text"
                                placeholder="Auto-detect"
                                value={settings.wg_endpoint_ip || ''}
                                onChange={(e) => handleChange('wg_endpoint_ip', e.target.value)}
                                className="w-full bg-gray-700 border border-gray-600 rounded-lg p-2 text-white"
                            />
                            <p className="text-xs text-gray-500 mt-1">Set this if your server is behind NAT or you have a specific domain</p>
                        </div>
                    </div>
                </div>
            </div>

            <button
                onClick={handleSave}
                disabled={saving}
                className="mt-8 bg-blue-600 hover:bg-blue-700 text-white px-8 py-3 rounded-lg font-bold flex items-center gap-2 shadow-lg"
            >
                <Save /> {saving ? 'Saving...' : 'Save Settings'}
            </button>
        </div>
    );
};

export default Settings;
