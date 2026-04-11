import React, { useState, useEffect } from 'react';
import axios from 'axios';
import jsPDF from 'jspdf';
import autoTable from 'jspdf-autotable';

function App() {
  const [medicines, setMedicines] = useState([]);
  const [searchTerm, setSearchTerm] = useState("");
  
  // NEW: State for the "Add Stock" Modal
  const [showModal, setShowModal] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    stock_quantity: '',
    expiry_date: ''
  });

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = () => {
    axios.get('http://127.0.0.1:8000/api/medicines/')
      .then(res => {
        const sorted = res.data.sort((a, b) => new Date(a.expiry_date) - new Date(b.expiry_date));
        setMedicines(sorted);
      })
      .catch(err => console.error(err));
  };

  // NEW: Function to send data to Django
  const handleAddStock = (e) => {
    e.preventDefault();
    axios.post('http://127.0.0.1:8000/api/medicines/', formData)
      .then(() => {
        setShowModal(false); // Close the pop-up
        setFormData({ name: '', stock_quantity: '', expiry_date: '' }); // Clear form
        fetchData(); // Refresh the list automatically!
      })
      .catch(err => alert("Error adding medicine: Check if all fields are correct."));
  };

  const handleExportPDF = () => {
    const doc = new jsPDF();
    doc.text("Pharmacy Inventory Status Report", 14, 15);
    const tableRows = filteredMedicines.map(med => [med.name, med.stock_quantity, med.expiry_date, med.status]);
    autoTable(doc, { head: [['Drug Name', 'Stock', 'Expiry Date', 'Status']], body: tableRows, startY: 25 });
    doc.save("Pharmacy_Inventory_Report.pdf");
  };

  const filteredMedicines = medicines.filter(med =>
    med.name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div style={{ padding: '30px', backgroundColor: '#f8f9fa', minHeight: '100vh', fontFamily: 'sans-serif' }}>
      
      {/* HEADER */}
      <header style={{ marginBottom: '30px' }}>
        <h1 style={{ color: '#0056b3' }}>🏥 Pharmacy Intelligence Dashboard</h1>
        <div style={{ display: 'flex', gap: '15px', marginTop: '20px' }}>
          <input 
            type="text" 
            placeholder="🔍 Search drug..." 
            style={{ padding: '12px', width: '300px', borderRadius: '8px', border: '1px solid #ddd' }}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
          <button 
            onClick={() => setShowModal(true)}
            style={{ backgroundColor: '#28a745', color: 'white', padding: '12px 20px', border: 'none', borderRadius: '8px', cursor: 'pointer', fontWeight: 'bold' }}
          >
            + Add Stock
          </button>
          <button onClick={handleExportPDF} style={{ backgroundColor: '#dc3545', color: 'white', padding: '12px 20px', border: 'none', borderRadius: '8px', cursor: 'pointer', fontWeight: 'bold' }}>
            📄 Export PDF
          </button>
        </div>
      </header>

      {/* MODAL POP-UP (Only shows when showModal is true) */}
      {showModal && (
        <div style={{ position: 'fixed', top: 0, left: 0, width: '100%', height: '100%', backgroundColor: 'rgba(0,0,0,0.5)', display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 1000 }}>
          <div style={{ backgroundColor: 'white', padding: '30px', borderRadius: '12px', width: '400px' }}>
            <h3>Add New Inventory</h3>
            <form onSubmit={handleAddStock}>
              <label>Drug Name:</label>
              <input type="text" required style={inputStyle} value={formData.name} onChange={(e) => setFormData({...formData, name: e.target.value})} />
              
              <label>Stock Quantity:</label>
              <input type="number" required style={inputStyle} value={formData.stock_quantity} onChange={(e) => setFormData({...formData, stock_quantity: e.target.value})} />
              
              <label>Expiry Date:</label>
              <input type="date" required style={inputStyle} value={formData.expiry_date} onChange={(e) => setFormData({...formData, expiry_date: e.target.value})} />
              
              <div style={{ display: 'flex', gap: '10px', marginTop: '20px' }}>
                <button type="submit" style={{ flex: 1, backgroundColor: '#28a745', color: 'white', border: 'none', padding: '10px', borderRadius: '5px', cursor: 'pointer' }}>Save Drug</button>
                <button type="button" onClick={() => setShowModal(false)} style={{ flex: 1, backgroundColor: '#6c757d', color: 'white', border: 'none', padding: '10px', borderRadius: '5px', cursor: 'pointer' }}>Cancel</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* THE TABLE */}
      <div style={{ backgroundColor: 'white', borderRadius: '12px', boxShadow: '0 4px 6px rgba(0,0,0,0.1)', overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ backgroundColor: '#007bff', color: 'white', textAlign: 'left' }}>
              <th style={{ padding: '15px' }}>Priority</th>
              <th style={{ padding: '15px' }}>Drug Name</th>
              <th style={{ padding: '15px' }}>Stock</th>
              <th style={{ padding: '15px' }}>Expiry Date</th>
              <th style={{ padding: '15px', textAlign: 'center' }}>Action</th>
            </tr>
          </thead>
          <tbody>
            {filteredMedicines.map((med, index) => (
              <tr key={med.id} style={{ borderBottom: '1px solid #eee' }}>
                <td style={{ padding: '15px' }}>#{index + 1}</td>
                <td style={{ padding: '15px' }}><strong>{med.name}</strong></td>
                <td style={{ padding: '15px' }}>{med.stock_quantity} {med.stock_quantity < 50 && <span style={{color: 'red', fontWeight: 'bold'}}>⚠️</span>}</td>
                <td style={{ padding: '15px' }}>{med.expiry_date}</td>
                <td style={{ padding: '15px', textAlign: 'center' }}>
                  <span style={{ padding: '8px 16px', borderRadius: '20px', fontSize: '12px', fontWeight: 'bold', backgroundColor: med.status === 'EXPIRED' ? '#ffdce0' : '#d4edda', color: med.status === 'EXPIRED' ? '#af1e2c' : '#155724' }}>
                    {med.status === 'EXPIRED' ? '🚫 DISPOSE' : '✅ SELL FIRST'}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

const inputStyle = { width: '100%', padding: '10px', marginBottom: '15px', borderRadius: '5px', border: '1px solid #ddd', boxSizing: 'border-box' };

export default App;