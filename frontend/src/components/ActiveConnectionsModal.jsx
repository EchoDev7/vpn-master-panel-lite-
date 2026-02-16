import React from 'react';
import { X, RefreshCw, Activity } from 'lucide-react';

const ActiveConnectionsModal = ({ connections, onClose, onRefresh }) => {
    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-2xl max-w-4xl w-full max-h-[80vh] overflow-hidden">
                {/* Header */}
                <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
                    <h2 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
                        <Activity className="text-green-500" size={28} />
                        Active Connections
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
                <div className="p-6 overflow-y-auto max-h-[60vh]">
                    {connections.length === 0 ? (
                        <div className="text-center py-12">
                            <Activity className="mx-auto text-gray-400 mb-4" size={48} />
                            <p className="text-gray-500 dark:text-gray-400 text-lg">No active connections</p>
                        </div>
                    ) : (
                        <div className="overflow-x-auto">
                            <table className="w-full">
                                <thead>
                                    <tr className="border-b border-gray-200 dark:border-gray-700">
                                        <th className="text-left py-3 px-4 text-sm font-semibold text-gray-700 dark:text-gray-300">Username</th>
                                        <th className="text-left py-3 px-4 text-sm font-semibold text-gray-700 dark:text-gray-300">Protocol</th>
                                        <th className="text-left py-3 px-4 text-sm font-semibold text-gray-700 dark:text-gray-300">Client IP</th>
                                        <th className="text-left py-3 px-4 text-sm font-semibold text-gray-700 dark:text-gray-300">Virtual IP</th>
                                        <th className="text-left py-3 px-4 text-sm font-semibold text-gray-700 dark:text-gray-300">Connected At</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {connections.map((conn, index) => (
                                        <tr
                                            key={index}
                                            className="border-b border-gray-100 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                                        >
                                            <td className="py-3 px-4 text-sm text-gray-900 dark:text-white font-medium">
                                                {conn.username || 'N/A'}
                                            </td>
                                            <td className="py-3 px-4">
                                                <span className="px-3 py-1 rounded-full text-xs font-medium bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200">
                                                    {conn.protocol?.toUpperCase() || 'N/A'}
                                                </span>
                                            </td>
                                            <td className="py-3 px-4 text-sm text-gray-700 dark:text-gray-300">
                                                {conn.client_ip || 'N/A'}
                                            </td>
                                            <td className="py-3 px-4 text-sm text-gray-700 dark:text-gray-300">
                                                {conn.virtual_ip || 'N/A'}
                                            </td>
                                            <td className="py-3 px-4 text-sm text-gray-700 dark:text-gray-300">
                                                {conn.connected_at ? new Date(conn.connected_at).toLocaleString() : 'N/A'}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div className="flex items-center justify-between p-6 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900">
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                        Total: <span className="font-semibold">{connections.length}</span> active connection{connections.length !== 1 ? 's' : ''}
                    </p>
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

export default ActiveConnectionsModal;
