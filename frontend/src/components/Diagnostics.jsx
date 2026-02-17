import { useState, useEffect } from 'react';
import { Activity, Shield, Server, Box, AlertTriangle, CheckCircle, RefreshCw, Terminal, GitBranch } from 'lucide-react';
import apiService from '../services/api';

export default function Diagnostics() {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [lastUpdated, setLastUpdated] = useState(null);

    const fetchDiagnostics = async () => {
        try {
            setLoading(true);
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
        <div className="space-y-6">
            {/* Header */}
            <div className="flex justify-between items-center bg-gray-800/50 p-6 rounded-xl border border-gray-700 backdrop-blur-sm">
                <div>
                    <h1 className="text-2xl font-bold text-white flex items-center gap-2">
                        <Activity className="w-8 h-8 text-blue-400" />
                        System Diagnostics
                    </h1>
                    <p className="text-gray-400 mt-1">Real-time system health and version monitoring</p>
                </div>
                <div className="flex items-center gap-4">
                    <span className="text-sm text-gray-400">
                        {lastUpdated ? `Last updated: ${lastUpdated.toLocaleTimeString()}` : ''}
                    </span>
                    <button
                        onClick={fetchDiagnostics}
                        className={`p-2 rounded-lg bg-gray-700 hover:bg-gray-600 transition-colors ${loading ? 'animate-spin' : ''}`}
                    >
                        <RefreshCw className="w-5 h-5 text-blue-400" />
                    </button>
                </div>
            </div>

            {/* Quick Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {/* System Load */}
                <div className="bg-gray-800/50 p-6 rounded-xl border border-gray-700 backdrop-blur-sm">
                    <h3 className="text-gray-400 mb-4 flex items-center gap-2">
                        <Server className="w-5 h-5" /> System Resources
                    </h3>
                    <div className="space-y-4">
                        <div>
                            <div className="flex justify-between mb-1">
                                <span className="text-sm text-gray-300">CPU Load (1m/5m/15m)</span>
                                <span className="text-sm text-blue-400 font-mono">
                                    {data.system.load_avg.map(l => l.toFixed(2)).join(' / ')}
                                </span>
                            </div>
                        </div>
                        <div>
                            <div className="flex justify-between mb-1">
                                <span className="text-sm text-gray-300">Memory Usage</span>
                                <span className="text-sm text-blue-400">{data.system.memory.percent}%</span>
                            </div>
                            <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
                                <div
                                    className={`h-full rounded-full transition-all duration-500 ${data.system.memory.percent > 90 ? 'bg-red-500' : 'bg-blue-500'}`}
                                    style={{ width: `${data.system.memory.percent}%` }}
                                ></div>
                            </div>
                            <p className="text-xs text-gray-500 mt-1">
                                {data.system.memory.used_mb}MB used of {data.system.memory.total_mb}MB
                            </p>
                        </div>
                        <div>
                            <div className="flex justify-between mb-1">
                                <span className="text-sm text-gray-300">Disk Usage (Root)</span>
                                <span className="text-sm text-purple-400">{data.system.disk.percent}%</span>
                            </div>
                            <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
                                <div
                                    className={`h-full rounded-full transition-all duration-500 ${data.system.disk.percent > 90 ? 'bg-red-500' : 'bg-purple-500'}`}
                                    style={{ width: `${data.system.disk.percent}%` }}
                                ></div>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Project Info */}
                <div className="bg-gray-800/50 p-6 rounded-xl border border-gray-700 backdrop-blur-sm">
                    <h3 className="text-gray-400 mb-4 flex items-center gap-2">
                        <GitBranch className="w-5 h-5" /> Project Version
                    </h3>
                    <div className="space-y-4">
                        <div className="flex justify-between items-center py-2 border-b border-gray-700">
                            <span className="text-gray-400">Current Branch</span>
                            <span className="text-white font-mono bg-gray-700 px-2 py-1 rounded text-sm">
                                {data.project.branch}
                            </span>
                        </div>
                        <div className="flex justify-between items-center py-2 border-b border-gray-700">
                            <span className="text-gray-400">Commit Hash</span>
                            <span className="text-blue-400 font-mono text-sm">
                                {data.project.commit}
                            </span>
                        </div>
                        <div className="py-2">
                            <span className="text-gray-400 block mb-1">Latest Change</span>
                            <p className="text-sm text-gray-300 italic truncate" title={data.project.last_message}>
                                "{data.project.last_message}"
                            </p>
                        </div>
                        {data.project.uncommitted_changes > 0 ? (
                            <div className="bg-yellow-900/30 text-yellow-500 p-3 rounded-lg text-sm flex items-center gap-2">
                                <AlertTriangle className="w-4 h-4" />
                                {data.project.uncommitted_changes} uncommitted file changes
                            </div>
                        ) : (
                            <div className="bg-green-900/30 text-green-500 p-3 rounded-lg text-sm flex items-center gap-2">
                                <CheckCircle className="w-4 h-4" />
                                Project is clean and up-to-date
                            </div>
                        )}
                    </div>
                </div>

                {/* Service Status */}
                <div className="bg-gray-800/50 p-6 rounded-xl border border-gray-700 backdrop-blur-sm">
                    <h3 className="text-gray-400 mb-4 flex items-center gap-2">
                        <Shield className="w-5 h-5" /> Core Services
                    </h3>
                    <div className="space-y-3">
                        {data.services.map((svc) => (
                            <div key={svc.name} className="flex justify-between items-center">
                                <span className="text-gray-300 text-sm truncate max-w-[150px]" title={svc.name}>
                                    {svc.name.replace('.service', '')}
                                </span>
                                <span className={`px-2 py-1 rounded text-xs font-semibold ${svc.active
                                    ? 'bg-green-900/30 text-green-400 border border-green-800'
                                    : 'bg-red-900/30 text-red-400 border border-red-800'
                                    }`}>
                                    {svc.status}
                                </span>
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            {/* Package Versions Table */}
            <div className="bg-gray-800/50 rounded-xl border border-gray-700 backdrop-blur-sm overflow-hidden">
                <div className="p-6 border-b border-gray-700">
                    <h3 className="text-lg font-semibold text-white flex items-center gap-2">
                        <Box className="w-5 h-5 text-blue-400" /> Package Versions & Updates
                    </h3>
                </div>
                <div className="overflow-x-auto">
                    <table className="w-full">
                        <thead className="bg-gray-900/50">
                            <tr>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Package</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Installed Version</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Latest Available</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Status</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-700">
                            {data.packages.map((pkg) => (
                                <tr key={pkg.name} className="hover:bg-gray-700/30 transition-colors">
                                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-white">
                                        {pkg.name}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300 font-mono">
                                        {pkg.installed}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-400 font-mono">
                                        {pkg.latest}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        {pkg.status === 'OK' || pkg.status === 'Up to date' ? (
                                            <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-900/30 text-green-400 border border-green-800">
                                                Up to date
                                            </span>
                                        ) : pkg.status === 'Not Installed' ? (
                                            <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-gray-700 text-gray-400">
                                                Not Installed
                                            </span>
                                        ) : (
                                            <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-yellow-900/30 text-yellow-400 border border-yellow-800 animate-pulse">
                                                Update Available
                                            </span>
                                        )}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* Network & Security Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Network connectivity */}
                <div className="bg-gray-800/50 p-6 rounded-xl border border-gray-700 backdrop-blur-sm">
                    <h3 className="text-gray-400 mb-4 flex items-center gap-2">
                        <Activity className="w-5 h-5" /> Network Connectivity
                    </h3>
                    <div className="space-y-3">
                        <div className="flex justify-between items-center py-2 border-b border-gray-700">
                            <span className="text-gray-400">Public IPv4</span>
                            <span className="text-white font-mono text-sm">{data.network?.public_ipv4 || 'Unknown'}</span>
                        </div>
                        <div className="flex justify-between items-center py-2 border-b border-gray-700">
                            <span className="text-gray-400">Public IPv6</span>
                            <span className="text-white font-mono text-sm">{data.network?.public_ipv6 || 'Not Detected'}</span>
                        </div>
                        <div className="flex justify-between items-center py-2 border-b border-gray-700">
                            <span className="text-gray-400">Latency (Google DNS)</span>
                            <span className={`font-mono text-sm ${data.network?.latency === 'Timeout' ? 'text-red-400' : 'text-green-400'}`}>
                                {data.network?.latency}
                            </span>
                        </div>
                        <div className="flex justify-between items-center py-2 border-b border-gray-700">
                            <span className="text-gray-400">Firewall (UFW)</span>
                            <span className="text-white font-mono text-sm">{data.network?.firewall_status}</span>
                        </div>
                    </div>
                </div>

                {/* VPN Security */}
                <div className="bg-gray-800/50 p-6 rounded-xl border border-gray-700 backdrop-blur-sm">
                    <h3 className="text-gray-400 mb-4 flex items-center gap-2">
                        <Shield className="w-5 h-5" /> VPN Security
                    </h3>
                    <div className="space-y-3">
                        <div className="flex justify-between items-center py-2 border-b border-gray-700">
                            <span className="text-gray-400">TUN Device</span>
                            <span className={data.vpn_security?.tun_available ? "text-green-400" : "text-red-400"}>
                                {data.vpn_security?.tun_available ? "Available" : "Missing"}
                            </span>
                        </div>
                        <div className="flex justify-between items-center py-2 border-b border-gray-700">
                            <span className="text-gray-400">IP Forwarding</span>
                            <span className={data.vpn_security?.ip_forwarding ? "text-green-400" : "text-red-400"}>
                                {data.vpn_security?.ip_forwarding ? "Enabled" : "Disabled"}
                            </span>
                        </div>
                        <div className="flex justify-between items-center py-2 border-b border-gray-700">
                            <span className="text-gray-400">Cert Expiry</span>
                            <span className="text-blue-400 font-mono text-xs">{data.vpn_security?.cert_expiry}</span>
                        </div>
                        <div className="flex justify-between items-center py-2 border-b border-gray-700">
                            <span className="text-gray-400">Database Health</span>
                            <span className={data.database?.status === 'OK' ? "text-green-400" : "text-red-400"}>
                                {data.database?.status}
                            </span>
                        </div>
                    </div>
                </div>
            </div>

            {/* Intelligent Log Analysis */}
            <div className="bg-gray-800/50 rounded-xl border border-gray-700 backdrop-blur-sm overflow-hidden">
                <div className="p-6 border-b border-gray-700">
                    <h3 className="text-lg font-semibold text-white flex items-center gap-2">
                        <Terminal className="w-5 h-5 text-yellow-500" /> Intelligent Log Analysis
                    </h3>
                </div>
                <div className="p-6">
                    {data.logs && data.logs.length > 0 ? (
                        <div className="space-y-4">
                            {data.logs.map((log, index) => (
                                <div key={index} className={`p-4 rounded-lg border ${log.level === 'CRITICAL' ? 'bg-red-900/20 border-red-700 text-red-200' :
                                        log.level === 'ERROR' ? 'bg-orange-900/20 border-orange-700 text-orange-200' :
                                            log.level === 'WARN' ? 'bg-yellow-900/20 border-yellow-700 text-yellow-200' :
                                                'bg-green-900/20 border-green-700 text-green-200'
                                    }`}>
                                    <div className="flex justify-between items-start">
                                        <div>
                                            <h4 className="font-bold flex items-center gap-2">
                                                [{log.level}] {log.message}
                                            </h4>
                                            {log.fix && (
                                                <p className="mt-1 text-sm opacity-90">
                                                    💡 <span className="font-semibold">Fix:</span> {log.fix}
                                                </p>
                                            )}
                                            {log.log_snippet && (
                                                <pre className="mt-2 text-xs opacity-75 overflow-x-auto p-2 bg-black/30 rounded">
                                                    {log.log_snippet}
                                                </pre>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <div className="text-center py-8 text-gray-500">
                            <CheckCircle className="w-12 h-12 mx-auto mb-3 text-green-500/50" />
                            <p>No critical error patterns detected in recent logs.</p>
                        </div>
                    )}
                </div>
            </div>

            {/* Recommended Tools */}
            <div className="bg-gray-800/50 rounded-xl border border-gray-700 backdrop-blur-sm overflow-hidden">
                <div className="p-6 border-b border-gray-700">
                    <h3 className="text-lg font-semibold text-white flex items-center gap-2">
                        <Box className="w-5 h-5 text-purple-400" /> Recommended Tools
                    </h3>
                </div>
                <div className="p-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {data.recommendations.map((tool) => (
                        <div key={tool.name} className={`p-4 rounded-lg border flex items-start justify-between ${tool.installed ? 'bg-gray-700/30 border-gray-600' : 'bg-gray-900/50 border-gray-700 border-dashed opacity-75'
                            }`}>
                            <div>
                                <h4 className="font-semibold text-gray-200">{tool.name}</h4>
                                <p className="text-xs text-gray-500 mt-1">{tool.description}</p>
                            </div>
                            <div className="mt-1">
                                {tool.installed ? (
                                    <CheckCircle className="w-5 h-5 text-green-500" />
                                ) : (
                                    <span className="text-xs px-2 py-1 bg-gray-700 rounded text-gray-400">Missing</span>
                                )}
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}
