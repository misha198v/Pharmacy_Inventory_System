import React, { useState } from 'react';
import { addMedicineBatch } from '../../services/sales.service';
import { formatApiError } from '../../utils/apiError';
import '../Common/Panels.css';
import '../Common/PanelsExtra.css';

const EMPTY = {
  name: '',
  batch_number: '',
  stock_quantity: '',
  price: '',
  expiry_date: '',
  reorder_level: '10',
};

// Details a new batch inherits from an existing batch of the same medicine.
const INHERITED = ['generic_name', 'category', 'unit', 'supplier'];

export default function AddMedicinePanel({ medicines, onAdded }) {
  const [form, setForm] = useState(EMPTY);
  const [confirming, setConfirming] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState('');
  const [done, setDone] = useState('');

  const names = [...new Set(medicines.map((m) => m.name))];
  const findKnown = (name) =>
    medicines.find((m) => m.name.toLowerCase() === name.trim().toLowerCase());

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm((prev) => {
      const next = { ...prev, [name]: value };
      // Typing a known medicine pre-fills its usual price and reorder level.
      if (name === 'name') {
        const known = findKnown(value);
        if (known) {
          if (!prev.price) next.price = String(known.price);
          next.reorder_level = String(known.reorder_level ?? prev.reorder_level);
        }
      }
      return next;
    });
  };

  const handleReview = (e) => {
    e.preventDefault();
    setError('');
    setDone('');
    setConfirming(true);
  };

  const handleConfirm = async () => {
    setIsSaving(true);
    const known = findKnown(form.name);
    const inherited = {};
    if (known) {
      INHERITED.forEach((key) => {
        if (known[key] !== undefined && known[key] !== null && known[key] !== '') {
          inherited[key] = known[key];
        }
      });
    }
    try {
      await addMedicineBatch({
        ...inherited,
        name: form.name.trim(),
        batch_number: form.batch_number.trim(),
        stock_quantity: Number(form.stock_quantity),
        price: form.price,
        expiry_date: form.expiry_date,
        reorder_level: Number(form.reorder_level),
      });
      setDone(
        `Added ${form.stock_quantity} x ${form.name.trim()} (batch ${form.batch_number.trim()}).`
      );
      setForm(EMPTY);
      if (onAdded) onAdded();
    } catch (err) {
      setError(formatApiError(err, 'Could not add the medicine. Is Django running?'));
    } finally {
      setIsSaving(false);
      setConfirming(false);
    }
  };

  const locked = confirming || isSaving;

  return (
    <section className="pn-card">
      <h2 className="pn-title">Add stock</h2>
      <p className="pn-sub">
        Record a batch you have received by hand. Use a new batch number for every delivery.
      </p>

      <form onSubmit={handleReview}>
        <div className="pn-form-grid">
          <div className="pn-field">
            <label htmlFor="add-name">Medicine</label>
            <input
              id="add-name"
              name="name"
              list="add-medicine-names"
              value={form.name}
              onChange={handleChange}
              disabled={locked}
              required
            />
            <datalist id="add-medicine-names">
              {names.map((n) => (
                <option key={n} value={n} />
              ))}
            </datalist>
          </div>
          <div className="pn-field">
            <label htmlFor="add-batch">Batch number</label>
            <input
              id="add-batch"
              name="batch_number"
              value={form.batch_number}
              onChange={handleChange}
              disabled={locked}
              required
            />
          </div>
          <div className="pn-field">
            <label htmlFor="add-qty">Quantity</label>
            <input
              id="add-qty"
              name="stock_quantity"
              type="number"
              min="1"
              value={form.stock_quantity}
              onChange={handleChange}
              disabled={locked}
              required
            />
          </div>
          <div className="pn-field">
            <label htmlFor="add-price">Price</label>
            <input
              id="add-price"
              name="price"
              type="number"
              min="0.01"
              step="0.01"
              value={form.price}
              onChange={handleChange}
              disabled={locked}
              required
            />
          </div>
          <div className="pn-field">
            <label htmlFor="add-expiry">Expiry date</label>
            <input
              id="add-expiry"
              name="expiry_date"
              type="date"
              value={form.expiry_date}
              onChange={handleChange}
              disabled={locked}
              required
            />
          </div>
          <div className="pn-field">
            <label htmlFor="add-reorder">Reorder level</label>
            <input
              id="add-reorder"
              name="reorder_level"
              type="number"
              min="0"
              value={form.reorder_level}
              onChange={handleChange}
              disabled={locked}
              required
            />
          </div>
        </div>

        {!confirming && (
          <div className="pn-form-actions">
            <button type="submit" className="pn-btn">
              Review entry
            </button>
          </div>
        )}
      </form>

      {confirming && (
        <div className="pn-confirm" role="alertdialog" aria-live="polite">
          <p>
            Add <strong>{form.stock_quantity}</strong> x <strong>{form.name}</strong> (batch{' '}
            {form.batch_number}, expires {form.expiry_date})? Once saved, only a manager can
            correct this entry.
          </p>
          <button className="pn-btn" onClick={handleConfirm} disabled={isSaving}>
            {isSaving ? 'Saving...' : 'Yes, add it'}
          </button>
          <button
            className="pn-btn pn-btn-ghost"
            onClick={() => setConfirming(false)}
            disabled={isSaving}
          >
            Go back and edit
          </button>
        </div>
      )}

      {error && (
        <div className="pn-alert" role="alert">
          {error}
        </div>
      )}
      {done && <div className="pn-success">{done}</div>}
    </section>
  );
}
