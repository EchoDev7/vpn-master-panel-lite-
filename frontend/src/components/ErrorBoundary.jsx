import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

class ErrorBoundary extends React.Component {
    constructor(props) {
        super(props);
        this.state = { hasError: false, error: null, errorInfo: null };
    }

    static getDerivedStateFromError(error) {
        return { hasError: true };
    }

    componentDidCatch(error, errorInfo) {
        console.error('ErrorBoundary caught an error:', error, errorInfo);
        this.setState({
            error,
            errorInfo
        });

        // Send to error tracking service (e.g., Sentry)
        // if (window.Sentry) {
        //   window.Sentry.captureException(error);
        // }
    }

    handleReset = () => {
        this.setState({ hasError: false, error: null, errorInfo: null });
        window.location.reload();
    };

    render() {
        if (this.state.hasError) {
            return (
                <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center p-6">
                    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl p-8 max-w-lg w-full">
                        <div className="flex items-center justify-center mb-6">
                            <div className="bg-red-100 dark:bg-red-900/20 rounded-full p-4">
                                <AlertTriangle className="text-red-600 dark:text-red-400" size={48} />
                            </div>
                        </div>

                        <h1 className="text-2xl font-bold text-gray-900 dark:text-white text-center mb-4">
                            Something went wrong
                        </h1>

                        <p className="text-gray-600 dark:text-gray-400 text-center mb-6">
                            We're sorry for the inconvenience. The application encountered an unexpected error.
                        </p>

                        {process.env.NODE_ENV === 'development' && this.state.error && (
                            <div className="bg-gray-100 dark:bg-gray-900 rounded-lg p-4 mb-6 overflow-auto max-h-48">
                                <p className="text-sm font-mono text-red-600 dark:text-red-400 mb-2">
                                    {this.state.error.toString()}
                                </p>
                                {this.state.errorInfo && (
                                    <pre className="text-xs text-gray-600 dark:text-gray-400 whitespace-pre-wrap">
                                        {this.state.errorInfo.componentStack}
                                    </pre>
                                )}
                            </div>
                        )}

                        <div className="flex gap-4">
                            <button
                                onClick={this.handleReset}
                                className="flex-1 bg-blue-500 hover:bg-blue-600 text-white font-medium py-3 px-4 rounded-lg transition-colors flex items-center justify-center gap-2"
                            >
                                <RefreshCw size={20} />
                                Reload Page
                            </button>
                            <button
                                onClick={() => window.history.back()}
                                className="flex-1 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-900 dark:text-white font-medium py-3 px-4 rounded-lg transition-colors"
                            >
                                Go Back
                            </button>
                        </div>

                        <p className="text-sm text-gray-500 dark:text-gray-400 text-center mt-6">
                            If this problem persists, please contact support.
                        </p>
                    </div>
                </div>
            );
        }

        return this.props.children;
    }
}

export default ErrorBoundary;
