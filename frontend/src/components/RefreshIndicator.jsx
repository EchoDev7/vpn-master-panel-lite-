import React from 'react';
import { Clock, RefreshCw } from 'lucide-react';

const RefreshIndicator = ({ lastUpdated, onRefresh, isRefreshing = false }) => {
    const getTimeAgo = (timestamp) => {
        if (!timestamp) return 'Never';

        const now = new Date();
        const updated = new Date(timestamp);
        const seconds = Math.floor((now - updated) / 1000);

        if (seconds < 60) return `${seconds}s ago`;
        const minutes = Math.floor(seconds / 60);
        if (minutes < 60) return `${minutes}m ago`;
        const hours = Math.floor(minutes / 60);
        if (hours < 24) return `${hours}h ago`;
        const days = Math.floor(hours / 24);
        return `${days}d ago`;
    };

    return (
        <div className="flex items-center gap-3 text-sm text-gray-600 dark:text-gray-400">
            <div className="flex items-center gap-1.5">
                <Clock size={14} />
                <span>Updated {getTimeAgo(lastUpdated)}</span>
            </div>
            {onRefresh && (
                <button
                    onClick={onRefresh}
                    disabled={isRefreshing}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    title="Refresh data"
                >
                    <RefreshCw
                        size={14}
                        className={isRefreshing ? 'animate-spin' : ''}
                    />
                    <span>{isRefreshing ? 'Refreshing...' : 'Refresh'}</span>
                </button>
            )}
        </div>
    );
};

export default RefreshIndicator;
