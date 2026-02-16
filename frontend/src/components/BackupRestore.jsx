import React, { useState } from 'react';
import { Database, Download, Upload, AlertCircle, CheckCircle, Clock } from 'lucide-react';
import apiService from '../services/api';

const BackupRestore = () => {
    const [creating, setCreating] = useState(false);
    const [restoring, setRestoring] = useState(false);
    const [backups, setBackups] = useState([]);
    const [message, setMessage] = useState(null);

    const handleCreateBackup = async () => {
        try {
            setCreating(true);
            setMessage(null);

            const response = await apiService.post('/system/backup');

            setMessage({
                type: 'success',
                text: 'Backup created successfully!'
            });

            // Download backup file
            const blob = new Blob([JSON.stringify(response.data)], { type: 'application/json' });
            const url = window.URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = `vpn-backup-${new Date().toISOString().split('T')[0]}.json`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            window.URL.revokeObjectURL(url);

            setCreating(false);
            loadBackups();
        } catch (error) {
            console.error('Backup failed:', error);
            setMessage({
                type: 'error',
                text: 'Backup creation failed. Please try again.'
            });
            setCreating(false);
        }
    };

    const handleRestore = async (file) => {
        if (!confirm('Are you sure you want to restore from this backup? This will overwrite current data.')) {
            return;
        }

        try {
            setRestoring(true);
            setMessage(null);

            const formData = new FormData();
            formData.append('backup', file);

            await apiService.post('/system/restore', formData, {
                headers: {
                    'Content-Type': 'multipart/form-data'
                }
            });

            setMessage({
                type: 'success',
                text: 'Restore completed successfully! Please refresh the page.'
            });
            setRestoring(false);
        } catch (error) {
            console.error('Restore failed:', error);
            setMessage({
                type: 'error',
                text: 'Restore failed. Please check the backup file and try again.'
            });
            setRestoring(false);
        }
    };

    const handleFileSelect = (event) => {
        const file = event.target.files[0];
        if (file) {
            handleRestore(file);
        }
    };

    const loadBackups = async () => {
        try {
            const response = await apiService.get('/system/backups');
            setBackups(response.data || []);
        } catch (error) {
            console.error('Failed to load backups:', error);
        }
    };

    return (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
            <div className="flex items-center gap-2 mb-6">
                <Database className="text-blue-500" size={20} />
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                    Backup & Restore
                </h3>
            </div>

            {/* Message */}
            {message && (
                <div className={`mb-6 p-4 rounded-lg border ${message.type === 'success'
                        ? 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800'
                        : 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800'
                    }`}>
                    <div className="flex items-center gap-2">
                        {message.type === 'success' ? (
                            <CheckCircle className="text-green-600 dark:text-green-400" size={20} />
                        ) : (
                            <AlertCircle className="text-red-600 dark:text-red-400" size={20} />
                        )}
                        <p className={`text-sm font-medium ${message.type === 'success'
                                ? 'text-green-800 dark:text-green-200'
                                : 'text-red-800 dark:text-red-200'
                            }`}>
                            {message.text}
                        </p>
                    </div>
                </div>
            )}

            {/* Create Backup */}
            <div className="mb-8">
                <h4 className="text-md font-semibold text-gray-900 dark:text-white mb-3">
                    Create Backup
                </h4>
                <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
                    Create a complete backup of all system data including users, servers, tunnels, and configurations.
                </p>
                <button
                    onClick={handleCreateBackup}
                    disabled={creating}
                    className="flex items-center gap-2 px-6 py-3 bg-blue-500 hover:bg-blue-600 disabled:bg-gray-400 text-white rounded-lg transition-colors font-medium"
                >
                    {creating ? (
                        <>
                            <Clock className="animate-spin" size={18} />
                            Creating Backup...
                        </>
                    ) : (
                        <>
                            <Download size={18} />
                            Create Backup
                        </>
                    )}
                </button>
            </div>

            {/* Restore from Backup */}
            <div className="border-t border-gray-200 dark:border-gray-700 pt-6">
                <h4 className="text-md font-semibold text-gray-900 dark:text-white mb-3">
                    Restore from Backup
                </h4>
                <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
                    Upload a backup file to restore your system data. This will overwrite all current data.
                </p>

                <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4 mb-4">
                    <div className="flex items-start gap-2">
                        <AlertCircle className="text-yellow-600 dark:text-yellow-400 flex-shrink-0 mt-0.5" size={18} />
                        <div>
                            <p className="text-sm font-semibold text-yellow-800 dark:text-yellow-200">
                                Warning
                            </p>
                            <p className="text-sm text-yellow-700 dark:text-yellow-300 mt-1">
                                Restoring from backup will replace all current data. Make sure to create a backup of your current state before proceeding.
                            </p>
                        </div>
                    </div>
                </div>

                <label className="flex items-center gap-2 px-6 py-3 bg-green-500 hover:bg-green-600 disabled:bg-gray-400 text-white rounded-lg transition-colors font-medium cursor-pointer inline-flex">
                    <Upload size={18} />
                    {restoring ? 'Restoring...' : 'Upload Backup File'}
                    <input
                        type="file"
                        accept=".json"
                        onChange={handleFileSelect}
                        disabled={restoring}
                        className="hidden"
                    />
                </label>
            </div>

            {/* Backup Info */}
            <div className="mt-8 p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
                <h4 className="text-sm font-semibold text-blue-900 dark:text-blue-100 mb-2">
                    What's included in backups?
                </h4>
                <ul className="text-sm text-blue-700 dark:text-blue-300 space-y-1">
                    <li>• All user accounts and credentials</li>
                    <li>• Server configurations</li>
                    <li>• Tunnel settings</li>
                    <li>• System settings and preferences</li>
                    <li>• Connection logs (last 30 days)</li>
                    <li>• Traffic statistics</li>
                </ul>
            </div>

            {/* Best Practices */}
            <div className="mt-4 p-4 bg-gray-50 dark:bg-gray-900 rounded-lg">
                <h4 className="text-sm font-semibold text-gray-900 dark:text-white mb-2">
                    Best Practices
                </h4>
                <ul className="text-sm text-gray-600 dark:text-gray-400 space-y-1">
                    <li>• Create regular backups (daily or weekly)</li>
                    <li>• Store backups in a secure, off-site location</li>
                    <li>• Test restore process periodically</li>
                    <li>• Keep multiple backup versions</li>
                    <li>• Document your backup schedule</li>
                </ul>
            </div>
        </div>
    );
};

export default BackupRestore;
