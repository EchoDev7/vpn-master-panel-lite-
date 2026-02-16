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
                    <div className="space-y-4">
                        <div>
                            <label className="block text-gray-400 text-sm mb-1">Protocol</label>
                            <select
                                value={settings.ovpn_protocol || 'udp'}
                                onChange={(e) => handleChange('ovpn_protocol', e.target.value)}
                                className="w-full bg-gray-700 border border-gray-600 rounded-lg p-2 text-white"
                            >
                                <option value="udp">UDP Only</option>
                                <option value="tcp">TCP Only</option>
                                <option value="both">Both (UDP & TCP)</option>
                            </select>
                        </div>
                        <div>
                            <label className="block text-gray-400 text-sm mb-1">Port (default: 1194)</label>
                            <input
                                type="text"
                                value={settings.ovpn_port || ''}
                                onChange={(e) => handleChange('ovpn_port', e.target.value)}
                                className="w-full bg-gray-700 border border-gray-600 rounded-lg p-2 text-white"
                            />
                        </div>
                        <div>
                            <label className="block text-gray-400 text-sm mb-1">DNS Servers</label>
                            <input
                                type="text"
                                value={settings.ovpn_dns || ''}
                                onChange={(e) => handleChange('ovpn_dns', e.target.value)}
                                className="w-full bg-gray-700 border border-gray-600 rounded-lg p-2 text-white"
                            />
                        </div>
                        <div>
                            <label className="block text-gray-400 text-sm mb-1">MTU (Tunnel MTU)</label>
                            <input
                                type="text"
                                value={settings.ovpn_mtu || '1500'}
                                onChange={(e) => handleChange('ovpn_mtu', e.target.value)}
                                className="w-full bg-gray-700 border border-gray-600 rounded-lg p-2 text-white"
                            />
                            <p className="text-xs text-gray-500 mt-1">Leave 1500 for standard, lower for restrictive networks (e.g. 1300)</p>
                        </div>
                        <div className="flex items-center gap-3 pt-2">
                            <input
                                type="checkbox"
                                id="scramble"
                                checked={settings.ovpn_scramble === '1'}
                                onChange={(e) => handleChange('ovpn_scramble', e.target.checked ? '1' : '0')}
                                className="w-5 h-5 rounded border-gray-600 bg-gray-700 text-blue-600"
                            />
                            <label htmlFor="scramble" className="text-gray-300">Enable XOR Scramble (Anti-Censorship)</label>
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
