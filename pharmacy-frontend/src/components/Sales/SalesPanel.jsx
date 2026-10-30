import React, { useEffect, useRef, useState } from 'react';
import { inventoryService } from '../../services/inventory.service';
import { recordSale } from '../../services/sales.service';
import { scanPack, linkBarcode } from '../../services/scan.service';
import '../Common/Panels.css';
import './SalesPanel.css';

const TITLES = {
  OK: 'Correct pack',
  CONFIRM_BATCH: 'Check the batch on the pack',
  BLOCKED: 'Wrong batch: sell the older one first',
  BATCH_USED_UP: 'Use the next batch',
  EXPIRED: 'Expired: do not sell',
  OUT_OF_STOCK: 'No stock left',
  BATCH_EMPTY: 'No units recorded in this batch',
  UNKNOWN_CODE: 'New barcode',
  UNKNOWN_MEDICINE: 'Medicine not found',
  UNKNOWN_BATCH: 'Batch not recognised',
};

const TONE = {
  OK: 'good',
  CONFIRM_BATCH: 'warn',
  UNKNOWN_CODE: 'warn',
  UNKNOWN_MEDICINE: 'warn',
};

// After a wrong pack the worker puts it back and tries another one,
// so we keep waiting for the batch number instead of starting over.
const KEEP_WAITING = ['BLOCKED', 'BATCH_USED_UP', 'EXPIRED', 'UNKNOWN_BATCH', 'BATCH_EMPTY'];

const CHIP = {
  next: 'Sell first',
  locked: 'Locked until the older batch is finished',
  used: 'Already counted in this sale',
};

