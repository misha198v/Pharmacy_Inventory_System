import React, { useCallback, useEffect, useState } from 'react';
import { createOrder, getReorderSuggestions } from '../../services/sales.service';
import { formatApiError } from '../../utils/apiError';
import '../Common/Panels.css';
import '../Common/PanelsExtra.css';

const STATUS_LABEL = {
  ORDER_NOW: 'Order now',
  EXPIRY_RISK: 'Expiry risk',
  ORDER_SOON: 'Order soon',
  OK: 'OK',
  OVERSTOCKED: 'Overstocked',
  NO_SALES_DATA: 'No sales data',
};

export default function ReorderPanel({ refreshKey, isManager, onOrdered }) {
  const [items, setItems] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [busyName, setBusyName] = useState(null);

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

  const handleOrder = async (item) => {
    const ok = window.confirm(
      `Create a purchase order for ${item.suggested_order} x ${item.medicine_name}?`
    );
    if (!ok) return;

    setBusyName(item.medicine_name);
    setError('');
    setNotice('');
    try {
      await createOrder({
        medicine_name: item.medicine_name,
        quantity: item.suggested_order,
      });
      setNotice(
        `Order created for ${item.suggested_order} x ${item.medicine_name}. You can follow it under Purchase orders.`
      );
      if (onOrdered) onOrdered();
    } catch (err) {
      setError(formatApiError(err, 'Could not create the order.'));
    } finally {
      setBusyName(null);
    }
  };

  const columns = isManager ? 8 : 7;

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
      {notice && <div className="pn-success">{notice}</div>}

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
              {isManager && <th>Action</th>}
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
                {isManager && (
                  <td>
                    {it.suggested_order > 0 && (
                      <button
                        className="pn-btn pn-btn-small"
                        onClick={() => handleOrder(it)}
                        disabled={busyName === it.medicine_name}
                      >
                        {busyName === it.medicine_name
                          ? 'Ordering...'
                          : `Order ${it.suggested_order}`}
                      </button>
                    )}
                  </td>
                )}
              </tr>
            ))}
            {!isLoading && items.length === 0 && (
              <tr>
                <td colSpan={columns}>No medicines yet.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
