import { api } from './api';

export const recordSale = (data) => api.post('/sales/', data);
export const getSales = () => api.get('/sales/');
export const getReorderSuggestions = (params) =>
  api.get('/reorder-suggestions/', { params });