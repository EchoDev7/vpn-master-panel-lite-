import React, { useState, useEffect } from 'react';
import { Users, Activity, Server, Shield, TrendingUp, Globe } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { apiService } from '../services/api';

export const Dashboard = () => {
  const [stats, setStats] = useState(null);
  const [trafficData, setTrafficData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDashboardData();
    const interval = setInterval(loadDashboardData, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, []);

  const loadDashboardData = async () => {
    try {
      const [statsRes, trafficRes] = await Promise.all([
        apiService.get('/monitoring/dashboard'),
        apiService.get('/monitoring/traffic-stats?days=7')
      ]);
      setStats(statsRes.data);
      setTrafficData(trafficRes.data);
      setLoading(false);
    } catch (error) {
      console.error('Failed to load dashboard:', error);
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="animate-spin rounded-full h-16 w-16 border-t-2 border-b-2 border-primary-500"></div>
      </div>
    );
  }

  const StatCard = ({ title, value, icon: Icon, color, subtitle }) => (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 border-l-4" style={{ borderColor: color }}>
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-gray-600 dark:text-gray-400">{title}</p>
          <p className="text-3xl font-bold text-gray-900 dark:text-white mt-2">{value}</p>
          {subtitle && <p className="text-sm text-gray-500 mt-1">{subtitle}</p>}
        </div>
        <div className="p-3 rounded-full" style={{ backgroundColor: color + '20' }}>
          <Icon size={32} style={{ color }} />
        </div>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-6">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white flex items-center gap-3">
          <Shield className="text-primary-500" size={36} />
          VPN Master Panel
        </h1>
        <p className="text-gray-600 dark:text-gray-400 mt-2">
          Advanced Multi-Protocol VPN Management with PersianShield™
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <StatCard
          title="Total Users"
          value={stats?.users?.total || 0}
          subtitle={`${stats?.users?.active || 0} active`}
          icon={Users}
          color="#3b82f6"
        />
        <StatCard
          title="Active Connections"
          value={stats?.connections?.active || 0}
          subtitle="Real-time"
          icon={Activity}
          color="#10b981"
        />
        <StatCard
          title="Traffic (24h)"
          value={`${stats?.traffic?.gb_24h || 0} GB`}
          subtitle="Upload + Download"
          icon={TrendingUp}
          color="#f59e0b"
        />
        <StatCard
          title="System Load"
          value={`${stats?.system?.cpu_percent || 0}%`}
          subtitle={`RAM: ${stats?.system?.memory_percent || 0}%`}
          icon={Server}
          color="#ef4444"
        />
      </div>

      {/* Traffic Chart */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 mb-8">
        <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
          <Globe className="text-primary-500" />
          Traffic Overview (7 Days)
        </h2>
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
            />
            <Line 
              type="monotone" 
              dataKey="download_gb" 
              stroke="#10b981" 
              strokeWidth={2}
              name="Download"
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <QuickAction
          title="Add New User"
          description="Create VPN account"
          color="#3b82f6"
          onClick={() => {/* Navigate to add user */}}
        />
        <QuickAction
          title="Setup Tunnel"
          description="Configure Iran-Foreign tunnel"
          color="#239F40"
          onClick={() => {/* Navigate to tunnels */}}
        />
        <QuickAction
          title="Server Management"
          description="Manage VPN servers"
          color="#DA0000"
          onClick={() => {/* Navigate to servers */}}
        />
      </div>
    </div>
  );
};

const QuickAction = ({ title, description, color, onClick }) => (
  <button
    onClick={onClick}
    className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 text-left hover:shadow-lg transition-shadow border-l-4"
    style={{ borderColor: color }}
  >
    <h3 className="text-lg font-semibold text-gray-900 dark:text-white">{title}</h3>
    <p className="text-sm text-gray-600 dark:text-gray-400 mt-2">{description}</p>
  </button>
);

export default Dashboard;
