import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_URL || 'http://127.0.0.1:8000/api';

export const api = axios.create({
  baseURL: API_BASE,
  timeout: 10000,
});

// Add token to requests
api.interceptors.request.use((config) => {
  let user = null;
  try {
    user = JSON.parse(localStorage.getItem('pharmacy_user'));
  } catch {
    user = null;
  }
  if (user?.token) {
    config.headers.Authorization = `Token ${user.token}`;
  }
  return config;
});

// Handle errors globally
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const isLoginRequest = error.config?.url?.includes('/login/');
    if (error.response?.status === 401 && !isLoginRequest) {
      localStorage.removeItem('pharmacy_user');
      window.location.href = '/';
    }
    return Promise.reject(error);
  }
);