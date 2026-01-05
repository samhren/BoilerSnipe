import axios from 'axios';

// In production, use same origin (empty string). In dev, use localhost:8000
const API_BASE_URL = import.meta.env.VITE_API_URL || '';

// Create axios instance
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add token to requests if available
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Handle 401 responses (unauthorized)
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Auth API
export const authAPI = {
  register: (userData) => api.post('/api/auth/register', userData),
  login: (credentials) => api.post('/api/auth/login', credentials),
  getCurrentUser: () => api.get('/api/auth/me'),
};

// Courses API
export const coursesAPI = {
  search: (query, termCode) => {
    const params = {};
    if (query) params.query = query;
    if (termCode) params.term_code = termCode;
    return api.get('/api/courses', { params });
  },
  getBycrn: (crn) => api.get(`/api/courses/${crn}`),
};

// Tracks API
export const tracksAPI = {
  create: (trackData) => api.post('/api/tracks', trackData),
  getAll: () => api.get('/api/tracks'),
  update: (trackId, updateData) => api.patch(`/api/tracks/${trackId}`, updateData),
  delete: (trackId) => api.delete(`/api/tracks/${trackId}`),
};

export default api;