export default function SalesPanel({ onSaleRecorded }) {
  const [names, setNames] = useState([]);
  const [mode, setMode] = useState('scan'); // 'scan' or 'type'
  const [input, setInput] = useState('');
  const [pending, setPending] = useState(null); // waiting for the batch number on the pack
  const [verdict, setVerdict] = useState(null);
  const [basket, setBasket] = useState([]);
  const [unknownCode, setUnknownCode] = useState(null);
  const [linkName, setLinkName] = useState('');
  const [isBusy, setIsBusy] = useState(false);
  const [error, setError] = useState('');
  const [results, setResults] = useState([]);
  const inputRef = useRef(null);

  // medicine names, for typing a name and for linking a new barcode
  useEffect(() => {
    inventoryService.getMedicines()
      .then((res) => {
        const list = res.data.results || res.data;
        const rows = Array.isArray(list) ? list : [];
        setNames([...new Set(rows.map((m) => m.name))]);
      })
      .catch(() => {});
  }, []);

  // keep the cursor in the scan box so the next scan is always typed into it
  useEffect(() => {
    if (!unknownCode && inputRef.current) inputRef.current.focus();
  }, [verdict, pending, basket, mode, unknownCode, isBusy]);

  const basketMap = () =>
    Object.fromEntries(basket.map((l) => [l.name.toLowerCase(), l.quantity]));

  const addToBasket = (v) => {
    const batchKey = v.expected_batch?.batch_number || 'no batch number';
    setBasket((prev) => {
      const i = prev.findIndex((l) => l.name.toLowerCase() === v.medicine.toLowerCase());
      if (i === -1) {
        return [...prev, { name: v.medicine, quantity: 1, batches: { [batchKey]: 1 } }];
      }
      const next = [...prev];
      const line = next[i];
      next[i] = {
        ...line,
        quantity: line.quantity + 1,
        batches: { ...line.batches, [batchKey]: (line.batches[batchKey] || 0) + 1 },
      };
      return next;
    });
  };

  const runScan = async (request, batchNumber) => {
    setIsBusy(true);
    setError('');
    setResults([]);
    try {
      const res = await scanPack({
        ...request,
        batch_number: batchNumber || undefined,
        basket: basketMap(),
      });
      const v = res.data;
      setVerdict(v);
      setUnknownCode(v.status === 'UNKNOWN_CODE' ? request.code : null);
      if (v.status === 'OK') {
        addToBasket(v);
        setPending(null);
      } else if (v.status === 'CONFIRM_BATCH') {
        setPending({ request, medicine: v.medicine });
      } else if (!(batchNumber && KEEP_WAITING.includes(v.status))) {
        setPending(null);
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not check the pack. Is Django running?');
    } finally {
      setIsBusy(false);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    const value = input.trim();
    if (!value || isBusy) return;
    setInput('');
    if (pending) runScan(pending.request, value);
    else if (mode === 'type') runScan({ medicine_name: value });
    else runScan({ code: value });
  };

  const handleLink = async () => {
    setIsBusy(true);
    setError('');
    const code = unknownCode;
    try {
      await linkBarcode({ code, medicine_name: linkName });
      setUnknownCode(null);
      setLinkName('');
      setVerdict(null);
      setIsBusy(false);
      await runScan({ code });
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not link the barcode.');
      setIsBusy(false);
    }
  };

  const handleComplete = async () => {
    setIsBusy(true);
    setError('');
    const saved = [];
    let remaining = basket;
    for (const line of basket) {
      try {
        const res = await recordSale({ medicine_name: line.name, quantity: line.quantity });
        saved.push(res.data);
        remaining = remaining.filter((l) => l !== line);
      } catch (err) {
        const why = err.response?.data?.detail || 'could not be saved. Is Django running?';
        setError(
          `${line.name}: ${why}` +
            (saved.length ? ' The items before it were saved.' : '')
        );
        break;
      }
    }
    setBasket(remaining);
    setResults(saved);
    setVerdict(null);
    setPending(null);
    setIsBusy(false);
    if (saved.length && onSaleRecorded) onSaleRecorded();
  };

  const clearSale = () => {
    setBasket([]);
    setVerdict(null);
    setPending(null);
    setUnknownCode(null);
    setError('');
  };

  const removeLine = (name) => setBasket((prev) => prev.filter((l) => l.name !== name));

  const inputLabel = pending
    ? `Confirm the pack: type or scan the batch number printed on the ${pending.medicine} pack`
    : mode === 'scan'
    ? 'Scan the pack'
    : 'Type the medicine name';

  return (
    <section className="pn-card">
      <h2 className="pn-title">Record a sale</h2>
      <p className="pn-sub">
        Scan each pack. The system checks it is the batch that has to be sold first.
      </p>

      <form onSubmit={handleSubmit} className="sp-scan">
        <label htmlFor="sale-scan" className="sp-scan-label">{inputLabel}</label>
        <div className="sp-scan-row">
          <input
            id="sale-scan"
            ref={inputRef}
            className="sp-scan-input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            list={mode === 'type' && !pending ? 'sale-medicine-names' : undefined}
            placeholder={
              pending ? 'Batch number on the pack' : mode === 'scan' ? 'Scan a pack...' : 'Medicine name'
            }
            autoComplete="off"
            disabled={isBusy || !!unknownCode}
          />
          <button type="submit" className="pn-btn" disabled={isBusy || !input.trim() || !!unknownCode}>
            {pending ? 'Confirm' : mode === 'scan' ? 'Check' : 'Add'}
          </button>
          {pending && (
            <button
              type="button"
              className="pn-btn pn-btn-ghost"
              onClick={() => { setPending(null); setVerdict(null); }}
            >
              Cancel
            </button>
          )}
        </div>
        <datalist id="sale-medicine-names">
          {names.map((n) => (
            <option key={n} value={n} />
          ))}
        </datalist>
        {!pending && (
          <button
            type="button"
            className="sp-link"
            onClick={() => setMode(mode === 'scan' ? 'type' : 'scan')}
          >
            {mode === 'scan' ? "Can't scan? Type the medicine name instead" : 'Back to scanning'}
          </button>
        )}
      </form>

      {verdict && (
        <div className={`sp-verdict sp-${TONE[verdict.status] || 'bad'}`} role="status" aria-live="polite">
          <strong>{TITLES[verdict.status] || 'Check the pack'}</strong>
          <p>{verdict.message}</p>
        </div>
      )}

      {unknownCode && (
        <div className="sp-link-box">
          <p>
            Barcode <strong>{unknownCode}</strong> is not linked to a medicine yet. Choose which
            medicine it belongs to (a manager must do this once per product):
          </p>
          <div className="sp-scan-row">
            <select value={linkName} onChange={(e) => setLinkName(e.target.value)}>
              <option value="">Choose a medicine...</option>
              {names.map((n) => (
                <option key={n} value={n}>{n}</option>
              ))}
            </select>
            <button className="pn-btn" onClick={handleLink} disabled={!linkName || isBusy}>
              Link barcode
            </button>
            <button
              className="pn-btn pn-btn-ghost"
              onClick={() => { setUnknownCode(null); setVerdict(null); }}
              disabled={isBusy}
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {verdict?.queue?.length > 0 && (
        <div className="sp-queue">
          <h3 className="sp-queue-title">Shelf order for {verdict.medicine}</h3>
          <ol className="sp-queue-list">
            {verdict.queue.map((b) => (
              <li key={b.batch_id} className={`sp-batch sp-batch-${b.state}`}>
                <span className="sp-batch-no">Batch {b.batch_number || '-'}</span>
                <span>Expires {b.expiry_pretty || b.expiry_date}</span>
                <span>{b.units_left} left</span>
                <span className="sp-chip">{CHIP[b.state]}</span>
              </li>
            ))}
          </ol>
        </div>
      )}

      {error && (
        <div className="pn-alert" role="alert">
          {error}
        </div>
      )}

      {basket.length > 0 && (
        <div className="sp-basket">
          <h3 className="sp-queue-title">This sale</h3>
          <table className="pn-table">
            <thead>
              <tr>
                <th>Medicine</th>
                <th>Packs</th>
                <th>From batch</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {basket.map((l) => (
                <tr key={l.name}>
                  <td>{l.name}</td>
                  <td>{l.quantity}</td>
                  <td>
                    {Object.entries(l.batches)
                      .map(([b, n]) => `${b} × ${n}`)
                      .join(', ')}
                  </td>
                  <td>
                    <button type="button" className="sp-link" onClick={() => removeLine(l.name)} disabled={isBusy}>
                      Remove
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="sp-actions">
            <button className="pn-btn" onClick={handleComplete} disabled={isBusy || !!pending}>
              {isBusy ? 'Saving...' : 'Complete sale'}
            </button>
            <button className="pn-btn pn-btn-ghost" onClick={clearSale} disabled={isBusy}>
              Clear
            </button>
          </div>
        </div>
      )}

      {results.length > 0 && (
        <div className="pn-result">
          {results.map((r, n) => (
            <div key={n}>
              <p>
                Sold <strong>{r.sold}</strong> x {r.medicine}. Batches used, soonest expiry first:
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
                  {r.allocations.map((a, i) => (
                    <tr key={i}>
                      <td>{a.batch_number || '-'}</td>
                      <td>{a.expiry_date || '-'}</td>
                      <td>{a.quantity}</td>
                      <td>{a.stock_after}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p>
                <a
                  className="sp-link"
                  href={`/patient.html?name=${encodeURIComponent(r.medicine)}`}
                  target="_blank"
                  rel="noreferrer"
                >
                  Open the patient information page for {r.medicine}
                </a>
              </p>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}