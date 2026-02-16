import React, { useState, useEffect } from 'react';
import { Plus, Globe, Play, Square, Trash2, RefreshCw, Settings, Download, XCircle, ChevronDown, ChevronUp, Activity, Shield, Zap, ExternalLink, RotateCw, X } from 'lucide-react';
import { apiService } from '../services/api';

// ===== Tunnel Branding =====
const TUNNEL_COLORS = {
    backhaul: { bg: 'bg-blue-500/15', border: 'border-blue-500', text: 'text-blue-400', dot: 'bg-blue-500' },
    rathole: { bg: 'bg-purple-500/15', border: 'border-purple-500', text: 'text-purple-400', dot: 'bg-purple-500' },
    persianshield: { bg: 'bg-amber-500/15', border: 'border-amber-500', text: 'text-amber-400', dot: 'bg-amber-500' },
    gost: { bg: 'bg-green-500/15', border: 'border-green-500', text: 'text-green-400', dot: 'bg-green-500' },
    chisel: { bg: 'bg-teal-500/15', border: 'border-teal-500', text: 'text-teal-400', dot: 'bg-teal-500' },
};

const TUNNEL_ICONS = {
    backhaul: '⚡', rathole: '🐀', persianshield: '🛡️', gost: '🌐', chisel: '🔨',
};

