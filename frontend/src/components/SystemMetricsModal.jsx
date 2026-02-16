import React from 'react';
import { X, RefreshCw, Server, Cpu, HardDrive, Activity } from 'lucide-react';

const SystemMetricsModal = ({ stats, onClose, onRefresh }) => {
    const getColorClass = (percent) => {
        if (percent >= 90) return 'text-red-500';
        if (percent >= 70) return 'text-yellow-500';
        return 'text-green-500';
    };

    const getProgressColor = (percent) => {
        if (percent >= 90) return 'bg-red-500';
        if (percent >= 70) return 'bg-yellow-500';
        return 'bg-green-500';
    };

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-2xl max-w-2xl w-full">
                {/* Header */}
                <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
                    <h2 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
                        <Server className="text-red-500" size={28} />
                        System Metrics
                    </h2>
                    <div className="flex gap-2">
                        <button
                            onClick={onRefresh}
                            className="p-2 rounded-lg bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
                            title="Refresh"
                        >
                            <RefreshCw size={20} className="text-gray-700 dark:text-gray-300" />
                        </button>
                        <button
                            onClick={onClose}
                            className="p-2 rounded-lg bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
                            title="Close"
                        >
                            <X size={20} className="text-gray-700 dark:text-gray-300" />
                        </button>
                    </div>
                </div>

                {/* Content */}
                <div className="p-6 space-y-6">
                    {/* CPU Usage */}
                    <div className="space-y-2">
                        <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                                <Cpu className={getColorClass(stats?.system?.cpu_percent || 0)} size={24} />
                                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">CPU Usage</h3>
                            </div>
                            <span className={`text-2xl font-bold ${getColorClass(stats?.system?.cpu_percent || 0)}`}>
                                {stats?.system?.cpu_percent?.toFixed(1) || 0}%
                            </span>
                        </div>
                        <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-4 overflow-hidden">
                            <div
                                className={`h-full ${getProgressColor(stats?.system?.cpu_percent || 0)} transition-all duration-500`}
                                style={{ width: `${stats?.system?.cpu_percent || 0}%` }}
                            />
                        </div>
                    </div>

                    {/* Memory Usage */}
                    <div className="space-y-2">
                        <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                                <Activity className={getColorClass(stats?.system?.memory_percent || 0)} size={24} />
                                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Memory Usage</h3>
                            </div>
                            <span className={`text-2xl font-bold ${getColorClass(stats?.system?.memory_percent || 0)}`}>
                                {stats?.system?.memory_percent?.toFixed(1) || 0}%
                            </span>
                        </div>
                        <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-4 overflow-hidden">
                            <div
                                className={`h-full ${getProgressColor(stats?.system?.memory_percent || 0)} transition-all duration-500`}
                                style={{ width: `${stats?.system?.memory_percent || 0}%` }}
                            />
                        </div>
                    </div>

                    {/* Disk Usage */}
                    <div className="space-y-2">
                        <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                                <HardDrive className={getColorClass(stats?.system?.disk_percent || 0)} size={24} />
                                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Disk Usage</h3>
                            </div>
                            <span className={`text-2xl font-bold ${getColorClass(stats?.system?.disk_percent || 0)}`}>
                                {stats?.system?.disk_percent?.toFixed(1) || 0}%
                            </span>
                        </div>
                        <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-4 overflow-hidden">
                            <div
                                className={`h-full ${getProgressColor(stats?.system?.disk_percent || 0)} transition-all duration-500`}
                                style={{ width: `${stats?.system?.disk_percent || 0}%` }}
                            />
                        </div>
                    </div>

                    {/* Additional Info */}
                    <div className="grid grid-cols-2 gap-4 pt-4 border-t border-gray-200 dark:border-gray-700">
                        <div className="bg-gray-50 dark:bg-gray-900 p-4 rounded-lg">
                            <p className="text-sm text-gray-600 dark:text-gray-400">Total Users</p>
                            <p className="text-2xl font-bold text-gray-900 dark:text-white">{stats?.users?.total || 0}</p>
                        </div>
                        <div className="bg-gray-50 dark:bg-gray-900 p-4 rounded-lg">
                            <p className="text-sm text-gray-600 dark:text-gray-400">Active Connections</p>
                            <p className="text-2xl font-bold text-gray-900 dark:text-white">{stats?.connections?.active || 0}</p>
                        </div>
                    </div>
                </div>

                {/* Footer */}
                <div className="flex items-center justify-end p-6 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900">
                    <button
                        onClick={onClose}
                        className="px-6 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg font-medium transition-colors"
                    >
                        Close
                    </button>
                </div>
            </div>
        </div>
    );
};

export default SystemMetricsModal;
