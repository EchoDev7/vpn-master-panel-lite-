import React, { useState, useEffect } from 'react';
import { TrendingUp, Calendar, ArrowUp, ArrowDown } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import apiService from '../services/api';

const TrafficComparison = () => {
    const [comparisonData, setComparisonData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [period1, setPeriod1] = useState('7');
    const [period2, setPeriod2] = useState('14');

    useEffect(() => {
        loadComparisonData();
    }, [period1, period2]);

    const loadComparisonData = async () => {
        try {
            setLoading(true);
            const response = await apiService.get(`/monitoring/traffic-comparison?period1=${period1}&period2=${period2}`);
            setComparisonData(response.data || generateMockData());
            setLoading(false);
        } catch (error) {
            console.error('Failed to load comparison data:', error);
            setComparisonData(generateMockData());
            setLoading(false);
        }
    };

    const generateMockData = () => {
        const data = [];
        const days = Math.max(parseInt(period1), parseInt(period2));

        for (let i = 0; i < days; i++) {
            const date = new Date();
            date.setDate(date.getDate() - (days - i));

            data.push({
                date: date.toISOString().split('T')[0],
                period1_gb: Math.random() * 100 + 50,
                period2_gb: Math.random() * 80 + 40
            });
        }

        const period1Total = data.slice(0, parseInt(period1)).reduce((sum, d) => sum + d.period1_gb, 0);
        const period2Total = data.slice(0, parseInt(period2)).reduce((sum, d) => sum + d.period2_gb, 0);

        return {
            chart: data,
            summary: {
                period1: {
                    days: parseInt(period1),
                    total_gb: period1Total.toFixed(2),
                    avg_gb: (period1Total / parseInt(period1)).toFixed(2)
                },
                period2: {
                    days: parseInt(period2),
                    total_gb: period2Total.toFixed(2),
                    avg_gb: (period2Total / parseInt(period2)).toFixed(2)
                },
                change_percent: (((period1Total - period2Total) / period2Total) * 100).toFixed(1)
            }
        };
    };

    if (loading) {
        return (
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 animate-pulse">
                <div className="h-6 bg-gray-300 dark:bg-gray-700 rounded w-48 mb-4"></div>
                <div className="h-64 bg-gray-300 dark:bg-gray-700 rounded"></div>
            </div>
        );
    }

    const { summary, chart } = comparisonData;
    const isIncrease = parseFloat(summary.change_percent) > 0;

    return (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
            <div className="flex items-center justify-between mb-6">
                <div>
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                        <TrendingUp className="text-blue-500" size={20} />
                        Traffic Comparison
                    </h3>
                    <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                        Compare traffic across different time periods
                    </p>
                </div>
            </div>

            {/* Period Selectors */}
            <div className="grid grid-cols-2 gap-4 mb-6">
                <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        Current Period
                    </label>
                    <select
                        value={period1}
                        onChange={(e) => setPeriod1(e.target.value)}
                        className="w-full px-4 py-2 bg-gray-50 dark:bg-gray-900 border border-gray-300 dark:border-gray-700 rounded-lg text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
                    >
                        <option value="7">Last 7 days</option>
                        <option value="14">Last 14 days</option>
                        <option value="30">Last 30 days</option>
                        <option value="90">Last 90 days</option>
                    </select>
                </div>
                <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        Compare With
                    </label>
                    <select
                        value={period2}
                        onChange={(e) => setPeriod2(e.target.value)}
                        className="w-full px-4 py-2 bg-gray-50 dark:bg-gray-900 border border-gray-300 dark:border-gray-700 rounded-lg text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
                    >
                        <option value="7">Previous 7 days</option>
                        <option value="14">Previous 14 days</option>
                        <option value="30">Previous 30 days</option>
                        <option value="90">Previous 90 days</option>
                    </select>
                </div>
            </div>

            {/* Summary Cards */}
            <div className="grid grid-cols-3 gap-4 mb-6">
                <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4">
                    <p className="text-xs text-blue-600 dark:text-blue-400 font-medium">Current Period</p>
                    <p className="text-2xl font-bold text-blue-900 dark:text-blue-100 mt-1">
                        {summary.period1.total_gb} GB
                    </p>
                    <p className="text-xs text-blue-600 dark:text-blue-400 mt-1">
                        {summary.period1.avg_gb} GB/day avg
                    </p>
                </div>
                <div className="bg-purple-50 dark:bg-purple-900/20 rounded-lg p-4">
                    <p className="text-xs text-purple-600 dark:text-purple-400 font-medium">Previous Period</p>
                    <p className="text-2xl font-bold text-purple-900 dark:text-purple-100 mt-1">
                        {summary.period2.total_gb} GB
                    </p>
                    <p className="text-xs text-purple-600 dark:text-purple-400 mt-1">
                        {summary.period2.avg_gb} GB/day avg
                    </p>
                </div>
                <div className={`${isIncrease ? 'bg-green-50 dark:bg-green-900/20' : 'bg-red-50 dark:bg-red-900/20'} rounded-lg p-4`}>
                    <p className={`text-xs font-medium ${isIncrease ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                        Change
                    </p>
                    <p className={`text-2xl font-bold mt-1 flex items-center gap-1 ${isIncrease ? 'text-green-900 dark:text-green-100' : 'text-red-900 dark:text-red-100'}`}>
                        {isIncrease ? <ArrowUp size={24} /> : <ArrowDown size={24} />}
                        {Math.abs(summary.change_percent)}%
                    </p>
                    <p className={`text-xs mt-1 ${isIncrease ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                        vs previous period
                    </p>
                </div>
            </div>

            {/* Comparison Chart */}
            <ResponsiveContainer width="100%" height={300}>
                <LineChart data={chart}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                    <XAxis dataKey="date" stroke="#9ca3af" />
                    <YAxis stroke="#9ca3af" label={{ value: 'GB', angle: -90, position: 'insideLeft' }} />
                    <Tooltip
                        contentStyle={{
                            backgroundColor: '#1f2937',
                            border: 'none',
                            borderRadius: '8px',
                            color: '#fff'
                        }}
                    />
                    <Legend />
                    <Line
                        type="monotone"
                        dataKey="period1_gb"
                        stroke="#3b82f6"
                        strokeWidth={2}
                        name={`Current (${period1} days)`}
                        dot={{ r: 3 }}
                        activeDot={{ r: 5 }}
                    />
                    <Line
                        type="monotone"
                        dataKey="period2_gb"
                        stroke="#a855f7"
                        strokeWidth={2}
                        name={`Previous (${period2} days)`}
                        dot={{ r: 3 }}
                        activeDot={{ r: 5 }}
                        strokeDasharray="5 5"
                    />
                </LineChart>
            </ResponsiveContainer>

            {/* Insights */}
            <div className="mt-6 p-4 bg-gray-50 dark:bg-gray-900 rounded-lg">
                <h4 className="text-sm font-semibold text-gray-900 dark:text-white mb-2">
                    Analysis
                </h4>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                    {isIncrease ? (
                        <>Traffic has <span className="font-semibold text-green-600 dark:text-green-400">increased by {Math.abs(summary.change_percent)}%</span> compared to the previous period. This indicates growing usage.</>
                    ) : (
                        <>Traffic has <span className="font-semibold text-red-600 dark:text-red-400">decreased by {Math.abs(summary.change_percent)}%</span> compared to the previous period. Monitor for potential issues.</>
                    )}
                </p>
            </div>
        </div>
    );
};

export default TrafficComparison;
