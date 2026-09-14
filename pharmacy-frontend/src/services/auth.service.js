import { api } from './api';

export const authService = {
  login: (credentials) => api.post('/login/', credentials),
  logout: () => localStorage.removeItem('pharmacy_user'),
};