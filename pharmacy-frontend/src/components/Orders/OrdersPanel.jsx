import React, { useCallback, useEffect, useState } from 'react';
import { getOrders, receiveOrder } from '../../services/sales.service';
import { formatApiError } from '../../utils/apiError';
import '../Common/Panels.css';
import '../Common/PanelsExtra.css';

export default function OrdersPanel({ refreshKey, onChanged }) {
  const [orders, setOrders] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [receivingId, setReceivingId] = useState(null);
  const [batchNumber, setBatchNumber] = useState('');
  const [expiry, setExpiry] = useState('');
  const [isSaving, setIsSaving] = useState(false);

  const load = useCallback(async () => {
    setIsLoading(true);
    try {
      const res = await getOrders();
      setOrders(Array.isArray(res.data) ? res.data : []);
    } catch (err) {
      setError(formatApiError(err, 'Could not load orders.'));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load, refreshKey]);

  const startReceive = (id) => {
    setReceivingId(id);
    setBatchNumber('');
    setExpiry('');
    setError('');
    setNotice('');
  };

  const confirmReceive = async (order) => {
    setIsSaving(true);
    setError('');
    try {
      await receiveOrder(order.id, {
        batch_number: batchNumber.trim(),
        expiry_date: expiry,
      });
      setNotice(`Received ${order.quantity} x ${order.medicine_name}. It is now in stock.`);
      setReceivingId(null);
      if (onChanged) onChanged();
    } catch (err) {
      setError(formatApiError(err, 'Could not receive this order.'));
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <section className="pn-card">
      <div className="pn-head">
        <div>
          <h2 className="pn-title">Purchase orders</h2>
          <p className="pn-sub">
            Orders placed from the suggestions. When a delivery arrives, record it here and it
            becomes a new batch in stock.
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

      {!isLoading && orders.length === 0 ? (
        <p className="pn-empty">
          No orders yet. A manager can create one from the Reorder suggestions above.
        </p>
      ) : (
        <div className="pn-scroll">
          <table className="pn-table">
            <thead>
              <tr>
                <th>Order</th>
                <th>Medicine</th>
                <th>Quantity</th>
                <th>Supplier</th>
                <th>Ordered</th>
                <th>Status</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {orders.map((o) => (
                <React.Fragment key={o.id}>
                  <tr>
                    <td>#{o.id}</td>
                    <td>{o.medicine_name}</td>
                    <td>{o.quantity}</td>
                    <td>{o.supplier || '-'}</td>
                    <td>
                      {new Date(o.ordered_at).toLocaleDateString()}
                      {o.ordered_by ? ` by ${o.ordered_by}` : ''}
                    </td>
                    <td>
                      <span className={`pn-badge pn-badge-${o.status}`}>
                        {o.status === 'ORDERED' ? 'Ordered' : 'Received'}
                      </span>
                    </td>
                    <td>
                      {o.status === 'ORDERED' && receivingId !== o.id && (
                        <button
                          className="pn-btn pn-btn-small"
                          onClick={() => startReceive(o.id)}
                        >
                          Receive delivery
                        </button>
                      )}
                    </td>
                  </tr>
                  {receivingId === o.id && (
                    <tr>
                      <td colSpan="7">
                        <div className="pn-inline">
                          <div className="pn-field">
                            <label htmlFor={`rcv-batch-${o.id}`}>Batch number</label>
                            <input
                              id={`rcv-batch-${o.id}`}
                              value={batchNumber}
                              onChange={(e) => setBatchNumber(e.target.value)}
                              disabled={isSaving}
                            />
                          </div>
                          <div className="pn-field">
                            <label htmlFor={`rcv-exp-${o.id}`}>Expiry date</label>
                            <input
                              id={`rcv-exp-${o.id}`}
                              type="date"
                              value={expiry}
                              onChange={(e) => setExpiry(e.target.value)}
                              disabled={isSaving}
                            />
                          </div>
                          <button
                            className="pn-btn pn-btn-small"
                            onClick={() => confirmReceive(o)}
                            disabled={isSaving || !batchNumber.trim() || !expiry}
                          >
                            {isSaving ? 'Saving...' : `Confirm: add ${o.quantity} to stock`}
                          </button>
                          <button
                            className="pn-btn pn-btn-small pn-btn-ghost"
                            onClick={() => setReceivingId(null)}
                            disabled={isSaving}
                          >
                            Cancel
                          </button>
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
