import React, { useState, useEffect } from 'react';
import { Plus, Globe, Play, Square, Trash2, RefreshCw, Settings } from 'lucide-react';
import { apiService } from '../services/api';

const Tunnels = () => {
    const [tunnels, setTunnels] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showCreateModal, setShowCreateModal] = useState(false);

    useEffect(() => {
        loadTunnels();
    }, []);

    const loadTunnels = async () => {
        try {
            const response = await apiService.getTunnels();
            setTunnels(response.data);
            setLoading(false);
        } catch (error) {
            console.error('Failed to load tunnels:', error);
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
                        <Globe className="text-green-500" size={36} />
                        Tunnel Management
                    </h1>
                    <p className="text-gray-600 dark:text-gray-400 mt-2">
                        Configure Iran-Foreign tunnels for your VPN servers
                    </p>
                </div>
                <button
                    onClick={() => setShowCreateModal(true)}
                    className="flex items-center gap-2 px-6 py-3 bg-green-500 hover:bg-green-600 text-white rounded-lg font-medium transition-colors shadow-md"
                >
                    <Plus size={20} />
                    Create Tunnel
                </button>
            </div>

            {/* Tunnels List */}
            {tunnels.length === 0 ? (
                <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-12 text-center">
                    <Globe className="mx-auto text-gray-400 mb-4" size={64} />
                    <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">No Tunnels Yet</h2>
                    <p className="text-gray-600 dark:text-gray-400 mb-6">
                        Create your first Iran-Foreign tunnel to get started
                    </p>
                    <button
                        onClick={() => setShowCreateModal(true)}
                        className="inline-flex items-center gap-2 px-6 py-3 bg-green-500 hover:bg-green-600 text-white rounded-lg font-medium transition-colors"
                    >
                        <Plus size={20} />
                        Create Tunnel
                    </button>
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {tunnels.map((tunnel) => (
                        <TunnelCard key={tunnel.id} tunnel={tunnel} onRefresh={loadTunnels} />
                    ))}
                </div>
            )}
        </div>
    );
};

const TunnelCard = ({ tunnel, onRefresh }) => {
    const [status, setStatus] = useState(null);
    const [loading, setLoading] = useState(false);

    const loadStatus = async () => {
        try {
            const response = await apiService.getTunnelStatus(tunnel.id);
            setStatus(response.data);
        } catch (error) {
            console.error('Failed to load tunnel status:', error);
        }
    };

    useEffect(() => {
        loadStatus();
        const interval = setInterval(loadStatus, 10000); // Refresh every 10s
        return () => clearInterval(interval);
    }, [tunnel.id]);

    const isActive = status?.status === 'active';

    return (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 border-l-4 border-green-500">
            <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                    {tunnel.name || `Tunnel ${tunnel.id}`}
                </h3>
                <span
                    className={`px-3 py-1 rounded-full text-xs font-medium ${isActive
                            ? 'bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200'
                            : 'bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-200'
                        }`}
                >
                    {isActive ? 'Active' : 'Inactive'}
                </span>
            </div>

            <div className="space-y-2 mb-4">
                <div className="flex justify-between text-sm">
                    <span className="text-gray-600 dark:text-gray-400">Type:</span>
                    <span className="text-gray-900 dark:text-white font-medium">
                        {tunnel.tunnel_type || 'N/A'}
                    </span>
                </div>
                <div className="flex justify-between text-sm">
                    <span className="text-gray-600 dark:text-gray-400">Iran Server:</span>
                    <span className="text-gray-900 dark:text-white font-medium">
                        {tunnel.iran_ip || 'N/A'}
                    </span>
                </div>
                <div className="flex justify-between text-sm">
                    <span className="text-gray-600 dark:text-gray-400">Foreign Server:</span>
                    <span className="text-gray-900 dark:text-white font-medium">
                        {tunnel.foreign_ip || 'N/A'}
                    </span>
                </div>
            </div>

            <div className="flex gap-2">
                <button
                    onClick={loadStatus}
                    className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg text-sm font-medium transition-colors"
                    title="Refresh Status"
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

export default Tunnels;
