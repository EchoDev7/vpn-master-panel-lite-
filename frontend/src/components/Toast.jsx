import React, { useEffect } from 'react';
import { CheckCircle, XCircle, X } from 'lucide-react';

const Toast = ({ message, type = 'success', onClose }) => {
    useEffect(() => {
        const timer = setTimeout(() => {
            onClose();
        }, 3000);
        return () => clearTimeout(timer);
    }, [onClose]);

    return (
        <div className="fixed top-6 right-6 z-50 animate-slide-in">
            <div className={`flex items-center gap-3 px-4 py-3 rounded-lg border shadow-xl backdrop-blur-md ${type === 'success' ? 'bg-green-500/10 border-green-500/20 text-green-400' : 'bg-red-500/10 border-red-500/20 text-red-400'
                }`}>
                {type === 'success' ? <CheckCircle size={20} /> : <XCircle size={20} />}
                <span className="font-medium text-sm">{message}</span>
                <button onClick={onClose} className="ml-2 hover:opacity-70 text-current">
                    <X size={16} />
                </button>
            </div>
        </div>
    );
};

export default Toast;
