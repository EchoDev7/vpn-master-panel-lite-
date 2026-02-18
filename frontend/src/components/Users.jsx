import React, { useState, useEffect } from 'react';
import { UserPlus, Trash2, RefreshCw, Key, Shield, CheckSquare, Square, MoreHorizontal, Activity, Clock, Download, Upload, X, Search, ChevronLeft, ChevronRight, Filter, Terminal, Power, CalendarPlus } from 'lucide-react';
import { apiService } from '../services/api';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer, AreaChart, Area } from 'recharts';

const Users = () => {
    const [users, setUsers] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showModal, setShowModal] = useState(false);
    const [modalMode, setModalMode] = useState('create'); // 'create' or 'edit'
    const [selectedUser, setSelectedUser] = useState(null);

    // Phase 3 State
    const [selectedUserIds, setSelectedUserIds] = useState(new Set());
    const [showDetailsModal, setShowDetailsModal] = useState(false);
    const [userDetails, setUserDetails] = useState(null);
    const [connectionLogs, setConnectionLogs] = useState([]);
    const [detailsLoading, setDetailsLoading] = useState(false);
    const [filterStatus, setFilterStatus] = useState(''); // backend param
    const [searchQuery, setSearchQuery] = useState('');
    const [page, setPage] = useState(1);
    const [pageSize, setPageSize] = useState(20);
    const [totalPages, setTotalPages] = useState(1);
    const [totalUsers, setTotalUsers] = useState(0);

    // Phase 4: Diagnostics
    const [activeTab, setActiveTab] = useState('overview'); // 'overview', 'logs'
    const [debugLogs, setDebugLogs] = useState([]);
    const [logsLoading, setLogsLoading] = useState(false);

    // Initial State matches backend UserCreate/UserUpdate models
    const initialFormState = {
        username: '',
        password: '',
        email: '',
        data_limit_gb: 0,
        expiry_days: 30,
        status: 'active',
        openvpn_enabled: true,
        wireguard_enabled: true,
        l2tp_enabled: false
    };

    const [formData, setFormData] = useState(initialFormState);

    useEffect(() => {
        loadUsers();
    }, [page, pageSize, filterStatus]);

    const loadUsers = async () => {
        try {
            setLoading(true);
            const params = {
                page,
                page_size: pageSize,
                search: searchQuery || undefined,
                status: filterStatus === 'all' || filterStatus === '' ? undefined : filterStatus
            };
            const response = await apiService.getUsers(params);
            setUsers(response.data.users || []);
            setTotalUsers(response.data.total);
            setTotalPages(Math.ceil(response.data.total / pageSize));
        } catch (error) {
            console.error('Failed to load users:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleSearchSubmit = (e) => {
        e.preventDefault();
        setPage(1);
        loadUsers();
    };

    const handleOpenCreate = () => {
        setModalMode('create');
        setFormData(initialFormState);
        setShowModal(true);
    };

    const handleOpenEdit = (user) => {
        setModalMode('edit');
        setSelectedUser(user);
        setFormData({
            username: user.username,
            password: '', // Leave empty to keep unchanged
            email: user.email || '',
            data_limit_gb: user.data_limit_gb,
            expiry_days: 0, // Not used in update directly mostly, but good to have
            status: user.status,
            openvpn_enabled: user.openvpn_enabled,
            wireguard_enabled: user.wireguard_enabled,
            l2tp_enabled: user.l2tp_enabled
        });
        setShowModal(true);
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        try {
            // Clean payload
            const payload = { ...formData };
            if (!payload.email) payload.email = null;
            if (modalMode === 'edit' && !payload.password) delete payload.password;

            if (modalMode === 'create') {
                await apiService.createUser(payload);
                alert('User created successfully!');
            } else {
                await apiService.updateUser(selectedUser.id, payload);
                alert('User updated successfully!');
            }

            setShowModal(false);
            loadUsers();
        } catch (error) {
            console.error('Operation error:', error);
            let errorMessage = `Failed to ${modalMode} user`;

            if (error.response?.data?.detail) {
                if (Array.isArray(error.response.data.detail)) {
                    errorMessage += ':\n' + error.response.data.detail.map(err =>
                        `- ${err.loc.join('.')} : ${err.msg}`
                    ).join('\n');
                } else {
                    errorMessage += ': ' + error.response.data.detail;
                }
            } else {
                errorMessage += ': ' + error.message;
            }

            alert(errorMessage);
        }
    };

    const [showConfigModal, setShowConfigModal] = useState(false);
    const [selectedConfigUser, setSelectedConfigUser] = useState(null);
    const [configType, setConfigType] = useState('openvpn');
    const [configContent, setConfigContent] = useState(null);
    const [configLoading, setConfigLoading] = useState(false);

    const handleOpenConfig = (user) => {
        setSelectedConfigUser(user);
        setShowConfigModal(true);
        setConfigContent(null);
        setConfigType('openvpn');
        loadConfig(user.id, 'openvpn');
    };

    const loadConfig = async (userId, type) => {
        try {
            setConfigLoading(true);
            setConfigType(type);
            setConfigContent(null);

            let response;
            if (type === 'openvpn') {
                response = await apiService.getUserConfigOpenVPN(userId);
            } else {
                response = await apiService.getUserConfigWireGuard(userId);
            }

            setConfigContent(response.data);
        } catch (error) {
            console.error('Failed to load config:', error);
            // Don't alert immediately, user sees empty state or we can show small error text
            setConfigContent({ content: `Error loading config: ${error.response?.data?.detail || error.message}`, filename: 'error.txt' });
        } finally {
            setConfigLoading(false);
        }
    };

    const [showRenewModal, setShowRenewModal] = useState(false);
    const [userToRenew, setUserToRenew] = useState(null);
    const [renewDays, setRenewDays] = useState(30);
    const [renewActivate, setRenewActivate] = useState(false); // Default false as per user request (no auto magic)

    const handleRenewClick = (user) => {
        setUserToRenew(user);
        setShowRenewModal(true);
        // Suggest activation if user is not active, but let admin decide
        if (user.status !== 'active') {
            setRenewActivate(true);
        } else {
            setRenewActivate(false);
        }
    };

    const confirmRenew = async () => {
        if (!userToRenew) return;
        try {
            // Calculate new date locally to support "Extension"
            const currentExpiry = userToRenew.expiry_date ? new Date(userToRenew.expiry_date) : new Date();
            const now = new Date();

            // If current expiry is in the future, add to it. If past, add to now.
            const baseDate = (currentExpiry > now) ? currentExpiry : now;
            const newExpiryDate = new Date(baseDate.getTime() + (renewDays * 24 * 60 * 60 * 1000));

            const payload = {
                expiry_date: newExpiryDate.toISOString()
            };

            if (renewActivate) {
                payload.status = 'active';
            }

            await apiService.updateUser(userToRenew.id, payload);
            alert(`User ${userToRenew.username} renewed until ${newExpiryDate.toLocaleDateString()}.`);
            loadUsers();
            setShowRenewModal(false);
            setUserToRenew(null);
        } catch (error) {
            console.error('Failed to renew user:', error);
            alert('Failed to renew user');
        }
    };

    const [showDeleteModal, setShowDeleteModal] = useState(false);
    const [userToDelete, setUserToDelete] = useState(null);

    const handleDeleteClick = (user) => {
        setUserToDelete(user);
        setShowDeleteModal(true);
    };

    const confirmDelete = async () => {
        if (!userToDelete) return;
        try {
            await apiService.deleteUser(userToDelete.id);
            loadUsers();
            setShowDeleteModal(false);
            setUserToDelete(null);
        } catch (error) {
            console.error('Failed to delete user:', error);
            alert('Failed to delete user');
        }
    };

    // Phase 3: Bulk Actions & Details
    const toggleSelectUser = (id) => {
        const newSelected = new Set(selectedUserIds);
        if (newSelected.has(id)) {
            newSelected.delete(id);
        } else {
            newSelected.add(id);
        }
        setSelectedUserIds(newSelected);
    };

    const toggleSelectAll = () => {
        if (selectedUserIds.size === users.length) {
            setSelectedUserIds(new Set());
        } else {
            setSelectedUserIds(new Set(users.map(u => u.id)));
        }
    };

    const handleBulkAction = async (action) => {
        if (!window.confirm(`Are you sure you want to ${action} ${selectedUserIds.size} users?`)) return;
        try {
            await apiService.bulkUserAction(action, Array.from(selectedUserIds));
            alert(`Bulk ${action} successful`);
            setSelectedUserIds(new Set());
            loadUsers();
        } catch (error) {
            console.error('Bulk action failed:', error);
            alert('Bulk action failed');
        }
    };

    const handleOpenDetails = async (user) => {
        setSelectedUser(user);
        setShowDetailsModal(true);
        setDetailsLoading(true);
        try {
            const [detailsRes, logsRes] = await Promise.all([
                apiService.getUserDetails(user.id),
                apiService.getUserConnections(user.id)
            ]);
            setUserDetails(detailsRes.data);
            setConnectionLogs(logsRes.data.logs);
        } catch (error) {
            console.error('Failed to load details:', error);
            alert('Failed to load user details');
        } finally {
            setDetailsLoading(false);
        }
    };

    const handleFetchLogs = async (userId) => {
        setLogsLoading(true);
        try {
            const response = await apiService.getUserLogs(userId);
            setDebugLogs(response.data.logs || []);
        } catch (error) {
            console.error('Failed to fetch logs:', error);
            setDebugLogs(['Error fetching logs.']);
        } finally {
            setLogsLoading(false);
        }
    };

    const handleKillSession = async (user) => {
        if (!window.confirm(`Are you sure you want to KILL the active session for ${user.username}? This will disconnect them immediately.`)) return;
        try {
            const response = await apiService.killUserSession(user.id);
            const results = response.data.results.join('\n');
            alert(`Session Kill Result:\n${results}`);
            // Refresh details to see if online status changes (might take a minute for sync)
            handleOpenDetails(user);
        } catch (error) {
            console.error('Failed to kill session:', error);
            alert('Failed to kill session');
        }
    };

    const handleResetTraffic = async (user) => {
        if (!window.confirm(`Reset traffic usage for ${user.username}?`)) return;
        try {
            await apiService.resetUserTraffic(user.id);
            loadUsers();
            alert('Traffic reset successfully');
        } catch (error) {
            console.error('Failed to reset traffic:', error);
            alert('Failed to reset traffic');
        }
    };

    if (loading && users.length === 0) {
        return <div className="p-8 text-center text-gray-400">Loading users...</div>;
    }

    return (
        <div className="p-6">
            <div className="flex justify-between items-center mb-6">
                <h2 className="text-2xl font-bold text-gray-100 flex items-center gap-2">
                    <Shield className="text-blue-500" /> User Management
                </h2>
                <button
                    onClick={handleOpenCreate}
                    className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg flex items-center gap-2 transition-colors"
                >
                    <UserPlus size={20} /> Add User
                </button>
            </div>


            {/* Bulk Actions Bar */}
            {
                selectedUserIds.size > 0 && (
                    <div className="bg-blue-900/30 border border-blue-500/30 p-4 rounded-xl mb-6 flex justify-between items-center backdrop-blur-sm animate-fade-in">
                        <span className="text-blue-200 font-medium">{selectedUserIds.size} users selected</span>
                        <div className="flex gap-3">
                            <button onClick={() => handleBulkAction('enable')} className="px-3 py-1.5 bg-green-600/80 hover:bg-green-600 text-white rounded-lg text-sm font-medium transition-colors">Enable</button>
                            <button onClick={() => handleBulkAction('disable')} className="px-3 py-1.5 bg-yellow-600/80 hover:bg-yellow-600 text-white rounded-lg text-sm font-medium transition-colors">Disable</button>
                            <button onClick={() => handleBulkAction('reset_traffic')} className="px-3 py-1.5 bg-purple-600/80 hover:bg-purple-600 text-white rounded-lg text-sm font-medium transition-colors">Reset Traffic</button>
                            <button onClick={() => handleBulkAction('delete')} className="px-3 py-1.5 bg-red-600/80 hover:bg-red-600 text-white rounded-lg text-sm font-medium transition-colors">Delete</button>
                        </div>
                    </div>
                )
            }

            <div className="flex flex-col md:flex-row justify-between items-center gap-4 mb-6 bg-gray-800 p-4 rounded-xl border border-gray-700 shadow-md">
                <div className="flex items-center gap-2 overflow-x-auto w-full md:w-auto no-scrollbar">
                    <Filter size={18} className="text-gray-400 min-w-[18px]" />
                    {['all', 'active', 'disabled', 'suspended', 'expired'].map(status => (
                        <button
                            key={status}
                            onClick={() => { setFilterStatus(status === 'all' ? '' : status); setPage(1); }}
                            className={`px-3 py-1.5 rounded-lg text-sm font-medium capitalize transition-colors whitespace-nowrap ${(filterStatus === status || (filterStatus === '' && status === 'all'))
                                ? 'bg-blue-600 text-white shadow-lg shadow-blue-900/40'
                                : 'bg-gray-700 text-gray-400 hover:bg-gray-600 hover:text-white'
                                }`}
                        >
                            {status}
                        </button>
                    ))}
                </div>

                <form onSubmit={handleSearchSubmit} className="relative w-full md:w-64">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={18} />
                    <input
                        type="text"
                        placeholder="Search users..."
                        className="w-full bg-gray-700 border border-gray-600 text-white rounded-lg pl-10 pr-4 py-2 focus:outline-none focus:border-blue-500 transition-colors"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                    />
                </form>
            </div>

            <div className="bg-gray-800 rounded-xl overflow-hidden shadow-2xl border border-gray-700">
                <table className="w-full text-left">
                    <thead className="bg-gray-700/50 text-gray-300">
                        <tr>
                            <th className="p-4 w-12 text-center">
                                <button onClick={toggleSelectAll} className="text-gray-400 hover:text-white">
                                    {selectedUserIds.size > 0 && selectedUserIds.size === users.length ? <CheckSquare size={20} /> : <Square size={20} />}
                                </button>
                            </th>
                            <th className="p-4">Username</th>
                            <th className="p-4">Status</th>
                            <th className="p-4">Data Limit</th>
                            <th className="p-4">Usage</th>
                            <th className="p-4">Expiry</th>
                            <th className="p-4 text-right">Actions</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-700">
                        {users.map((user) => (
                            <tr key={user.id} className={`hover:bg-gray-700/30 transition-colors ${selectedUserIds.has(user.id) ? 'bg-blue-900/10' : ''}`}>
                                <td className="p-4 text-center">
                                    <button onClick={() => toggleSelectUser(user.id)} className={`${selectedUserIds.has(user.id) ? 'text-blue-400' : 'text-gray-600 hover:text-gray-400'}`}>
                                        {selectedUserIds.has(user.id) ? <CheckSquare size={20} /> : <Square size={20} />}
                                    </button>
                                </td>
                                <td className="p-4 text-white font-medium">
                                    <button onClick={() => handleOpenDetails(user)} className="hover:underline hover:text-blue-400 text-left">
                                        {user.username}
                                    </button>
                                </td>
                                <td className="p-4">
                                    <div className="flex items-center gap-2">
                                        <div className={`w-2.5 h-2.5 rounded-full ${user.is_online ? 'bg-green-500 animate-pulse' : 'bg-gray-600'}`} title={user.is_online ? "Online" : "Offline"}></div>
                                        <span className={`px-2 py-1 rounded text-xs ${user.status === 'active' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
                                            {user.status}
                                        </span>
                                    </div>
                                </td>
                                <td className="p-4 text-gray-300">
                                    {user.data_limit_gb > 0 ? `${user.data_limit_gb} GB` : 'Unlimited'}
                                </td>
                                <td className="p-4 text-gray-300">
                                    <div className="flex flex-col gap-1">
                                        <span className="text-sm">{(user.data_usage_gb || 0).toFixed(2)} GB</span>
                                        {user.data_limit_gb > 0 && (
                                            <div className="w-24 h-1.5 bg-gray-700 rounded-full overflow-hidden">
                                                <div
                                                    className={`h-full rounded-full ${(user.data_usage_gb / user.data_limit_gb) > 0.9 ? 'bg-red-500' :
                                                        (user.data_usage_gb / user.data_limit_gb) > 0.7 ? 'bg-yellow-500' : 'bg-blue-500'
                                                        }`}
                                                    style={{ width: `${Math.min((user.data_usage_gb / user.data_limit_gb) * 100, 100)}%` }}
                                                ></div>
                                            </div>
                                        )}
                                    </div>
                                </td>
                                <td className="p-4 text-gray-300">
                                    {user.expiry_date ? new Date(user.expiry_date).toLocaleDateString() : 'Never'}
                                </td>
                                <td className="p-4 text-right space-x-2">
                                    <button onClick={() => handleOpenDetails(user)} className="text-gray-400 hover:text-white p-1" title="Details">
                                        <Activity size={18} />
                                    </button>
                                    <button onClick={() => handleOpenEdit(user)} className="text-blue-400 hover:text-blue-300 p-1" title="Edit">
                                        Edit
                                    </button>
                                    <button onClick={() => handleOpenConfig(user)} className="text-yellow-400 hover:text-yellow-300 p-1" title="Configuration">
                                        <Key size={18} />
                                    </button>
                                    <button onClick={() => handleRenewClick(user)} className="text-green-400 hover:text-green-300 p-1" title="Renew">
                                        <Clock size={18} />
                                    </button>
                                    <button onClick={() => handleResetTraffic(user)} className="text-purple-400 hover:text-purple-300 p-1" title="Reset Traffic">
                                        <RefreshCw size={18} />
                                    </button>
                                    <button onClick={() => handleDeleteClick(user)} className="text-red-400 hover:text-red-300 p-1" title="Delete">
                                        <Trash2 size={18} />
                                    </button>
                                </td>
                            </tr>
                        ))}
                        {users.length === 0 && (
                            <tr>
                                <td colSpan="6" className="p-8 text-center text-gray-500">
                                    No users found. Create one to get started.
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>

                {/* Pagination */}
                <div className="bg-gray-700/30 border-t border-gray-700 p-4 flex justify-between items-center">
                    <span className="text-sm text-gray-400">
                        Showing {users.length > 0 ? ((page - 1) * pageSize) + 1 : 0} to {Math.min(page * pageSize, totalUsers)} of {totalUsers} users
                    </span>
                    <div className="flex items-center gap-2">
                        <button
                            onClick={() => setPage(p => Math.max(1, p - 1))}
                            disabled={page === 1}
                            className="p-2 rounded-lg bg-gray-700 text-gray-300 hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            <ChevronLeft size={20} />
                        </button>
                        <div className="flex gap-1">
                            {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                                let p = i + 1;
                                if (totalPages > 5 && page > 3) p = page - 2 + i;
                                if (p > totalPages) return null;

                                return (
                                    <button
                                        key={p}
                                        onClick={() => setPage(p)}
                                        className={`w-8 h-8 rounded-lg text-sm font-medium ${page === p
                                            ? 'bg-blue-600 text-white'
                                            : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                                            }`}
                                    >
                                        {p}
                                    </button>
                                );
                            })}
                        </div>
                        <button
                            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                            disabled={page === totalPages}
                            className="p-2 rounded-lg bg-gray-700 text-gray-300 hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            <ChevronRight size={20} />
                        </button>
                    </div>
                </div>
            </div>

            {/* User Modal (Create/Edit) */}
            {
                showModal && (
                    <div className="fixed inset-0 bg-black/70 flex items-center justify-center p-4 z-50">
                        <div className="bg-gray-800 rounded-xl p-6 w-full max-w-md border border-gray-700 shadow-2xl">
                            <h3 className="text-xl font-bold text-white mb-4">
                                {modalMode === 'create' ? 'Create New User' : 'Edit User'}
                            </h3>
                            <form onSubmit={handleSubmit} className="space-y-4">
                                <div>
                                    <label className="block text-gray-400 text-sm mb-1">Username</label>
                                    <input
                                        type="text"
                                        required
                                        disabled={modalMode === 'edit'}
                                        className={`w-full bg-gray-700 border border-gray-600 rounded-lg p-2 text-white focus:outline-none focus:border-blue-500 ${modalMode === 'edit' ? 'opacity-50 cursor-not-allowed' : ''}`}
                                        value={formData.username}
                                        onChange={e => setFormData({ ...formData, username: e.target.value })}
                                    />
                                </div>
                                <div>
                                    <label className="block text-gray-400 text-sm mb-1">
                                        Password {modalMode === 'edit' && '(Leave blank to keep unchanged)'}
                                    </label>
                                    <input
                                        type="text"
                                        required={modalMode === 'create'}
                                        minLength={6}
                                        placeholder={modalMode === 'create' ? "Min 6 chars" : "New password"}
                                        className="w-full bg-gray-700 border border-gray-600 rounded-lg p-2 text-white focus:outline-none focus:border-blue-500"
                                        value={formData.password}
                                        onChange={e => setFormData({ ...formData, password: e.target.value })}
                                    />
                                </div>
                                <div>
                                    <label className="block text-gray-400 text-sm mb-1">Email (Optional)</label>
                                    <input
                                        type="email"
                                        className="w-full bg-gray-700 border border-gray-600 rounded-lg p-2 text-white focus:outline-none focus:border-blue-500"
                                        value={formData.email}
                                        onChange={e => setFormData({ ...formData, email: e.target.value })}
                                    />
                                </div>
                                <div className="grid grid-cols-2 gap-4">
                                    <div>
                                        <label className="block text-gray-400 text-sm mb-1">Data Limit (GB)</label>
                                        <input
                                            type="number"
                                            min="0"
                                            step="0.1"
                                            className="w-full bg-gray-700 border border-gray-600 rounded-lg p-2 text-white focus:outline-none focus:border-blue-500"
                                            value={formData.data_limit_gb}
                                            onChange={e => {
                                                // Handle leading zeros or empty string cleanly
                                                const val = e.target.value;
                                                setFormData({ ...formData, data_limit_gb: val === '' ? 0 : parseFloat(val) })
                                            }}
                                        />
                                        <span className="text-xs text-gray-500">0 = Unlimited</span>
                                    </div>
                                    <div>
                                        {modalMode === 'create' && (
                                            <>
                                                <label className="block text-gray-400 text-sm mb-1">Duration (Days)</label>
                                                <input
                                                    type="number"
                                                    min="0"
                                                    className="w-full bg-gray-700 border border-gray-600 rounded-lg p-2 text-white focus:outline-none focus:border-blue-500"
                                                    value={formData.expiry_days}
                                                    onChange={e => setFormData({ ...formData, expiry_days: parseInt(e.target.value) })}
                                                />
                                            </>
                                        )}
                                        {modalMode === 'edit' && (
                                            <>
                                                <label className="block text-gray-400 text-sm mb-1">Status</label>
                                                <select
                                                    value={formData.status}
                                                    onChange={e => setFormData({ ...formData, status: e.target.value })}
                                                    className="w-full bg-gray-700 border border-gray-600 rounded-lg p-2 text-white focus:outline-none focus:border-blue-500"
                                                >
                                                    <option value="active">Active</option>
                                                    <option value="disabled">Disabled</option>
                                                    <option value="suspended">Suspended</option>
                                                </select>
                                            </>
                                        )}
                                    </div>
                                </div>

                                <div className="bg-gray-700/30 p-3 rounded-lg border border-gray-700">
                                    <label className="block text-gray-400 text-sm mb-2">Allowed Protocols</label>
                                    <div className="flex gap-4">
                                        <label className="flex items-center gap-2 cursor-pointer">
                                            <input
                                                type="checkbox"
                                                checked={formData.openvpn_enabled}
                                                onChange={e => setFormData({ ...formData, openvpn_enabled: e.target.checked })}
                                                className="form-checkbox bg-gray-600 border-gray-500 rounded text-blue-500 focus:ring-0 focus:ring-offset-0"
                                            />
                                            <span className="text-gray-300 text-sm">OpenVPN</span>
                                        </label>
                                        <label className="flex items-center gap-2 cursor-pointer">
                                            <input
                                                type="checkbox"
                                                checked={formData.wireguard_enabled}
                                                onChange={e => setFormData({ ...formData, wireguard_enabled: e.target.checked })}
                                                className="form-checkbox bg-gray-600 border-gray-500 rounded text-green-500 focus:ring-0 focus:ring-offset-0"
                                            />
                                            <span className="text-gray-300 text-sm">WireGuard</span>
                                        </label>
                                        <label className="flex items-center gap-2 cursor-pointer">
                                            <input
                                                type="checkbox"
                                                checked={formData.l2tp_enabled}
                                                onChange={e => setFormData({ ...formData, l2tp_enabled: e.target.checked })}
                                                className="form-checkbox bg-gray-600 border-gray-500 rounded text-purple-500 focus:ring-0 focus:ring-offset-0"
                                            />
                                            <span className="text-gray-300 text-sm">L2TP</span>
                                        </label>
                                    </div>
                                </div>

                                <div className="flex gap-3 mt-6">
                                    <button
                                        type="button"
                                        onClick={() => setShowModal(false)}
                                        className="flex-1 bg-gray-700 hover:bg-gray-600 text-white py-2 rounded-lg"
                                    >
                                        Cancel
                                    </button>
                                    <button
                                        type="submit"
                                        className="flex-1 bg-blue-600 hover:bg-blue-700 text-white py-2 rounded-lg font-medium"
                                    >
                                        {modalMode === 'create' ? 'Create User' : 'Update User'}
                                    </button>
                                </div>
                            </form>
                        </div>
                    </div>
                )
            }

            {/* Delete Confirmation Modal */}
            {
                showDeleteModal && userToDelete && (
                    <div className="fixed inset-0 bg-black/70 flex items-center justify-center p-4 z-50">
                        <div className="bg-gray-800 rounded-xl p-6 w-full max-w-sm border border-gray-700 shadow-2xl text-center">
                            <Trash2 className="mx-auto text-red-500 mb-4" size={48} />
                            <h3 className="text-xl font-bold text-white mb-2">Delete User?</h3>
                            <p className="text-gray-400 mb-6">
                                Are you sure you want to delete <span className="text-white font-semibold">{userToDelete.username}</span>? This action cannot be undone.
                            </p>
                            <div className="flex gap-3">
                                <button
                                    onClick={() => setShowDeleteModal(false)}
                                    className="flex-1 bg-gray-700 hover:bg-gray-600 text-white py-2 rounded-lg"
                                >
                                    Cancel
                                </button>
                                <button
                                    onClick={confirmDelete}
                                    className="flex-1 bg-red-600 hover:bg-red-700 text-white py-2 rounded-lg font-medium"
                                >
                                    Delete
                                </button>
                            </div>
                        </div>
                    </div>
                )
            }

            {/* Renew Modal */}
            {
                showRenewModal && userToRenew && (
                    <div className="fixed inset-0 bg-black/70 flex items-center justify-center p-4 z-50">
                        <div className="bg-gray-800 rounded-xl p-6 w-full max-w-sm border border-gray-700 shadow-2xl">
                            <h3 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
                                <CalendarPlus className="text-green-500" /> Extend Expiry
                            </h3>
                            <p className="text-gray-300 mb-4">
                                Extend access for <span className="font-semibold text-white">{userToRenew.username}</span>.
                                Days will be added to the current expiry date (or now if expired).
                            </p>
                            <div className="mb-6">
                                <label className="block text-gray-400 text-sm mb-2">Duration (Days)</label>
                                <div className="flex gap-2 mb-2">
                                    {[30, 90, 180, 365].map(days => (
                                        <button
                                            key={days}
                                            onClick={() => setRenewDays(days)}
                                            className={`px-3 py-1 rounded text-sm transition-colors ${renewDays === days ? 'bg-green-600 text-white' : 'bg-gray-700 text-gray-300 hover:bg-gray-600'}`}
                                        >
                                            {days}d
                                        </button>
                                    ))}
                                </div>
                                <input
                                    type="number"
                                    min="1"
                                    className="w-full bg-gray-700 border border-gray-600 rounded-lg p-2 text-white focus:outline-none focus:border-green-500"
                                    value={renewDays}
                                    onChange={e => setRenewDays(parseInt(e.target.value) || 0)}
                                />
                                <div className="mt-4 flex items-center gap-2">
                                    <input
                                        type="checkbox"
                                        id="renewActivate"
                                        checked={renewActivate}
                                        onChange={e => setRenewActivate(e.target.checked)}
                                        className="rounded bg-gray-700 border-gray-600 text-green-500 focus:ring-0 w-4 h-4 cursor-pointer"
                                    />
                                    <label htmlFor="renewActivate" className="text-gray-300 text-sm cursor-pointer select-none">
                                        Activate user (Set status to Active)
                                    </label>
                                </div>
                            </div>
                            <div className="flex gap-3">
                                <button
                                    onClick={() => setShowRenewModal(false)}
                                    className="flex-1 bg-gray-700 hover:bg-gray-600 text-white py-2 rounded-lg"
                                >
                                    Cancel
                                </button>
                                <button
                                    onClick={confirmRenew}
                                    className="flex-1 bg-green-600 hover:bg-green-700 text-white py-2 rounded-lg font-medium"
                                >
                                    Confirm
                                </button>
                            </div>
                        </div>
                    </div>
                )
            }

            {/* Config Modal */}
            {
                showConfigModal && selectedConfigUser && (
                    <div className="fixed inset-0 bg-black/70 flex items-center justify-center p-4 z-50">
                        <div className="bg-gray-800 rounded-xl p-6 w-full max-w-2xl border border-gray-700 shadow-2xl h-[80vh] flex flex-col">
                            <div className="flex justify-between items-center mb-4">
                                <h3 className="text-xl font-bold text-white flex items-center gap-2">
                                    <Key className="text-yellow-500" /> Configuration: {selectedConfigUser.username}
                                </h3>
                                <button onClick={() => setShowConfigModal(false)} className="text-gray-400 hover:text-white">
                                    ✕
                                </button>
                            </div>

                            <div className="flex gap-2 mb-4">
                                <button
                                    onClick={() => loadConfig(selectedConfigUser.id, 'openvpn')}
                                    className={`px-4 py-2 rounded-lg flex-1 font-medium ${configType === 'openvpn' ? 'bg-primary-600 text-white' : 'bg-gray-700 text-gray-300 hover:bg-gray-600'}`}
                                >
                                    OpenVPN
                                </button>
                                <button
                                    onClick={() => loadConfig(selectedConfigUser.id, 'wireguard')}
                                    className={`px-4 py-2 rounded-lg flex-1 font-medium ${configType === 'wireguard' ? 'bg-green-600 text-white' : 'bg-gray-700 text-gray-300 hover:bg-gray-600'}`}
                                >
                                    WireGuard
                                </button>
                            </div>

                            <div className="flex-1 overflow-hidden bg-gray-900 rounded-lg border border-gray-700 relative">
                                {configLoading ? (
                                    <div className="absolute inset-0 flex items-center justify-center text-gray-400">
                                        Loading configuration...
                                    </div>
                                ) : configContent ? (
                                    <textarea
                                        readOnly
                                        value={configContent.content}
                                        className="w-full h-full bg-transparent text-gray-300 p-4 font-mono text-xs resize-none focus:outline-none"
                                    />
                                ) : (
                                    <div className="absolute inset-0 flex items-center justify-center text-gray-500 flex-col gap-2">
                                        <p>Select a protocol to view config</p>
                                        <p className="text-xs">Ensure the protocol is enabled for this user</p>
                                    </div>
                                )}
                            </div>

                            <div className="mt-4 flex justify-end gap-3">
                                <button
                                    onClick={() => {
                                        if (!configContent) return;
                                        const blob = new Blob([configContent.content], { type: 'text/plain' });
                                        const url = window.URL.createObjectURL(blob);
                                        const a = document.createElement('a');
                                        a.href = url;
                                        a.download = configContent.filename;
                                        a.click();
                                    }}
                                    disabled={!configContent}
                                    className={`px-4 py-2 rounded-lg font-medium flex items-center gap-2 ${configContent ? 'bg-blue-600 hover:bg-blue-700 text-white' : 'bg-gray-700 text-gray-500 cursor-not-allowed'}`}
                                >
                                    Download File
                                </button>
                                <button
                                    onClick={() => setShowConfigModal(false)}
                                    className="bg-gray-700 hover:bg-gray-600 text-white px-4 py-2 rounded-lg"
                                >
                                    Close
                                </button>
                            </div>
                        </div>
                    </div>
                )
            }

            {/* Details Modal (Phase 3) */}
            {
                showDetailsModal && selectedUser && (
                    <div className="fixed inset-0 bg-black/80 flex items-center justify-center p-4 z-50 backdrop-blur-sm">
                        <div className="bg-gray-800 rounded-xl w-full max-w-4xl max-h-[90vh] border border-gray-700 shadow-2xl overflow-hidden flex flex-col">
                            <div className="p-6 border-b border-gray-700 flex justify-between items-center bg-gray-900/50">
                                <div>
                                    <h3 className="text-2xl font-bold text-white flex items-center gap-3">
                                        <Activity className="text-blue-500" /> {selectedUser.username}
                                        <span className={`px-2 py-0.5 rounded text-sm ${selectedUser.status === 'active' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
                                            {selectedUser.status}
                                        </span>
                                    </h3>
                                    <div className="flex gap-4 mt-4">
                                        <button
                                            onClick={() => setActiveTab('overview')}
                                            className={`pb-2 text-sm font-medium transition-colors border-b-2 ${activeTab === 'overview' ? 'text-blue-400 border-blue-400' : 'text-gray-400 border-transparent hover:text-gray-300'}`}
                                        >
                                            Overview
                                        </button>
                                        <button
                                            onClick={() => { setActiveTab('logs'); handleFetchLogs(selectedUser.id); }}
                                            className={`pb-2 text-sm font-medium transition-colors border-b-2 ${activeTab === 'logs' ? 'text-blue-400 border-blue-400' : 'text-gray-400 border-transparent hover:text-gray-300'}`}
                                        >
                                            Troubleshooting Logs
                                        </button>
                                    </div>
                                </div>
                                <div className="flex items-center gap-3">
                                    {selectedUser.is_online && (
                                        <button
                                            onClick={() => handleKillSession(selectedUser)}
                                            className="bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/50 px-3 py-1.5 rounded-lg flex items-center gap-2 text-xs font-bold uppercase tracking-wider transition-colors"
                                        >
                                            <Power size={14} /> Kill Session
                                        </button>
                                    )}
                                    <button onClick={() => setShowDetailsModal(false)} className="text-gray-400 hover:text-white p-2 hover:bg-gray-700/50 rounded-lg transition-colors">
                                        <X size={24} />
                                    </button>
                                </div>
                            </div>

                            <div className="p-6 overflow-y-auto custom-scrollbar space-y-8 flex-1">
                                {detailsLoading ? (
                                    <div className="flex justify-center py-20">
                                        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
                                    </div>
                                ) : activeTab === 'overview' ? (
                                    <>
                                        {/* Stats Cards & Chart */}
                                        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                                            {/* Cards Column */}
                                            <div className="space-y-6">
                                                <div className="bg-gray-700/30 p-5 rounded-xl border border-gray-700">
                                                    <p className="text-gray-400 text-sm font-medium mb-1">Total Traffic</p>
                                                    <h4 className="text-2xl font-bold text-white mb-2">{userDetails?.stats?.total_traffic_gb} GB</h4>
                                                    <div className="flex gap-4 text-xs">
                                                        <span className="flex items-center gap-1 text-green-400"><Upload size={12} /> Upload</span>
                                                        <span className="flex items-center gap-1 text-blue-400"><Download size={12} /> Download</span>
                                                    </div>
                                                </div>
                                                <div className="bg-gray-700/30 p-5 rounded-xl border border-gray-700">
                                                    <p className="text-gray-400 text-sm font-medium mb-1">Expiry Date</p>
                                                    <h4 className="text-2xl font-bold text-white mb-2">
                                                        {selectedUser.expiry_date ? new Date(selectedUser.expiry_date).toLocaleDateString() : 'Never'}
                                                    </h4>
                                                    <p className="text-xs text-yellow-400">{userDetails?.stats?.days_until_expiry ?? '∞'} days remaining</p>
                                                </div>
                                                <div className="bg-gray-700/30 p-5 rounded-xl border border-gray-700">
                                                    <p className="text-gray-400 text-sm font-medium mb-1">Last Seen</p>
                                                    <h4 className="text-xl font-bold text-white mb-2">
                                                        {selectedUser.last_connection ? new Date(selectedUser.last_connection).toLocaleString() : 'Never'}
                                                    </h4>
                                                    <p className="text-xs text-gray-400">
                                                        {selectedUser.is_online ? <span className="text-green-400 font-bold">● Online Now</span> : 'Offline'}
                                                    </p>
                                                </div>
                                            </div>

                                            {/* Chart Column */}
                                            <div className="lg:col-span-2 bg-gray-700/30 p-5 rounded-xl border border-gray-700 flex flex-col">
                                                <h4 className="text-gray-200 font-bold mb-4 flex items-center gap-2">
                                                    <Activity size={18} className="text-blue-400" /> Recent Activity (Duration)
                                                </h4>
                                                <div className="flex-1 min-h-[200px]">
                                                    <ResponsiveContainer width="100%" height="100%">
                                                        <AreaChart data={connectionLogs.slice(0, 10).reverse().map(log => ({
                                                            time: new Date(log.connected_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
                                                            duration: Math.round(((log.disconnected_at ? new Date(log.disconnected_at) : new Date()) - new Date(log.connected_at)) / 60000),
                                                            protocol: log.protocol
                                                        }))}>
                                                            <defs>
                                                                <linearGradient id="colorDuration" x1="0" y1="0" x2="0" y2="1">
                                                                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.8} />
                                                                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                                                                </linearGradient>
                                                            </defs>
                                                            <CartesianGrid strokeDasharray="3 3" stroke="#374151" vertical={false} />
                                                            <XAxis dataKey="time" stroke="#9ca3af" tick={{ fontSize: 12 }} />
                                                            <YAxis stroke="#9ca3af" tick={{ fontSize: 12 }} unit="m" />
                                                            <RechartsTooltip
                                                                contentStyle={{ backgroundColor: '#1f2937', borderColor: '#374151', color: '#f3f4f6' }}
                                                                itemStyle={{ color: '#60a5fa' }}
                                                            />
                                                            <Area type="monotone" dataKey="duration" stroke="#3b82f6" fillOpacity={1} fill="url(#colorDuration)" name="Duration (min)" />
                                                        </AreaChart>
                                                    </ResponsiveContainer>
                                                </div>
                                            </div>
                                        </div>

                                        {/* Connection History */}
                                        <div>
                                            <h4 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                                                <Clock size={20} className="text-purple-400" /> Recent Connections
                                            </h4>
                                            <div className="bg-gray-900/50 rounded-xl overflow-hidden border border-gray-700">
                                                <table className="w-full text-left text-sm">
                                                    <thead className="bg-gray-700/50 text-gray-400">
                                                        <tr>
                                                            <th className="p-3 font-medium">Time</th>
                                                            <th className="p-3 font-medium">Protocol</th>
                                                            <th className="p-3 font-medium">IP Address</th>
                                                            <th className="p-3 font-medium text-right">Duration</th>
                                                        </tr>
                                                    </thead>
                                                    <tbody className="divide-y divide-gray-800">
                                                        {connectionLogs.length > 0 ? connectionLogs.map((log) => (
                                                            <tr key={log.id} className="hover:bg-gray-800/50 transition-colors">
                                                                <td className="p-3 text-gray-300">{new Date(log.connected_at).toLocaleString()}</td>
                                                                <td className="p-3">
                                                                    <span className={`px-2 py-0.5 rounded text-xs uppercase font-medium ${log.protocol === 'openvpn' ? 'bg-orange-500/20 text-orange-400' : 'bg-blue-500/20 text-blue-400'}`}>
                                                                        {log.protocol}
                                                                    </span>
                                                                </td>
                                                                <td className="p-3 text-gray-300 font-mono text-xs">{log.ip_address}</td>
                                                                <td className="p-3 text-right text-gray-400">
                                                                    {log.disconnected_at ? 'Ended' : 'Active'}
                                                                </td>
                                                            </tr>
                                                        )) : (
                                                            <tr>
                                                                <td colSpan="4" className="p-6 text-center text-gray-500">No connection history found</td>
                                                            </tr>
                                                        )}
                                                    </tbody>
                                                </table>
                                            </div>
                                        </div>
                                    </>
                                ) : (
                                    <div className="h-full flex flex-col">
                                        <div className="flex justify-between items-center mb-4">
                                            <h4 className="text-lg font-bold text-white flex items-center gap-2">
                                                <Terminal size={20} className="text-gray-400" /> System Logs (OpenVPN)
                                            </h4>
                                            <button
                                                onClick={() => handleFetchLogs(selectedUser.id)}
                                                className="text-sm text-blue-400 hover:text-blue-300 flex items-center gap-1"
                                            >
                                                <RefreshCw size={14} /> Refresh
                                            </button>
                                        </div>
                                        <div className="bg-black/80 rounded-xl border border-gray-700 p-4 font-mono text-xs overflow-y-auto max-h-[500px] flex-1">
                                            {logsLoading ? (
                                                <div className="text-gray-400 animate-pulse">Loading logs...</div>
                                            ) : debugLogs.length > 0 ? (
                                                <div className="space-y-1">
                                                    {debugLogs.map((log, i) => (
                                                        <div key={i} className="text-gray-300 border-b border-gray-800/50 pb-0.5 mb-0.5 break-all">
                                                            <span className="text-gray-500 mr-2">{i + 1}</span>
                                                            {log}
                                                        </div>
                                                    ))}
                                                </div>
                                            ) : (
                                                <div className="text-gray-500 italic">No logs found for this user in openvpn.log</div>
                                            )}
                                        </div>
                                        <p className="text-gray-500 text-xs mt-2">
                                            Showing last 100 lines matching "{selectedUser.username}" from /var/log/openvpn/openvpn.log
                                        </p>
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                )
            }
        </div >
    );
};

export default Users;
