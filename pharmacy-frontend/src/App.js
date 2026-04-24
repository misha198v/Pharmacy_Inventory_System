import React, { useState, useEffect } from 'react';
import axios from 'axios';
import jsPDF from 'jspdf';
import autoTable from 'jspdf-autotable';

const API = 'http://127.0.0.1:8000/api';

function App() {
  const [user, setUser] = useState(null); // { username, role, token }
  const [medicines, setMedicines] = useState([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [showModal, setShowModal] = useState(false);
  const [formData, setFormData] = useState({
    name: '', stock_quantity: '', expiry_date: '', price: '', reorder_level: '10'
  });
  const [loginData, setLoginData] = useState({ username: '', password: '' });
  const [loginError, setLoginError] = useState('');
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => {
    const saved = localStorage.getItem('pharmacy_user');
    if (saved) {
      const parsed = JSON.parse(saved);
      setUser(parsed);
      fetchData(parsed.token);
    }
  }, []);

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoginError('');
    try {
      const res = await axios.post(`${API}/login/`, loginData);
      const userData = { username: res.data.username, role: res.data.role, token: res.data.token };
      setUser(userData);
      localStorage.setItem('pharmacy_user', JSON.stringify(userData));
      fetchData(res.data.token);
    } catch (err) {
      setLoginError('Invalid username or password.');
    }
  };

  const handleLogout = () => {
    setUser(null);
    setMedicines([]);
    localStorage.removeItem('pharmacy_user');
  };

  const authHeaders = (token) => ({
    headers: { Authorization: `Token ${token || user?.token}` }
  });

  const fetchData = (token) => {
    axios.get(`${API}/medicines/`, authHeaders(token))
      .then(res => {
        const sorted = res.data.sort((a, b) => new Date(a.expiry_date) - new Date(b.expiry_date));
        setMedicines(sorted);
      })
      .catch(err => console.error(err));
  };

  const handleDelete = (id) => {
    if (user?.role !== 'manager') { alert('Only managers can delete medicines.'); return; }
    if (window.confirm("Are you sure you want to remove this stock entry?")) {
      axios.delete(`${API}/medicines/${id}/`, authHeaders())
        .then(() => setMedicines(medicines.filter(med => med.id !== id)))
        .catch(err => alert("Error deleting: " + err.message));
    }
  };

  const handleAddStock = (e) => {
    e.preventDefault();
    const payload = {
      name: formData.name,
      stock_quantity: parseInt(formData.stock_quantity),
      price: parseFloat(formData.price),
      expiry_date: formData.expiry_date,
      reorder_level: parseInt(formData.reorder_level),
      description: '',
    };
    axios.post(`${API}/medicines/`, payload, authHeaders())
      .then(() => {
        setShowModal(false);
        setFormData({ name: '', stock_quantity: '', expiry_date: '', price: '', reorder_level: '10' });
        fetchData();
      })
      .catch(err => {
        if (err.response) { alert("Error: " + JSON.stringify(err.response.data)); }
        else { alert("Network error: " + err.message); }
      });
  };

  const handleExportPDF = () => {
    const doc = new jsPDF();
    doc.text("Pharmacy Inventory Status Report", 14, 15);
    const tableRows = filteredMedicines.map(med => [med.name, med.stock_quantity, med.price, med.expiry_date, med.status, med.added_by_username]);
    autoTable(doc, { head: [['Drug Name', 'Stock', 'Price (UGX)', 'Expiry Date', 'Status', 'Added By']], body: tableRows, startY: 25 });
    doc.save("Pharmacy_Inventory_Report.pdf");
  };

  const filteredMedicines = medicines.filter(med => med.name.toLowerCase().includes(searchTerm.toLowerCase()));
  const totalValue = filteredMedicines.reduce((acc, med) => acc + (Number(med.stock_quantity) * Number(med.price)), 0);

  // LOGIN SCREEN
  if (!user) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh', backgroundColor: '#f0f4f8' }}>
        <div style={{ backgroundColor: 'white', padding: '40px', borderRadius: '16px', boxShadow: '0 8px 24px rgba(0,0,0,0.12)', width: '360px' }}>
          <div style={{ textAlign: 'center', marginBottom: '30px' }}>
            <div style={{ fontSize: '48px' }}>🏥</div>
            <h2 style={{ color: '#0056b3', margin: '10px 0 5px' }}>Pharmacy System</h2>
            <p style={{ color: '#888', margin: 0 }}>Sign in to continue</p>
          </div>
          <form onSubmit={handleLogin}>
            <label style={labelStyle}>Username</label>
            <input type="text" required style={inputStyle} value={loginData.username} onChange={(e) => setLoginData({ ...loginData, username: e.target.value })} />
            <label style={labelStyle}>Password</label>
            <input type="password" required style={inputStyle} value={loginData.password} onChange={(e) => setLoginData({ ...loginData, password: e.target.value })} />
            {loginError && <p style={{ color: 'red', fontSize: '13px', margin: '0 0 10px' }}>{loginError}</p>}
            <button type="submit" style={{ width: '100%', padding: '12px', backgroundColor: '#0056b3', color: 'white', border: 'none', borderRadius: '8px', fontSize: '16px', cursor: 'pointer', fontWeight: 'bold' }}>
              Sign In
            </button>
          </form>
        </div>
      </div>
    );
  }

  // MAIN DASHBOARD
  return (
    <div style={{ padding: '30px', backgroundColor: '#f8f9fa', minHeight: '100vh', fontFamily: 'sans-serif' }}>
      <header style={{ marginBottom: '30px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h1 style={{ color: '#0056b3', margin: 0 }}>🏥 Pharmacy Intelligence Dashboard</h1>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <span style={{ backgroundColor: user.role === 'manager' ? '#fff3cd' : '#d4edda', padding: '6px 14px', borderRadius: '20px', fontSize: '13px', fontWeight: 'bold', color: user.role === 'manager' ? '#856404' : '#155724' }}>
              {user.role === 'manager' ? '👔 Manager' : '👤 Staff'}: {user.username}
            </span>
            <button onClick={handleLogout} style={{ backgroundColor: '#dc3545', color: 'white', border: 'none', padding: '8px 16px', borderRadius: '8px', cursor: 'pointer', fontSize: '13px' }}>
              Sign Out
            </button>
          </div>
        </div>
        <p style={{ color: '#666', fontSize: '18px', marginTop: '10px' }}>
          Total Stock Value: <strong style={{ color: '#28a745' }}>{totalValue.toLocaleString()} UGX</strong>
        </p>
        <div style={{ display: 'flex', gap: '15px', marginTop: '20px' }}>
          <input type="text" placeholder="🔍 Search drug..." style={{ padding: '12px', width: '300px', borderRadius: '8px', border: '1px solid #ddd' }} onChange={(e) => setSearchTerm(e.target.value)} />
          <button onClick={() => setShowModal(true)} style={{ backgroundColor: '#28a745', color: 'white', padding: '12px 20px', border: 'none', borderRadius: '8px', cursor: 'pointer', fontWeight: 'bold' }}>+ Add Stock</button>
          <button onClick={handleExportPDF} style={{ backgroundColor: '#dc3545', color: 'white', padding: '12px 20px', border: 'none', borderRadius: '8px', cursor: 'pointer', fontWeight: 'bold' }}>📄 Export PDF</button>
        </div>
      </header>

      {showModal && (
        <div style={{ position: 'fixed', top: 0, left: 0, width: '100%', height: '100%', backgroundColor: 'rgba(0,0,0,0.5)', display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 1000 }}>
          <div style={{ backgroundColor: 'white', padding: '30px', borderRadius: '12px', width: '400px' }}>
            <h3>Add New Inventory</h3>
            <p style={{ color: '#666', fontSize: '13px', marginTop: '-10px' }}>Adding as: <strong>{user.username}</strong></p>
            <form onSubmit={handleAddStock}>
              <label style={labelStyle}>Drug Name:</label>
              <input type="text" required style={inputStyle} value={formData.name} onChange={(e) => setFormData({ ...formData, name: e.target.value })} />
              <label style={labelStyle}>Stock Quantity:</label>
              <input type="number" required style={inputStyle} value={formData.stock_quantity} onChange={(e) => setFormData({ ...formData, stock_quantity: e.target.value })} />
              <label style={labelStyle}>Unit Price (UGX):</label>
              <input type="number" required style={inputStyle} value={formData.price} onChange={(e) => setFormData({ ...formData, price: e.target.value })} />
              <label style={labelStyle}>Expiry Date:</label>
              <input type="date" required style={inputStyle} value={formData.expiry_date} onChange={(e) => setFormData({ ...formData, expiry_date: e.target.value })} />
              <div style={{ display: 'flex', gap: '10px' }}>
                <button type="submit" style={{ flex: 1, backgroundColor: '#28a745', color: 'white', border: 'none', padding: '10px', borderRadius: '5px' }}>Save</button>
                <button type="button" onClick={() => setShowModal(false)} style={{ flex: 1, backgroundColor: '#6c757d', color: 'white', border: 'none', padding: '10px', borderRadius: '5px' }}>Cancel</button>
              </div>
            </form>
          </div>
        </div>
      )}

      <div style={{ backgroundColor: 'white', borderRadius: '12px', boxShadow: '0 4px 6px rgba(0,0,0,0.1)', overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ backgroundColor: '#007bff', color: 'white', textAlign: 'left' }}>
              <th style={{ padding: '15px' }}>Priority</th>
              <th style={{ padding: '15px' }}>Drug Name</th>
              <th style={{ padding: '15px' }}>Stock</th>
              <th style={{ padding: '15px' }}>Price</th>
              <th style={{ padding: '15px' }}>Expiry Date</th>
              <th style={{ padding: '15px' }}>Status</th>
              <th style={{ padding: '15px' }}>Added By</th>
              {user.role === 'manager' && <th style={{ padding: '15px', textAlign: 'center' }}>Manage</th>}
            </tr>
          </thead>
          <tbody>
            {filteredMedicines.map((med, index) => (
              <tr key={med.id} style={{ borderBottom: '1px solid #eee' }}>
                <td style={{ padding: '15px' }}>#{index + 1}</td>
                <td style={{ padding: '15px' }}><strong>{med.name}</strong></td>
                <td style={{ padding: '15px' }}>
                  {med.stock_quantity} {Number(med.stock_quantity) < Number(med.reorder_level) && <span style={{ color: 'red', fontWeight: 'bold' }}>⚠️ Low</span>}
                </td>
                <td style={{ padding: '15px' }}>{Number(med.price).toLocaleString()} UGX</td>
                <td style={{ padding: '15px' }}>{med.expiry_date}</td>
                <td style={{ padding: '15px' }}>
                  <span style={{ padding: '5px 10px', borderRadius: '15px', fontSize: '11px', fontWeight: 'bold', backgroundColor: med.status === 'EXPIRED' ? '#ffdce0' : '#d4edda', color: med.status === 'EXPIRED' ? '#af1e2c' : '#155724' }}>
                    {med.status}
                  </span>
                </td>
                <td style={{ padding: '15px', color: '#555', fontSize: '13px' }}>👤 {med.added_by_username}</td>
                {user.role === 'manager' && (
                  <td style={{ padding: '15px', textAlign: 'center' }}>
                    <button onClick={() => handleDelete(med.id)} style={{ backgroundColor: 'transparent', border: 'none', color: '#dc3545', cursor: 'pointer', fontSize: '18px' }} title="Delete Drug">🗑️</button>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

const inputStyle = { width: '100%', padding: '10px', marginBottom: '10px', borderRadius: '5px', border: '1px solid #ddd', boxSizing: 'border-box' };
const labelStyle = { display: 'block', marginBottom: '4px', fontWeight: '600', fontSize: '13px', color: '#444' };

export default App;