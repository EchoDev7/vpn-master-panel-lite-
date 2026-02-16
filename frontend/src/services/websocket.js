/**
 * WebSocket Service
 * Handles WebSocket connection for real-time updates
 */

class WebSocketService {
    constructor() {
        this.ws = null;
        this.token = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 3000;
        this.listeners = new Map();
        this.isConnecting = false;
        this.isManualClose = false;
    }

    /**
     * Connect to WebSocket server
     * @param {string} token - JWT token for authentication
     */
    connect(token) {
        if (this.isConnecting || (this.ws && this.ws.readyState === WebSocket.OPEN)) {
            console.log('WebSocket already connected or connecting');
            return;
        }

        this.token = token;
        this.isConnecting = true;
        this.isManualClose = false;

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.hostname;
        const port = import.meta.env.VITE_API_PORT || '8000';
        const wsUrl = `${protocol}//${host}:${port}/ws/${token}`;

        console.log('Connecting to WebSocket:', wsUrl);

        try {
            this.ws = new WebSocket(wsUrl);

            this.ws.onopen = () => {
                console.log('WebSocket connected');
                this.isConnecting = false;
                this.reconnectAttempts = 0;
                this.emit('connection', { status: 'connected' });
            };

            this.ws.onmessage = (event) => {
                try {
                    const message = JSON.parse(event.data);
                    console.log('WebSocket message:', message);
                    this.handleMessage(message);
                } catch (error) {
                    console.error('Error parsing WebSocket message:', error);
                }
            };

            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.isConnecting = false;
                this.emit('error', error);
            };

            this.ws.onclose = (event) => {
                console.log('WebSocket closed:', event.code, event.reason);
                this.isConnecting = false;
                this.emit('connection', { status: 'disconnected' });

                // Attempt reconnection if not manually closed
                if (!this.isManualClose && this.reconnectAttempts < this.maxReconnectAttempts) {
                    this.reconnectAttempts++;
                    console.log(`Reconnecting... Attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts}`);
                    setTimeout(() => this.connect(this.token), this.reconnectDelay);
                }
            };
        } catch (error) {
            console.error('Error creating WebSocket:', error);
            this.isConnecting = false;
        }
    }

    /**
     * Disconnect from WebSocket server
     */
    disconnect() {
        this.isManualClose = true;
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
    }

    /**
     * Send message to server
     * @param {object} message - Message to send
     */
    send(message) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(message));
        } else {
            console.warn('WebSocket not connected, cannot send message');
        }
    }

    /**
     * Handle incoming message
     * @param {object} message - Received message
     */
    handleMessage(message) {
        const { type, data } = message;

        switch (type) {
            case 'ping':
                // Respond to ping with pong
                this.send({ type: 'pong', timestamp: new Date().toISOString() });
                break;

            case 'connection':
                this.emit('connection', data);
                break;

            case 'notification':
                this.emit('notification', data);
                break;

            case 'user_created':
            case 'user_updated':
            case 'user_deleted':
                this.emit('user_change', { type, data });
                break;

            case 'connection_status':
                this.emit('connection_status', data);
                break;

            case 'traffic_update':
                this.emit('traffic_update', data);
                break;

            case 'system_alert':
                this.emit('system_alert', data);
                break;

            case 'activity':
                this.emit('activity', data);
                break;

            default:
                console.log('Unknown message type:', type);
        }
    }

    /**
     * Subscribe to events
     * @param {string} event - Event name
     * @param {function} callback - Callback function
     * @returns {function} Unsubscribe function
     */
    on(event, callback) {
        if (!this.listeners.has(event)) {
            this.listeners.set(event, new Set());
        }
        this.listeners.get(event).add(callback);

        // Return unsubscribe function
        return () => {
            const callbacks = this.listeners.get(event);
            if (callbacks) {
                callbacks.delete(callback);
            }
        };
    }

    /**
     * Emit event to listeners
     * @param {string} event - Event name
     * @param {any} data - Event data
     */
    emit(event, data) {
        const callbacks = this.listeners.get(event);
        if (callbacks) {
            callbacks.forEach(callback => {
                try {
                    callback(data);
                } catch (error) {
                    console.error(`Error in ${event} listener:`, error);
                }
            });
        }
    }

    /**
     * Subscribe to specific events
     * @param {array} events - Array of event names
     */
    subscribe(events) {
        this.send({ type: 'subscribe', events });
    }

    /**
     * Unsubscribe from specific events
     * @param {array} events - Array of event names
     */
    unsubscribe(events) {
        this.send({ type: 'unsubscribe', events });
    }

    /**
     * Mark notification as read
     * @param {number} notificationId - Notification ID
     */
    markNotificationAsRead(notificationId) {
        this.send({ type: 'notification_read', notification_id: notificationId });
    }

    /**
     * Get connection status
     * @returns {string} Connection status
     */
    getStatus() {
        if (!this.ws) return 'disconnected';
        switch (this.ws.readyState) {
            case WebSocket.CONNECTING:
                return 'connecting';
            case WebSocket.OPEN:
                return 'connected';
            case WebSocket.CLOSING:
                return 'closing';
            case WebSocket.CLOSED:
                return 'disconnected';
            default:
                return 'unknown';
        }
    }
}

// Create singleton instance
const websocketService = new WebSocketService();

export default websocketService;
