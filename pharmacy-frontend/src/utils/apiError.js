// Turns an API error into one readable sentence.
// Handles both error shapes our backend sends:
//   { detail: "..." }
//   { detail: "Validation failed.", errors: { field: ["message"] } }
export function formatApiError(err, fallback) {
  const data = err && err.response && err.response.data;
  if (!data) return fallback;

  if (data.errors && typeof data.errors === 'object') {
    return Object.entries(data.errors)
      .map(([field, messages]) => `${field}: ${[].concat(messages).join(' ')}`)
      .join(' | ');
  }
  return data.detail || fallback;
}
