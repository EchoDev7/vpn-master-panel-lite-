import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || '';

class APIService {
  constructor() {
    this.client = axios.create({
      baseURL: `${API_BASE_URL}/api/v1`,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Add token to requests
    this.client.interceptors.request.use((config) => {
      const token = localStorage.getItem('access_token');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    });

    // Handle token refresh
    this.client.interceptors.response.use(
      (response) => response,
      async (error) => {
        const originalRequest = error.config;

        if (error.response?.status === 401 && !originalRequest._retry) {
          originalRequest._retry = true;

          try {
            const refreshToken = localStorage.getItem('refresh_token');
            const response = await axios.post(
              `${API_BASE_URL}/api/v1/auth/refresh`,
              { refresh_token: refreshToken }
            );

            const { access_token, refresh_token } = response.data;
            localStorage.setItem('access_token', access_token);
            localStorage.setItem('refresh_token', refresh_token);

            originalRequest.headers.Authorization = `Bearer ${access_token}`;
            return this.client(originalRequest);
          } catch (refreshError) {
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');
            window.location.href = '/login';
            return Promise.reject(refreshError);
          }
        }

        return Promise.reject(error);
      }
    );
  }

  // Authentication
  async login(username, password) {
    const response = await this.client.post('/auth/login', { username, password });
    const { access_token, refresh_token } = response.data;
    localStorage.setItem('access_token', access_token);
    localStorage.setItem('refresh_token', refresh_token);
    return response;
  }

  async logout() {
    await this.client.post('/auth/logout');
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
  }

  async getCurrentUser() {
    return this.client.get('/auth/me');
  }

  // Users
  async getUsers(params = {}) {
    return this.client.get('/users/', { params });
  }

  async createUser(userData) {
    return this.client.post('/users/', userData);
  }

  async updateUser(userId, userData) {
    return this.client.put(`/users/${userId}`, userData);
  }

  async deleteUser(userId) {
    return this.client.delete(`/users/${userId}`);
  }

  // Servers
  async getServers() {
    return this.client.get('/servers/');
  }

  async createServer(serverData) {
    return this.client.post('/servers/', serverData);
  }

  // Tunnels
  async getTunnels() {
    return this.client.get('/tunnels/');
  }

  async createTunnel(tunnelData) {
    return this.client.post('/tunnels/', tunnelData);
  }

  async getTunnelStatus(tunnelId) {
    return this.client.get(`/tunnels/${tunnelId}/status`);
  }

  // Monitoring
  async getDashboardStats() {
    return this.client.get('/monitoring/dashboard');
  }

  async getTrafficStats(days = 7) {
    return this.client.get('/monitoring/traffic-stats', { params: { days } });
  }

  async getActiveConnections() {
    return this.client.get('/monitoring/active-connections');
  }

  // Generic methods
  async get(url, config = {}) {
    return this.client.get(url, config);
  }

  async post(url, data, config = {}) {
    return this.client.post(url, data, config);
  }

  async put(url, data, config = {}) {
    return this.client.put(url, data, config);
  }

  async delete(url, config = {}) {
    return this.client.delete(url, config);
  }
}

export const apiService = new APIService();
export default apiService;
