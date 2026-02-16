import { useState, useEffect } from 'react';
import { Gauge, TrendingUp, TrendingDown, RefreshCw, Wifi } from 'lucide-react';
import { LineChart, Line, ResponsiveContainer, XAxis, YAxis, Tooltip } from 'recharts';
import apiService from '../services/api';

const NetworkSpeedWidget = () => {
    const [speeds, setSpeeds] = useState(null);
    const [history, setHistory] = useState([]);
    const [loading, setLoading] = useState(true);

    const loadSpeed = async () => {
        try {
            const response = await apiService.get('/monitoring/network-speed');
            const data = response.data;
            setSpeeds(data);

            // Add to history (keep last 60 data points = 2 minutes at 2-second intervals)
            setHistory(prev => {
                const newHistory = [...prev, {
                    timestamp: new Date().toLocaleTimeString(),
                    client_upload: data.client_server?.upload_mbps || 0,
                    client_download: data.client_server?.download_mbps || 0,
                    tunnel_upload: data.tunnel?.upload_mbps || 0,
                    tunnel_download: data.tunnel?.download_mbps || 0,
                    total: data.total?.total_mbps || 0
                }];
                return newHistory.slice(-60);
            });

            setLoading(false);
        } catch (error) {
            console.error('Failed to load network speed:', error);
            setLoading(false);
        }
    };

    useEffect(() => {
        loadSpeed();
        const interval = setInterval(loadSpeed, 2000); // Refresh every 2 seconds
        return () => clearInterval(interval);
    }, []);

    const SpeedGauge = ({ title, upload, download, color, icon: Icon }) => {
        const total = (upload || 0) + (download || 0);
        const maxSpeed = 1000; // Max 1000 Mbps for gauge
        const percentage = Math.min((total / maxSpeed) * 100, 100);

        return (
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-4 border-l-4" style={{ borderColor: color }}>
                <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                        {Icon && <Icon className="text-gray-600 dark:text-gray-400" size={18} />}
                        <h3 className="font-semibold text-gray-900 dark:text-white text-sm">
                            {title}
                        </h3>
                    </div>
                    <Gauge className="text-gray-400" size={16} />
                </div>

                {/* Speed Display */}
                <div className="text-center mb-3">
                    <div className="text-3xl font-bold text-gray-900 dark:text-white">
                        {total.toFixed(2)}
                    </div>
                    <div className="text-xs text-gray-600 dark:text-gray-400">Mbps</div>
                </div>

                {/* Progress Bar */}
                <div className="bg-gray-200 dark:bg-gray-700 rounded-full h-2 mb-3">
                    <div
                        className="h-2 rounded-full transition-all duration-300"
                        style={{
                            width: `${percentage}%`,
                            backgroundColor: color
                        }}
                    ></div>
                </div>

                {/* Upload/Download */}
                <div className="grid grid-cols-2 gap-2 text-xs">
                    <div className="flex items-center gap-1">
                        <TrendingUp size={14} className="text-blue-500" />
                        <span className="text-gray-600 dark:text-gray-400">Upload:</span>
                        <span className="font-semibold text-gray-900 dark:text-white">
                            {(upload || 0).toFixed(2)}
                        </span>
                    </div>
                    <div className="flex items-center gap-1">
                        <TrendingDown size={14} className="text-green-500" />
                        <span className="text-gray-600 dark:text-gray-400">Download:</span>
                        <span className="font-semibold text-gray-900 dark:text-white">
                            {(download || 0).toFixed(2)}
                        </span>
                    </div>
                </div>

                {/* Interface Info */}
                {speeds?.client_server?.interface && title.includes('Client') && (
                    <div className="mt-2 text-xs text-gray-500 dark:text-gray-400 text-center">
                        Interface: {speeds.client_server.interface}
                    </div>
                )}
                {speeds?.tunnel?.interface && title.includes('Tunnel') && (
                    <div className="mt-2 text-xs text-gray-500 dark:text-gray-400 text-center">
                        Interface: {speeds.tunnel.interface}
                    </div>
                )}
            </div>
        );
    };

    if (loading) {
        return (
            <div className="space-y-4">
                <div className="animate-pulse grid grid-cols-1 md:grid-cols-3 gap-4">
                    {[1, 2, 3].map(i => (
                        <div key={i} className="bg-gray-200 dark:bg-gray-700 rounded-lg h-40"></div>
                    ))}
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <h2 className="text-xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
                    <Wifi className="text-blue-500" size={24} />
                    Real-time Network Speed
                </h2>
                <button
                    onClick={loadSpeed}
                    className="p-2 rounded-lg bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
                    title="Refresh"
                >
                    <RefreshCw size={18} className="text-gray-700 dark:text-gray-300" />
                </button>
            </div>

            {/* Speed Gauges */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <SpeedGauge
                    title="Client → Server"
                    upload={speeds?.client_server?.upload_mbps}
                    download={speeds?.client_server?.download_mbps}
                    color="#3b82f6"
                    icon={Wifi}
                />
                <SpeedGauge
                    title="Server → Server (Tunnel)"
                    upload={speeds?.tunnel?.upload_mbps}
                    download={speeds?.tunnel?.download_mbps}
                    color="#10b981"
                    icon={TrendingUp}
                />
                <SpeedGauge
                    title="Total Bandwidth"
                    upload={speeds?.total?.upload_mbps}
                    download={speeds?.total?.download_mbps}
                    color="#f59e0b"
                    icon={Gauge}
                />
            </div>

            {/* Historical Speed Graph */}
            {history.length > 1 && (
                <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                        Speed History (Last 2 Minutes)
                    </h3>
                    <ResponsiveContainer width="100%" height={200}>
                        <LineChart data={history}>
                            <XAxis
                                dataKey="timestamp"
                                tick={{ fontSize: 10 }}
                                stroke="#9ca3af"
                            />
                            <YAxis
                                tick={{ fontSize: 10 }}
                                stroke="#9ca3af"
                                label={{ value: 'Mbps', angle: -90, position: 'insideLeft', fontSize: 12 }}
                            />
                            <Tooltip
                                contentStyle={{
                                    backgroundColor: '#1f2937',
                                    border: 'none',
                                    borderRadius: '8px',
                                    color: '#fff'
                                }}
                            />
                            <Line
                                type="monotone"
                                dataKey="client_download"
                                stroke="#3b82f6"
                                strokeWidth={2}
                                dot={false}
                                name="Client Download"
                            />
                            <Line
                                type="monotone"
                                dataKey="tunnel_download"
                                stroke="#10b981"
                                strokeWidth={2}
                                dot={false}
                                name="Tunnel Download"
                            />
                            <Line
                                type="monotone"
                                dataKey="total"
                                stroke="#f59e0b"
                                strokeWidth={2}
                                dot={false}
                                name="Total"
                            />
                        </LineChart>
                    </ResponsiveContainer>

                    {/* Legend */}
                    <div className="flex justify-center gap-6 mt-4 text-sm">
                        <div className="flex items-center gap-2">
                            <div className="w-4 h-1 bg-blue-500 rounded"></div>
                            <span className="text-gray-600 dark:text-gray-400">Client Download</span>
                        </div>
                        <div className="flex items-center gap-2">
                            <div className="w-4 h-1 bg-green-500 rounded"></div>
                            <span className="text-gray-600 dark:text-gray-400">Tunnel Download</span>
                        </div>
                        <div className="flex items-center gap-2">
                            <div className="w-4 h-1 bg-yellow-500 rounded"></div>
                            <span className="text-gray-600 dark:text-gray-400">Total</span>
                        </div>
                    </div>
                </div>
            )}

            {/* Peak Speeds */}
            {history.length > 0 && (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4">
                        <div className="text-sm text-blue-600 dark:text-blue-400 mb-1">Peak Client Speed</div>
                        <div className="text-2xl font-bold text-blue-700 dark:text-blue-300">
                            {Math.max(...history.map(h => h.client_download + h.client_upload)).toFixed(2)} Mbps
                        </div>
                    </div>
                    <div className="bg-green-50 dark:bg-green-900/20 rounded-lg p-4">
                        <div className="text-sm text-green-600 dark:text-green-400 mb-1">Peak Tunnel Speed</div>
                        <div className="text-2xl font-bold text-green-700 dark:text-green-300">
                            {Math.max(...history.map(h => h.tunnel_download + h.tunnel_upload)).toFixed(2)} Mbps
                        </div>
                    </div>
                    <div className="bg-yellow-50 dark:bg-yellow-900/20 rounded-lg p-4">
                        <div className="text-sm text-yellow-600 dark:text-yellow-400 mb-1">Peak Total Speed</div>
                        <div className="text-2xl font-bold text-yellow-700 dark:text-yellow-300">
                            {Math.max(...history.map(h => h.total)).toFixed(2)} Mbps
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default NetworkSpeedWidget;
