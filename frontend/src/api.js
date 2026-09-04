const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "http://localhost:8000").replace(/\/$/, "");

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, options);
  if (!response.ok) {
    let message = "The operations service is unavailable.";
    try {
      const body = await response.json();
      message = body.detail || message;
    } catch {
      // Keep API errors safe when the server returns non-JSON output.
    }
    throw new Error(message);
  }
  return response.json();
}

export const api = {
  health: () => request("/health"),
  summary: () => request("/summary"),
  transactions: (params = {}) => {
    const query = new URLSearchParams({ page: "1", page_size: "50", ...params });
    return request(`/transactions?${query}`);
  },
  transaction: (id) => request(`/transactions/${encodeURIComponent(id)}`),
  investigate: (id) => request(`/transactions/${encodeURIComponent(id)}/investigate`, { method: "POST" }),
  exceptions: (params = {}) => {
    const query = new URLSearchParams({ page: "1", page_size: "50", ...params });
    return request(`/exceptions?${query}`);
  },
};

export { API_BASE_URL };