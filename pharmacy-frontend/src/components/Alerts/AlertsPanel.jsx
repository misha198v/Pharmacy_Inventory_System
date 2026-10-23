import React, { useState } from 'react';
import { writeOffBatch } from '../../services/sales.service';
import { formatApiError } from '../../utils/apiError';
import '../Common/Panels.css';
import '../Common/PanelsExtra.css';

export default function AlertsPanel({ medicines, isManager, onChanged }) {
  const [error, setError] = useState('');
  const [busyId, setBusyId] = useState(null);

  // Everything that is not OK, except expired batches with nothing left to deal with.
  const flagged = medicines
    .filter((m) => m.status !== 'OK' && !(m.status === 'EXPIRED' && m.stock_quantity === 0))
    .sort((a, b) => {
      const rank = (m) => (m.status === 'EXPIRED' ? 0 : 1);
      if (rank(a) !== rank(b)) return rank(a) - rank(b);
      return String(a.expiry_date || '9999').localeCompare(String(b.expiry_date || '9999'));
    });

  const handleWriteOff = async (med) => {
    const ok = window.confirm(
      `Write off ${med.stock_quantity} expired units of ${med.name} (batch ${
        med.batch_number || '-'
      })? This is recorded in the history.`
    );
    if (!ok) return;

    setBusyId(med.id);
    setError('');
    try {
      await writeOffBatch(med.id, { reason: 'Expired stock written off' });
      if (onChanged) onChanged();
    } catch (err) {
      setError(formatApiError(err, 'Could not write off this batch.'));
    } finally {
      setBusyId(null);
    }
  };

  return (
    <section className="pn-card">
      <h2 className="pn-title">Needs attention</h2>
      <p className="pn-sub">Batches that are expired, close to expiry, or at their reorder level.</p>

      {error && (
        <div className="pn-alert" role="alert">
          {error}
        </div>
      )}

      {flagged.length === 0 ? (
        <p className="pn-empty">Nothing needs attention right now.</p>
      ) : (
        <div className="pn-scroll">
          <table className="pn-table">
            <thead>
              <tr>
                <th>Medicine</th>
                <th>Batch</th>
                <th>In stock</th>
                <th>Expires</th>
                <th>Status</th>
                {isManager && <th>Action</th>}
              </tr>
            </thead>
            <tbody>
              {flagged.map((m) => (
                <tr key={m.id}>
                  <td>{m.name}</td>
                  <td>{m.batch_number || '-'}</td>
                  <td>{m.stock_quantity}</td>
                  <td>{m.expiry_date || '-'}</td>
                  <td>
                    <span className={`status-badge status-${m.status.toLowerCase()}`}>
                      {m.status}
                    </span>
                  </td>
                  {isManager && (
                    <td>
                      {m.status === 'EXPIRED' && m.stock_quantity > 0 && (
                        <button
                          className="pn-btn pn-btn-small pn-btn-danger"
                          onClick={() => handleWriteOff(m)}
                          disabled={busyId === m.id}
                        >
                          {busyId === m.id ? 'Writing off...' : 'Write off'}
                        </button>
                      )}
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
