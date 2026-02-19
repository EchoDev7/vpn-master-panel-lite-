import React, { Suspense, lazy, useState, useEffect, useRef, memo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
    Users, Activity, TrendingUp, Cpu, Globe, ArrowUpRight,
    Zap, Map, ShieldCheck, ActivitySquare
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

    const CustomAreaTooltip = ({ active, payload, label }) => {
        if (active && payload && payload.length) {
            return (
                <div className="bg-white/95 dark:bg-gray-800/95 backdrop-blur-xl p-4 rounded-2xl shadow-2xl border border-gray-100 dark:border-gray-700/50">
                    <p className="text-sm font-bold text-gray-800 dark:text-gray-200 mb-3 ml-1">{label}</p>
                    {payload.map((entry, index) => (
                        <div key={index} className="flex items-center gap-3 mb-2 last:mb-0">
                            <div className="w-2.5 h-2.5 rounded-full shadow-sm" style={{ backgroundColor: entry.color }} />
                            <span className="text-sm font-medium text-gray-600 dark:text-gray-400 w-20">
                                {entry.name}:
                            </span>
                            <span className="text-sm font-extrabold text-gray-900 dark:text-white text-right">
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
            className={`relative overflow-hidden bg-white/60 dark:bg-gray-800/60 backdrop-blur-2xl rounded-3xl p-6 border border-white/20 dark:border-gray-700/50 shadow-lg transition-all duration-500 group ${clickable ? 'cursor-pointer hover:shadow-2xl hover:-translate-y-1.5' : ''
                }`}
            onClick={onClick}
            role={clickable ? "button" : "presentation"}
            tabIndex={clickable ? 0 : -1}
        >
            {/* Ambient Corner Glow */}
            <div className={`absolute -right-10 -top-10 w-32 h-32 rounded-full blur-3xl opacity-30 bg-gradient-to-br ${gradient} transition-opacity duration-500 group-hover:opacity-50`} />

            <div className="relative z-10 flex items-center justify-between">
                <div>
                    <p className="text-xs font-bold tracking-widest text-gray-400 dark:text-gray-500 uppercase mb-1">{title}</p>
                    <p className="text-4xl font-extrabold text-gray-900 dark:text-white tracking-tight">
                        {value}
                    </p>
                    {subtitle && (
                        <div className="flex items-center gap-1.5 mt-3 text-sm text-gray-500 dark:text-gray-400 bg-gray-100/50 dark:bg-gray-900/50 w-max px-2.5 py-1 rounded-full border border-gray-200/50 dark:border-gray-700/50">
                            {subtitle.includes('Up') ? <ArrowUpRight size={14} className="text-emerald-500" /> : <ActivitySquare size={14} className="text-blue-500" />}
                            <span className="font-medium">{subtitle}</span>
                        </div>
                    )}
                </div>
                <div className={`p-4 rounded-2xl bg-gradient-to-br ${gradient} shadow-lg text-white transform transition-transform duration-500 group-hover:scale-110 group-hover:rotate-6 ring-4 ring-white/20 dark:ring-gray-800/20`}>
                    <Icon size={28} strokeWidth={2.5} />
                </div>
            </div>

            {/* Subtle bottom highlight */}
            <div className={`absolute bottom-0 left-0 w-full h-1 bg-gradient-to-r ${gradient} opacity-0 transition-opacity duration-500 group-hover:opacity-100`} />
        </div>
    ));

    return (
        <div className="min-h-screen p-4 md:p-8 space-y-8 animate-in fade-in duration-700">
            {/* Hero Header Section */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white/70 dark:bg-gray-800/70 backdrop-blur-2xl p-6 md:p-8 rounded-[2rem] border border-white/20 dark:border-gray-700 shadow-xl overflow-hidden relative">
                {/* Decorative background elements */}
                <div className="absolute top-0 right-0 w-96 h-96 bg-blue-500/10 rounded-full blur-3xl -translate-y-1/2 translate-x-1/3 pointer-events-none" />
                <div className="absolute bottom-0 left-0 w-96 h-96 bg-purple-500/10 rounded-full blur-3xl translate-y-1/2 -translate-x-1/3 pointer-events-none" />

                <div className="relative z-10">
                    <h1 className="text-3xl md:text-5xl font-extrabold tracking-tight text-transparent bg-clip-text bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 dark:from-blue-400 dark:via-indigo-400 dark:to-purple-400 flex items-center gap-4">
                        <div className="p-3 bg-white dark:bg-gray-900 rounded-2xl shadow-md border border-gray-100 dark:border-gray-800">
                            <ShieldCheck size={40} className="text-blue-600 dark:text-blue-400" />
                        </div>
                        Enterprise Overview
                    </h1>
                    <p className="text-gray-600 dark:text-gray-400 mt-3 font-medium text-lg ml-[72px]">
                        Monitoring real-time node performance and network tunnels.
                    </p>
                </div>
                <div className="flex items-center gap-4 relative z-10 self-start md:self-auto mt-4 md:mt-0">
                    <RefreshIndicator
                        lastUpdated={lastUpdated}
                        onRefresh={handleManualRefresh}
                        isRefreshing={isRefreshing}
                    />
                    <div className="bg-white/80 dark:bg-gray-800/80 p-3 rounded-xl shadow-md border border-white/40 dark:border-gray-600 hover:scale-105 transition-transform cursor-pointer">
                        <NotificationBell onClick={() => setShowNotifications(true)} />
                    </div>
                </div>
            </div>

            {/* Primary Metrics Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
                <StatCard
                    title="Total Population"
                    value={stats?.users?.total || 0}
                    subtitle={`${stats?.users?.active || 0} active accounts`}
                    icon={Users}
                    gradient="from-blue-600 to-cyan-500"
                    onClick={() => navigate('/users')}
                />
                <StatCard
                    title="Live Tunnels"
                    value={stats?.connections?.active || 0}
                    subtitle="Concurrent sessions"
                    icon={Activity}
                    gradient="from-emerald-500 to-teal-400"
                    onClick={async () => {
                        await loadActiveConnections();
                        setShowConnectionsModal(true);
                    }}
                />
                <StatCard
                    title="Edge Traffic (24h)"
                    value={`${stats?.traffic?.gb_24h || 0} GB`}
                    subtitle="Combined Up/Down throughput"
                    icon={Globe}
                    gradient="from-amber-500 to-orange-500"
                    onClick={() => trafficChartRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' })}
                />
                <StatCard
                    title="Compute Load"
                    value={`${stats?.system?.cpu_percent || 0}%`}
                    subtitle={`RAM saturation: ${stats?.system?.memory_percent || 0}%`}
                    icon={Cpu}
                    gradient="from-rose-500 to-pink-500"
                    onClick={() => setShowSystemModal(true)}
                />
            </div>

            {/* Ingress / Egress Specific Tracking */}
            {trafficByType && trafficByType.summary && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="bg-white/60 dark:bg-gray-800/60 backdrop-blur-2xl p-6 rounded-[2rem] border border-white/20 dark:border-gray-700 shadow-lg flex items-center justify-between group">
                        <div>
                            <p className="text-xs font-bold tracking-widest text-indigo-500 dark:text-indigo-400 uppercase mb-2">Direct Routing Data</p>
                            <h3 className="text-3xl font-extrabold text-gray-900 dark:text-white">
                                {trafficByType.summary.direct?.gb || 0} <span className="text-lg text-gray-500 font-medium">GB</span>
                            </h3>
                            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1 font-medium bg-gray-100 dark:bg-gray-900 w-max px-3 py-1 rounded-lg">Last {trafficDays} days tracking</p>
                        </div>
                        <div className="p-5 bg-indigo-50 dark:bg-indigo-500/10 rounded-[1.5rem] group-hover:scale-110 transition-transform duration-500">
                            <Zap size={36} className="text-indigo-500" />
                        </div>
                    </div>

                    <div className="bg-white/60 dark:bg-gray-800/60 backdrop-blur-2xl p-6 rounded-[2rem] border border-white/20 dark:border-gray-700 shadow-lg flex items-center justify-between group">
                        <div>
                            <p className="text-xs font-bold tracking-widest text-purple-500 dark:text-purple-400 uppercase mb-2">Foreign Tunnel Data</p>
                            <h3 className="text-3xl font-extrabold text-gray-900 dark:text-white">
                                {trafficByType.summary.tunnel?.gb || 0} <span className="text-lg text-gray-500 font-medium">GB</span>
                            </h3>
                            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1 font-medium bg-gray-100 dark:bg-gray-900 w-max px-3 py-1 rounded-lg">Last {trafficDays} days tracking</p>
                        </div>
                        <div className="p-5 bg-purple-50 dark:bg-purple-500/10 rounded-[1.5rem] group-hover:scale-110 transition-transform duration-500">
                            <Map size={36} className="text-purple-500" />
                        </div>
                    </div>
                </div>
            )}

            {/* Premium Traffic Analytical Chart */}
            <div ref={trafficChartRef} className="bg-white/80 dark:bg-gray-800/80 backdrop-blur-3xl rounded-[2rem] shadow-xl border border-white/40 dark:border-gray-700/60 p-6 md:p-8 lg:p-10 relative overflow-hidden">
                <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-blue-500 via-indigo-500 to-emerald-500" />

                <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-10">
                    <div>
                        <h2 className="text-2xl font-extrabold text-gray-900 dark:text-white flex items-center gap-3">
                            <div className="p-2 bg-blue-50 dark:bg-blue-900/40 rounded-lg">
                                <TrendingUp className="text-blue-600 dark:text-blue-400" size={24} />
                            </div>
                            Bandwidth Velocity
                        </h2>
                        <p className="text-sm font-medium text-gray-500 dark:text-gray-400 mt-2 ml-12">Network throughput overlay across the past {trafficDays} days</p>
                    </div>
                    <div className="flex gap-2 mt-6 sm:mt-0 bg-gray-100/80 dark:bg-gray-900/80 p-1.5 rounded-2xl border border-gray-200/50 dark:border-gray-700/50 backdrop-blur-sm">
                        {[7, 14, 30].map(days => (
                            <button
                                key={days}
                                onClick={() => setTrafficDays(days)}
                                className={`px-6 py-2 rounded-xl text-sm font-bold transition-all duration-300 ${trafficDays === days
                                    ? 'bg-white dark:bg-gray-800 text-blue-600 dark:text-blue-400 shadow-md ring-1 ring-gray-200 dark:ring-gray-700'
                                    : 'text-gray-500 hover:text-gray-900 dark:hover:text-white hover:bg-white/50 dark:hover:bg-gray-700/50'
                                    }`}
                            >
                                {days}D
                            </button>
                        ))}
                    </div>
                </div>

                <div className="h-[400px] w-full">
                    {trafficData && trafficData.length > 0 ? (
                        <ResponsiveContainer width="100%" height="100%">
                            <AreaChart data={trafficData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                                <defs>
                                    <linearGradient id="colorUpload" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.4} />
                                        <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.0} />
                                    </linearGradient>
                                    <linearGradient id="colorDownload" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor="#10b981" stopOpacity={0.4} />
                                        <stop offset="95%" stopColor="#10b981" stopOpacity={0.0} />
                                    </linearGradient>
                                </defs>
                                <CartesianGrid strokeDasharray="4 4" vertical={false} stroke="#6b7280" strokeOpacity={0.15} />
                                <XAxis
                                    dataKey="date"
                                    stroke="#9ca3af"
                                    tickLine={false}
                                    axisLine={false}
                                    dy={15}
                                    tick={{ fontSize: 12, fontWeight: 600 }}
                                />
                                <YAxis
                                    stroke="#9ca3af"
                                    tickLine={false}
                                    axisLine={false}
                                    dx={-15}
                                    tickFormatter={(val) => `${val}G`}
                                    tick={{ fontSize: 12, fontWeight: 600 }}
                                />
                                <RechartsTooltip content={<CustomAreaTooltip />} cursor={{ stroke: '#6b7280', strokeWidth: 1, strokeDasharray: '3 3' }} />
                                <Area
                                    type="monotone"
                                    dataKey="upload_gb"
                                    stroke="#3b82f6"
                                    strokeWidth={4}
                                    fill="url(#colorUpload)"
                                    name="Upload"
                                    animationDuration={1500}
                                    activeDot={{ r: 6, strokeWidth: 0, fill: '#3b82f6', style: { filter: 'drop-shadow(0px 0px 5px rgba(59, 130, 246, 0.8))' } }}
                                />
                                <Area
                                    type="monotone"
                                    dataKey="download_gb"
                                    stroke="#10b981"
                                    strokeWidth={4}
                                    fill="url(#colorDownload)"
                                    name="Download"
                                    animationDuration={1500}
                                    activeDot={{ r: 6, strokeWidth: 0, fill: '#10b981', style: { filter: 'drop-shadow(0px 0px 5px rgba(16, 185, 129, 0.8))' } }}
                                />
                            </AreaChart>
                        </ResponsiveContainer>
                    ) : (
                        <div className="h-full w-full flex flex-col items-center justify-center text-gray-500 dark:text-gray-400">
                            <TrendingUp size={48} className="opacity-20 mb-4" />
                            <p className="font-medium text-lg">No traffic data recorded in this period</p>
                        </div>
                    )}
                </div>
            </div>

            {/* Quick Actions Shortcuts */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <QuickAction
                    title="Provision Client"
                    description="Create a new secure tunnel profile"
                    gradient="from-blue-600 to-indigo-600"
                    onClick={() => navigate('/users')}
                />
                <QuickAction
                    title="Routing Tunnels"
                    description="Configure Edge/Core VPN relays"
                    gradient="from-emerald-500 to-teal-600"
                    onClick={() => navigate('/tunnels')}
                />
                <QuickAction
                    title="Infrastructure"
                    description="Manage backend cluster nodes"
                    gradient="from-rose-500 to-orange-600"
                    onClick={() => navigate('/servers')}
                />
            </div>

            {/* Advanced Analytical Sub-Widgets Section */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 pt-4">
                <Suspense fallback={<SkeletonWidget />}>
                    <ServerResourcesWidget />
                </Suspense>
                <Suspense fallback={<SkeletonWidget />}>
                    <NetworkSpeedWidget />
                </Suspense>
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 pb-12">
                <Suspense fallback={<SkeletonWidget />}>
                    <ProtocolDistributionChart />
                </Suspense>
                <Suspense fallback={<SkeletonWidget />}>
                    <ActivityTimeline limit={5} />
                </Suspense>
            </div>

            {/* Modals Rendering */}
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
        className="group relative overflow-hidden bg-white/60 dark:bg-gray-800/60 backdrop-blur-2xl rounded-3xl shadow-lg hover:shadow-2xl transition-all duration-500 p-8 text-left border border-white/20 dark:border-gray-700/50"
    >
        {/* Animated progressive border underline */}
        <div className={`absolute bottom-0 left-0 w-full h-1.5 bg-gradient-to-r ${gradient} transform origin-left transition-transform duration-500 scale-x-0 group-hover:scale-x-100`} />

        {/* Glow effect on hover */}
        <div className={`absolute inset-0 bg-gradient-to-br ${gradient} opacity-0 group-hover:opacity-5 transition-opacity duration-500`} />

        <h3 className="text-xl font-extrabold tracking-tight text-gray-900 dark:text-white group-hover:text-transparent group-hover:bg-clip-text group-hover:bg-gradient-to-r group-hover:from-blue-600 group-hover:to-indigo-500 transition-all duration-300">
            {title}
        </h3>
        <p className="text-sm font-medium text-gray-500 dark:text-gray-400 mt-2">{description}</p>

        <div className="absolute right-6 bottom-6 opacity-0 translate-x-4 group-hover:opacity-100 group-hover:translate-x-0 transition-all duration-500 ease-out">
            <div className={`p-3 rounded-2xl bg-gradient-to-br ${gradient} shadow-md text-white`}>
                <ArrowUpRight size={20} strokeWidth={3} />
            </div>
        </div>
    </button>
));

export default Dashboard;

