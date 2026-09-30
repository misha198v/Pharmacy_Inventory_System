import { api } from './api';

export const inventoryService = {
  // Existing API calls
  getMedicines: () => api.get('/medicines/'),
  addMedicine: (payload) => api.post('/medicines/', payload),
  deleteMedicine: (id) => api.delete(`/medicines/${id}/`),

  // Feature 1: Low-stock detection
  checkLowStock: (medicines, threshold = 20) => {
    return medicines.filter(item => item.quantity < threshold);
  },

  // Feature 2: Expiration sorting
  sortByExpiry: (medicines) => {
    return [...medicines].sort((a, b) => a.days_until_expiry - b.days_until_expiry);
  },

  // Feature 3: Quick search by batch number or description
  filterMedicines: (medicines, query) => {
    const lowerQuery = query.toLowerCase();
    return medicines.filter(item => 
      item.description.toLowerCase().includes(lowerQuery) ||
      item.batch_number.toLowerCase().includes(lowerQuery)
    );
  }
};