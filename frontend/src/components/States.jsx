import React from 'react';
import { AlertCircle, Database, Wifi, Users, RefreshCw } from 'lucide-react';

// Generic Error State
export const ErrorState = ({
    title = "Something went wrong",
    message = "We couldn't load this data. Please try again.",
    onRetry,
    icon: Icon = AlertCircle
}) => (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-8 text-center">
        <div className="flex justify-center mb-4">
            <div className="bg-red-100 dark:bg-red-900/20 rounded-full p-4">
                <Icon className="text-red-600 dark:text-red-400" size={48} />
            </div>
        </div>
        <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
            {title}
        </h3>
        <p className="text-gray-600 dark:text-gray-400 mb-6">
            {message}
        </p>
        {onRetry && (
            <button
                onClick={onRetry}
                className="bg-blue-500 hover:bg-blue-600 text-white font-medium py-2 px-6 rounded-lg transition-colors inline-flex items-center gap-2"
            >
                <RefreshCw size={18} />
                Try Again
            </button>
        )}
    </div>
);

// Empty State
export const EmptyState = ({
    title = "No data yet",
    message = "Get started by creating your first item.",
    icon: Icon = Database,
    actionLabel,
    onAction
}) => (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-12 text-center">
        <div className="flex justify-center mb-6">
            <div className="bg-gray-100 dark:bg-gray-700 rounded-full p-6">
                <Icon className="text-gray-400 dark:text-gray-500" size={64} />
            </div>
        </div>
        <h3 className="text-2xl font-semibold text-gray-900 dark:text-white mb-3">
            {title}
        </h3>
        <p className="text-gray-600 dark:text-gray-400 mb-8 max-w-md mx-auto">
            {message}
        </p>
        {actionLabel && onAction && (
            <button
                onClick={onAction}
                className="bg-blue-500 hover:bg-blue-600 text-white font-medium py-3 px-8 rounded-lg transition-colors"
            >
                {actionLabel}
            </button>
        )}
    </div>
);

// No Connection State
export const NoConnectionState = ({ onRetry }) => (
    <ErrorState
        title="No connection"
        message="Unable to connect to the server. Please check your internet connection."
        onRetry={onRetry}
        icon={Wifi}
    />
);

// No Users State
export const NoUsersState = ({ onAddUser }) => (
    <EmptyState
        title="No users yet"
        message="Create your first VPN user to get started with your VPN management."
        icon={Users}
        actionLabel="Add User"
        onAction={onAddUser}
    />
);

// API Error State
export const ApiErrorState = ({ error, onRetry }) => (
    <ErrorState
        title="Failed to load data"
        message={error?.message || "An unexpected error occurred while fetching data."}
        onRetry={onRetry}
    />
);

// Inline Error Message
export const InlineError = ({ message }) => (
    <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 flex items-start gap-3">
        <AlertCircle className="text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" size={20} />
        <p className="text-sm text-red-800 dark:text-red-200">
            {message}
        </p>
    </div>
);

// Success Message
export const SuccessMessage = ({ message, onClose }) => (
    <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4 flex items-start justify-between gap-3">
        <div className="flex items-start gap-3">
            <div className="bg-green-500 rounded-full p-1">
                <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
            </div>
            <p className="text-sm text-green-800 dark:text-green-200">
                {message}
            </p>
        </div>
        {onClose && (
            <button onClick={onClose} className="text-green-600 dark:text-green-400 hover:text-green-800 dark:hover:text-green-200">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
            </button>
        )}
    </div>
);

export default {
    Error: ErrorState,
    Empty: EmptyState,
    NoConnection: NoConnectionState,
    NoUsers: NoUsersState,
    ApiError: ApiErrorState,
    InlineError,
    Success: SuccessMessage
};
