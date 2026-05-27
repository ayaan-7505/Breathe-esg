import client from './client';

export const authAPI = {
  login: async (email, password) => {
    const response = await client.post('/auth/login/', { email, password });
    return response.data;
  },

  logout: async () => {
    try {
      await client.post('/auth/logout/');
    } finally {
      localStorage.removeItem('breathe_token');
      localStorage.removeItem('breathe_user');
      localStorage.removeItem('breathe_tenant_id');
    }
  },

  getCurrentUser: async () => {
    const response = await client.get('/auth/me/');
    return response.data;
  },

  refreshToken: async () => {
    const response = await client.post('/auth/refresh/');
    return response.data;
  },
};

export default authAPI;