// ===== Create Tunnel Modal =====
const CreateTunnelModal = ({ show, onClose, onCreated, availableTunnels }) => {
    const [form, setForm] = useState({
        name: '', tunnel_type: 'backhaul', protocol: 'tcp', mode: 'server',
        iran_server_ip: '', iran_server_port: 8443,
        foreign_server_ip: '', foreign_server_port: 8443,
        forwarded_ports: '', config: {},
        domain_fronting_enabled: false, domain_fronting_domain: '', tls_obfuscation: false,
    });
    const [creating, setCreating] = useState(false);

    if (!show) return null;

    const handleCreate = async () => {
        if (!form.name || !form.iran_server_ip || !form.foreign_server_ip) {
            alert('Please fill name, Iran IP, and Foreign IP'); return;
        }
        setCreating(true);
        try {
            const data = {
                ...form,
                iran_server_port: parseInt(form.iran_server_port),
                foreign_server_port: parseInt(form.foreign_server_port),
                forwarded_ports: form.forwarded_ports ? form.forwarded_ports.split(',').map(p => parseInt(p.trim())).filter(Boolean) : [],
            };
            await apiService.createTunnel(data);
            alert('✅ Tunnel created successfully!');
            onCreated();
            onClose();
        } catch (e) {
            alert(`❌ Error: ${e.response?.data?.detail || e.message}`);
        } finally { setCreating(false); }
    };

    const selected = availableTunnels.find(t => t.id === form.tunnel_type);

    return (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
            <div className="bg-gray-800 rounded-2xl border border-gray-700 w-full max-w-2xl max-h-[90vh] overflow-y-auto shadow-2xl">
                <div className="flex items-center justify-between p-6 border-b border-gray-700">
                    <h2 className="text-xl font-bold text-white flex items-center gap-2">
                        <Plus className="text-green-400" size={24} /> Create New Tunnel
                    </h2>
                    <button onClick={onClose} className="text-gray-400 hover:text-white"><X size={20} /></button>
                </div>

                <div className="p-6 space-y-5">
                    {/* Tunnel Type Selector */}
                    <div>
                        <label className="block text-gray-400 text-sm mb-2">Tunnel Type</label>
                        <div className="grid grid-cols-5 gap-2">
                            {availableTunnels.map(t => (
                                <button key={t.id} onClick={() => setForm({ ...form, tunnel_type: t.id })}
                                    className={`p-3 rounded-xl text-center text-sm font-medium border-2 transition-all ${form.tunnel_type === t.id
                                        ? `${TUNNEL_COLORS[t.id]?.border || 'border-blue-500'} ${TUNNEL_COLORS[t.id]?.bg || 'bg-blue-500/15'} ${TUNNEL_COLORS[t.id]?.text || 'text-blue-400'}`
                                        : 'border-gray-700 bg-gray-700/50 text-gray-400 hover:border-gray-500'}`}>
                                    <div className="text-2xl mb-1">{TUNNEL_ICONS[t.id] || '🔗'}</div>
                                    <div className="text-xs">{t.name}</div>
                                    {!t.installed && <div className="text-[10px] text-red-400 mt-0.5">Not Installed</div>}
                                </button>
                            ))}
                        </div>
                    </div>

                    {selected && (
                        <div className={`${TUNNEL_COLORS[selected.id]?.bg || 'bg-gray-700/50'} rounded-lg p-3 border ${TUNNEL_COLORS[selected.id]?.border || 'border-gray-600'}`}>
                            <p className="text-sm text-gray-300">{selected.description}</p>
                            <div className="flex gap-2 mt-2 flex-wrap">
                                {selected.features?.map((f, i) => (
                                    <span key={i} className="text-[10px] bg-gray-800/50 text-gray-400 px-2 py-0.5 rounded">{f}</span>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Name & Protocol */}
                    <div className="grid grid-cols-3 gap-4">
                        <div>
                            <label className="block text-gray-400 text-sm mb-1">Tunnel Name</label>
                            <input value={form.name} onChange={e => setForm({ ...form, name: e.target.value })}
                                placeholder="my-tunnel" className="w-full bg-gray-700 border border-gray-600 rounded-lg p-2.5 text-white text-sm focus:border-blue-500 focus:outline-none" />
                        </div>
                        <div>
                            <label className="block text-gray-400 text-sm mb-1">Protocol</label>
                            <select value={form.protocol} onChange={e => setForm({ ...form, protocol: e.target.value })}
                                className="w-full bg-gray-700 border border-gray-600 rounded-lg p-2.5 text-white text-sm focus:border-blue-500 focus:outline-none">
                                <option value="tcp">TCP</option>
                                <option value="udp">UDP</option>
                                <option value="ws">WebSocket</option>
                                <option value="wss">WebSocket Secure</option>
                                <option value="relay+ws">Relay + WS</option>
                            </select>
                        </div>
                        <div>
                            <label className="block text-gray-400 text-sm mb-1">Mode</label>
                            <select value={form.mode} onChange={e => setForm({ ...form, mode: e.target.value })}
                                className="w-full bg-gray-700 border border-gray-600 rounded-lg p-2.5 text-white text-sm focus:border-blue-500 focus:outline-none">
                                <option value="server">Server (Iran Side)</option>
                                <option value="client">Client (Foreign Side)</option>
                            </select>
                        </div>
                    </div>

                    {/* Iran Server */}
                    <div>
                        <label className="block text-gray-400 text-sm mb-2 flex items-center gap-1">
                            🇮🇷 Iran Server
                        </label>
                        <div className="grid grid-cols-2 gap-4">
                            <input value={form.iran_server_ip} onChange={e => setForm({ ...form, iran_server_ip: e.target.value })}
                                placeholder="1.2.3.4" className="bg-gray-700 border border-gray-600 rounded-lg p-2.5 text-white text-sm focus:border-blue-500 focus:outline-none" />
                            <input type="number" value={form.iran_server_port} onChange={e => setForm({ ...form, iran_server_port: e.target.value })}
                                placeholder="8443" className="bg-gray-700 border border-gray-600 rounded-lg p-2.5 text-white text-sm focus:border-blue-500 focus:outline-none" />
                        </div>
                    </div>

                    {/* Foreign Server */}
                    <div>
                        <label className="block text-gray-400 text-sm mb-2 flex items-center gap-1">
                            🌍 Foreign Server
                        </label>
                        <div className="grid grid-cols-2 gap-4">
                            <input value={form.foreign_server_ip} onChange={e => setForm({ ...form, foreign_server_ip: e.target.value })}
                                placeholder="5.6.7.8" className="bg-gray-700 border border-gray-600 rounded-lg p-2.5 text-white text-sm focus:border-blue-500 focus:outline-none" />
                            <input type="number" value={form.foreign_server_port} onChange={e => setForm({ ...form, foreign_server_port: e.target.value })}
                                placeholder="8443" className="bg-gray-700 border border-gray-600 rounded-lg p-2.5 text-white text-sm focus:border-blue-500 focus:outline-none" />
                        </div>
                    </div>

                    {/* Forwarded Ports */}
                    <div>
                        <label className="block text-gray-400 text-sm mb-1">Forwarded Ports (comma-separated)</label>
                        <input value={form.forwarded_ports} onChange={e => setForm({ ...form, forwarded_ports: e.target.value })}
                            placeholder="443, 8080, 2096" className="w-full bg-gray-700 border border-gray-600 rounded-lg p-2.5 text-white text-sm focus:border-blue-500 focus:outline-none" />
                    </div>

                    {/* Anti-Censorship */}
                    <div className="flex gap-4">
                        <label className="flex items-center gap-2 cursor-pointer">
                            <input type="checkbox" checked={form.domain_fronting_enabled} onChange={e => setForm({ ...form, domain_fronting_enabled: e.target.checked })}
                                className="w-4 h-4 rounded border-gray-600 bg-gray-700 text-blue-600 focus:ring-blue-500" />
                            <span className="text-gray-300 text-sm">Domain Fronting</span>
                        </label>
                        <label className="flex items-center gap-2 cursor-pointer">
                            <input type="checkbox" checked={form.tls_obfuscation} onChange={e => setForm({ ...form, tls_obfuscation: e.target.checked })}
                                className="w-4 h-4 rounded border-gray-600 bg-gray-700 text-blue-600 focus:ring-blue-500" />
                            <span className="text-gray-300 text-sm">TLS Obfuscation</span>
                        </label>
                    </div>

                    {form.domain_fronting_enabled && (
                        <input value={form.domain_fronting_domain} onChange={e => setForm({ ...form, domain_fronting_domain: e.target.value })}
                            placeholder="cloudflare.com" className="w-full bg-gray-700 border border-gray-600 rounded-lg p-2.5 text-white text-sm focus:border-blue-500 focus:outline-none" />
                    )}
                </div>

                <div className="p-6 border-t border-gray-700 flex justify-end gap-3">
                    <button onClick={onClose} className="px-5 py-2.5 bg-gray-700 hover:bg-gray-600 text-gray-300 rounded-lg text-sm font-medium transition-colors">Cancel</button>
                    <button onClick={handleCreate} disabled={creating}
                        className="px-6 py-2.5 bg-green-600 hover:bg-green-700 text-white rounded-lg text-sm font-bold flex items-center gap-2 transition-colors disabled:opacity-50">
                        <Plus size={16} /> {creating ? 'Creating...' : 'Create Tunnel'}
                    </button>
                </div>
            </div>
        </div>
    );
};

// ===== Tunnel Status Card =====
const TunnelCard = ({ tunnel, onRefresh }) => {
    const [status, setStatus] = useState(null);
    const [loading, setLoading] = useState(false);
    const [expanded, setExpanded] = useState(false);

    const colors = TUNNEL_COLORS[tunnel.tunnel_type] || TUNNEL_COLORS.backhaul;
    const icon = TUNNEL_ICONS[tunnel.tunnel_type] || '🔗';

    const loadStatus = async () => {
        try {
            const res = await apiService.getTunnelStatus(tunnel.id);
            setStatus(res.data);
        } catch { }
    };

    useEffect(() => {
        loadStatus();
        const iv = setInterval(loadStatus, 15000);
        return () => clearInterval(iv);
    }, [tunnel.id]);

    const isActive = tunnel.is_active || status?.running;

    const handleAction = async (action) => {
        setLoading(true);
        try {
            if (action === 'start') await apiService.startTunnel(tunnel.id);
            if (action === 'stop') await apiService.stopTunnel(tunnel.id);
            if (action === 'restart') await apiService.restartTunnel(tunnel.id);
            if (action === 'delete') {
                if (!window.confirm(`Delete tunnel "${tunnel.name}"?`)) { setLoading(false); return; }
                await apiService.deleteTunnel(tunnel.id);
            }
            onRefresh();
        } catch (e) {
            alert(`❌ ${e.response?.data?.detail || e.message}`);
        } finally { setLoading(false); }
    };

    return (
        <div className={`bg-gray-800 rounded-xl border-l-4 ${colors.border} shadow-lg overflow-hidden`}>
            <div className="p-5">
                <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-3">
                        <span className="text-2xl">{icon}</span>
                        <div>
                            <h3 className="text-white font-bold text-base">{tunnel.name}</h3>
                            <span className={`text-xs font-semibold uppercase ${colors.text}`}>{tunnel.tunnel_type}</span>
                        </div>
                    </div>
                    <div className="flex items-center gap-2">
                        <span className={`w-2.5 h-2.5 rounded-full ${isActive ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`}></span>
                        <span className={`text-xs font-medium px-2.5 py-1 rounded-full ${isActive ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
                            {isActive ? 'Active' : tunnel.status || 'Inactive'}
                        </span>
                    </div>
                </div>

                <div className="grid grid-cols-2 gap-3 text-sm mb-3">
                    <div className="bg-gray-900/50 rounded-lg p-2.5">
                        <span className="text-gray-500 text-xs">🇮🇷 Iran</span>
                        <p className="text-white font-mono text-xs mt-0.5">{tunnel.iran_server_ip}:{tunnel.iran_server_port}</p>
                    </div>
                    <div className="bg-gray-900/50 rounded-lg p-2.5">
                        <span className="text-gray-500 text-xs">🌍 Foreign</span>
                        <p className="text-white font-mono text-xs mt-0.5">{tunnel.foreign_server_ip}:{tunnel.foreign_server_port}</p>
                    </div>
                </div>

                {tunnel.forwarded_ports && tunnel.forwarded_ports.length > 0 && (
                    <div className="flex gap-1 flex-wrap mb-3">
                        <span className="text-[10px] text-gray-500 mr-1">Ports:</span>
                        {tunnel.forwarded_ports.map(p => (
                            <span key={p} className="text-[10px] bg-gray-700 text-gray-300 px-1.5 py-0.5 rounded">{p}</span>
                        ))}
                    </div>
                )}

                {/* Actions */}
                <div className="flex gap-2">
                    {isActive ? (
                        <button onClick={() => handleAction('stop')} disabled={loading}
                            className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 bg-red-600/20 hover:bg-red-600/30 text-red-400 rounded-lg text-xs font-medium transition-colors border border-red-600/30">
                            <Square size={12} /> Stop
                        </button>
                    ) : (
                        <button onClick={() => handleAction('start')} disabled={loading}
                            className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 bg-green-600/20 hover:bg-green-600/30 text-green-400 rounded-lg text-xs font-medium transition-colors border border-green-600/30">
                            <Play size={12} /> Start
                        </button>
                    )}
                    <button onClick={() => handleAction('restart')} disabled={loading}
                        className="flex items-center justify-center gap-1.5 px-3 py-2 bg-blue-600/20 hover:bg-blue-600/30 text-blue-400 rounded-lg text-xs font-medium transition-colors border border-blue-600/30">
                        <RotateCw size={12} />
                    </button>
                    <button onClick={loadStatus}
                        className="flex items-center justify-center gap-1.5 px-3 py-2 bg-gray-700 hover:bg-gray-600 text-gray-300 rounded-lg text-xs font-medium transition-colors">
                        <RefreshCw size={12} />
                    </button>
                    <button onClick={() => handleAction('delete')} disabled={loading}
                        className="flex items-center justify-center gap-1.5 px-3 py-2 bg-red-600/20 hover:bg-red-600/30 text-red-400 rounded-lg text-xs font-medium transition-colors border border-red-600/30">
                        <Trash2 size={12} />
                    </button>
                </div>

                {/* Extra flags */}
                {(tunnel.domain_fronting_enabled || tunnel.tls_obfuscation) && (
                    <div className="flex gap-2 mt-2">
                        {tunnel.domain_fronting_enabled && <span className="text-[10px] bg-amber-500/20 text-amber-400 px-2 py-0.5 rounded">🛡️ Domain Fronting</span>}
                        {tunnel.tls_obfuscation && <span className="text-[10px] bg-blue-500/20 text-blue-400 px-2 py-0.5 rounded">🔒 TLS Obfuscation</span>}
                    </div>
                )}
            </div>
        </div>
    );
};


// ===== Tunnel Store Card =====
const TunnelStoreCard = ({ info, onInstall, onUninstall }) => {
    const [installing, setInstalling] = useState(false);
    const colors = TUNNEL_COLORS[info.id] || TUNNEL_COLORS.backhaul;
    const icon = TUNNEL_ICONS[info.id] || '🔗';

    const handle = async (action) => {
        setInstalling(true);
        try {
            if (action === 'install') {
                await apiService.installTunnel(info.id);
                alert(`✅ ${info.name} installed!`);
            } else {
                await apiService.uninstallTunnel(info.id);
                alert(`✅ ${info.name} uninstalled`);
            }
            if (action === 'install') onInstall?.();
            else onUninstall?.();
        } catch (e) {
            alert(`❌ ${e.response?.data?.detail || e.message}`);
        } finally { setInstalling(false); }
    };

    return (
        <div className={`bg-gray-800 rounded-xl border ${colors.border} overflow-hidden`}>
            <div className={`${colors.bg} p-4 border-b ${colors.border}`}>
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <span className="text-3xl">{icon}</span>
                        <div>
                            <h3 className="text-white font-bold">{info.name}</h3>
                            <span className="text-gray-400 text-xs">{info.language} • by {info.author}</span>
                        </div>
                    </div>
                    {info.iran_recommended && (
                        <span className="text-[10px] bg-amber-500/20 text-amber-400 px-2 py-1 rounded font-bold">🇮🇷 IRAN</span>
                    )}
                </div>
            </div>
            <div className="p-4">
                <p className="text-gray-400 text-sm mb-3">{info.description}</p>
                <div className="flex gap-1.5 flex-wrap mb-3">
                    {info.protocols?.map((p, i) => (
                        <span key={i} className="text-[10px] bg-gray-700 text-gray-300 px-2 py-0.5 rounded uppercase">{p}</span>
                    ))}
                </div>
                <div className="flex gap-1.5 flex-wrap mb-4">
                    {info.features?.map((f, i) => (
                        <span key={i} className={`text-[10px] ${colors.bg} ${colors.text} px-2 py-0.5 rounded`}>{f}</span>
                    ))}
                </div>
                <div className="flex gap-2 items-center">
                    {info.installed ? (
                        <>
                            <span className="flex items-center gap-1.5 text-green-400 text-xs font-medium">
                                <span className="w-2 h-2 bg-green-500 rounded-full"></span> Installed
                            </span>
                            {info.id !== 'persianshield' && (
                                <button onClick={() => handle('uninstall')} disabled={installing}
                                    className="ml-auto px-3 py-1.5 bg-red-600/20 hover:bg-red-600/30 text-red-400 rounded text-xs font-medium border border-red-600/30 transition-colors disabled:opacity-50">
                                    {installing ? '...' : 'Uninstall'}
                                </button>
                            )}
                        </>
                    ) : (
                        <button onClick={() => handle('install')} disabled={installing}
                            className="w-full px-4 py-2.5 bg-green-600 hover:bg-green-700 text-white rounded-lg text-sm font-bold flex items-center justify-center gap-2 transition-colors disabled:opacity-50">
                            <Download size={14} /> {installing ? 'Installing...' : 'Install on Server'}
                        </button>
                    )}
                    {info.repo && info.repo !== 'Built-in' && (
                        <a href={info.repo} target="_blank" rel="noreferrer"
                            className="ml-auto text-gray-500 hover:text-gray-300 transition-colors">
                            <ExternalLink size={14} />
                        </a>
                    )}
                </div>
            </div>
        </div>
    );
};


// ===== Main Component =====
const Tunnels = () => {
    const [tunnels, setTunnels] = useState([]);
    const [availableTunnels, setAvailableTunnels] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showCreateModal, setShowCreateModal] = useState(false);
    const [activeView, setActiveView] = useState('tunnels'); // 'tunnels' | 'store'

    useEffect(() => {
        loadAll();
    }, []);

    const loadAll = async () => {
        setLoading(true);
        try {
            const [tunnelsRes, availableRes] = await Promise.all([
                apiService.getTunnels(),
                apiService.getAvailableTunnels(),
            ]);
            setTunnels(tunnelsRes.data);
            setAvailableTunnels(availableRes.data);
        } catch (e) {
            console.error('Failed to load:', e);
        } finally { setLoading(false); }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-screen">
                <div className="animate-spin rounded-full h-16 w-16 border-t-2 border-b-2 border-green-500"></div>
            </div>
        );
    }

    return (
        <div className="p-6 max-w-6xl mx-auto">
            {/* Header */}
            <div className="flex items-center justify-between mb-6">
                <div>
                    <h1 className="text-3xl font-bold text-white flex items-center gap-3">
                        <Globe className="text-green-400" size={32} /> Tunnel Management
                    </h1>
                    <p className="text-gray-400 mt-1">Install, configure, and manage Iran-Foreign tunnels</p>
                </div>
                <div className="flex gap-3">
                    <button onClick={loadAll} className="p-2.5 bg-gray-700 hover:bg-gray-600 text-gray-300 rounded-lg transition-colors">
                        <RefreshCw size={18} />
                    </button>
                    <button onClick={() => setShowCreateModal(true)}
                        className="flex items-center gap-2 px-5 py-2.5 bg-green-600 hover:bg-green-700 text-white rounded-lg font-bold text-sm transition-colors shadow-lg">
                        <Plus size={18} /> Create Tunnel
                    </button>
                </div>
            </div>

            {/* Tab Switcher */}
            <div className="flex gap-2 mb-6">
                <button onClick={() => setActiveView('tunnels')}
                    className={`px-5 py-2.5 rounded-lg text-sm font-semibold transition-all ${activeView === 'tunnels' ? 'bg-green-600 text-white shadow-lg' : 'bg-gray-800 text-gray-400 hover:text-white border border-gray-700'}`}>
                    <Activity className="w-4 h-4 inline mr-2" />Active Tunnels ({tunnels.length})
                </button>
                <button onClick={() => setActiveView('store')}
                    className={`px-5 py-2.5 rounded-lg text-sm font-semibold transition-all ${activeView === 'store' ? 'bg-blue-600 text-white shadow-lg' : 'bg-gray-800 text-gray-400 hover:text-white border border-gray-700'}`}>
                    <Download className="w-4 h-4 inline mr-2" />Tunnel Store ({availableTunnels.length})
                </button>
            </div>

            {/* Active Tunnels View */}
            {activeView === 'tunnels' && (
                <>
                    {tunnels.length === 0 ? (
                        <div className="bg-gray-800 rounded-2xl border border-gray-700 p-16 text-center">
                            <Globe className="mx-auto text-gray-600 mb-4" size={64} />
                            <h2 className="text-2xl font-bold text-white mb-2">No Active Tunnels</h2>
                            <p className="text-gray-400 mb-6">Install a tunnel from the Store, then create your first Iran-Foreign tunnel.</p>
                            <div className="flex justify-center gap-3">
                                <button onClick={() => setActiveView('store')}
                                    className="flex items-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors">
                                    <Download size={18} /> Go to Tunnel Store
                                </button>
                                <button onClick={() => setShowCreateModal(true)}
                                    className="flex items-center gap-2 px-6 py-3 bg-green-600 hover:bg-green-700 text-white rounded-lg font-medium transition-colors">
                                    <Plus size={18} /> Create Tunnel
                                </button>
                            </div>
                        </div>
                    ) : (
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                            {tunnels.map(tunnel => (
                                <TunnelCard key={tunnel.id} tunnel={tunnel} onRefresh={loadAll} />
                            ))}
                        </div>
                    )}
                </>
            )}

            {/* Tunnel Store View */}
            {activeView === 'store' && (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                    {availableTunnels.map(info => (
                        <TunnelStoreCard key={info.id} info={info} onInstall={loadAll} onUninstall={loadAll} />
                    ))}
                </div>
            )}

            {/* Create Modal */}
            <CreateTunnelModal
                show={showCreateModal}
                onClose={() => setShowCreateModal(false)}
                onCreated={loadAll}
                availableTunnels={availableTunnels}
            />
        </div>
    );
};

export default Tunnels;
