import client from './client';

export const emissionsAPI = {
  getRecords: async (params = {}) => {
    const response = await client.get('/emissions/', { params });
    return response.data;
  },

  getRecord: async (id) => {
    const response = await client.get(`/emissions/${id}/`);
    return response.data;
  },

  getSummary: async (params = {}) => {
    const response = await client.get('/emissions/summary/', { params });
    return response.data;
  },

  getChartData: async (params = {}) => {
    const response = await client.get('/emissions/charts/', { params });
    return response.data;
  },

  approve: async (id) => {
    const response = await client.post(`/emissions/${id}/approve/`);
    return response.data;
  },

  reject: async (id, reason) => {
    const response = await client.post(`/emissions/${id}/reject/`, { reason });
    return response.data;
  },

  flag: async (id, reason) => {
    const response = await client.post(`/emissions/${id}/flag/`, { reason });
    return response.data;
  },

  lock: async (id) => {
    const response = await client.post(`/emissions/${id}/lock/`);
    return response.data;
  },

  bulkAction: async (action, ids, reason = '') => {
    const response = await client.post('/emissions/bulk/', { action, ids, reason });
    return response.data;
  },

  getProvenance: async (id) => {
    const response = await client.get(`/emissions/${id}/provenance/`);
    return response.data;
  },
};

export default emissionsAPI;
