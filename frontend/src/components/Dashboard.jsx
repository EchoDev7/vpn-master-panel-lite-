import React, { Suspense, lazy, useState, useEffect, useRef, memo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
    Users, Activity, TrendingUp, Server, Shield,
    Globe, RefreshCw, ArrowUpRight, ArrowDownRight,
    Zap, Cpu, Map, ShieldCheck, ActivitySquare
} from 'lucide-react';
import {
    AreaChart, Area, XAxis, YAxis, CartesianGrid,
    Tooltip as RechartsTooltip, ResponsiveContainer
} from 'recharts';
import apiService from '../services/api';
import ActiveConnectionsModal from './ActiveConnectionsModal';
import SystemMetricsModal from './SystemMetricsModal';
import { SkeletonDashboard, SkeletonWidget } from './Skeletons';
import { ApiErrorState } from './States';
import RefreshIndicator from './RefreshIndicator';
import NotificationCenter, { NotificationBell } from './NotificationCenter';
import useWebSocket from '../hooks/useWebSocket';

const ServerResourcesWidget = lazy(() => import('./ServerResourcesWidget'));
const NetworkSpeedWidget = lazy(() => import('./NetworkSpeedWidget'));
const ProtocolDistributionChart = lazy(() => import('./ProtocolDistributionChart'));
const ActivityTimeline = lazy(() => import('./ActivityTimeline'));

