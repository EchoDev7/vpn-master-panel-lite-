import React, { useState, useEffect } from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';
import { Shield, RefreshCw } from 'lucide-react';
import apiService from '../services/api';

const COLORS = {
    openvpn: '#3b82f6',    // Blue
    wireguard: '#10b981',  // Green
    other: '#6b7280'       // Gray
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
            const percentage = ((data.value / total) * 100).toFixed(1);

            return (
                <div className="bg-gray-900 text-white px-4 py-2 rounded-lg shadow-lg">
                    <p className="font-semibold">{data.name}</p>
                    <p className="text-sm">{data.value} users ({percentage}%)</p>
                </div>
            );
        }
        return null;
    };

    const CustomLabel = ({ cx, cy, midAngle, innerRadius, outerRadius, percent }) => {
        const RADIAN = Math.PI / 180;
        const radius = innerRadius + (outerRadius - innerRadius) * 0.5;
        const x = cx + radius * Math.cos(-midAngle * RADIAN);
        const y = cy + radius * Math.sin(-midAngle * RADIAN);

        return (
            <text
                x={x}
                y={y}
                fill="white"
                textAnchor={x > cx ? 'start' : 'end'}
                dominantBaseline="central"
                className="font-bold text-sm"
            >
                {`${(percent * 100).toFixed(0)}%`}
            </text>
        );
    };

    if (loading) {
        return (
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 animate-pulse">
                <div className="h-6 bg-gray-300 dark:bg-gray-700 rounded w-48 mb-4"></div>
                <div className="h-64 bg-gray-300 dark:bg-gray-700 rounded"></div>
            </div>
        );
    }

    if (error || data.length === 0) {
        return (
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                    <Shield className="text-blue-500" size={20} />
                    Protocol Distribution
                </h3>
                <div className="text-center py-12 text-gray-500 dark:text-gray-400">
                    No active connections
                </div>
            </div>
        );
    }

    const total = data.reduce((sum, item) => sum + item.value, 0);

    return (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
            <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                    <Shield className="text-blue-500" size={20} />
                    Protocol Distribution
                </h3>
                <button
                    onClick={loadProtocolStats}
                    className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                    title="Refresh"
                >
                    <RefreshCw size={16} className="text-gray-600 dark:text-gray-400" />
                </button>
            </div>

            <ResponsiveContainer width="100%" height={250}>
                <PieChart>
                    <Pie
                        data={data}
                        cx="50%"
                        cy="50%"
                        labelLine={false}
                        label={CustomLabel}
                        outerRadius={80}
                        fill="#8884d8"
                        dataKey="value"
                    >
                        {data.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                    </Pie>
                    <Tooltip content={<CustomTooltip />} />
                </PieChart>
            </ResponsiveContainer>

            {/* Legend */}
            <div className="mt-4 space-y-2">
                {data.map((item, index) => (
                    <div key={index} className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                            <div
                                className="w-4 h-4 rounded"
                                style={{ backgroundColor: item.color }}
                            ></div>
                            <span className="text-sm text-gray-700 dark:text-gray-300">
                                {item.name}
                            </span>
                        </div>
                        <span className="text-sm font-semibold text-gray-900 dark:text-white">
                            {item.value} ({((item.value / total) * 100).toFixed(1)}%)
                        </span>
                    </div>
                ))}
            </div>

            <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
                <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-gray-600 dark:text-gray-400">
                        Total Active Users
                    </span>
                    <span className="text-lg font-bold text-gray-900 dark:text-white">
                        {total}
                    </span>
                </div>
            </div>
        </div>
    );
};

export default ProtocolDistributionChart;
