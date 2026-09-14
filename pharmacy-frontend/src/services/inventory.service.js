import { api } from './api';

export const inventoryService = {
  getMedicines: () => api.get('/medicines/'),
  addMedicine: (payload) => api.post('/medicines/', payload),
  deleteMedicine: (id) => api.delete(`/medicines/${id}/`),
};