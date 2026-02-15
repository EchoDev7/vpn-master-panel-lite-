
import { useState } from 'react'
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom'
import Dashboard from './components/Dashboard'
import Users from './components/Users'
// ... inside Routes
<Route path="/users" element={<Users />} />

import Login from './components/Login'
import ProtectedRoute from './components/ProtectedRoute'

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
                            <h1 className="text-2xl font-bold text-white">VPN Master Panel</h1>
                        </div>
                        <nav className="flex space-x-6">
                            <Link to="/" className="text-gray-300 hover:text-white transition-colors">
                                Dashboard
                            </Link>
                            <Link to="/servers" className="text-gray-300 hover:text-white transition-colors">
                                Servers
                            </Link>
                            <Link to="/users" className="text-gray-300 hover:text-white transition-colors">
                                Users
                            </Link>
                            <button onClick={() => {
                                localStorage.clear();
                                window.location.href = '/login';
                            }} className="text-red-400 hover:text-red-300 transition-colors">
                                Logout
                            </button>
                        </nav>
                    </div>
                </div>
            </header>

            {/* Main Content */}
            <main className="container mx-auto px-4 py-8">
                <Routes>
                    <Route path="/" element={<Dashboard />} />
                    <Route path="/servers" element={<ComingSoon title="Servers Management" />} />
                    <Route path="/users" element={<Users />} />
                </Routes>
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
