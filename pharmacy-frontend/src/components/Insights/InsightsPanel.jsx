import React, { useEffect, useState } from 'react';
import SalesForecastChart from './SalesForecastChart';
import { getForecastChart, getHistory } from '../../services/sales.service';
import { formatApiError } from '../../utils/apiError';
import '../Common/Panels.css';
import '../Common/PanelsExtra.css';
import './Insights.css';

export default function InsightsPanel({ names, refreshKey }) {
  const [selected, setSelected] = useState('');
  const [chart, setChart] = useState(null);
  const [logs, setLogs] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  // Start with the first medicine once the list is known.
  useEffect(() => {
    if (!selected && names.length > 0) setSelected(names[0]);
  }, [names, selected]);

  useEffect(() => {
    if (!selected) return undefined;
    let cancelled = false;
    setIsLoading(true);
    setError('');
    Promise.all([getForecastChart(selected), getHistory(selected)])
      .then(([chartRes, historyRes]) => {
        if (cancelled) return;
        setChart(chartRes.data);
        setLogs(Array.isArray(historyRes.data) ? historyRes.data : []);
      })
      .catch((err) => {
        if (!cancelled) setError(formatApiError(err, 'Could not load this medicine.'));
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [selected, refreshKey]);

  const hasSales = chart && chart.history.some((p) => p.units > 0);

  return (
    <section className="pn-card">
      <div className="pn-head">
        <div>
          <h2 className="pn-title">Sales, forecast and history</h2>
          <p className="pn-sub">Pick a medicine to see how it sells and everything that happened to its stock.</p>
        </div>
        <select
          className="pn-select"
          aria-label="Medicine"
          value={selected}
          onChange={(e) => setSelected(e.target.value)}
        >
          {names.map((n) => (
            <option key={n} value={n}>
              {n}
            </option>
          ))}
        </select>
      </div>

      {error && (
        <div className="pn-alert" role="alert">
          {error}
        </div>
      )}
      {isLoading && !chart && <p className="pn-empty">Loading...</p>}

      {chart && hasSales && (
        <SalesForecastChart
          name={chart.medicine_name}
          history={chart.history}
          forecast={chart.forecast}
        />
      )}
      {chart && !hasSales && !isLoading && (
        <p className="ins-empty">
          No sales were recorded for {chart.medicine_name} in the last 28 days, so there is
          nothing to forecast from yet.
        </p>
      )}

      {chart && (
        <div className="ins-history">
          <h3>History of {chart.medicine_name}</h3>
          {logs.length === 0 ? (
            <p className="pn-empty">No changes recorded yet.</p>
          ) : (
            <div className="pn-scroll pn-scroll-y">
              <table className="pn-table">
                <thead>
                  <tr>
                    <th>When</th>
                    <th>Batch</th>
                    <th>Action</th>
                    <th>Stock</th>
                    <th>Reason</th>
                    <th>By</th>
                  </tr>
                </thead>
                <tbody>
                  {logs.map((l) => (
                    <tr key={l.id}>
                      <td>{new Date(l.timestamp).toLocaleString()}</td>
                      <td>{l.batch_number || '-'}</td>
                      <td>
                        <span className={`pn-badge pn-badge-${l.action}`}>{l.action}</span>
                      </td>
                      <td>
                        {l.stock_before} to {l.stock_after}
                      </td>
                      <td>{l.reason || '-'}</td>
                      <td>{l.performed_by || '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
