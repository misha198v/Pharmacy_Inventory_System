import React, { useState, useEffect, useCallback } from 'react';
import AppLayout from '../Layout/AppLayout';
import AlertsPanel from '../Alerts/AlertsPanel';
import SalesPanel from '../Sales/SalesPanel';
import InsightsPanel from '../Insights/InsightsPanel';
import ReorderPanel from '../Reorder/ReorderPanel';
import OrdersPanel from '../Orders/OrdersPanel';
import AddMedicinePanel from '../Inventory/AddMedicinePanel';
import UsersPanel from '../Users/UsersPanel';
import { useAuth } from '../../context/AuthContext';
import { inventoryService } from '../../services/inventory.service';
import './Dashboard.css';

export default function Dashboard() {
  const { user } = useAuth();
  const isManager = user?.role === 'manager';

  const [summary, setSummary] = useState(null);
  const [medicines, setMedicines] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [refreshKey, setRefreshKey] = useState(0);

  const loadData = useCallback(async () => {
    try {
      const [summaryRes, medicinesRes] = await Promise.all([
        inventoryService.getDashboardSummary(),
        inventoryService.getMedicines(),
      ]);
      setSummary(summaryRes.data);

      const list = medicinesRes.data.results || medicinesRes.data;
      setMedicines(Array.isArray(list) ? list : []);
      setError('');
    } catch {
      setError('Failed to load dashboard data.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Anything that changes stock (a sale, an order received, a write-off, new stock)
  // reloads the cards and table, and refreshes every panel.
  const refreshAll = () => {
    loadData();
    setRefreshKey((k) => k + 1);
  };

  if (loading) return <AppLayout><p>Loading dashboard...</p></AppLayout>;
  if (error) return <AppLayout><p className="error-text">{error}</p></AppLayout>;

  const names = [...new Set(medicines.map((m) => m.name))];

  return (
    <AppLayout>
      <h1>Dashboard</h1>

      <div className="summary-cards">
        <div className="summary-card">
          <h3>Total Medicines</h3>
          <p>{summary.total_medicines}</p>
        </div>
        <div className="summary-card">
          <h3>Total Stock Value</h3>
          <p>${summary.total_stock_value}</p>
        </div>
        <div className="summary-card low-stock">
          <h3>Low Stock</h3>
          <p>{summary.low_stock_count}</p>
        </div>
        <div className="summary-card expiring">
          <h3>Expiring Soon</h3>
          <p>{summary.expiring_soon_count}</p>
        </div>
      </div>

      <AlertsPanel medicines={medicines} isManager={isManager} onChanged={refreshAll} />

      <h2>Inventory</h2>
      <table className="medicine-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Stock</th>
            <th>Price</th>
            <th>Expiry Date</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {medicines.map((med) => (
            <tr key={med.id}>
              <td>{med.name}</td>
              <td>{med.stock_quantity}</td>
              <td>${med.price}</td>
              <td>{med.expiry_date}</td>
              <td>
                <span className={`status-badge status-${med.status.toLowerCase()}`}>
                  {med.status}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <SalesPanel onSaleRecorded={refreshAll} />
      <InsightsPanel names={names} refreshKey={refreshKey} />
      <ReorderPanel refreshKey={refreshKey} isManager={isManager} onOrdered={refreshAll} />
      <OrdersPanel refreshKey={refreshKey} onChanged={refreshAll} />
      <AddMedicinePanel medicines={medicines} onAdded={refreshAll} />
      {isManager && <UsersPanel currentUsername={user?.username} />}
    </AppLayout>
  );
}
