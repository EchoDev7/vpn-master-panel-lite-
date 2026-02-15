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
        status: 'active'
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
            status: user.status
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

    const handleDelete = async (userId) => {
        if (window.confirm('Are you sure you want to delete this user?')) {
            try {
                await apiService.deleteUser(userId);
                loadUsers();
            } catch (error) {
                alert('Failed to delete user');
            }
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
                                    <span className={`px-2 py-1 rounded text-xs ${user.status === 'active' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
                                        {user.status}
                                    </span>
                                </td>
                                <td className="p-4 text-gray-300">
                                    {user.data_limit_gb > 0 ? `${user.data_limit_gb} GB` : 'Unlimited'}
                                </td>
                                <td className="p-4 text-gray-300">
                                    {user.data_usage_gb?.toFixed(2) || 0} GB
                                </td>
                                <td className="p-4 text-gray-300">
                                    {user.expiry_date ? new Date(user.expiry_date).toLocaleDateString() : 'Never'}
                                </td>
                                <td className="p-4 text-right space-x-2">
                                    <button onClick={() => handleOpenEdit(user)} className="text-blue-400 hover:text-blue-300 p-1">
                                        Edit
                                    </button>
                                    <button onClick={() => handleDelete(user.id)} className="text-red-400 hover:text-red-300 p-1">
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
                                        onChange={e => setFormData({ ...formData, data_limit_gb: parseFloat(e.target.value) })}
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
        </div>
    );
};

export default Users;
