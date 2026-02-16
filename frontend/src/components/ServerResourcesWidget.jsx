import { useState, useEffect } from 'react';
import { Cpu, HardDrive, Activity, Server, RefreshCw } from 'lucide-react';
import { LineChart, Line, ResponsiveContainer, Tooltip, BarChart, Bar, XAxis, YAxis } from 'recharts';
import apiService from '../services/api';

const ServerResourcesWidget = () => {
    const [resources, setResources] = useState(null);
    const [loading, setLoading] = useState(true);

    const loadResources = async () => {
        try {
            const response = await apiService.get('/monitoring/server-resources');
            setResources(response.data);
            setLoading(false);
        } catch (error) {
            console.error('Failed to load server resources:', error);
            setLoading(false);
        }
    };

    useEffect(() => {
        loadResources();
        const interval = setInterval(loadResources, 3000); // Refresh every 3 seconds
        return () => clearInterval(interval);
    }, []);

    if (loading) {
        return (
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
                <div className="animate-pulse space-y-4">
                    <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-1/3"></div>
                    <div className="h-32 bg-gray-200 dark:bg-gray-700 rounded"></div>
                </div>
            </div>
        );
    }

    const getColorForPercent = (percent) => {
        if (percent >= 90) return 'text-red-500';
        if (percent >= 70) return 'text-yellow-500';
        return 'text-green-500';
    };

    const getBarColorForPercent = (percent) => {
        if (percent >= 90) return '#ef4444';
        if (percent >= 70) return '#f59e0b';
        return '#10b981';
    };

    return (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
            {/* Header */}
            <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
                    <Server className="text-blue-500" size={24} />
                    Server Resources
                </h2>
                <button
                    onClick={loadResources}
                    className="p-2 rounded-lg bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
                    title="Refresh"
                >
                    <RefreshCw size={18} className="text-gray-700 dark:text-gray-300" />
                </button>
            </div>

            {/* CPU Section */}
            <div className="mb-6">
                <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                        <Cpu className="text-blue-500" size={20} />
                        <h3 className="font-semibold text-gray-900 dark:text-white">
                            CPU Usage
                        </h3>
                    </div>
                    <span className={`text-2xl font-bold ${getColorForPercent(resources?.cpu?.total || 0)}`}>
                        {resources?.cpu?.total?.toFixed(1)}%
                    </span>
                </div>

                {/* Per-core CPU bars */}
                <div className="space-y-2 mb-3">
                    {resources?.cpu?.per_core?.map((usage, index) => (
                        <div key={index} className="flex items-center gap-2">
                            <span className="text-xs text-gray-600 dark:text-gray-400 w-12">
                                Core {index}
                            </span>
                            <div className="flex-1 bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                                <div
                                    className="h-2 rounded-full transition-all duration-300"
                                    style={{
                                        width: `${usage}%`,
                                        backgroundColor: getBarColorForPercent(usage)
                                    }}
                                ></div>
                            </div>
                            <span className="text-xs text-gray-600 dark:text-gray-400 w-10 text-right">
                                {usage.toFixed(0)}%
                            </span>
                        </div>
                    ))}
                </div>

                {/* Load Average */}
                <div className="grid grid-cols-3 gap-2 text-center">
                    <div className="bg-gray-50 dark:bg-gray-700 rounded p-2">
                        <div className="text-xs text-gray-600 dark:text-gray-400">1 min</div>
                        <div className="text-sm font-semibold text-gray-900 dark:text-white">
                            {resources?.cpu?.load_average?.['1min']}
                        </div>
                    </div>
                    <div className="bg-gray-50 dark:bg-gray-700 rounded p-2">
                        <div className="text-xs text-gray-600 dark:text-gray-400">5 min</div>
                        <div className="text-sm font-semibold text-gray-900 dark:text-white">
                            {resources?.cpu?.load_average?.['5min']}
                        </div>
                    </div>
                    <div className="bg-gray-50 dark:bg-gray-700 rounded p-2">
                        <div className="text-xs text-gray-600 dark:text-gray-400">15 min</div>
                        <div className="text-sm font-semibold text-gray-900 dark:text-white">
                            {resources?.cpu?.load_average?.['15min']}
                        </div>
                    </div>
                </div>
            </div>

            {/* Memory Section */}
            <div className="mb-6">
                <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                        <Activity className="text-green-500" size={20} />
                        <h3 className="font-semibold text-gray-900 dark:text-white">
                            Memory
                        </h3>
                    </div>
                    <span className={`text-2xl font-bold ${getColorForPercent(resources?.memory?.percent || 0)}`}>
                        {resources?.memory?.percent?.toFixed(1)}%
                    </span>
                </div>

                <div className="bg-gray-200 dark:bg-gray-700 rounded-full h-4 mb-2">
                    <div
                        className="h-4 rounded-full transition-all duration-300"
                        style={{
                            width: `${resources?.memory?.percent}%`,
                            backgroundColor: getBarColorForPercent(resources?.memory?.percent || 0)
                        }}
                    ></div>
                </div>

                <div className="grid grid-cols-2 gap-2 text-sm">
                    <div className="flex justify-between">
                        <span className="text-gray-600 dark:text-gray-400">Used:</span>
                        <span className="font-semibold text-gray-900 dark:text-white">
                            {resources?.memory?.used_gb} GB
                        </span>
                    </div>
                    <div className="flex justify-between">
                        <span className="text-gray-600 dark:text-gray-400">Free:</span>
                        <span className="font-semibold text-gray-900 dark:text-white">
                            {resources?.memory?.free_gb} GB
                        </span>
                    </div>
                    <div className="flex justify-between">
                        <span className="text-gray-600 dark:text-gray-400">Total:</span>
                        <span className="font-semibold text-gray-900 dark:text-white">
                            {resources?.memory?.total_gb} GB
                        </span>
                    </div>
                    <div className="flex justify-between">
                        <span className="text-gray-600 dark:text-gray-400">Available:</span>
                        <span className="font-semibold text-gray-900 dark:text-white">
                            {resources?.memory?.available_gb} GB
                        </span>
                    </div>
                </div>
            </div>

            {/* Disk Partitions */}
            <div className="mb-6">
                <div className="flex items-center gap-2 mb-3">
                    <HardDrive className="text-purple-500" size={20} />
                    <h3 className="font-semibold text-gray-900 dark:text-white">
                        Disk Usage
                    </h3>
                </div>

                <div className="space-y-3">
                    {resources?.partitions?.map((partition, index) => (
                        <div key={index} className="bg-gray-50 dark:bg-gray-700 rounded p-3">
                            <div className="flex justify-between items-center mb-2">
                                <span className="text-sm font-medium text-gray-900 dark:text-white">
                                    {partition.mountpoint}
                                </span>
                                <span className={`text-sm font-bold ${getColorForPercent(partition.percent)}`}>
                                    {partition.percent.toFixed(1)}%
                                </span>
                            </div>
                            <div className="bg-gray-200 dark:bg-gray-600 rounded-full h-2 mb-1">
                                <div
                                    className="h-2 rounded-full transition-all duration-300"
                                    style={{
                                        width: `${partition.percent}%`,
                                        backgroundColor: getBarColorForPercent(partition.percent)
                                    }}
                                ></div>
                            </div>
                            <div className="flex justify-between text-xs text-gray-600 dark:text-gray-400">
                                <span>{partition.used_gb} GB used</span>
                                <span>{partition.free_gb} GB free of {partition.total_gb} GB</span>
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            {/* System Info */}
            <div className="grid grid-cols-2 gap-4 pt-4 border-t border-gray-200 dark:border-gray-700">
                <div className="text-center">
                    <div className="text-xs text-gray-600 dark:text-gray-400">Uptime</div>
                    <div className="text-lg font-semibold text-gray-900 dark:text-white">
                        {resources?.uptime_days} days
                    </div>
                </div>
                <div className="text-center">
                    <div className="text-xs text-gray-600 dark:text-gray-400">Processes</div>
                    <div className="text-lg font-semibold text-gray-900 dark:text-white">
                        {resources?.process_count}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default ServerResourcesWidget;
