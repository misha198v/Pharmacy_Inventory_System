import React, { useEffect, useState } from 'react';
import { inventoryService } from '../../services/inventory.service'; 
import { recordSale } from '../../services/sales.service';
import '../Common/Panels.css';

export default function SalesPanel({ onSaleRecorded }) {
  const [names, setNames] = useState([]);
  const [medicineName, setMedicineName] = useState('');
  const [quantity, setQuantity] = useState('');
  const [confirming, setConfirming] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);

  // medicine names for the suggestion list
  useEffect(() => {
    inventoryService.getMedicines()
      .then((res) => {
        const list = res.data.results || res.data;
        const rows = Array.isArray(list) ? list : [];
        setNames([...new Set(rows.map((m) => m.name))]);
      })
      .catch(() => {});
  }, []);

  const handleReview = (e) => {
    e.preventDefault();
    setError('');
    setResult(null);
    setConfirming(true);
  };

  const handleConfirm = async () => {
    setIsSaving(true);
    try {
      const res = await recordSale({
        medicine_name: medicineName.trim(),
        quantity: Number(quantity),
      });
      setResult(res.data);
      setMedicineName('');
      setQuantity('');
      if (onSaleRecorded) onSaleRecorded();
    } catch (err) {
      setError(
        err.response?.data?.detail || 'Could not record the sale. Is Django running?'
      );
    } finally {
      setIsSaving(false);
      setConfirming(false);
    }
  };

  return (
    <section className="pn-card">
      <h2 className="pn-title">Record a sale</h2>
      <p className="pn-sub">
        The system picks the batch that expires first. You only enter what was sold.
      </p>

      <form onSubmit={handleReview} className="pn-form">
        <div className="pn-field">
          <label htmlFor="sale-name">Medicine</label>
          <input
            id="sale-name"
            list="sale-medicine-names"
            value={medicineName}
            onChange={(e) => setMedicineName(e.target.value)}
            disabled={confirming || isSaving}
            required
          />
          <datalist id="sale-medicine-names">
            {names.map((n) => (
              <option key={n} value={n} />
            ))}
          </datalist>
        </div>

        <div className="pn-field pn-field-small">
          <label htmlFor="sale-qty">Quantity</label>
          <input
            id="sale-qty"
            type="number"
            min="1"
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
            disabled={confirming || isSaving}
            required
          />
        </div>

        {!confirming && (
          <button type="submit" className="pn-btn">
            Review sale
          </button>
        )}
      </form>

      {confirming && (
        <div className="pn-confirm" role="alertdialog" aria-live="polite">
          <p>
            Sell <strong>{quantity}</strong> x <strong>{medicineName}</strong>? A sale
            cannot be edited after it is saved.
          </p>
          <button className="pn-btn" onClick={handleConfirm} disabled={isSaving}>
            {isSaving ? 'Saving...' : 'Yes, record it'}
          </button>
          <button
            className="pn-btn pn-btn-ghost"
            onClick={() => setConfirming(false)}
            disabled={isSaving}
          >
            Cancel
          </button>
        </div>
      )}

      {error && (
        <div className="pn-alert" role="alert">
          {error}
        </div>
      )}

      {result && (
        <div className="pn-result">
          <p>
            Sold <strong>{result.sold}</strong> x {result.medicine}. Batches used, soonest
            expiry first:
          </p>
          <table className="pn-table">
            <thead>
              <tr>
                <th>Batch</th>
                <th>Expires</th>
                <th>Units taken</th>
                <th>Left in batch</th>
              </tr>
            </thead>
            <tbody>
              {result.allocations.map((a, i) => (
                <tr key={i}>
                  <td>{a.batch_number || '-'}</td>
                  <td>{a.expiry_date || '-'}</td>
                  <td>{a.quantity}</td>
                  <td>{a.stock_after}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}