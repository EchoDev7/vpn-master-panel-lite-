import React from 'react';

// Skeleton for Stat Cards
export const SkeletonCard = () => (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 border-l-4 border-gray-300 dark:border-gray-600 animate-pulse">
        <div className="flex items-center justify-between">
            <div className="flex-1">
                <div className="h-4 bg-gray-300 dark:bg-gray-700 rounded w-24 mb-3"></div>
                <div className="h-8 bg-gray-300 dark:bg-gray-700 rounded w-16 mb-2"></div>
                <div className="h-3 bg-gray-300 dark:bg-gray-700 rounded w-20"></div>
            </div>
            <div className="w-16 h-16 bg-gray-300 dark:bg-gray-700 rounded-full"></div>
        </div>
    </div>
);

// Skeleton for Charts
export const SkeletonChart = ({ height = 300 }) => (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 animate-pulse">
        <div className="flex items-center justify-between mb-4">
            <div className="h-6 bg-gray-300 dark:bg-gray-700 rounded w-40"></div>
            <div className="flex gap-2">
                <div className="h-10 w-20 bg-gray-300 dark:bg-gray-700 rounded"></div>
                <div className="h-10 w-20 bg-gray-300 dark:bg-gray-700 rounded"></div>
                <div className="h-10 w-20 bg-gray-300 dark:bg-gray-700 rounded"></div>
            </div>
        </div>
        <div className="relative" style={{ height }}>
            <div className="absolute inset-0 flex items-end justify-between px-4">
                {[...Array(7)].map((_, i) => (
                    <div
                        key={i}
                        className="bg-gray-300 dark:bg-gray-700 rounded-t w-12"
                        style={{ height: `${Math.random() * 60 + 40}%` }}
                    ></div>
                ))}
            </div>
        </div>
    </div>
);

// Skeleton for Widgets
export const SkeletonWidget = () => (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 animate-pulse">
        <div className="flex items-center justify-between mb-6">
            <div className="h-6 bg-gray-300 dark:bg-gray-700 rounded w-48"></div>
            <div className="h-8 w-8 bg-gray-300 dark:bg-gray-700 rounded"></div>
        </div>
        <div className="space-y-4">
            <div className="h-4 bg-gray-300 dark:bg-gray-700 rounded w-full"></div>
            <div className="h-4 bg-gray-300 dark:bg-gray-700 rounded w-5/6"></div>
            <div className="h-4 bg-gray-300 dark:bg-gray-700 rounded w-4/6"></div>
            <div className="h-32 bg-gray-300 dark:bg-gray-700 rounded w-full mt-4"></div>
        </div>
    </div>
);

// Skeleton for Tables
export const SkeletonTable = ({ rows = 5, columns = 4 }) => (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md overflow-hidden animate-pulse">
        <div className="p-4 border-b border-gray-200 dark:border-gray-700">
            <div className="h-6 bg-gray-300 dark:bg-gray-700 rounded w-32"></div>
        </div>
        <div className="overflow-x-auto">
            <table className="min-w-full">
                <thead className="bg-gray-50 dark:bg-gray-900">
                    <tr>
                        {[...Array(columns)].map((_, i) => (
                            <th key={i} className="px-6 py-3">
                                <div className="h-4 bg-gray-300 dark:bg-gray-700 rounded w-20"></div>
                            </th>
                        ))}
                    </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                    {[...Array(rows)].map((_, rowIndex) => (
                        <tr key={rowIndex}>
                            {[...Array(columns)].map((_, colIndex) => (
                                <td key={colIndex} className="px-6 py-4">
                                    <div className="h-4 bg-gray-300 dark:bg-gray-700 rounded w-24"></div>
                                </td>
                            ))}
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    </div>
);

// Skeleton for Dashboard Grid
export const SkeletonDashboard = () => (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-6">
        {/* Header Skeleton */}
        <div className="mb-8 animate-pulse">
            <div className="h-10 bg-gray-300 dark:bg-gray-700 rounded w-64 mb-2"></div>
            <div className="h-4 bg-gray-300 dark:bg-gray-700 rounded w-96"></div>
        </div>

        {/* Stats Grid Skeleton */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            {[...Array(4)].map((_, i) => (
                <SkeletonCard key={i} />
            ))}
        </div>

        {/* Traffic Type Breakdown Skeleton */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
            {[...Array(2)].map((_, i) => (
                <SkeletonCard key={i} />
            ))}
        </div>

        {/* Chart Skeleton */}
        <SkeletonChart />

        {/* Widgets Skeleton */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-8">
            {[...Array(2)].map((_, i) => (
                <SkeletonWidget key={i} />
            ))}
        </div>
    </div>
);

export default {
    Card: SkeletonCard,
    Chart: SkeletonChart,
    Widget: SkeletonWidget,
    Table: SkeletonTable,
    Dashboard: SkeletonDashboard
};
