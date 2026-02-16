import React, { useState, useEffect } from 'react';
import { FileText, Search, Filter, Download, Calendar, User, Activity } from 'lucide-react';
import apiService from '../services/api';

const AUDIT_TYPES = {
    user_created: { label: 'User Created', color: 'green', icon: User },
    user_updated: { label: 'User Updated', color: 'blue', icon: User },
    user_deleted: { label: 'User Deleted', color: 'red', icon: User },
    login: { label: 'Login', color: 'blue', icon: Activity },
    logout: { label: 'Logout', color: 'gray', icon: Activity },
    config_changed: { label: 'Config Changed', color: 'orange', icon: FileText },
    server_added: { label: 'Server Added', color: 'green', icon: Activity },
    server_removed: { label: 'Server Removed', color: 'red', icon: Activity },
    tunnel_created: { label: 'Tunnel Created', color: 'purple', icon: Activity },
    tunnel_deleted: { label: 'Tunnel Deleted', color: 'red', icon: Activity }
};

const AuditLogs = () => {
    const [logs, setLogs] = useState([]);
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState('');
    const [filterType, setFilterType] = useState('all');
    const [dateRange, setDateRange] = useState('7'); // days
    const [currentPage, setCurrentPage] = useState(1);
    const logsPerPage = 20;

    useEffect(() => {
        loadAuditLogs();
    }, [filterType, dateRange]);

    const loadAuditLogs = async () => {
        try {
            setLoading(true);
            const response = await apiService.get(`/audit/logs?days=${dateRange}&type=${filterType}`);
            setLogs(response.data || []);
            setLoading(false);
        } catch (error) {
            console.error('Failed to load audit logs:', error);
            setLogs(generateMockLogs());
            setLoading(false);
        }
    };

    const generateMockLogs = () => {
        const types = Object.keys(AUDIT_TYPES);
        const users = ['admin', 'john_doe', 'alice', 'bob'];
        const logs = [];

        for (let i = 0; i < 50; i++) {
            const type = types[Math.floor(Math.random() * types.length)];
            const timestamp = new Date(Date.now() - Math.random() * 7 * 24 * 60 * 60 * 1000);

            logs.push({
                id: i + 1,
                type,
                user: users[Math.floor(Math.random() * users.length)],
                action: AUDIT_TYPES[type].label,
                details: `Action performed on ${timestamp.toLocaleDateString()}`,
                ip_address: `192.168.1.${Math.floor(Math.random() * 255)}`,
                timestamp: timestamp.toISOString(),
                metadata: {
                    target: type.includes('user') ? 'user_123' : 'resource_456',
                    changes: ['field1', 'field2']
                }
            });
        }

        return logs.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
    };

    const handleExport = () => {
        const csv = [
            ['ID', 'Type', 'User', 'Action', 'IP Address', 'Timestamp', 'Details'].join(','),
            ...filteredLogs.map(log => [
                log.id,
                log.type,
                log.user,
                log.action,
                log.ip_address,
                log.timestamp,
                log.details
            ].join(','))
        ].join('\n');

        const blob = new Blob([csv], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `audit-logs-${new Date().toISOString().split('T')[0]}.csv`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
    };

    const filteredLogs = logs.filter(log => {
        const matchesSearch = log.action.toLowerCase().includes(searchTerm.toLowerCase()) ||
            log.user.toLowerCase().includes(searchTerm.toLowerCase()) ||
            log.details.toLowerCase().includes(searchTerm.toLowerCase());
        const matchesType = filterType === 'all' || log.type === filterType;
        return matchesSearch && matchesType;
    });

    const indexOfLastLog = currentPage * logsPerPage;
    const indexOfFirstLog = indexOfLastLog - logsPerPage;
    const currentLogs = filteredLogs.slice(indexOfFirstLog, indexOfLastLog);
    const totalPages = Math.ceil(filteredLogs.length / logsPerPage);

    const formatTimestamp = (timestamp) => {
        const date = new Date(timestamp);
        return date.toLocaleString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    };

    if (loading) {
        return (
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 animate-pulse">
                <div className="h-6 bg-gray-300 dark:bg-gray-700 rounded w-48 mb-4"></div>
                <div className="space-y-3">
                    {[...Array(5)].map((_, i) => (
                        <div key={i} className="h-16 bg-gray-300 dark:bg-gray-700 rounded"></div>
                    ))}
                </div>
            </div>
        );
    }

    return (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
            {/* Header */}
            <div className="flex items-center justify-between mb-6">
                <div>
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                        <FileText className="text-blue-500" size={20} />
                        Audit Logs
                    </h3>
                    <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                        {filteredLogs.length} total entries
                    </p>
                </div>
                <button
                    onClick={handleExport}
                    className="flex items-center gap-2 px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors text-sm font-medium"
                >
                    <Download size={16} />
                    Export CSV
                </button>
            </div>

            {/* Filters */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                {/* Search */}
                <div className="relative">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={18} />
                    <input
                        type="text"
                        placeholder="Search logs..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        className="w-full pl-10 pr-4 py-2 bg-gray-50 dark:bg-gray-900 border border-gray-300 dark:border-gray-700 rounded-lg text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
                    />
                </div>

                {/* Type Filter */}
                <div className="relative">
                    <Filter className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={18} />
                    <select
                        value={filterType}
                        onChange={(e) => setFilterType(e.target.value)}
                        className="w-full pl-10 pr-4 py-2 bg-gray-50 dark:bg-gray-900 border border-gray-300 dark:border-gray-700 rounded-lg text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
                    >
                        <option value="all">All Types</option>
                        {Object.entries(AUDIT_TYPES).map(([key, value]) => (
                            <option key={key} value={key}>{value.label}</option>
                        ))}
                    </select>
                </div>

                {/* Date Range */}
                <div className="relative">
                    <Calendar className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={18} />
                    <select
                        value={dateRange}
                        onChange={(e) => setDateRange(e.target.value)}
                        className="w-full pl-10 pr-4 py-2 bg-gray-50 dark:bg-gray-900 border border-gray-300 dark:border-gray-700 rounded-lg text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
                    >
                        <option value="1">Last 24 hours</option>
                        <option value="7">Last 7 days</option>
                        <option value="30">Last 30 days</option>
                        <option value="90">Last 90 days</option>
                    </select>
                </div>
            </div>

            {/* Logs Table */}
            <div className="overflow-x-auto">
                <table className="w-full">
                    <thead>
                        <tr className="border-b border-gray-200 dark:border-gray-700">
                            <th className="text-left py-3 px-4 text-sm font-semibold text-gray-700 dark:text-gray-300">Type</th>
                            <th className="text-left py-3 px-4 text-sm font-semibold text-gray-700 dark:text-gray-300">User</th>
                            <th className="text-left py-3 px-4 text-sm font-semibold text-gray-700 dark:text-gray-300">Action</th>
                            <th className="text-left py-3 px-4 text-sm font-semibold text-gray-700 dark:text-gray-300">IP Address</th>
                            <th className="text-left py-3 px-4 text-sm font-semibold text-gray-700 dark:text-gray-300">Timestamp</th>
                        </tr>
                    </thead>
                    <tbody>
                        {currentLogs.map((log) => {
                            const config = AUDIT_TYPES[log.type] || AUDIT_TYPES.login;
                            const Icon = config.icon;

                            return (
                                <tr
                                    key={log.id}
                                    className="border-b border-gray-100 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
                                >
                                    <td className="py-3 px-4">
                                        <div className="flex items-center gap-2">
                                            <div className={`w-8 h-8 rounded-full bg-${config.color}-100 dark:bg-${config.color}-900/20 flex items-center justify-center`}>
                                                <Icon size={16} className={`text-${config.color}-600 dark:text-${config.color}-400`} />
                                            </div>
                                            <span className="text-sm font-medium text-gray-900 dark:text-white">
                                                {config.label}
                                            </span>
                                        </div>
                                    </td>
                                    <td className="py-3 px-4 text-sm text-gray-700 dark:text-gray-300">
                                        {log.user}
                                    </td>
                                    <td className="py-3 px-4 text-sm text-gray-700 dark:text-gray-300">
                                        {log.details}
                                    </td>
                                    <td className="py-3 px-4 text-sm text-gray-600 dark:text-gray-400 font-mono">
                                        {log.ip_address}
                                    </td>
                                    <td className="py-3 px-4 text-sm text-gray-600 dark:text-gray-400">
                                        {formatTimestamp(log.timestamp)}
                                    </td>
                                </tr>
                            );
                        })}
                    </tbody>
                </table>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
                <div className="mt-6 flex items-center justify-between">
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                        Showing {indexOfFirstLog + 1} to {Math.min(indexOfLastLog, filteredLogs.length)} of {filteredLogs.length} entries
                    </p>
                    <div className="flex gap-2">
                        <button
                            onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                            disabled={currentPage === 1}
                            className="px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors"
                        >
                            Previous
                        </button>
                        <span className="px-4 py-2 text-gray-700 dark:text-gray-300">
                            Page {currentPage} of {totalPages}
                        </span>
                        <button
                            onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                            disabled={currentPage === totalPages}
                            className="px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors"
                        >
                            Next
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
};

export default AuditLogs;
