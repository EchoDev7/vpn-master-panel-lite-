import React, { useState, useEffect } from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';
import { Shield, RefreshCw, Activity } from 'lucide-react';
import apiService from '../services/api';

const COLORS = {
    openvpn: '#3b82f6',    // Blue
    wireguard: '#10b981',  // Green
    other: '#8b5cf6'       // Purple
};

const ProtocolDistributionChart = () => {
    const [data, setData] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        loadProtocolStats();
        const interval = setInterval(loadProtocolStats, 30000);
        return () => clearInterval(interval);
    }, []);

    const loadProtocolStats = async () => {
        try {
            setError(null);
            const response = await apiService.get('/monitoring/protocol-distribution');

            // Transform data for pie chart
            const chartData = [
                { name: 'OpenVPN', value: response.data.openvpn || 0, color: COLORS.openvpn },
                { name: 'WireGuard', value: response.data.wireguard || 0, color: COLORS.wireguard }
            ].filter(item => item.value > 0);

            setData(chartData);
            setLoading(false);
        } catch (err) {
            console.error('Failed to load protocol stats:', err);
            setError(err);
            setLoading(false);
        }
    };

    const CustomTooltip = ({ active, payload }) => {
        if (active && payload && payload.length) {
            const data = payload[0];
            const total = payload[0].payload.total || data.value;
            // Prevent NaN if total is 0 somehow inside tooltip
            const percentage = total > 0 ? ((data.value / total) * 100).toFixed(1) : 0;

            return (
                <div className="bg-white/90 dark:bg-gray-800/90 backdrop-blur-md px-4 py-3 rounded-xl shadow-xl border border-gray-100 dark:border-gray-700">
                    <p className="font-bold text-gray-900 dark:text-white flex items-center gap-2 mb-1">
                        <div className="w-3 h-3 rounded-full" style={{ backgroundColor: data.payload.color }} />
                        {data.name}
                    </p>
                    <p className="text-sm font-medium text-gray-600 dark:text-gray-300">
                        {data.value} users <span className="text-gray-400">({percentage}%)</span>
                    </p>
                </div>
            );
        }
        return null;
    };

    if (loading) {
        return (
            <div className="bg-white/70 dark:bg-gray-800/70 backdrop-blur-2xl rounded-3xl shadow-lg border border-white/20 dark:border-gray-700 p-6 md:p-8 animate-pulse">
                <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded-lg w-48 mb-8"></div>
                <div className="h-[250px] bg-gray-200 dark:bg-gray-700 rounded-full w-[250px] mx-auto"></div>
            </div>
        );
    }

    const total = data.reduce((sum, item) => sum + item.value, 0);

    return (
        <div className="relative overflow-hidden bg-white/70 dark:bg-gray-800/70 backdrop-blur-2xl rounded-3xl shadow-lg border border-white/20 dark:border-gray-700 p-6 md:p-8 transition-all duration-300 hover:shadow-xl">
            {/* Ambient Background Glow */}
            <div className="absolute -right-20 -top-20 w-64 h-64 bg-blue-500/10 rounded-full blur-3xl pointer-events-none" />

            <div className="flex items-center justify-between mb-8 relative z-10">
                <h3 className="text-xl font-bold text-gray-900 dark:text-white flex items-center gap-3">
                    <div className="p-2 bg-blue-100 dark:bg-blue-900/50 rounded-xl text-blue-600 dark:text-blue-400">
                        <Shield size={22} />
                    </div>
                    Protocol Usage
                </h3>
                <button
                    onClick={loadProtocolStats}
                    className="p-2 bg-gray-100 dark:bg-gray-700/50 hover:bg-white dark:hover:bg-gray-700 rounded-xl transition-all duration-300 shadow-sm hover:shadow text-gray-500 dark:text-gray-400 hover:text-blue-500 hover:rotate-180"
                    title="Refresh"
                >
                    <RefreshCw size={18} />
                </button>
            </div>

            {error || data.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-[250px] space-y-4">
                    <div className="w-16 h-16 bg-gray-100 dark:bg-gray-800 rounded-full flex items-center justify-center border border-gray-200 dark:border-gray-700">
                        <Activity size={28} className="text-gray-400 dark:text-gray-500 opacity-50" />
                    </div>
                    <p className="text-gray-500 dark:text-gray-400 font-medium">No active connections</p>
                </div>
            ) : (
                <>
                    <div className="relative h-[250px] w-full flex items-center justify-center">
                        <ResponsiveContainer width="100%" height="100%">
                            <PieChart>
                                <Pie
                                    data={data}
                                    cx="50%"
                                    cy="50%"
                                    innerRadius={70}
                                    outerRadius={95}
                                    paddingAngle={5}
                                    dataKey="value"
                                    stroke="none"
                                    cornerRadius={8}
                                >
                                    {data.map((entry, index) => (
                                        <Cell key={`cell-${index}`} fill={entry.color} />
                                    ))}
                                </Pie>
                                <Tooltip content={<CustomTooltip />} />
                            </PieChart>
                        </ResponsiveContainer>
                        {/* Center Metric */}
                        <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                            <span className="text-3xl font-extrabold text-gray-900 dark:text-white">
                                {total}
                            </span>
                            <span className="text-xs font-semibold tracking-wider text-gray-500 uppercase mt-1">
                                Users
                            </span>
                        </div>
                    </div>

                    {/* Legend */}
                    <div className="mt-8 space-y-3 pb-2">
                        {data.map((item, index) => (
                            <div key={index} className="flex items-center justify-between group">
                                <div className="flex items-center gap-3">
                                    <div
                                        className="w-3 h-3 rounded-full shadow-sm transition-transform duration-300 group-hover:scale-125"
                                        style={{ backgroundColor: item.color }}
                                    ></div>
                                    <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                                        {item.name}
                                    </span>
                                </div>
                                <div className="flex items-center gap-2">
                                    <span className="text-sm font-bold text-gray-900 dark:text-white">
                                        {item.value}
                                    </span>
                                    <span className="text-xs font-medium text-gray-500 bg-gray-100 dark:bg-gray-800 px-2 py-0.5 rounded-md">
                                        {((item.value / total) * 100).toFixed(0)}%
                                    </span>
                                </div>
                            </div>
                        ))}
                    </div>
                </>
            )}
        </div>
    );
};

export default ProtocolDistributionChart;
