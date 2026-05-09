const API_BASE = "http://localhost:8000/api";

function getHeaders(body) {
  const token = localStorage.getItem("flaw_token");
  const headers = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (!(body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }
  return headers;
}

async function request(url, options = {}) {
  const res = await fetch(`${API_BASE}${url}`, {
    ...options,
    headers: { ...getHeaders(options.body), ...options.headers },
  });
  if (res.status === 401) {
    localStorage.removeItem("flaw_token");
    localStorage.removeItem("flaw_user");
    window.location.href = "/login";
    return null;
  }
  if (res.status === 204) return null;
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(err.detail || "Request failed");
  }
  return res.json();
}

// Auth
export const authAPI = {
  signup: (data) => request("/auth/signup", { method: "POST", body: JSON.stringify(data) }),
  login: (data) => request("/auth/login", { method: "POST", body: JSON.stringify(data) }),
  me: () => request("/auth/me"),
};

// Chats
export const chatAPI = {
  list: () => request("/chats"),
  create: (title = "New Chat") => request("/chats", { method: "POST", body: JSON.stringify({ title }) }),
  delete: (id) => request(`/chats/${id}`, { method: "DELETE" }),
  getMessages: (id) => request(`/chats/${id}/messages`),
  sendMessage: (id, content, type = "text") =>
    request(`/chats/${id}/messages`, { method: "POST", body: JSON.stringify({ content, message_type: type }) }),
  uploadMedia: (id, formData) =>
    request(`/chats/${id}/upload`, { method: "POST", body: formData }),
};

// System
export const systemAPI = {
  openApp: (appName) => request("/system/open", { method: "POST", body: JSON.stringify({ app_name: appName }) }),
  playMedia: (appName) => request("/system/play", { method: "POST", body: JSON.stringify({ app_name: appName }) }),
  sendMessage: (person, message) => request("/system/message", { method: "POST", body: JSON.stringify({ person, message }) }),
};
