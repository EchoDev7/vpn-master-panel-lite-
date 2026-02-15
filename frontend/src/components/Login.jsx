import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Lock, User } from 'lucide-react';
import { apiService } from '../services/api';

const Login = () => {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const navigate = useNavigate();

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setLoading(true);

        try {
            await apiService.login(username, password);
            navigate('/');
        } catch (err) {
            console.error('Login failed:', err);
            setError('Invalid username or password');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen bg-gray-900 flex items-center justify-center p-4">
            <div className="bg-gray-800 p-8 rounded-xl shadow-2xl w-full max-w-md border border-gray-700">
                <div className="text-center mb-8">
                    <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl mx-auto flex items-center justify-center mb-4">
                        <Lock className="w-8 h-8 text-white" />
                    </div>
                    <h1 className="text-2xl font-bold text-white">VPN Master Panel</h1>
                    <p className="text-gray-400 mt-2">Sign in to manage your server</p>
                </div>

                {error && (
                    <div className="bg-red-500/20 border border-red-500/50 text-red-200 p-3 rounded-lg mb-6 text-sm text-center">
                        {error}
                    </div>
                )}

                <form onSubmit={handleSubmit} className="space-y-6">
                    <div>
                        <label className="block text-gray-400 text-sm font-medium mb-2">Username</label>
                        <div className="relative">
                            <User className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-500" size={18} />
                            <input
                                type="text"
                                value={username}
                                onChange={(e) => setUsername(e.target.value)}
                                className="w-full bg-gray-700 border border-gray-600 text-white rounded-lg pl-10 pr-4 py-2.5 focus:outline-none focus:border-blue-500 transition-colors"
                                placeholder="Enter username"
                                required
                            />
                        </div>
                    </div>

                    <div>
                        <label className="block text-gray-400 text-sm font-medium mb-2">Password</label>
                        <div className="relative">
                            <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-500" size={18} />
                            <input
                                type="password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                className="w-full bg-gray-700 border border-gray-600 text-white rounded-lg pl-10 pr-4 py-2.5 focus:outline-none focus:border-blue-500 transition-colors"
                                placeholder="Enter password"
                                required
                            />
                        </div>
                    </div>

                    <button
                        type="submit"
                        disabled={loading}
                        className={`w-full bg-gradient-to-r from-blue-600 to-purple-600 text-white font-bold py-3 rounded-lg shadow-lg hover:from-blue-700 hover:to-purple-700 transition-all transform hover:scale-[1.02] ${loading ? 'opacity-70 cursor-not-allowed' : ''
                            }`}
                    >
                        {loading ? 'Signing in...' : 'Sign In'}
                    </button>
                </form>
            </div>
        </div>
    );
};

export default Login;
