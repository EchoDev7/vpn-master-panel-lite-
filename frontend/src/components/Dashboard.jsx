import React, { Suspense, lazy, useState, useEffect, useRef, memo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Users, Activity, TrendingUp, Server, Shield, UserPlus, Settings as SettingsIcon, Globe, RefreshCw } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import apiService from '../services/api';
import ActiveConnectionsModal from './ActiveConnectionsModal';
import SystemMetricsModal from './SystemMetricsModal';
import { SkeletonDashboard, SkeletonWidget } from './Skeletons';
import { ApiErrorState } from './States';
import RefreshIndicator from './RefreshIndicator';

// Lazy load heavy components for better performance
const ServerResourcesWidget = lazy(() => import('./ServerResourcesWidget'));
const NetworkSpeedWidget = lazy(() => import('./NetworkSpeedWidget'));

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
  const [activeConnections, setActiveConnections] = useState([]);
  const [trafficByType, setTrafficByType] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [isRefreshing, setIsRefreshing] = useState(false);


  useEffect(() => {
    loadDashboardData();
    const interval = setInterval(loadDashboardData, 30000); // Refresh every 30s
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

  const handleUsersCardClick = () => {
    navigate('/users');
  };

  const handleConnectionsCardClick = async () => {
    await loadActiveConnections();
    setShowConnectionsModal(true);
  };

  const handleTrafficCardClick = () => {
    trafficChartRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  };

  const handleSystemCardClick = () => {
    setShowSystemModal(true);
  };

  if (loading) {
    return <SkeletonDashboard />;
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-6">
        <ApiErrorState error={error} onRetry={loadDashboardData} />
      </div>
    );
  }

  // Memoized StatCard component for better performance
  const StatCard = memo(({ title, value, icon: Icon, color, subtitle, onClick, clickable = true }) => (
    <div
      className={`bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 border-l-4 transition-all duration-300 ${clickable ? 'cursor-pointer hover:shadow-xl hover:scale-105 hover:-translate-y-1' : ''
        }`}
      style={{ borderColor: color }}
      onClick={onClick}
      role={clickable ? "button" : "presentation"}
      tabIndex={clickable ? 0 : -1}
    >
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-gray-600 dark:text-gray-400">{title}</p>
          <p className="text-3xl font-bold text-gray-900 dark:text-white mt-2">{value}</p>
          {subtitle && <p className="text-sm text-gray-500 mt-1">{subtitle}</p>}
        </div>
        <div className="p-3 rounded-full transition-transform duration-300 hover:scale-110" style={{ backgroundColor: color + '20' }}>
          <Icon size={32} style={{ color }} />
        </div>
      </div>
    </div>
  ));

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-6">
      {/* Header with Refresh Indicator */}
      <div className="mb-8 flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white flex items-center gap-3">
            <Shield className="text-primary-500" size={36} />
            VPN Master Panel
          </h1>
          <p className="text-gray-600 dark:text-gray-400 mt-2">
            Advanced Multi-Protocol VPN Management with PersianShield™
          </p>
        </div>
        <RefreshIndicator
          lastUpdated={lastUpdated}
          onRefresh={handleManualRefresh}
          isRefreshing={isRefreshing}
        />
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <StatCard
          title="Total Users"
          value={stats?.users?.total || 0}
          subtitle={`${stats?.users?.active || 0} active`}
          icon={Users}
          color="#3b82f6"
          onClick={handleUsersCardClick}
        />
        <StatCard
          title="Active Connections"
          value={stats?.connections?.active || 0}
          subtitle="Real-time"
          icon={Activity}
          color="#10b981"
          onClick={handleConnectionsCardClick}
        />
        <StatCard
          title="Traffic (24h)"
          value={`${stats?.traffic?.gb_24h || 0} GB`}
          subtitle="Upload + Download"
          icon={TrendingUp}
          color="#f59e0b"
          onClick={handleTrafficCardClick}
        />
        <StatCard
          title="System Load"
          value={`${stats?.system?.cpu_percent || 0}%`}
          subtitle={`RAM: ${stats?.system?.memory_percent || 0}%`}
          icon={Server}
          color="#ef4444"
          onClick={handleSystemCardClick}
        />
      </div>

      {/* Traffic Type Breakdown */}
      {trafficByType && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          <StatCard
            title="Direct Traffic"
            value={`${trafficByType?.summary?.direct?.gb || 0} GB`}
            subtitle={`Last ${trafficDays} days`}
            icon={Activity}
            color="#3b82f6"
            clickable={false}
          />
          <StatCard
            title="Tunnel Traffic"
            value={`${trafficByType?.summary?.tunnel?.gb || 0} GB`}
            subtitle={`Last ${trafficDays} days`}
            icon={Globe}
            color="#10b981"
            clickable={false}
          />
        </div>
      )}

      {/* Traffic Chart */}
      <div ref={trafficChartRef} className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 mb-8">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <Globe className="text-primary-500" />
            Traffic Overview ({trafficDays} Days)
          </h2>
          <div className="flex gap-2">
            <button
              onClick={() => setTrafficDays(7)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${trafficDays === 7
                ? 'bg-blue-500 text-white shadow-md'
                : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600'
                }`}
            >
              7 Days
            </button>
            <button
              onClick={() => setTrafficDays(14)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${trafficDays === 14
                ? 'bg-blue-500 text-white shadow-md'
                : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600'
                }`}
            >
              14 Days
            </button>
            <button
              onClick={() => setTrafficDays(30)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${trafficDays === 30
                ? 'bg-blue-500 text-white shadow-md'
                : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600'
                }`}
            >
              30 Days
            </button>
            <button
              onClick={handleManualRefresh}
              disabled={isRefreshing}
              className="px-4 py-2 rounded-lg text-sm font-medium bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600 transition-all flex items-center gap-2 disabled:opacity-50"
              title="Refresh"
            >
              <RefreshCw size={16} className={isRefreshing ? 'animate-spin' : ''} />
            </button>
          </div>
        </div>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={trafficData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis dataKey="date" stroke="#9ca3af" />
            <YAxis stroke="#9ca3af" label={{ value: 'GB', angle: -90, position: 'insideLeft' }} />
            <Tooltip
              contentStyle={{
                backgroundColor: '#1f2937',
                border: 'none',
                borderRadius: '8px',
                color: '#fff'
              }}
            />
            <Line
              type="monotone"
              dataKey="upload_gb"
              stroke="#3b82f6"
              strokeWidth={2}
              name="Upload"
              dot={{ r: 4 }}
              activeDot={{ r: 6 }}
            />
            <Line
              type="monotone"
              dataKey="download_gb"
              stroke="#10b981"
              strokeWidth={2}
              name="Download"
              dot={{ r: 4 }}
              activeDot={{ r: 6 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <QuickAction
          title="Add New User"
          description="Create VPN account"
          color="#3b82f6"
          onClick={() => navigate('/users')}
        />
        <QuickAction
          title="Setup Tunnel"
          description="Configure Iran-Foreign tunnel"
          color="#239F40"
          onClick={() => navigate('/tunnels')}
        />
        <QuickAction
          title="Server Management"
          description="Manage VPN servers"
          color="#DA0000"
          onClick={() => navigate('/servers')}
        />
      </div>

      {/* Advanced Monitoring Widgets with Lazy Loading */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <Suspense fallback={<SkeletonWidget />}>
          <ServerResourcesWidget />
        </Suspense>
        <Suspense fallback={<SkeletonWidget />}>
          <NetworkSpeedWidget />
        </Suspense>
      </div>

      {/* Modals */}
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
    </div>
  );
};

const QuickAction = memo(({ title, description, color, onClick }) => (
  <button
    onClick={onClick}
    className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 text-left hover:shadow-lg transition-shadow border-l-4"
    style={{ borderColor: color }}
  >
    <h3 className="text-lg font-semibold text-gray-900 dark:text-white">{title}</h3>
    <p className="text-sm text-gray-600 dark:text-gray-400 mt-2">{description}</p>
  </button>
));

export default Dashboard;
