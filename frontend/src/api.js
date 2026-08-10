const TOKEN_KEY = "pwa_analytics_dashboard_token";


export const getToken = () => sessionStorage.getItem(TOKEN_KEY) || "";

export const setToken = (token) => {
  if (token) sessionStorage.setItem(TOKEN_KEY, token);
  else sessionStorage.removeItem(TOKEN_KEY);
};

const queryString = (filters = {}) => {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== "" && value !== null && value !== undefined) params.set(key, value);
  });
  const query = params.toString();
  return query ? `?${query}` : "";
};

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

export const apiGet = async (path, filters = {}) => {
  const response = await fetch(`${path}${queryString(filters)}`, {
    headers: getToken() ? { "X-Analytics-Token": getToken() } : {},
  });
  if (!response.ok) {
    let message = `HTTP ${response.status}`;
    try {
      message = (await response.json()).message || message;
    } catch (_) {}
    throw new ApiError(message, response.status);
  }
  return response.json();
};

export const exportEventsCsv = async (filters = {}) => {
  const response = await fetch(`/api/dashboard/events.csv${queryString(filters)}`, {
    headers: getToken() ? { "X-Analytics-Token": getToken() } : {},
  });
  if (!response.ok) throw new ApiError(`HTTP ${response.status}`, response.status);
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `pwa-analytics-${new Date().toISOString().slice(0, 10)}.csv`;
  anchor.click();
  URL.revokeObjectURL(url);
};

