import axios from 'axios';

const API_URL = '/api';

const api = axios.create({
  baseURL: API_URL,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const authService = {
  register: async (username, email, password) => {
    const response = await api.post('/auth/register', { username, email, password });
    return response.data;
  },
  login: async (username, password) => {
    const formData = new FormData();
    formData.append('username', username);
    formData.append('password', password);
    const response = await api.post('/auth/login', formData);
    if (response.data.access_token) {
      localStorage.setItem('token', response.data.access_token);
    }
    return response.data;
  },
  logout: () => {
    localStorage.removeItem('token');
  },
  getCurrentUser: async () => {
    const response = await api.get('/auth/me');
    return response.data;
  },
  isAuthenticated: () => {
    return !!localStorage.getItem('token');
  },
};

export const fileService = {
  uploadFile: async (file, isLocked = false) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('is_locked', isLocked);
    const response = await api.post('/files/upload', formData, {
      params: { is_locked: isLocked }
    });
    return response.data;
  },
  getFiles: async () => {
    const response = await api.get('/files');
    return response.data;
  },
  getFileUrl: (fileId) => {
    const token = localStorage.getItem('token');
    return `${API_URL}/files/${fileId}?token=${encodeURIComponent(token)}`;
  },
  updateFileLock: async (fileId, isLocked) => {
    const response = await api.patch(`/files/${fileId}/lock`, { is_locked: isLocked });
    return response.data;
  },
  deleteFile: async (fileId) => {
    const response = await api.delete(`/files/${fileId}`);
    return response.data;
  },
};

export default api;
