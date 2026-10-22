import React, { useCallback, useEffect, useState } from 'react';
import { getReorderSuggestions } from '../../services/sales.service';
import '../Common/Panels.css';

const STATUS_LABEL = {
  ORDER_NOW: 'Order now',
  EXPIRY_RISK: 'Expiry risk',
  ORDER_SOON: 'Order soon',
  OK: 'OK',
  OVERSTOCKED: 'Overstocked',
  NO_SALES_DATA: 'No sales data',
};

export default function ReorderPanel({ refreshKey }) {
  const [items, setItems] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setIsLoading(true);
    setError('');
    try {
      const res = await getReorderSuggestions();
      setItems(Array.isArray(res.data) ? res.data : []);
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not load suggestions.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load, refreshKey]);

  return (
    <section className="pn-card">
      <div className="pn-head">
        <div>
          <h2 className="pn-title">Reorder suggestions</h2>
          <p className="pn-sub">
            Based on the last 28 days of sales, delivery time and expiry dates.
          </p>
        </div>
        <button className="pn-btn pn-btn-ghost" onClick={load} disabled={isLoading}>
          {isLoading ? 'Loading...' : 'Refresh'}
        </button>
      </div>

      {error && (
        <div className="pn-alert" role="alert">
          {error}
        </div>
      )}

      <div className="pn-scroll">
        <table className="pn-table">
          <thead>
            <tr>
              <th>Medicine</th>
              <th>In stock</th>
              <th>Sold per day</th>
              <th>Days of cover</th>
              <th>Likely to expire unsold</th>
              <th>Suggested order</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {items.map((it) => (
              <tr key={it.medicine_name}>
                <td>{it.medicine_name}</td>
                <td>{it.on_hand}</td>
                <td>{it.avg_daily_demand}</td>
                <td>{it.days_of_cover ?? '-'}</td>
                <td>{it.at_risk_units}</td>
                <td>{it.suggested_order ?? '-'}</td>
                <td>
                  <span className={`pn-badge pn-badge-${it.status}`}>
                    {STATUS_LABEL[it.status] || it.status}
                  </span>
                </td>
              </tr>
            ))}
            {!isLoading && items.length === 0 && (
              <tr>
                <td colSpan="7">No medicines yet.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}