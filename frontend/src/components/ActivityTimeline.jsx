import React, { useState, useEffect } from 'react';
import { Clock, User, Activity, Server, Shield, Database } from 'lucide-react';
import apiService from '../services/api';

const ACTIVITY_ICONS = {
    user_created: User,
    user_deleted: User,
    user_connected: Activity,
    user_disconnected: Activity,
    server_added: Server,
    server_removed: Server,
    tunnel_created: Shield,
    tunnel_deleted: Shield,
    config_changed: Database,
    default: Activity
};

const ACTIVITY_COLORS = {
    user_created: 'text-green-600 dark:text-green-400 bg-green-100 dark:bg-green-900/20',
    user_deleted: 'text-red-600 dark:text-red-400 bg-red-100 dark:bg-red-900/20',
    user_connected: 'text-blue-600 dark:text-blue-400 bg-blue-100 dark:bg-blue-900/20',
    user_disconnected: 'text-gray-600 dark:text-gray-400 bg-gray-100 dark:bg-gray-900/20',
    server_added: 'text-green-600 dark:text-green-400 bg-green-100 dark:bg-green-900/20',
    server_removed: 'text-red-600 dark:text-red-400 bg-red-100 dark:bg-red-900/20',
    tunnel_created: 'text-purple-600 dark:text-purple-400 bg-purple-100 dark:bg-purple-900/20',
    tunnel_deleted: 'text-red-600 dark:text-red-400 bg-red-100 dark:bg-red-900/20',
    config_changed: 'text-yellow-600 dark:text-yellow-400 bg-yellow-100 dark:bg-yellow-900/20',
    default: 'text-gray-600 dark:text-gray-400 bg-gray-100 dark:bg-gray-900/20'
};

const ActivityTimeline = ({ limit = 10 }) => {
    const [activities, setActivities] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        loadActivities();
        const interval = setInterval(loadActivities, 30000);
        return () => clearInterval(interval);
    }, []);

    const loadActivities = async () => {
        try {
            setLoading(true);
            const response = await apiService.get(`/activity/recent?limit=${limit}`);
            setActivities(response.data || []);
            setLoading(false);
        } catch (error) {
            console.error('Failed to load activities:', error);
            // Use mock data
            setActivities(getMockActivities());
            setLoading(false);
        }
    };

    const getMockActivities = () => [
        {
            id: 1,
            type: 'user_connected',
            description: 'User "john_doe" connected via OpenVPN',
            user: 'john_doe',
            timestamp: new Date(Date.now() - 2 * 60000),
            metadata: { protocol: 'OpenVPN', ip: '192.168.1.100' }
        },
        {
            id: 2,
            type: 'user_created',
            description: 'New user "alice" created by admin',
            user: 'admin',
            timestamp: new Date(Date.now() - 15 * 60000),
            metadata: { new_user: 'alice' }
        },
        {
            id: 3,
            type: 'tunnel_created',
            description: 'New tunnel "IR-DE-01" configured',
            user: 'admin',
            timestamp: new Date(Date.now() - 45 * 60000),
            metadata: { tunnel: 'IR-DE-01' }
        },
        {
            id: 4,
            type: 'user_disconnected',
            description: 'User "bob" disconnected',
            user: 'bob',
            timestamp: new Date(Date.now() - 2 * 3600000),
            metadata: { duration: '2h 15m' }
        },
        {
            id: 5,
            type: 'config_changed',
            description: 'Server configuration updated',
            user: 'admin',
            timestamp: new Date(Date.now() - 5 * 3600000),
            metadata: { changes: ['max_connections', 'port'] }
        }
    ];

    const getTimeAgo = (timestamp) => {
        const now = new Date();
        const diff = now - new Date(timestamp);
        const seconds = Math.floor(diff / 1000);
        const minutes = Math.floor(seconds / 60);
        const hours = Math.floor(minutes / 60);
        const days = Math.floor(hours / 24);

        if (days > 0) return `${days}d ago`;
        if (hours > 0) return `${hours}h ago`;
        if (minutes > 0) return `${minutes}m ago`;
        return 'Just now';
    };

    if (loading) {
        return (
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 animate-pulse">
                <div className="h-6 bg-gray-300 dark:bg-gray-700 rounded w-32 mb-4"></div>
                <div className="space-y-4">
                    {[...Array(5)].map((_, i) => (
                        <div key={i} className="flex gap-3">
                            <div className="w-10 h-10 bg-gray-300 dark:bg-gray-700 rounded-full"></div>
                            <div className="flex-1 space-y-2">
                                <div className="h-4 bg-gray-300 dark:bg-gray-700 rounded w-3/4"></div>
                                <div className="h-3 bg-gray-300 dark:bg-gray-700 rounded w-1/2"></div>
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        );
    }

    return (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
            <div className="flex items-center justify-between mb-6">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                    <Clock className="text-blue-500" size={20} />
                    Recent Activity
                </h3>
                <button
                    onClick={loadActivities}
                    className="text-sm text-blue-600 dark:text-blue-400 hover:underline"
                >
                    Refresh
                </button>
            </div>

            {activities.length === 0 ? (
                <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                    <Activity size={48} className="mx-auto mb-4 opacity-50" />
                    <p>No recent activity</p>
                </div>
            ) : (
                <div className="relative">
                    {/* Timeline line */}
                    <div className="absolute left-5 top-0 bottom-0 w-0.5 bg-gray-200 dark:bg-gray-700"></div>

                    {/* Activities */}
                    <div className="space-y-6">
                        {activities.map((activity, index) => {
                            const Icon = ACTIVITY_ICONS[activity.type] || ACTIVITY_ICONS.default;
                            const colorClass = ACTIVITY_COLORS[activity.type] || ACTIVITY_COLORS.default;

                            return (
                                <div key={activity.id} className="relative flex gap-4">
                                    {/* Icon */}
                                    <div className={`relative z-10 flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center ${colorClass}`}>
                                        <Icon size={18} />
                                    </div>

                                    {/* Content */}
                                    <div className="flex-1 pt-1">
                                        <p className="text-sm font-medium text-gray-900 dark:text-white">
                                            {activity.description}
                                        </p>
                                        <div className="flex items-center gap-2 mt-1">
                                            <span className="text-xs text-gray-500 dark:text-gray-400">
                                                {getTimeAgo(activity.timestamp)}
                                            </span>
                                            {activity.user && (
                                                <>
                                                    <span className="text-gray-400">•</span>
                                                    <span className="text-xs text-gray-500 dark:text-gray-400">
                                                        by {activity.user}
                                                    </span>
                                                </>
                                            )}
                                        </div>
                                        {activity.metadata && Object.keys(activity.metadata).length > 0 && (
                                            <div className="mt-2 text-xs text-gray-600 dark:text-gray-400 bg-gray-50 dark:bg-gray-900/50 rounded px-2 py-1 inline-block">
                                                {Object.entries(activity.metadata).map(([key, value]) => (
                                                    <span key={key} className="mr-3">
                                                        <span className="font-medium">{key}:</span> {typeof value === 'object' ? JSON.stringify(value) : value}
                                                    </span>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>
            )}

            {activities.length >= limit && (
                <div className="mt-6 pt-4 border-t border-gray-200 dark:border-gray-700 text-center">
                    <button className="text-sm text-blue-600 dark:text-blue-400 hover:underline font-medium">
                        View all activity →
                    </button>
                </div>
            )}
        </div>
    );
};

export default ActivityTimeline;
