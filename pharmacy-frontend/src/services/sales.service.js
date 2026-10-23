import { api } from './api';

// Sales
export const recordSale = (data) => api.post('/sales/', data);
export const getSales = () => api.get('/sales/');

// Forecast
export const getReorderSuggestions = (params) =>
  api.get('/reorder-suggestions/', { params });
export const getForecastChart = (name) =>
  api.get('/forecast-chart/', { params: { name } });

// Stock in
export const addMedicineBatch = (data) => api.post('/medicines/', data);

// Purchase orders
export const getOrders = () => api.get('/orders/');
export const createOrder = (data) => api.post('/orders/', data);
export const receiveOrder = (id, data) => api.post(`/orders/${id}/receive/`, data);

// Expired stock
export const writeOffBatch = (id, data) => api.post(`/medicines/${id}/write-off/`, data);

// Audit trail
export const getHistory = (name) => api.get('/history/', { params: { name } });

// User accounts (managers only)
export const getUsers = () => api.get('/users/');
export const createUser = (data) => api.post('/users/', data);
export const setUserActive = (id, isActive) =>
  api.post(`/users/${id}/active/`, { is_active: isActive });
export const resetUserPassword = (id, password) =>
  api.post(`/users/${id}/reset-password/`, { password });
