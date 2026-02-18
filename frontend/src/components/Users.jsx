import React, { useState, useEffect } from 'react';
import { UserPlus, Trash2, RefreshCw, Key, Shield } from 'lucide-react';
import { apiService } from '../services/api';

const Users = () => {
    const [users, setUsers] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showModal, setShowModal] = useState(false);
    const [modalMode, setModalMode] = useState('create'); // 'create' or 'edit'
    const [selectedUser, setSelectedUser] = useState(null);

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
    }, []);

    const loadUsers = async () => {
        try {
            setLoading(true);
            const response = await apiService.getUsers();
            setUsers(response.data.users || []);
        } catch (error) {
            console.error('Failed to load users:', error);
        } finally {
            setLoading(false);
        }
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

            <div className="bg-gray-800 rounded-lg overflow-hidden shadow-xl border border-gray-700">
                <table className="w-full text-left">
                    <thead className="bg-gray-700/50 text-gray-300">
                        <tr>
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
                            <tr key={user.id} className="hover:bg-gray-700/30 transition-colors">
                                <td className="p-4 text-white font-medium">{user.username}</td>
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
                                    <button onClick={() => handleOpenEdit(user)} className="text-blue-400 hover:text-blue-300 p-1" title="Edit">
                                        Edit
                                    </button>
                                    <button onClick={() => handleOpenConfig(user)} className="text-yellow-400 hover:text-yellow-300 p-1" title="Configuration">
                                        <Key size={18} />
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
            </div>

            {/* User Modal (Create/Edit) */}
            {showModal && (
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
            )}

            {/* Delete Confirmation Modal */}
            {showDeleteModal && userToDelete && (
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
            )}

            {/* Config Modal */}
            {showConfigModal && selectedConfigUser && (
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
            )}
        </div>
    );
};

export default Users;
