import React, { Suspense, lazy } from 'react';
import { BarChart3, Shield } from 'lucide-react';
import { SkeletonWidget } from './Skeletons';

// Lazy load all analytics components
const UserLocationMap = lazy(() => import('./UserLocationMap'));
const UsageHeatmap = lazy(() => import('./UsageHeatmap'));
const TrafficComparison = lazy(() => import('./TrafficComparison'));
const AuditLogs = lazy(() => import('./AuditLogs'));
const BackupRestore = lazy(() => import('./BackupRestore'));
const ExportData = lazy(() => import('./ExportData'));

const Analytics = () => {
    return (
        <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-6">
            {/* Header */}
            <div className="mb-8">
                <h1 className="text-3xl font-bold text-gray-900 dark:text-white flex items-center gap-3">
                    <BarChart3 className="text-blue-500" size={36} />
                    Advanced Analytics
                </h1>
                <p className="text-gray-600 dark:text-gray-400 mt-2">
                    Comprehensive insights, reports, and system management
                </p>
            </div>

            {/* Traffic Analysis Section */}
            <div className="mb-8">
                <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                    <Shield className="text-blue-500" size={24} />
                    Traffic Analysis
                </h2>
                <div className="grid grid-cols-1 gap-6">
                    <Suspense fallback={<SkeletonWidget />}>
                        <TrafficComparison />
                    </Suspense>
                </div>
            </div>

            {/* Geographic & Usage Patterns */}
            <div className="mb-8">
                <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4">
                    Geographic & Usage Patterns
                </h2>
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    <Suspense fallback={<SkeletonWidget />}>
                        <UserLocationMap />
                    </Suspense>
                    <Suspense fallback={<SkeletonWidget />}>
                        <UsageHeatmap />
                    </Suspense>
                </div>
            </div>

            {/* System Management */}
            <div className="mb-8">
                <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4">
                    System Management
                </h2>
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    <Suspense fallback={<SkeletonWidget />}>
                        <BackupRestore />
                    </Suspense>
                    <Suspense fallback={<SkeletonWidget />}>
                        <ExportData />
                    </Suspense>
                </div>
            </div>

            {/* Audit & Security */}
            <div className="mb-8">
                <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4">
                    Audit & Security
                </h2>
                <Suspense fallback={<SkeletonWidget />}>
                    <AuditLogs />
                </Suspense>
            </div>
        </div>
    );
};

export default Analytics;
