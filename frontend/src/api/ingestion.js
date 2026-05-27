import client from './client';

export const ingestionAPI = {
  uploadFile: async (file, sourceType, onProgress) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('source_type', sourceType);

    const response = await client.post('/ingestion/upload/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (progressEvent) => {
        if (onProgress) {
          const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress(percent);
        }
      },
    });
    return response.data;
  },

  getJobs: async (params = {}) => {
    const response = await client.get('/ingestion/jobs/', { params });
    return response.data;
  },

  getJobDetail: async (jobId) => {
    const response = await client.get(`/ingestion/jobs/${jobId}/`);
    return response.data;
  },

  getJobErrors: async (jobId) => {
    const response = await client.get(`/ingestion/jobs/${jobId}/errors/`);
    return response.data;
  },

  retryJob: async (jobId) => {
    const response = await client.post(`/ingestion/jobs/${jobId}/retry/`);
    return response.data;
  },
};

export default ingestionAPI;
