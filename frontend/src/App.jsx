
import { useState } from 'react'
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom'
import './i18n/config'; // Import i18n configuration
import Dashboard from './components/Dashboard'
import Users from './components/Users'
import Settings from './components/Settings'
import Tunnels from './components/Tunnels'
import Servers from './components/Servers'
import Analytics from './components/Analytics'
import Diagnostics from './components/Diagnostics'
import Login from './components/Login'
import ProtectedRoute from './components/ProtectedRoute'
import ErrorBoundary from './components/ErrorBoundary'

import LanguageSwitcher from './components/LanguageSwitcher';
import SubscriptionPlans from './components/SubscriptionPlans';

function App() {
    return (
        <Router>
            <Routes>
                <Route path="/login" element={<Login />} />
                <Route
                    path="/*"
                    element={
                        <ProtectedRoute>
                            <MainLayout />
                        </ProtectedRoute>
                    }
                />
            </Routes>
        </Router>
    )
}

function MainLayout() {
    return (
        <div className="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-gray-900">
            {/* Header */}
            <header className="bg-gray-800/50 backdrop-blur-lg border-b border-gray-700">
                <div className="container mx-auto px-4 py-4">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-3">
                            <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
                                <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                                </svg>
                            </div>
                            <h1 className="text-2xl font-bold text-white">VPN Master</h1>
                        </div>
                        <nav className="flex items-center space-x-6">
                            <Link to="/" className="text-gray-300 hover:text-white transition-colors">
                                Dashboard
                            </Link>
                            <Link to="/analytics" className="text-gray-300 hover:text-white transition-colors">
                                Analytics
                            </Link>
                            <Link to="/servers" className="text-gray-300 hover:text-white transition-colors">
                                Servers
                            </Link>
                            <Link to="/users" className="text-gray-300 hover:text-white transition-colors">
                                Users
                            </Link>
                            <Link to="/subscription" className="text-gray-300 hover:text-white transition-colors">
                                Subscription
                            </Link>
                            <Link to="/diagnostics" className="text-gray-300 hover:text-white transition-colors">
                                Diagnostics
                            </Link>
                            <Link to="/settings" className="text-gray-300 hover:text-white transition-colors">
                                Settings
                            </Link>
                            <div className="border-l border-gray-600 pl-4 flex items-center space-x-4">
                                <LanguageSwitcher />
                                <button onClick={() => {
                                    localStorage.clear();
                                    window.location.href = '/login';
                                }} className="text-red-400 hover:text-red-300 transition-colors">
                                    Logout
                                </button>
                            </div>
                        </nav>
                    </div>
                </div>
            </header>

            {/* Main Content */}
            <main className="container mx-auto px-4 py-8">
                <ErrorBoundary>
                    <Routes>
                        <Route path="/" element={<Dashboard />} />
                        <Route path="/analytics" element={<Analytics />} />
                        <Route path="/servers" element={<Servers />} />
                        <Route path="/tunnels" element={<Tunnels />} />
                        <Route path="/users" element={<Users />} />
                        <Route path="/subscription" element={<SubscriptionPlans />} />
                        <Route path="/diagnostics" element={<Diagnostics />} />
                        <Route path="/settings" element={<Settings />} />
                    </Routes>
                </ErrorBoundary>
            </main>

            {/* Footer */}
            <footer className="bg-gray-800/30 backdrop-blur-lg border-t border-gray-700 mt-12">
                <div className="container mx-auto px-4 py-6 text-center text-gray-400">
                    <p>VPN Master Panel v1.0.0 - Powered by FastAPI & React</p>
                </div>
            </footer>
        </div>
    )
}

function ComingSoon({ title }) {
    return (
        <div className="flex items-center justify-center min-h-[400px]">
            <div className="text-center">
                <h2 className="text-3xl font-bold text-white mb-4">{title}</h2>
                <p className="text-gray-400">Coming Soon...</p>
            </div>
        </div>
    )
}

export default App
