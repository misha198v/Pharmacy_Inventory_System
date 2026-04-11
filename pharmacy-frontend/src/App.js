import React, { useState, useEffect } from 'react';
import axios from 'axios';

function App() {
  const [medicines, setMedicines] = useState([]);

  // This is the "Hook" that runs as soon as the page loads
  useEffect(() => {
    // We call your Django API here
    axios.get('http://127.0.0.1:8000/api/medicines/')
      .then(res => {
        setMedicines(res.data);
      })
      .catch(err => {
        console.error("The bridge is broken! Check Django or CORS:", err);
      });
  }, []);

  return (
    <div style={{ padding: '40px', backgroundColor: '#f8f9fa', minHeight: '100vh' }}>
      <header style={{ marginBottom: '30px', borderBottom: '3px solid #007bff' }}>
        <h1 style={{ color: '#2c3e50' }}>💊 Pharmacy AI Inventory Dashboard</h1>
        <p>Real-time Expiry Tracking & Stock Analysis</p>
      </header>

      <table style={{ width: '100%', borderCollapse: 'collapse', backgroundColor: 'white', boxShadow: '0 4px 8px rgba(0,0,0,0.1)' }}>
        <thead>
          <tr style={{ backgroundColor: '#007bff', color: 'white' }}>
            <th style={{ padding: '15px' }}>Drug Name</th>
            <th style={{ padding: '15px' }}>Stock</th>
            <th style={{ padding: '15px' }}>Expiry Date</th>
            <th style={{ padding: '15px' }}>Status</th>
          </tr>
        </thead>
        <tbody>
          {medicines.map(med => (
            <tr key={med.id} style={{ borderBottom: '1px solid #ddd', textAlign: 'center' }}>
              <td style={{ padding: '15px' }}><strong>{med.name}</strong></td>
              <td style={{ padding: '15px' }}>{med.stock_quantity}</td>
              <td style={{ padding: '15px' }}>{med.expiry_date}</td>
              <td style={{ padding: '15px' }}>
                <span style={{ 
                  padding: '8px 12px', 
                  borderRadius: '20px',
                  fontSize: '0.85rem',
                  fontWeight: 'bold',
                  // This is your Notebook logic in React!
                  backgroundColor: med.status === 'EXPIRED' ? '#ff4d4d' : 
                                   med.status === 'EXPIRING' ? '#ffcc00' : '#28a745',
                  color: 'white'
                }}>
                  {med.status} ({med.days_until_expiry} days left)
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default App;