import React, { useState, useEffect } from 'react';
import { Plus, Server, Play, Square, Trash2, RefreshCw, Settings, HardDrive } from 'lucide-react';
import { apiService } from '../services/api';

const Servers = () => {
    const [servers, setServers] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showCreateModal, setShowCreateModal] = useState(false);

    useEffect(() => {
        loadServers();
    }, []);

    const loadServers = async () => {
        try {
            const response = await apiService.getServers();
            setServers(response.data);
            setLoading(false);
        } catch (error) {
            console.error('Failed to load servers:', error);
            setLoading(false);
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-screen">
                <div className="animate-spin rounded-full h-16 w-16 border-t-2 border-b-2 border-primary-500"></div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-6">
            {/* Header */}
            <div className="mb-8 flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-gray-900 dark:text-white flex items-center gap-3">
                        <Server className="text-blue-500" size={36} />
                        Server Management
                    </h1>
                    <p className="text-gray-600 dark:text-gray-400 mt-2">
                        Manage your VPN servers and monitor their status
                    </p>
                </div>
                <button
                    onClick={() => setShowCreateModal(true)}
                    className="flex items-center gap-2 px-6 py-3 bg-blue-500 hover:bg-blue-600 text-white rounded-lg font-medium transition-colors shadow-md"
                >
                    <Plus size={20} />
                    Add Server
                </button>
            </div>

            {/* Servers List */}
            {servers.length === 0 ? (
                <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-12 text-center">
                    <Server className="mx-auto text-gray-400 mb-4" size={64} />
                    <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">No Servers Yet</h2>
                    <p className="text-gray-600 dark:text-gray-400 mb-6">
                        Add your first VPN server to get started
                    </p>
                    <button
                        onClick={() => setShowCreateModal(true)}
                        className="inline-flex items-center gap-2 px-6 py-3 bg-blue-500 hover:bg-blue-600 text-white rounded-lg font-medium transition-colors"
                    >
                        <Plus size={20} />
                        Add Server
                    </button>
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {servers.map((server) => (
                        <ServerCard key={server.id} server={server} onRefresh={loadServers} />
                    ))}
                </div>
            )}
        </div>
    );
};

const ServerCard = ({ server, onRefresh }) => {
    const isOnline = server.status === 'online';

    return (
        <div className={`bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 border-l-4 ${isOnline ? 'border-green-500' : 'border-red-500'
            }`}>
            <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                    {server.name || `Server ${server.id}`}
                </h3>
                <span
                    className={`px-3 py-1 rounded-full text-xs font-medium ${isOnline
                            ? 'bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200'
                            : 'bg-red-100 dark:bg-red-900 text-red-800 dark:text-red-200'
                        }`}
                >
                    {isOnline ? 'Online' : 'Offline'}
                </span>
            </div>

            <div className="space-y-2 mb-4">
                <div className="flex justify-between text-sm">
                    <span className="text-gray-600 dark:text-gray-400">IP Address:</span>
                    <span className="text-gray-900 dark:text-white font-medium">
                        {server.ip_address || 'N/A'}
                    </span>
                </div>
                <div className="flex justify-between text-sm">
                    <span className="text-gray-600 dark:text-gray-400">Location:</span>
                    <span className="text-gray-900 dark:text-white font-medium">
                        {server.location || 'N/A'}
                    </span>
                </div>
                <div className="flex justify-between text-sm">
                    <span className="text-gray-600 dark:text-gray-400">Type:</span>
                    <span className="text-gray-900 dark:text-white font-medium">
                        {server.server_type || 'N/A'}
                    </span>
                </div>
                <div className="flex justify-between text-sm">
                    <span className="text-gray-600 dark:text-gray-400">Active Users:</span>
                    <span className="text-gray-900 dark:text-white font-medium">
                        {server.active_users || 0}
                    </span>
                </div>
            </div>

            {/* Protocol Badges */}
            <div className="flex flex-wrap gap-2 mb-4">
                {server.openvpn_enabled && (
                    <span className="px-2 py-1 bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 text-xs rounded-full">
                        OpenVPN
                    </span>
                )}
                {server.wireguard_enabled && (
                    <span className="px-2 py-1 bg-purple-100 dark:bg-purple-900 text-purple-800 dark:text-purple-200 text-xs rounded-full">
                        WireGuard
                    </span>
                )}
                {server.l2tp_enabled && (
                    <span className="px-2 py-1 bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200 text-xs rounded-full">
                        L2TP
                    </span>
                )}
                {server.cisco_enabled && (
                    <span className="px-2 py-1 bg-orange-100 dark:bg-orange-900 text-orange-800 dark:text-orange-200 text-xs rounded-full">
                        Cisco
                    </span>
                )}
            </div>

            <div className="flex gap-2">
                <button
                    onClick={onRefresh}
                    className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg text-sm font-medium transition-colors"
                    title="Refresh"
                >
                    <RefreshCw size={16} />
                </button>
                <button
                    className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-gray-500 hover:bg-gray-600 text-white rounded-lg text-sm font-medium transition-colors"
                    title="Settings"
                >
                    <Settings size={16} />
                </button>
                <button
                    className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-red-500 hover:bg-red-600 text-white rounded-lg text-sm font-medium transition-colors"
                    title="Delete"
                >
                    <Trash2 size={16} />
                </button>
            </div>
        </div>
    );
};

export default Servers;
