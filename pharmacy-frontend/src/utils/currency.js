// One place that decides how money looks across Pharmio.
export const CURRENCY_CODE = 'UGX';

export function formatMoney(value) {
  const amount = Number(value);
  if (!Number.isFinite(amount)) return '-';
  return `${CURRENCY_CODE} ${amount.toLocaleString('en-US', { maximumFractionDigits: 0 })}`;
}