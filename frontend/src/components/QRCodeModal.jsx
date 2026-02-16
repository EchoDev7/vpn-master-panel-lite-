import React, { useState } from 'react';
import QRCode from 'qrcode.react';
import { X, Download, Copy, Check } from 'lucide-react';

const QRCodeModal = ({ isOpen, onClose, config, username, protocol = 'OpenVPN' }) => {
    const [copied, setCopied] = useState(false);

    if (!isOpen) return null;

    const handleDownloadQR = () => {
        const canvas = document.getElementById('qr-code-canvas');
        const pngUrl = canvas
            .toDataURL("image/png")
            .replace("image/png", "image/octet-stream");

        const downloadLink = document.createElement("a");
        downloadLink.href = pngUrl;
        downloadLink.download = `${username}-${protocol}-qr.png`;
        document.body.appendChild(downloadLink);
        downloadLink.click();
        document.body.removeChild(downloadLink);
    };

    const handleCopyConfig = async () => {
        try {
            await navigator.clipboard.writeText(config);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        } catch (err) {
            console.error('Failed to copy:', err);
        }
    };

    const handleDownloadConfig = () => {
        const blob = new Blob([config], { type: 'text/plain' });
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `${username}-${protocol.toLowerCase()}.conf`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
    };

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
                {/* Header */}
                <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
                    <div>
                        <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
                            {protocol} Configuration
                        </h2>
                        <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                            User: <span className="font-semibold">{username}</span>
                        </p>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                    >
                        <X size={24} className="text-gray-600 dark:text-gray-400" />
                    </button>
                </div>

                {/* Content */}
                <div className="p-6 space-y-6">
                    {/* QR Code Section */}
                    <div className="flex flex-col items-center">
                        <div className="bg-white p-6 rounded-lg shadow-inner">
                            <QRCode
                                id="qr-code-canvas"
                                value={config}
                                size={256}
                                level="H"
                                includeMargin={true}
                            />
                        </div>
                        <p className="text-sm text-gray-600 dark:text-gray-400 mt-4 text-center">
                            Scan this QR code with your {protocol} app
                        </p>
                        <button
                            onClick={handleDownloadQR}
                            className="mt-4 flex items-center gap-2 px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors"
                        >
                            <Download size={18} />
                            Download QR Code
                        </button>
                    </div>

                    {/* Configuration Text */}
                    <div>
                        <div className="flex items-center justify-between mb-2">
                            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                                Configuration File
                            </h3>
                            <div className="flex gap-2">
                                <button
                                    onClick={handleCopyConfig}
                                    className="flex items-center gap-2 px-3 py-1.5 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-900 dark:text-white rounded-lg transition-colors text-sm"
                                >
                                    {copied ? (
                                        <>
                                            <Check size={16} className="text-green-500" />
                                            Copied!
                                        </>
                                    ) : (
                                        <>
                                            <Copy size={16} />
                                            Copy
                                        </>
                                    )}
                                </button>
                                <button
                                    onClick={handleDownloadConfig}
                                    className="flex items-center gap-2 px-3 py-1.5 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-900 dark:text-white rounded-lg transition-colors text-sm"
                                >
                                    <Download size={16} />
                                    Download
                                </button>
                            </div>
                        </div>
                        <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4 max-h-64 overflow-y-auto">
                            <pre className="text-sm text-gray-800 dark:text-gray-200 font-mono whitespace-pre-wrap break-all">
                                {config}
                            </pre>
                        </div>
                    </div>

                    {/* Instructions */}
                    <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
                        <h4 className="font-semibold text-blue-900 dark:text-blue-200 mb-2">
                            Setup Instructions:
                        </h4>
                        <ol className="text-sm text-blue-800 dark:text-blue-300 space-y-1 list-decimal list-inside">
                            <li>Download and install {protocol} client on your device</li>
                            <li>Scan the QR code or import the configuration file</li>
                            <li>Connect to the VPN</li>
                            <li>Verify your connection is secure</li>
                        </ol>
                    </div>
                </div>

                {/* Footer */}
                <div className="flex justify-end gap-3 p-6 border-t border-gray-200 dark:border-gray-700">
                    <button
                        onClick={onClose}
                        className="px-6 py-2 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-900 dark:text-white rounded-lg transition-colors font-medium"
                    >
                        Close
                    </button>
                </div>
            </div>
        </div>
    );
};

export default QRCodeModal;
