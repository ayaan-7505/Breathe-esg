import client from './client';

export const auditAPI = {
  getLogs: async (params = {}) => {
    const response = await client.get('/audit/logs/', { params });
    return response.data;
  },

  getLogDetail: async (id) => {
    const response = await client.get(`/audit/logs/${id}/`);
    return response.data;
  },

  getRecordHistory: async (recordId) => {
    const response = await client.get(`/audit/logs/`, {
      params: { record_id: recordId },
    });
    return response.data;
  },
};

export default auditAPI;
