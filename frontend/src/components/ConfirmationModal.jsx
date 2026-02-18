import React from 'react';
import { AlertTriangle, X } from 'lucide-react';

const ConfirmationModal = ({ isOpen, onClose, onConfirm, title, message, confirmText = "Confirm", confirmColor = "blue" }) => {
    if (!isOpen) return null;

    const colorClasses = {
        blue: "bg-blue-600 hover:bg-blue-700",
        red: "bg-red-600 hover:bg-red-700",
        orange: "bg-orange-600 hover:bg-orange-700",
        green: "bg-green-600 hover:bg-green-700",
        teal: "bg-teal-600 hover:bg-teal-700",
    };

    return (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center p-4 z-50 animate-fade-in backdrop-blur-sm">
            <div className="bg-gray-800 rounded-xl p-6 w-full max-w-sm border border-gray-700 shadow-2xl relative">
                <button onClick={onClose} className="absolute top-4 right-4 text-gray-400 hover:text-white">
                    <X size={20} />
                </button>
                <div className="flex flex-col items-center text-center">
                    <div className={`w-12 h-12 rounded-full ${confirmColor === 'red' ? 'bg-red-500/10' : 'bg-blue-500/10'} flex items-center justify-center mb-4`}>
                        <AlertTriangle className={`${confirmColor === 'red' ? 'text-red-400' : 'text-blue-400'}`} size={24} />
                    </div>
                    <h3 className="text-xl font-bold text-white mb-2">{title}</h3>
                    <p className="text-gray-300 mb-6 whitespace-pre-line text-sm">{message}</p>
                    <div className="flex gap-3 w-full">
                        <button
                            onClick={onClose}
                            className="flex-1 bg-gray-700 hover:bg-gray-600 text-white py-2 rounded-lg transition-colors font-medium"
                        >
                            Cancel
                        </button>
                        <button
                            onClick={() => { onConfirm(); onClose(); }}
                            className={`flex-1 ${colorClasses[confirmColor] || colorClasses.blue} text-white py-2 rounded-lg font-medium transition-colors`}
                        >
                            {confirmText}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default ConfirmationModal;
