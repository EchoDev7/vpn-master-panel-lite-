import React, { useState, useEffect } from 'react';
import { Bell, X, Check, AlertCircle, Info, CheckCircle, XCircle, Clock } from 'lucide-react';
import apiService from '../services/api';

const NOTIFICATION_TYPES = {
    info: { icon: Info, color: 'blue', bgColor: 'bg-blue-50 dark:bg-blue-900/20', borderColor: 'border-blue-200 dark:border-blue-800' },
    success: { icon: CheckCircle, color: 'green', bgColor: 'bg-green-50 dark:bg-green-900/20', borderColor: 'border-green-200 dark:border-green-800' },
    warning: { icon: AlertCircle, color: 'yellow', bgColor: 'bg-yellow-50 dark:bg-yellow-900/20', borderColor: 'border-yellow-200 dark:border-yellow-800' },
    error: { icon: XCircle, color: 'red', bgColor: 'bg-red-50 dark:bg-red-900/20', borderColor: 'border-red-200 dark:border-red-800' }
};

const NotificationCenter = ({ isOpen, onClose }) => {
    const [notifications, setNotifications] = useState([]);
    const [loading, setLoading] = useState(true);
    const [filter, setFilter] = useState('all'); // all, unread, read

    useEffect(() => {
        if (isOpen) {
            loadNotifications();
        }
    }, [isOpen]);

    const loadNotifications = async () => {
        try {
            setLoading(true);
            const response = await apiService.get('/notifications');
            setNotifications(response.data || []);
            setLoading(false);
        } catch (error) {
            console.error('Failed to load notifications:', error);
            // Use mock data for now
            setNotifications(getMockNotifications());
            setLoading(false);
        }
    };

    const getMockNotifications = () => [
        {
            id: 1,
            type: 'success',
            title: 'New User Connected',
            message: 'User "john_doe" successfully connected via OpenVPN',
            timestamp: new Date(Date.now() - 5 * 60000),
            read: false
        },
        {
            id: 2,
            type: 'warning',
            title: 'High CPU Usage',
            message: 'Server CPU usage reached 85%. Consider scaling resources.',
            timestamp: new Date(Date.now() - 15 * 60000),
            read: false
        },
        {
            id: 3,
            type: 'info',
            title: 'System Update Available',
            message: 'A new version of VPN Master Panel is available.',
            timestamp: new Date(Date.now() - 2 * 3600000),
            read: true
        },
        {
            id: 4,
            type: 'error',
            title: 'Connection Failed',
            message: 'User "test_user" failed to connect. Invalid credentials.',
            timestamp: new Date(Date.now() - 24 * 3600000),
            read: true
        }
    ];

    const handleMarkAsRead = async (id) => {
        try {
            await apiService.post(`/notifications/${id}/read`);
            setNotifications(notifications.map(n =>
                n.id === id ? { ...n, read: true } : n
            ));
        } catch (error) {
            console.error('Failed to mark as read:', error);
            // Optimistic update
            setNotifications(notifications.map(n =>
                n.id === id ? { ...n, read: true } : n
            ));
        }
    };

    const handleMarkAllAsRead = async () => {
        try {
            await apiService.post('/notifications/read-all');
            setNotifications(notifications.map(n => ({ ...n, read: true })));
        } catch (error) {
            console.error('Failed to mark all as read:', error);
            setNotifications(notifications.map(n => ({ ...n, read: true })));
        }
    };

    const handleClearAll = async () => {
        try {
            await apiService.delete('/notifications');
            setNotifications([]);
        } catch (error) {
            console.error('Failed to clear notifications:', error);
            setNotifications([]);
        }
    };

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

    const filteredNotifications = notifications.filter(n => {
        if (filter === 'unread') return !n.read;
        if (filter === 'read') return n.read;
        return true;
    });

    const unreadCount = notifications.filter(n => !n.read).length;

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-start justify-end z-50 p-4">
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-2xl w-full max-w-md max-h-[90vh] flex flex-col mt-16 mr-4">
                {/* Header */}
                <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
                    <div className="flex items-center gap-3">
                        <Bell className="text-blue-500" size={24} />
                        <div>
                            <h2 className="text-lg font-bold text-gray-900 dark:text-white">
                                Notifications
                            </h2>
                            {unreadCount > 0 && (
                                <p className="text-xs text-gray-600 dark:text-gray-400">
                                    {unreadCount} unread
                                </p>
                            )}
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                    >
                        <X size={20} className="text-gray-600 dark:text-gray-400" />
                    </button>
                </div>

                {/* Filters */}
                <div className="flex items-center gap-2 p-4 border-b border-gray-200 dark:border-gray-700">
                    <button
                        onClick={() => setFilter('all')}
                        className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${filter === 'all'
                                ? 'bg-blue-500 text-white'
                                : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                            }`}
                    >
                        All ({notifications.length})
                    </button>
                    <button
                        onClick={() => setFilter('unread')}
                        className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${filter === 'unread'
                                ? 'bg-blue-500 text-white'
                                : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                            }`}
                    >
                        Unread ({unreadCount})
                    </button>
                    <button
                        onClick={() => setFilter('read')}
                        className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${filter === 'read'
                                ? 'bg-blue-500 text-white'
                                : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                            }`}
                    >
                        Read ({notifications.length - unreadCount})
                    </button>
                </div>

                {/* Actions */}
                {notifications.length > 0 && (
                    <div className="flex items-center gap-2 px-4 py-2 border-b border-gray-200 dark:border-gray-700">
                        <button
                            onClick={handleMarkAllAsRead}
                            className="text-sm text-blue-600 dark:text-blue-400 hover:underline"
                        >
                            Mark all as read
                        </button>
                        <span className="text-gray-400">•</span>
                        <button
                            onClick={handleClearAll}
                            className="text-sm text-red-600 dark:text-red-400 hover:underline"
                        >
                            Clear all
                        </button>
                    </div>
                )}

                {/* Notifications List */}
                <div className="flex-1 overflow-y-auto">
                    {loading ? (
                        <div className="p-8 text-center">
                            <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-blue-500 mx-auto"></div>
                        </div>
                    ) : filteredNotifications.length === 0 ? (
                        <div className="p-8 text-center text-gray-500 dark:text-gray-400">
                            <Bell size={48} className="mx-auto mb-4 opacity-50" />
                            <p>No notifications</p>
                        </div>
                    ) : (
                        <div className="divide-y divide-gray-200 dark:divide-gray-700">
                            {filteredNotifications.map((notification) => {
                                const config = NOTIFICATION_TYPES[notification.type] || NOTIFICATION_TYPES.info;
                                const Icon = config.icon;

                                return (
                                    <div
                                        key={notification.id}
                                        className={`p-4 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors ${!notification.read ? 'bg-blue-50/50 dark:bg-blue-900/10' : ''
                                            }`}
                                    >
                                        <div className="flex gap-3">
                                            <div className={`flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center ${config.bgColor}`}>
                                                <Icon size={20} className={`text-${config.color}-600 dark:text-${config.color}-400`} />
                                            </div>
                                            <div className="flex-1 min-w-0">
                                                <div className="flex items-start justify-between gap-2">
                                                    <h4 className="text-sm font-semibold text-gray-900 dark:text-white">
                                                        {notification.title}
                                                    </h4>
                                                    {!notification.read && (
                                                        <button
                                                            onClick={() => handleMarkAsRead(notification.id)}
                                                            className="flex-shrink-0 p-1 hover:bg-gray-200 dark:hover:bg-gray-600 rounded transition-colors"
                                                            title="Mark as read"
                                                        >
                                                            <Check size={16} className="text-gray-600 dark:text-gray-400" />
                                                        </button>
                                                    )}
                                                </div>
                                                <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                                                    {notification.message}
                                                </p>
                                                <div className="flex items-center gap-1 mt-2 text-xs text-gray-500 dark:text-gray-500">
                                                    <Clock size={12} />
                                                    <span>{getTimeAgo(notification.timestamp)}</span>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

// Notification Bell Button Component
export const NotificationBell = ({ onClick }) => {
    const [unreadCount, setUnreadCount] = useState(0);

    useEffect(() => {
        loadUnreadCount();
        const interval = setInterval(loadUnreadCount, 30000);
        return () => clearInterval(interval);
    }, []);

    const loadUnreadCount = async () => {
        try {
            const response = await apiService.get('/notifications/unread-count');
            setUnreadCount(response.data.count || 0);
        } catch (error) {
            // Mock data
            setUnreadCount(2);
        }
    };

    return (
        <button
            onClick={onClick}
            className="relative p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
            title="Notifications"
        >
            <Bell size={20} className="text-gray-700 dark:text-gray-300" />
            {unreadCount > 0 && (
                <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs font-bold rounded-full w-5 h-5 flex items-center justify-center">
                    {unreadCount > 9 ? '9+' : unreadCount}
                </span>
            )}
        </button>
    );
};

export default NotificationCenter;
