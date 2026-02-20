import React, { useEffect, useMemo, useState } from 'react';
import { Copy, ExternalLink, Loader2, RefreshCw, Search, ShieldCheck } from 'lucide-react';
import { apiService } from '../services/api';

const getBackendOrigin = () => {
    const configured = import.meta.env.VITE_API_URL;
    if (configured) {
        return configured.replace(/\/$/, '');
    }

    if (window.location.port === '5173') {
        return `${window.location.protocol}//${window.location.hostname}:8001`;
    }

    return window.location.origin;
};

const formatExpiry = (value) => {
    if (!value) return 'Never';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return 'Unknown';
    return date.toLocaleDateString();
};

const formatTraffic = (user) => {
    const used = Number(user?.data_usage_gb || 0).toFixed(2);
    const limit = Number(user?.data_limit_gb || 0);
    if (limit <= 0) {
        return `${used} GB / Unlimited`;
    }
    return `${used} GB / ${limit} GB`;
};

const SubscriptionPlans = () => {
    const [users, setUsers] = useState([]);
    const [loading, setLoading] = useState(true);
    const [query, setQuery] = useState('');
    const [error, setError] = useState('');
    const [copiedUserId, setCopiedUserId] = useState(null);
    const [regeneratingUserId, setRegeneratingUserId] = useState(null);

    const backendOrigin = useMemo(() => getBackendOrigin(), []);

    const loadUsers = async (search = '') => {
        try {
            setLoading(true);
            setError('');
            const response = await apiService.getUsers({
                page: 1,
                page_size: 200,
                search: search || undefined,
            });
            setUsers(response?.data?.users || []);
        } catch (err) {
            console.error('Failed to load users for subscription links:', err);
            setError(err?.response?.data?.detail || 'Failed to load users.');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadUsers();
    }, []);

    const buildSubscriptionLink = (token) => {
        if (!token) return '';
        return `${backendOrigin}/sub/${token}`;
    };

    const handleCopyLink = async (user) => {
        if (!user.subscription_token) return;
        try {
            await navigator.clipboard.writeText(buildSubscriptionLink(user.subscription_token));
            setCopiedUserId(user.id);
            setTimeout(() => setCopiedUserId(null), 1500);
        } catch (err) {
            console.error('Failed to copy subscription link:', err);
        }
    };

    const handleRegenerate = async (user) => {
        setRegeneratingUserId(user.id);
        try {
            await apiService.regenerateToken(user.id);
            await loadUsers(query);
        } catch (err) {
            console.error('Failed to regenerate token:', err);
            setError(err?.response?.data?.detail || 'Failed to regenerate token.');
        } finally {
            setRegeneratingUserId(null);
        }
    };

    const handleSearch = (event) => {
        event.preventDefault();
        loadUsers(query.trim());
    };

    return (
        <div className="max-w-7xl mx-auto px-4 py-8 text-white">
            <div className="mb-8 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                <div>
                    <h1 className="text-3xl font-bold flex items-center gap-3">
                        <ShieldCheck className="w-8 h-8 text-cyan-300" />
                        Subscription Portal Links
                    </h1>
                    <p className="text-gray-300 mt-2">
                        Copy or open each user's dedicated link. The public subscription page is available at <code>/sub/&lt;token&gt;</code>.
                    </p>
                </div>

                <form onSubmit={handleSearch} className="flex gap-2">
                    <div className="relative">
                        <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                        <input
                            value={query}
                            onChange={(e) => setQuery(e.target.value)}
                            placeholder="Search username"
                            className="pl-9 pr-3 py-2 rounded-lg bg-gray-800/80 border border-gray-700 text-sm focus:outline-none focus:ring-2 focus:ring-cyan-500"
                        />
                    </div>
                    <button
                        type="submit"
                        className="px-4 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-sm font-medium"
                    >
                        Search
                    </button>
                </form>
            </div>

            {error && (
                <div className="mb-4 rounded-lg border border-red-400/30 bg-red-500/10 p-3 text-red-200 text-sm">
                    {error}
                </div>
            )}

            {loading ? (
                <div className="flex items-center justify-center py-20">
                    <Loader2 className="w-8 h-8 animate-spin text-cyan-300" />
                </div>
            ) : (
                <div className="overflow-x-auto rounded-xl border border-gray-700 bg-gray-900/60">
                    <table className="w-full text-sm">
                        <thead className="bg-gray-800/80 text-gray-200">
                            <tr>
                                <th className="px-4 py-3 text-left">User</th>
                                <th className="px-4 py-3 text-left">Status</th>
                                <th className="px-4 py-3 text-left">Expiry</th>
                                <th className="px-4 py-3 text-left">Traffic</th>
                                <th className="px-4 py-3 text-left">Subscription Link</th>
                                <th className="px-4 py-3 text-left">Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {users.map((user) => {
                                const subLink = buildSubscriptionLink(user.subscription_token);
                                return (
                                    <tr key={user.id} className="border-t border-gray-800 hover:bg-gray-800/40">
                                        <td className="px-4 py-3 font-medium">{user.username}</td>
                                        <td className="px-4 py-3">
                                            <span className={`px-2 py-1 rounded text-xs ${user.status === 'active' ? 'bg-emerald-500/20 text-emerald-200' : 'bg-red-500/20 text-red-200'}`}>
                                                {user.status}
                                            </span>
                                        </td>
                                        <td className="px-4 py-3 text-gray-300">{formatExpiry(user.expiry_date)}</td>
                                        <td className="px-4 py-3 text-gray-300">{formatTraffic(user)}</td>
                                        <td className="px-4 py-3 text-gray-300 max-w-[380px]">
                                            <div className="truncate">{subLink || 'No token'}</div>
                                        </td>
                                        <td className="px-4 py-3">
                                            <div className="flex flex-wrap gap-2">
                                                <button
                                                    type="button"
                                                    disabled={!subLink}
                                                    onClick={() => handleCopyLink(user)}
                                                    className="px-3 py-1.5 rounded bg-blue-600/80 hover:bg-blue-500 disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1"
                                                >
                                                    <Copy size={14} />
                                                    {copiedUserId === user.id ? 'Copied' : 'Copy'}
                                                </button>

                                                <a
                                                    href={subLink || '#'}
                                                    target="_blank"
                                                    rel="noreferrer"
                                                    onClick={(e) => {
                                                        if (!subLink) e.preventDefault();
                                                    }}
                                                    className="px-3 py-1.5 rounded bg-emerald-600/80 hover:bg-emerald-500 disabled:opacity-40 flex items-center gap-1"
                                                >
                                                    <ExternalLink size={14} /> Open
                                                </a>

                                                <button
                                                    type="button"
                                                    onClick={() => handleRegenerate(user)}
                                                    disabled={regeneratingUserId === user.id}
                                                    className="px-3 py-1.5 rounded bg-amber-600/80 hover:bg-amber-500 disabled:opacity-50 flex items-center gap-1"
                                                >
                                                    {regeneratingUserId === user.id ? (
                                                        <Loader2 size={14} className="animate-spin" />
                                                    ) : (
                                                        <RefreshCw size={14} />
                                                    )}
                                                    Regenerate
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                );
                            })}

                            {users.length === 0 && (
                                <tr>
                                    <td colSpan={6} className="text-center px-4 py-10 text-gray-400">
                                        No users found.
                                    </td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
};

export default SubscriptionPlans;
