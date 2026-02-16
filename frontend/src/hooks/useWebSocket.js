/**
 * useWebSocket Hook
 * React hook for WebSocket connection
 */
import { useEffect, useState, useCallback, useRef } from 'react';
import websocketService from '../services/websocket';

export const useWebSocket = () => {
    const [isConnected, setIsConnected] = useState(false);
    const [connectionStatus, setConnectionStatus] = useState('disconnected');
    const listenersRef = useRef([]);

    useEffect(() => {
        // Get token from localStorage
        const token = localStorage.getItem('token');

        if (token) {
            // Connect to WebSocket
            websocketService.connect(token);

            // Subscribe to connection events
            const unsubConnection = websocketService.on('connection', (data) => {
                setIsConnected(data.status === 'connected');
                setConnectionStatus(data.status);
            });

            listenersRef.current.push(unsubConnection);

            // Update initial status
            setConnectionStatus(websocketService.getStatus());
        }

        // Cleanup on unmount
        return () => {
            listenersRef.current.forEach(unsub => unsub());
            listenersRef.current = [];
        };
    }, []);

    const subscribe = useCallback((event, callback) => {
        const unsubscribe = websocketService.on(event, callback);
        listenersRef.current.push(unsubscribe);
        return unsubscribe;
    }, []);

    const send = useCallback((message) => {
        websocketService.send(message);
    }, []);

    return {
        isConnected,
        connectionStatus,
        subscribe,
        send,
        websocketService
    };
};

export default useWebSocket;
