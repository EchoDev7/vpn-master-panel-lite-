import { useState, useEffect } from 'react';
import { Activity, Shield, Server, Box, AlertTriangle, CheckCircle, RefreshCw, Terminal, GitBranch, Globe, Database, Link, Clock } from 'lucide-react';
import apiService from '../services/api';

export default function Diagnostics() {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [showLiveLogs, setShowLiveLogs] = useState(false);
    const [liveLogs, setLiveLogs] = useState({ openvpn: [], auth: [] });
    const [lastUpdated, setLastUpdated] = useState(null);

    const fetchDiagnostics = async () => {
        try {
            // Only set loading on first load to avoid flickering
            if (!data) setLoading(true);
            const response = await apiService.getFullDiagnostics();
            setData(response.data);
            setLastUpdated(new Date());
            setError(null);
        } catch (err) {
            console.error('Failed to fetch diagnostics:', err);
            if (err.response && err.response.status === 401) {
                setError('Session expired. Please login again.');
            } else {
                setError('Failed to load diagnostics data. Please try again.');
            }
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchDiagnostics();
        const interval = setInterval(fetchDiagnostics, 10000); // Auto-refresh every 10s
        return () => clearInterval(interval);
    }, []);

    useEffect(() => {
        let interval;
        if (showLiveLogs) {
            const fetchLive = async () => {
                try {
                    const res = await apiService.getLiveLogs(50);
                    setLiveLogs(res.data);
                } catch (e) {
                    console.error("Live logs error", e);
                }
            };
            fetchLive();
            interval = setInterval(fetchLive, 2000);
        }
        return () => clearInterval(interval);
    }, [showLiveLogs]);

    if (loading && !data) {
        return (
            <div className="flex items-center justify-center min-h-screen">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
            </div>
        );
    }

    if (error && !data) {
        return (
            <div className="min-h-screen flex items-center justify-center text-red-400">
                <div className="text-center">
                    <AlertTriangle className="w-12 h-12 mx-auto mb-4" />
                    <p>{error}</p>
                    <button
                        onClick={fetchDiagnostics}
                        className="mt-4 px-4 py-2 bg-blue-600 rounded-lg hover:bg-blue-700 text-white"
                    >
                        Retry
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-6 pb-12">
            {/* Header */}
            <div className="flex justify-between items-center bg-gray-800/50 p-6 rounded-xl border border-gray-700 backdrop-blur-sm">
                <div>
                    <h1 className="text-2xl font-bold text-white flex items-center gap-2">
                        <Activity className="w-8 h-8 text-cyan-400" />
                        VPN Master Panel Diagnostics
                    </h1>
                    <p className="text-gray-400 mt-1">Ultimate System Diagnostics & Health Report</p>
                </div>
                <div className="flex items-center gap-4">
                    <button
                        onClick={() => setShowLiveLogs(!showLiveLogs)}
                        className={`hidden md:flex px-4 py-2 rounded-lg font-bold items-center gap-2 transition-all ${showLiveLogs ? 'bg-red-600/20 text-red-400 border border-red-500 animate-pulse' : 'bg-gray-700 hover:bg-gray-600 text-white'}`}
                    >
                        {showLiveLogs ? <span className="flex items-center gap-2"><div className="w-2 h-2 bg-red-500 rounded-full animate-ping"></div> Stop Live Monitor</span> : <span className="flex items-center gap-2"><Terminal className="w-4 h-4" /> Live Debugger</span>}
                    </button>
                    <span className="text-sm text-gray-400 font-mono hidden md:block">
                        {lastUpdated ? `Report Time: ${lastUpdated.toLocaleTimeString()}` : ''}
                    </span>
                    <button
                        onClick={fetchDiagnostics}
                        className={`p-2 rounded-lg bg-gray-700 hover:bg-gray-600 transition-colors ${loading ? 'animate-spin' : ''}`}
                    >
                        <RefreshCw className="w-5 h-5 text-cyan-400" />
                    </button>
                </div>
            </div>

            {/* Live Logs Section */}
            {showLiveLogs && (
                <div className="bg-black rounded-xl border-2 border-cyan-500/50 shadow-2xl overflow-hidden animate-in fade-in slide-in-from-top-4 duration-300">
                    <div className="bg-gray-900/80 p-4 border-b border-gray-800 flex justify-between items-center">
                        <h3 className="text-cyan-400 font-bold flex items-center gap-2 animate-pulse">
                            <Activity className="w-5 h-5" /> Live Connection Monitor (Real-time)
                        </h3>
                        <span className="text-xs text-gray-500 font-mono">Auto-refreshing every 2s</span>
                    </div>
                    <div className="grid grid-cols-1 lg:grid-cols-2 divide-y lg:divide-y-0 lg:divide-x divide-gray-800 h-96">
                        <div className="flex flex-col">
                            <div className="p-2 bg-gray-900/50 text-xs font-bold text-gray-400 border-b border-gray-800">System Logs (OpenVPN Service)</div>
                            <div className="flex-1 p-4 overflow-y-auto font-mono text-xs text-green-400/90 whitespace-pre-wrap">
                                {liveLogs.openvpn?.join('\n') || "Waiting for logs..."}
                            </div>
                        </div>
                        <div className="flex flex-col">
                            <div className="p-2 bg-gray-900/50 text-xs font-bold text-gray-400 border-b border-gray-800">Authentication Logs (User Auth)</div>
                            <div className="flex-1 p-4 overflow-y-auto font-mono text-xs text-yellow-400/90 whitespace-pre-wrap">
                                {liveLogs.auth?.join('\n') || "No authentication attempts recorded yet."}
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* 1. System & OS Resources */}
            <div className="bg-gray-800/50 p-6 rounded-xl border border-gray-700 backdrop-blur-sm">
                <h3 className="text-yellow-400 font-bold mb-4 flex items-center gap-2">
                    📊 1. System & OS Resources
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                    <div className="bg-gray-900/50 p-3 rounded border border-gray-800">
                        <span className="text-gray-400 block text-xs uppercase mb-1">OS</span>
                        <span className="text-cyan-400 font-mono text-sm">{data.system.os || 'Unknown'}</span>
                    </div>
                    <div className="bg-gray-900/50 p-3 rounded border border-gray-800">
                        <span className="text-gray-400 block text-xs uppercase mb-1">Kernel</span>
                        <span className="text-cyan-400 font-mono text-sm">{data.system.kernel || 'Unknown'}</span>
                    </div>
                    <div className="bg-gray-900/50 p-3 rounded border border-gray-800">
                        <span className="text-gray-400 block text-xs uppercase mb-1">Uptime</span>
                        <span className="text-cyan-400 font-mono text-sm">{data.system.uptime || 'Unknown'}</span>
                    </div>
                    <div className="bg-gray-900/50 p-3 rounded border border-gray-800">
                        <span className="text-gray-400 block text-xs uppercase mb-1">Load Average</span>
                        <span className="text-cyan-400 font-mono text-sm">{data.system.load_avg.map(l => l.toFixed(2)).join(', ')}</span>
                    </div>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
                    <div className="bg-gray-900/50 p-3 rounded border border-gray-800">
                        <div className="flex justify-between items-center mb-1">
                            <span className="text-gray-400 text-xs uppercase">Memory</span>
                            <span className={`text-xs font-bold ${data.system.memory.percent > 90 ? 'text-red-400' : 'text-green-400'}`}>
                                [{data.system.memory.percent > 90 ? 'FAIL' : 'OK'}]
                            </span>
                        </div>
                        <div className="w-full bg-gray-700 h-2 rounded-full overflow-hidden mb-1">
                            <div className={`h-full ${data.system.memory.percent > 90 ? 'bg-red-500' : 'bg-green-500'}`} style={{ width: `${data.system.memory.percent}%` }}></div>
                        </div>
                        <span className="text-white font-mono text-sm">{data.system.memory.used_mb}MB / {data.system.memory.total_mb}MB ({data.system.memory.percent}%)</span>
                    </div>
                    <div className="bg-gray-900/50 p-3 rounded border border-gray-800">
                        <div className="flex justify-between items-center mb-1">
                            <span className="text-gray-400 text-xs uppercase">Disk (/)</span>
                            <span className={`text-xs font-bold ${data.system.disk.percent > 90 ? 'text-red-400' : 'text-green-400'}`}>
                                [{data.system.disk.percent > 90 ? 'FAIL' : 'OK'}]
                            </span>
                        </div>
                        <div className="w-full bg-gray-700 h-2 rounded-full overflow-hidden mb-1">
                            <div className={`h-full ${data.system.disk.percent > 90 ? 'bg-red-500' : 'bg-green-500'}`} style={{ width: `${data.system.disk.percent}%` }}></div>
                        </div>
                        <span className="text-white font-mono text-sm">{data.system.disk.used_gb}GB / {data.system.disk.total_gb}GB ({data.system.disk.percent}%)</span>
                    </div>
                </div>
            </div>

            {/* 2. Network & Connectivity */}
            <div className="bg-gray-800/50 p-6 rounded-xl border border-gray-700 backdrop-blur-sm">
                <h3 className="text-yellow-400 font-bold mb-4 flex items-center gap-2">
                    📡 2. Network & Connectivity
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="space-y-2 text-sm font-mono">
                        <div className="flex justify-between border-b border-gray-700 pb-1">
                            <span className="text-gray-400">Public IPv4</span>
                            <span className="text-green-400">{data.network?.public_ipv4}</span>
                        </div>
                        <div className="flex justify-between border-b border-gray-700 pb-1">
                            <span className="text-gray-400">Public IPv6</span>
                            <span className="text-green-400">{data.network?.public_ipv6}</span>
                        </div>
                        <div className="flex justify-between border-b border-gray-700 pb-1">
                            <span className="text-gray-400">Latency (Google)</span>
                            <span className={`font-bold ${data.network?.latency === 'Timeout' ? 'text-red-400' : 'text-green-400'}`}>
                                {data.network?.latency}
                            </span>
                        </div>
                        <div className="flex justify-between border-b border-gray-700 pb-1">
                            <span className="text-gray-400">Firewall</span>
                            <span className="text-green-400">{data.network?.firewall_status}</span>
                        </div>
                    </div>
                    <div>
                        <span className="text-cyan-400 block mb-2 text-sm font-bold">Active Listening Ports:</span>
                        <div className="bg-gray-900/50 p-3 rounded border border-gray-800 font-mono text-xs h-32 overflow-y-auto">
                            {data.network?.listening_ports.map((p, i) => (
                                <div key={i} className="text-gray-300">{p}</div>
                            ))}
                        </div>
                    </div>
                </div>
            </div>

            {/* 3. Core Services Status */}
            <div className="bg-gray-800/50 p-6 rounded-xl border border-gray-700 backdrop-blur-sm">
                <h3 className="text-yellow-400 font-bold mb-4 flex items-center gap-2">
                    ⚙️ 3. Core Services Status
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                    {data.services.map((svc) => (
                        <div key={svc.name} className="flex items-center justify-between bg-gray-900/30 p-3 rounded border border-gray-700">
                            <span className="text-gray-300 text-sm">{svc.name}</span>
                            <span className={`px-2 py-0.5 rounded text-xs font-bold ${svc.status === 'Running' ? 'bg-green-900/50 text-green-400' :
                                svc.status === 'Failed' ? 'bg-red-900/50 text-red-400' : 'bg-yellow-900/50 text-yellow-400'
                                }`}>
                                {svc.status.toUpperCase()}
                            </span>
                        </div>
                    ))}
                </div>
            </div>

            {/* 4. Installed Packages & Updates */}
            <div className="bg-gray-800/50 p-6 rounded-xl border border-gray-700 backdrop-blur-sm">
                <h3 className="text-yellow-400 font-bold mb-4 flex items-center gap-2">
                    📦 4. Installed Packages & Updates
                </h3>
                <div className="overflow-x-auto">
                    <table className="w-full text-sm font-mono text-left">
                        <thead className="text-gray-500 border-b border-gray-600 bg-gray-900/30">
                            <tr>
                                <th className="p-3">PACKAGE</th>
                                <th className="p-3">INSTALLED</th>
                                <th className="p-3">LATEST AVAILABLE</th>
                                <th className="p-3">STATUS</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-700/50">
                            {data.packages.map((pkg) => (
                                <tr key={pkg.name} className="hover:bg-gray-700/10">
                                    <td className="p-3 text-cyan-400 font-bold">{pkg.name}</td>
                                    <td className="p-3 text-gray-300">{pkg.installed}</td>
                                    <td className="p-3 text-gray-400">{pkg.latest}</td>
                                    <td className="p-3">
                                        <span className={pkg.status === 'OK' || pkg.status === 'Up to date' ? 'text-green-400 font-bold' : 'text-yellow-400 font-bold'}>
                                            {pkg.status}
                                        </span>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* 5. Recommended Tools */}
            <div className="bg-gray-800/50 p-6 rounded-xl border border-gray-700 backdrop-blur-sm">
                <h3 className="text-yellow-400 font-bold mb-4 flex items-center gap-2">
                    🛠️ 5. Recommended Professional Tools
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                    {data.recommendations.map((tool) => (
                        <div key={tool.name} className="flex justify-between items-center text-sm font-mono bg-gray-900/20 p-2 rounded border border-gray-700">
                            <span className="text-gray-300">{tool.name}</span>
                            <span className={tool.installed ? "text-green-400 font-bold text-xs" : "text-yellow-400 font-bold text-xs"}>
                                [{tool.installed ? "INSTALLED" : "MISSING"}]
                            </span>
                        </div>
                    ))}
                </div>
            </div>

            {/* 6. VPN Configuration & Security */}
            <div className="bg-gray-800/50 p-6 rounded-xl border border-gray-700 backdrop-blur-sm">
                <h3 className="text-yellow-400 font-bold mb-4 flex items-center gap-2">
                    🔒 6. VPN Configuration & Security
                </h3>
                <div className="space-y-2 text-sm font-mono">
                    <div className="flex justify-between border-b border-gray-700 pb-1">
                        <span className="text-gray-400">TUN Device</span>
                        <span className={data.vpn_security.tun_available ? "text-green-400 font-bold" : "text-red-400 font-bold"}>
                            [{data.vpn_security.tun_available ? "OK" : "FAIL"}] Available
                        </span>
                    </div>
                    <div className="flex justify-between border-b border-gray-700 pb-1">
                        <span className="text-gray-400">IPv4 Forwarding</span>
                        <span className={data.vpn_security.ip_forwarding ? "text-green-400 font-bold" : "text-red-400 font-bold"}>
                            [{data.vpn_security.ip_forwarding ? "OK" : "FAIL"}] Enabled
                        </span>
                    </div>
                    <div className="flex justify-between border-b border-gray-700 pb-1">
                        <span className="text-gray-400">Cert Expiry</span>
                        <span className="text-green-400 font-bold">[OK] {data.vpn_security.cert_expiry}</span>
                    </div>
                </div>
            </div>

            {/* 7. Application & Database Connectivity */}
            <div className="bg-gray-800/50 p-6 rounded-xl border border-gray-700 backdrop-blur-sm">
                <h3 className="text-yellow-400 font-bold mb-4 flex items-center gap-2">
                    🔌 7. Application & Connectivity
                </h3>
                <div className="space-y-2 text-sm font-mono mb-4">
                    <div className="flex justify-between border-b border-gray-700 pb-1">
                        <span className="text-gray-400">Backend Port (8001)</span>
                        <span className={data.network?.listening_ports.some(p => p.includes('8001')) ? "text-green-400 font-bold" : "text-red-400 font-bold"}>
                            [{data.network?.listening_ports.some(p => p.includes('8001')) ? "OK" : "FAIL"}] Open
                        </span>
                    </div>
                    <div className="flex justify-between border-b border-gray-700 pb-1">
                        <span className="text-gray-400">Frontend Port (3000)</span>
                        <span className={data.network?.listening_ports.some(p => p.includes('3000')) ? "text-green-400 font-bold" : "text-red-400 font-bold"}>
                            [{data.network?.listening_ports.some(p => p.includes('3000')) ? "OK" : "FAIL"}] Open
                        </span>
                    </div>
                </div>

                <div className="bg-gray-900/30 p-4 rounded border border-gray-700">
                    <h4 className="text-cyan-400 mb-2 font-bold flex items-center gap-2">
                        <Database className="w-4 h-4" /> Deep Database Diagnostics
                    </h4>
                    <div className="space-y-1 text-xs font-mono pl-2">
                        <div className="flex justify-between">
                            <span className="text-gray-400">Integrity Check</span>
                            <span className={data.database.integrity === 'OK' ? "text-green-400" : "text-red-400"}>[{data.database.integrity}]</span>
                        </div>
                        <div className="flex justify-between">
                            <span className="text-gray-400">Core Tables</span>
                            <span className={data.database.status === 'OK' ? "text-green-400" : "text-red-400"}>
                                [{data.database.status === 'OK' ? "OK" : "FAIL"}] {data.database.status === 'OK' ? "All Present" : "Missing Tables"}
                            </span>
                        </div>
                        <div className="flex justify-between">
                            <span className="text-gray-400">Admin User</span>
                            <span className={data.database.admin_user !== 'MISSING' ? "text-green-400" : "text-red-400"}>
                                [{data.database.admin_user !== 'MISSING' ? "OK" : "FAIL"}] {data.database.admin_user}
                            </span>
                        </div>
                    </div>
                </div>
            </div>

            {/* 8. API Health Check */}
            <div className="bg-gray-800/50 p-6 rounded-xl border border-gray-700 backdrop-blur-sm">
                <h3 className="text-yellow-400 font-bold mb-4 flex items-center gap-2">
                    🔗 8. API Health Check
                </h3>
                <div className="space-y-2 text-sm font-mono">
                    {data.api_health?.map((api) => (
                        <div key={api.endpoint} className="flex justify-between border-b border-gray-700 pb-1">
                            <span className="text-gray-400">{api.endpoint}</span>
                            <span className={api.status === 'Available' || api.status === 'Secure/Active' ? "text-green-400 font-bold" : "text-red-400 font-bold"}>
                                [{api.status === 'Available' || api.status === 'Secure/Active' ? "OK" : "FAIL"}] {api.status} ({api.code})
                            </span>
                        </div>
                    ))}
                    {(!data.api_health || data.api_health.length === 0) && <span className="text-gray-500">No API health data available.</span>}
                </div>
            </div>

            {/* 9. Project Status */}
            <div className="bg-gray-800/50 p-6 rounded-xl border border-gray-700 backdrop-blur-sm">
                <h3 className="text-yellow-400 font-bold mb-4 flex items-center gap-2">
                    💻 9. Project Git Status
                </h3>
                <div className="space-y-2 text-sm font-mono">
                    <div className="flex justify-between border-b border-gray-700 pb-1">
                        <span className="text-gray-400">Branch/Commit</span>
                        <span className="text-cyan-400 text-right">{data.project.branch} / {data.project.commit}</span>
                    </div>
                    <div className="border-b border-gray-700 pb-1">
                        <span className="text-gray-400 block">Latest Change</span>
                        <span className="text-cyan-400 truncate block opacity-75">{data.project.last_message}</span>
                    </div>
                    <div className="flex justify-between border-b border-gray-700 pb-1">
                        <span className="text-gray-400">File Status</span>
                        {data.project.uncommitted_changes > 0 ? (
                            <span className="text-yellow-400 font-bold">⚠️ Uncommitted Changes Detected</span>
                        ) : (
                            <span className="text-green-400 font-bold">Clean</span>
                        )}
                    </div>
                </div>
            </div>

            {/* 10. Intelligent Log Analysis */}
            <div className="bg-gray-800/50 rounded-xl border border-gray-700 backdrop-blur-sm overflow-hidden">
                <div className="p-6 border-b border-gray-700">
                    <h3 className="text-cyan-400 font-bold flex items-center gap-2">
                        🧠 10. Intelligent Log Analysis
                    </h3>
                </div>
                <div className="p-6">
                    {data.logs && data.logs.length > 0 && data.logs[0].level !== 'OK' ? (
                        <div className="space-y-4">
                            {data.logs.map((log, index) => (
                                <div key={index} className={`p-4 rounded-lg border ${log.level === 'CRITICAL' ? 'bg-red-900/20 border-red-700 text-red-200' :
                                    log.level === 'ERROR' ? 'bg-orange-900/20 border-orange-700 text-orange-200' :
                                        log.level === 'WARN' ? 'bg-yellow-900/20 border-yellow-700 text-yellow-200' :
                                            'bg-green-900/20 border-green-700 text-green-200'
                                    }`}>
                                    <div>
                                        <h4 className="font-bold">[{log.level}] {log.message}</h4>
                                        {log.fix && <p className="mt-1 text-sm text-yellow-400">💡 Fix: {log.fix}</p>}
                                    </div>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <div className="text-center py-4 text-green-400 font-mono font-bold">
                            [OK] No critical error patterns detected in recent logs.
                        </div>
                    )}

                    <div className="mt-6 border-t border-gray-700 pt-4">
                        <h4 className="text-cyan-400 font-bold mb-2">💡 Quick Fixes:</h4>
                        <ul className="list-disc list-inside text-sm text-gray-300 space-y-1 font-mono">
                            <li>OpenVPN Flapping? <span className="text-yellow-400">./update.sh (Fixes PKI/Config)</span></li>
                            <li>Backend Restart? <span className="text-yellow-400">systemctl restart vpnmaster-backend</span></li>
                        </ul>
                    </div>
                </div>
            </div>

            {/* 11 & 12. Raw Logs */}
            <div className="bg-black rounded-xl border border-gray-800 overflow-hidden font-mono text-xs">
                <div className="p-3 bg-gray-900 border-b border-gray-800 text-yellow-400 font-bold">
                    📜 11. Recent OpenVPN Logs (Last 10 Lines)
                </div>
                <div className="p-4 text-gray-300 overflow-x-auto whitespace-pre leading-relaxed select-text">
                    {data.raw_logs?.openvpn?.join('\n') || "No logs available."}
                </div>
                <div className="p-3 bg-gray-900 border-b border-gray-800 border-t text-yellow-400 font-bold mt-2">
                    📜 12. Recent Backend Logs (Last 10 Lines)
                </div>
                <div className="p-4 text-gray-300 overflow-x-auto whitespace-pre leading-relaxed select-text">
                    {data.raw_logs?.backend?.join('\n') || "No logs available."}
                </div>
            </div>
        </div>
    );
}
