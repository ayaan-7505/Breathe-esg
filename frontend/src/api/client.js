import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

const client = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
});

// Request interceptor — attach auth token
client.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('breathe_token');
    if (token) {
      config.headers.Authorization = `Token ${token}`;
    }
    const tenantId = localStorage.getItem('breathe_tenant_id');
    if (tenantId) {
      config.headers['X-Tenant-ID'] = tenantId;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor — handle 401s
client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('breathe_token');
      localStorage.removeItem('breathe_user');
      localStorage.removeItem('breathe_tenant_id');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default client;
