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
  create: (title = "New Chat", systemPrompt = null) => request("/chats", { method: "POST", body: JSON.stringify({ title, system_prompt: systemPrompt }) }),
  delete: (id) => request(`/chats/${id}`, { method: "DELETE" }),
  getMessages: (id, limit = 50, offset = 0) => request(`/chats/${id}/messages?limit=${limit}&offset=${offset}`),
  sendMessage: (id, content, type = "text", mediaUrl = null) =>
    request(`/chats/${id}/messages`, { method: "POST", body: JSON.stringify({ content, message_type: type, media_url: mediaUrl }) }),
  editMessage: (chatId, messageId, content) =>
    request(`/chats/${chatId}/messages/${messageId}`, { method: "PUT", body: JSON.stringify({ content }) }),
  exportConversation: (id, format = "json") => request(`/chats/${id}/export?format=${format}`),
  sendMessage: (id, content, type = "text", mediaUrl = null) =>
    request(`/chats/${id}/messages`, { method: "POST", body: JSON.stringify({ content, message_type: type, media_url: mediaUrl }) }),
  streamMessage: async (id, content, type = "text", mediaUrl = null, onChunk) => {
    const token = localStorage.getItem("flaw_token");
    const response = await fetch(`${API_BASE}/chats/${id}/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`
      },
      body: JSON.stringify({ content, message_type: type, media_url: mediaUrl })
    });

    if (!response.ok) throw new Error("Stream failed");

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      const chunk = decoder.decode(value, { stream: true });
      onChunk(chunk);
    }
  },
  uploadMedia: (id, formData) =>
    request(`/chats/${id}/upload`, { method: "POST", body: formData }),
};

// System
export const systemAPI = {
  openApp: (appName) => request("/system/open", { method: "POST", body: JSON.stringify({ app_name: appName }) }),
  playMedia: (appName) => request("/system/play", { method: "POST", body: JSON.stringify({ app_name: appName }) }),
  sendMessage: (person, message, isImage = false) => request("/system/message", { method: "POST", body: JSON.stringify({ person, message, is_image: isImage }) }),
  askAgent: (query, mediaUrl = null) => request("/system/ask", { method: "POST", body: JSON.stringify({ query, media_url: mediaUrl }) }),
  process: (query) => request("/system/process", { method: "POST", body: JSON.stringify({ query }) }),
  takeScreenshot: () => request("/system/screenshot", { method: "POST" }),
};