export const Dashboard = () => {
    const navigate = useNavigate();
    const trafficChartRef = useRef(null);

    const [stats, setStats] = useState(null);
    const [trafficData, setTrafficData] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [trafficDays, setTrafficDays] = useState(7);
    const [showConnectionsModal, setShowConnectionsModal] = useState(false);
    const [showSystemModal, setShowSystemModal] = useState(false);
    const [showNotifications, setShowNotifications] = useState(false);
    const [activeConnections, setActiveConnections] = useState([]);
    const [trafficByType, setTrafficByType] = useState(null);
    const [lastUpdated, setLastUpdated] = useState(null);
    const [isRefreshing, setIsRefreshing] = useState(false);

    const { lastMessage } = useWebSocket();

    useEffect(() => {
        if (lastMessage) {
            handleWebSocketMessage(lastMessage);
        }
    }, [lastMessage]);

    const handleWebSocketMessage = (message) => {
        if (message.type === 'dashboard_update') {
            setStats(prevStats => ({ ...prevStats, ...message.data }));
            setLastUpdated(new Date());
        }
    };

    useEffect(() => {
        loadDashboardData();
        const interval = setInterval(loadDashboardData, 30000);
        return () => clearInterval(interval);
    }, [trafficDays]);

    const loadDashboardData = async (isManualRefresh = false) => {
        try {
            if (isManualRefresh) setIsRefreshing(true);
            setError(null);

            const [dashboardRes, trafficRes, trafficByTypeRes] = await Promise.all([
                apiService.get('/monitoring/dashboard'),
                apiService.get(`/monitoring/traffic-stats?days=${trafficDays}`),
                apiService.get(`/monitoring/traffic-by-type?days=${trafficDays}`)
            ]);

            setStats(dashboardRes.data);
            setTrafficData(trafficRes.data);
            setTrafficByType(trafficByTypeRes.data);
            setLastUpdated(new Date());
            setLoading(false);
            setIsRefreshing(false);
        } catch (error) {
            console.error('Failed to load dashboard data:', error);
            setError(error);
            setLoading(false);
            setIsRefreshing(false);
        }
    };

    const handleManualRefresh = () => {
        loadDashboardData(true);
    };

    const loadActiveConnections = async () => {
        try {
            const response = await apiService.get('/monitoring/active-connections');
            setActiveConnections(response.data);
        } catch (error) {
            console.error('Failed to load connections:', error);
        }
    };

    const CustomTooltip = ({ active, payload, label }) => {
        if (active && payload && payload.length) {
            return (
                <div className="bg-white/90 dark:bg-gray-800/90 backdrop-blur-md p-4 rounded-xl shadow-2xl border border-gray-200 dark:border-gray-700">
                    <p className="text-sm font-semibold text-gray-800 dark:text-gray-200 mb-2">{label}</p>
                    {payload.map((entry, index) => (
                        <div key={index} className="flex items-center gap-2 mt-1">
                            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: entry.color }} />
                            <span className="text-sm text-gray-600 dark:text-gray-400 font-medium">
                                {entry.name}:
                            </span>
                            <span className="text-sm font-bold text-gray-900 dark:text-white">
                                {entry.value} GB
                            </span>
                        </div>
                    ))}
                </div>
            );
        }
        return null;
    };

    if (loading) return <SkeletonDashboard />;

    if (error) {
        return (
            <div className="min-h-screen bg-transparent p-6">
                <ApiErrorState error={error} onRetry={loadDashboardData} />
            </div>
        );
    }

    const StatCard = memo(({ title, value, subtitle, icon: Icon, gradient, onClick, clickable = true }) => (
        <div
            className={`relative overflow-hidden bg-white dark:bg-gray-800 rounded-2xl p-6 border border-gray-100 dark:border-gray-700/50 shadow-sm transition-all duration-300 ${clickable ? 'cursor-pointer hover:shadow-2xl hover:-translate-y-1 hover:border-blue-500/30' : ''
                }`}
            onClick={onClick}
            role={clickable ? "button" : "presentation"}
            tabIndex={clickable ? 0 : -1}
        >
            {/* Background Glow */}
            <div className={`absolute -right-10 -top-10 w-32 h-32 rounded-full blur-3xl opacity-20 bg-gradient-to-br ${gradient}`} />

            <div className="relative z-10 flex items-center justify-between">
                <div>
                    <p className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1 tracking-wide uppercase">{title}</p>
                    <p className="text-4xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-gray-900 to-gray-600 dark:from-white dark:to-gray-300">
                        {value}
                    </p>
                    {subtitle && (
                        <div className="flex items-center gap-1 mt-2 text-sm text-gray-500 dark:text-gray-400">
                            {subtitle.includes('Up') ? <ArrowUpRight size={14} className="text-emerald-500" /> : <ActivitySquare size={14} className="text-blue-500" />}
                            <span>{subtitle}</span>
                        </div>
                    )}
                </div>
                <div className={`p-4 rounded-2xl bg-gradient-to-br ${gradient} shadow-lg text-white transform transition-transform duration-500 hover:rotate-12`}>
                    <Icon size={28} strokeWidth={2.5} />
                </div>
            </div>
        </div>
    ));

    return (
        <div className="min-h-screen p-4 md:p-8 space-y-8 animate-in fade-in duration-500">
            {/* Header section */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white/40 dark:bg-gray-800/40 backdrop-blur-xl p-6 rounded-3xl border border-white/20 shadow-sm">
                <div>
                    <h1 className="text-3xl md:text-4xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-purple-600 dark:from-blue-400 dark:to-purple-400 flex items-center gap-3">
                        <ShieldCheck size={40} className="text-blue-500" />
                        VPN Master Panel
                    </h1>
                    <p className="text-gray-600 dark:text-gray-400 mt-2 font-medium">
                        Real-time Lite Edition Monitoring Overview
                    </p>
                </div>
                <div className="flex items-center gap-4">
                    <RefreshIndicator
                        lastUpdated={lastUpdated}
                        onRefresh={handleManualRefresh}
                        isRefreshing={isRefreshing}
                    />
                    <div className="bg-white dark:bg-gray-700 p-2 rounded-full shadow-sm border border-gray-100 dark:border-gray-600">
                        <NotificationBell onClick={() => setShowNotifications(true)} />
                    </div>
                </div>
            </div>

            {/* Main Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <StatCard
                    title="Total Users"
                    value={stats?.users?.total || 0}
                    subtitle={`${stats?.users?.active || 0} active accounts`}
                    icon={Users}
                    gradient="from-blue-500 to-cyan-500"
                    onClick={() => navigate('/users')}
                />
                <StatCard
                    title="Active Tunnels"
                    value={stats?.connections?.active || 0}
                    subtitle="Live connections"
                    icon={Activity}
                    gradient="from-emerald-500 to-teal-500"
                    onClick={async () => {
                        await loadActiveConnections();
                        setShowConnectionsModal(true);
                    }}
                />
                <StatCard
                    title="Traffic (24h)"
                    value={`${stats?.traffic?.gb_24h ?? 0} GB`}
                    subtitle="Up/Down bandwidth usage"
                    icon={Globe}
                    gradient="from-orange-500 to-amber-500"
                    onClick={() => trafficChartRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' })}
                />
                <StatCard
                    title="System Load"
                    value={`${stats?.system?.cpu_percent ?? 0}%`}
                    subtitle={`RAM used: ${stats?.system?.memory_percent ?? 0}%`}
                    icon={Cpu}
                    gradient="from-rose-500 to-pink-500"
                    onClick={() => setShowSystemModal(true)}
                />
            </div>

            {/* Traffic Type Breakdown */}
            {trafficByType && trafficByType.summary && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <StatCard
                        title="Direct Traffic"
                        value={`${trafficByType.summary.direct?.gb ?? 0} GB`}
                        subtitle={`Total direct in last ${trafficDays} days`}
                        icon={Zap}
                        gradient="from-indigo-500 to-blue-500"
                        clickable={false}
                    />
                    <StatCard
                        title="Tunnel Traffic"
                        value={`${trafficByType.summary.tunnel?.gb ?? 0} GB`}
                        subtitle={`Overcast mapped in last ${trafficDays} days`}
                        icon={Map}
                        gradient="from-fuchsia-500 to-purple-500"
                        clickable={false}
                    />
                </div>
            )}

            {/* Gorgeous Traffic Area Chart */}
            <div ref={trafficChartRef} className="bg-white/70 dark:bg-gray-800/70 backdrop-blur-2xl rounded-3xl shadow-xl border border-white/20 dark:border-gray-700 p-6 md:p-8">
                <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-8">
                    <div>
                        <h2 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-3">
                            <TrendingUp className="text-blue-500" size={28} />
                            Bandwidth Analytics
                        </h2>
                        <p className="text-sm text-gray-500 mt-1">Network throughput over the past {trafficDays} days</p>
                    </div>
                    <div className="flex gap-2 mt-4 sm:mt-0 bg-gray-100/50 dark:bg-gray-900/50 p-1.5 rounded-xl border border-gray-200 dark:border-gray-700">
                        {[7, 14, 30].map(days => (
                            <button
                                key={days}
                                onClick={() => setTrafficDays(days)}
                                className={`px-5 py-2 rounded-lg text-sm font-semibold transition-all duration-300 ${trafficDays === days
                                    ? 'bg-white dark:bg-gray-700 text-blue-600 dark:text-blue-400 shadow-md transform scale-105'
                                    : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white hover:bg-white/50 dark:hover:bg-gray-700/50'
                                    }`}
                            >
                                {days}D
                            </button>
                        ))}
                    </div>
                </div>

                <div className="h-[350px] w-full">
                    <ResponsiveContainer width="100%" height="100%">
                        <AreaChart data={trafficData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                            <defs>
                                <linearGradient id="colorUpload" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.4} />
                                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                                </linearGradient>
                                <linearGradient id="colorDownload" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.4} />
                                    <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                                </linearGradient>
                            </defs>
                            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#374151" opacity={0.2} />
                            <XAxis
                                dataKey="date"
                                stroke="#6b7280"
                                tickLine={false}
                                axisLine={false}
                                dy={10}
                                tick={{ fontSize: 12, fontWeight: 500 }}
                            />
                            <YAxis
                                stroke="#6b7280"
                                tickLine={false}
                                axisLine={false}
                                dx={-10}
                                tickFormatter={(val) => `${val}GB`}
                                tick={{ fontSize: 12, fontWeight: 500 }}
                            />
                            <RechartsTooltip content={<CustomTooltip />} />
                            <Area
                                type="monotone"
                                dataKey="upload_gb"
                                stroke="#3b82f6"
                                strokeWidth={3}
                                fillOpacity={1}
                                fill="url(#colorUpload)"
                                name="Upload"
                                animationDuration={1500}
                                activeDot={{ r: 8, strokeWidth: 0, fill: '#3b82f6', className: 'animate-pulse' }}
                            />
                            <Area
                                type="monotone"
                                dataKey="download_gb"
                                stroke="#10b981"
                                strokeWidth={3}
                                fillOpacity={1}
                                fill="url(#colorDownload)"
                                name="Download"
                                animationDuration={1500}
                                activeDot={{ r: 8, strokeWidth: 0, fill: '#10b981', className: 'animate-pulse' }}
                            />
                        </AreaChart>
                    </ResponsiveContainer>
                </div>
            </div>

            {/* Quick Actions Panel */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <QuickAction
                    title="Add User Account"
                    description="Provision a new VPN profile"
                    gradient="from-blue-500 to-indigo-600"
                    onClick={() => navigate('/users')}
                />
                <QuickAction
                    title="Configure Tunneling"
                    description="Setup Iran-Foreign bridges"
                    gradient="from-emerald-500 to-teal-600"
                    onClick={() => navigate('/tunnels')}
                />
                <QuickAction
                    title="Server Nodes"
                    description="Manage backend infrastructure"
                    gradient="from-rose-500 to-orange-600"
                    onClick={() => navigate('/servers')}
                />
            </div>

            {/* Advanced Widgets Row */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 pt-4">
                <Suspense fallback={<SkeletonWidget />}>
                    <ServerResourcesWidget />
                </Suspense>
                <Suspense fallback={<SkeletonWidget />}>
                    <NetworkSpeedWidget />
                </Suspense>
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <Suspense fallback={<SkeletonWidget />}>
                    <ProtocolDistributionChart />
                </Suspense>
                <Suspense fallback={<SkeletonWidget />}>
                    <ActivityTimeline limit={5} />
                </Suspense>
            </div>

            {/* Render Modals */}
            {showConnectionsModal && (
                <ActiveConnectionsModal
                    connections={activeConnections}
                    onClose={() => setShowConnectionsModal(false)}
                    onRefresh={loadActiveConnections}
                />
            )}
            {showSystemModal && (
                <SystemMetricsModal
                    stats={stats}
                    onClose={() => setShowSystemModal(false)}
                    onRefresh={loadDashboardData}
                />
            )}
            {showNotifications && (
                <NotificationCenter
                    isOpen={showNotifications}
                    onClose={() => setShowNotifications(false)}
                />
            )}
        </div>
    );
};

const QuickAction = memo(({ title, description, gradient, onClick }) => (
    <button
        onClick={onClick}
        className="group relative overflow-hidden bg-white dark:bg-gray-800 rounded-2xl shadow-sm hover:shadow-xl transition-all duration-300 p-6 text-left border border-gray-100 dark:border-gray-700"
    >
        <div className={`absolute top-0 left-0 w-full h-1 bg-gradient-to-r ${gradient} transform origin-left transition-transform duration-300 scale-x-0 group-hover:scale-x-100`} />
        <h3 className="text-xl font-bold tracking-tight text-gray-900 dark:text-white group-hover:text-blue-500 transition-colors">
            {title}
        </h3>
        <p className="text-sm font-medium text-gray-500 dark:text-gray-400 mt-2">{description}</p>

        <div className="absolute right-6 bottom-6 opacity-0 translate-x-4 group-hover:opacity-100 group-hover:translate-x-0 transition-all duration-300">
            <div className={`p-2 rounded-full bg-gradient-to-r ${gradient} text-white`}>
                <ArrowUpRight size={18} />
            </div>
        </div>
    </button>
));

export default Dashboard;

