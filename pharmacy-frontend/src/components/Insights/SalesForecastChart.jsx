import React, { useMemo, useState } from 'react';
import './Insights.css';

// Chart geometry (everything is drawn in this coordinate space and scaled to fit).
const W = 820;
const H = 280;
const M = { top: 20, right: 12, bottom: 30, left: 40 };

// Picks a clean top value and step for the y axis (0, 5, 10, 15 ...).
function niceScale(max) {
  if (!max || max <= 0) return { max: 4, step: 1 };
  const rough = max / 4;
  const mag = Math.pow(10, Math.floor(Math.log10(rough)));
  const norm = rough / mag;
  const nice = norm <= 1 ? 1 : norm <= 2 ? 2 : norm <= 5 ? 5 : 10;
  const step = nice * mag;
  return { max: Math.ceil(max / step) * step, step };
}

// A column with a rounded top and a square bottom (it sits on the baseline).
function columnPath(x, y, w, h, r) {
  if (h <= 0) return '';
  const rr = Math.min(r, w / 2, h);
  return (
    `M${x},${y + h} V${y + rr} Q${x},${y} ${x + rr},${y} ` +
    `H${x + w - rr} Q${x + w},${y} ${x + w},${y + rr} V${y + h} Z`
  );
}

const shortDate = (iso) =>
  new Date(`${iso}T00:00:00`).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' });
const longDate = (iso) =>
  new Date(`${iso}T00:00:00`).toLocaleDateString('en-GB', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
  });
const fmtUnits = (n) => String(Math.round(n * 10) / 10);
const fmtTick = (v) => (v >= 1000 ? `${v / 1000}K` : String(v));

export default function SalesForecastChart({ name, history, forecast }) {
  const [hover, setHover] = useState(null);
  const [showTable, setShowTable] = useState(false);

  const points = useMemo(
    () => [
      ...history.map((p) => ({ ...p, kind: 'actual' })),
      ...forecast.map((p) => ({ ...p, kind: 'forecast' })),
    ],
    [history, forecast]
  );

  const n = points.length;
  if (n === 0) return null;

  const maxVal = Math.max(0, ...points.map((p) => p.units));
  const { max: yMax, step } = niceScale(maxVal);
  const innerW = W - M.left - M.right;
  const innerH = H - M.top - M.bottom;
  const slot = innerW / n;
  const barW = Math.min(24, Math.max(2, slot - 2)); // at least a 2px gap between columns
  const yOf = (v) => M.top + innerH - (v / yMax) * innerH;

  const ticks = [];
  for (let v = 0; v <= yMax + 1e-9; v += step) ticks.push(Math.round(v * 100) / 100);

  const dividerX = M.left + history.length * slot;
  const hovered = hover !== null ? points[hover] : null;
  const tipLeft =
    hover !== null
      ? Math.min(88, Math.max(12, ((M.left + (hover + 0.5) * slot) / W) * 100))
      : 0;

  const totalSold = history.reduce((s, p) => s + p.units, 0);
  const label =
    `Daily units sold of ${name} over the last ${history.length} days, ` +
    `with the forecast for the next ${forecast.length} days. ` +
    `${totalSold} units were sold in the period shown.`;

  return (
    <div className="ins-chart">
      <h3 className="ins-title">Daily sales of {name}</h3>
      <p className="ins-sub">
        Units sold per day over the last {history.length} days, and what we expect over the next{' '}
        {forecast.length}. The forecast is the average of the same weekday over the last 4 weeks.
      </p>

      <div className="ins-legend">
        <span className="ins-key">
          <i className="ins-swatch ins-swatch-actual" />
          Actual sales
        </span>
        <span className="ins-key">
          <i className="ins-swatch ins-swatch-forecast" />
          Forecast
        </span>
        <button className="ins-link" onClick={() => setShowTable((s) => !s)}>
          {showTable ? 'Show chart' : 'View as table'}
        </button>
      </div>

      {showTable ? (
        <div className="pn-scroll-y">
          <table className="pn-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Type</th>
                <th>Units</th>
              </tr>
            </thead>
            <tbody>
              {points.map((p) => (
                <tr key={`${p.kind}-${p.date}`}>
                  <td>{longDate(p.date)}</td>
                  <td>{p.kind === 'actual' ? 'Actual' : 'Forecast'}</td>
                  <td>{fmtUnits(p.units)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="ins-scroll">
          <div className="ins-plot" onMouseLeave={() => setHover(null)}>
            <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={label}>
              {/* unit label */}
              <text x="0" y="11" className="ins-axis-text">
                units/day
              </text>

              {/* gridlines and y labels */}
              {ticks.map((t) => (
                <g key={t}>
                  <line
                    x1={M.left}
                    x2={W - M.right}
                    y1={yOf(t)}
                    y2={yOf(t)}
                    stroke={t === 0 ? 'var(--ins-base)' : 'var(--ins-grid)'}
                    strokeWidth="1"
                  />
                  <text
                    x={M.left - 8}
                    y={yOf(t) + 4}
                    textAnchor="end"
                    className="ins-axis-text"
                  >
                    {fmtTick(t)}
                  </text>
                </g>
              ))}

              {/* hover wash behind the columns */}
              {hover !== null && (
                <rect
                  x={M.left + hover * slot}
                  y={M.top}
                  width={slot}
                  height={innerH}
                  fill="var(--ins-hover)"
                />
              )}

              {/* columns */}
              {points.map((p, i) => {
                const h = (p.units / yMax) * innerH;
                if (h <= 0) return null;
                const x = M.left + i * slot + (slot - barW) / 2;
                return (
                  <path
                    key={`${p.kind}-${p.date}`}
                    d={columnPath(x, yOf(p.units), barW, h, 4)}
                    fill={p.kind === 'actual' ? 'var(--ins-actual)' : 'var(--ins-forecast)'}
                  />
                );
              })}

              {/* where the past ends and the forecast begins */}
              <line
                x1={dividerX}
                x2={dividerX}
                y1={M.top - 4}
                y2={M.top + innerH}
                stroke="var(--ins-base)"
                strokeWidth="1"
              />
              <text x={dividerX + 6} y={M.top + 6} className="ins-divider-text">
                Today
              </text>

              {/* x labels, one a week */}
              {points.map((p, i) =>
                i % 7 === 0 ? (
                  <text
                    key={`x-${p.date}`}
                    x={M.left + (i + 0.5) * slot}
                    y={H - 10}
                    textAnchor="middle"
                    className="ins-axis-text"
                  >
                    {shortDate(p.date)}
                  </text>
                ) : null
              )}

              {/* hit targets: one full-height strip per day */}
              {points.map((p, i) => (
                <rect
                  key={`hit-${p.kind}-${p.date}`}
                  x={M.left + i * slot}
                  y={M.top}
                  width={slot}
                  height={innerH}
                  fill="transparent"
                  onMouseEnter={() => setHover(i)}
                />
              ))}
            </svg>

            {hovered && (
              <div className="ins-tooltip" style={{ left: `${tipLeft}%` }}>
                <strong>{longDate(hovered.date)}</strong>
                <span className="ins-tt-row">
                  <i
                    className={`ins-swatch ${
                      hovered.kind === 'actual' ? 'ins-swatch-actual' : 'ins-swatch-forecast'
                    }`}
                  />
                  {hovered.kind === 'actual' ? 'Sold' : 'Forecast'}: {fmtUnits(hovered.units)} units
                </span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
