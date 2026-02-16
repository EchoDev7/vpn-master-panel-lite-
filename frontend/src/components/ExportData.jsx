import React, { useState } from 'react';
import { Download, FileText, Database } from 'lucide-react';
import apiService from '../services/api';

const ExportData = () => {
    const [exporting, setExporting] = useState(false);
    const [exportType, setExportType] = useState('users');

    const handleExport = async (format) => {
        try {
            setExporting(true);
            const response = await apiService.get(`/export/${exportType}?format=${format}`, {
                responseType: 'blob'
            });

            const blob = new Blob([response.data], {
                type: format === 'csv' ? 'text/csv' : 'application/json'
            });

            const url = window.URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = `${exportType}-${new Date().toISOString().split('T')[0]}.${format}`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            window.URL.revokeObjectURL(url);

            setExporting(false);
        } catch (error) {
            console.error('Export failed:', error);
            setExporting(false);
            alert('Export failed. Please try again.');
        }
    };

    return (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
            <div className="flex items-center gap-2 mb-6">
                <Database className="text-blue-500" size={20} />
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                    Export Data
                </h3>
            </div>

            {/* Export Type Selection */}
            <div className="mb-6">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Select Data Type
                </label>
                <select
                    value={exportType}
                    onChange={(e) => setExportType(e.target.value)}
                    className="w-full px-4 py-2 bg-gray-50 dark:bg-gray-900 border border-gray-300 dark:border-gray-700 rounded-lg text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
                >
                    <option value="users">Users</option>
                    <option value="connections">Connection Logs</option>
                    <option value="traffic">Traffic Statistics</option>
                    <option value="servers">Servers</option>
                    <option value="tunnels">Tunnels</option>
                    <option value="audit">Audit Logs</option>
                </select>
            </div>

            {/* Export Buttons */}
            <div className="space-y-3">
                <button
                    onClick={() => handleExport('csv')}
                    disabled={exporting}
                    className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-blue-500 hover:bg-blue-600 disabled:bg-gray-400 text-white rounded-lg transition-colors font-medium"
                >
                    <FileText size={18} />
                    Export as CSV
                </button>
                <button
                    onClick={() => handleExport('json')}
                    disabled={exporting}
                    className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-green-500 hover:bg-green-600 disabled:bg-gray-400 text-white rounded-lg transition-colors font-medium"
                >
                    <Download size={18} />
                    Export as JSON
                </button>
            </div>

            {exporting && (
                <div className="mt-4 p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
                    <p className="text-sm text-blue-700 dark:text-blue-300 text-center">
                        Preparing export...
                    </p>
                </div>
            )}
        </div>
    );
};

export default ExportData;
