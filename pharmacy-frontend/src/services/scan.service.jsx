import {api} from './api';

// Check one scanned pack. Body: { code } or { medicine_name }, plus optional
// batch_number (printed on the pack) and basket ({ "name": units }).
export const scanPack = (payload) => api.post('/scan/', payload);

// Manager only: remember which medicine a barcode belongs to.
export const linkBarcode = (payload) => api.post('/scan/link/', payload);