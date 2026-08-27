const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const TOKEN_KEY = "consiliai_token";

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

export function isLoggedIn() {
  return Boolean(getToken());
}

/**
 * fastapi-users' /auth/register expects JSON: { email, password }.
 * Throws with a readable message on failure (e.g. "REGISTER_USER_ALREADY_EXISTS").
 */
export async function register(email, password) {
  const res = await fetch(`${API_BASE}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail?.reason || body.detail || "Registration failed");
  }
  return res.json();
}

/**
 * fastapi-users' /auth/jwt/login expects OAuth2 form encoding
 * (application/x-www-form-urlencoded with `username` + `password`), not
 * JSON — the `username` field carries the email.
 */
export async function login(email, password) {
  const body = new URLSearchParams();
  body.set("username", email);
  body.set("password", password);

  const res = await fetch(`${API_BASE}/auth/jwt/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Invalid email or password");
  }
  const data = await res.json();
  setToken(data.access_token);
  return data;
}

export function logout() {
  clearToken();
}

/**
 * Sends one message to the orchestrator. thread_id is derived server-side
 * from the authenticated user now — the frontend never generates or sends
 * one (see main.py's /chat).
 */
export async function sendChatMessage(message) {
  const token = getToken();
  if (!token) throw new Error("Not authenticated");

  const body = new URLSearchParams();
  body.set("message", message);

  const res = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
      Authorization: `Bearer ${token}`,
    },
    body,
  });

  if (res.status === 401) {
    clearToken();
    throw new Error("Session expired — please log in again.");
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Something went wrong talking to the assistant.");
  }
  return res.json(); // { reply, state: {...} }
}

export async function getChatHistory() {
  const token = getToken();
  if (!token) throw new Error("Not authenticated");

  const res = await fetch(`${API_BASE}/chat/history`, {
    headers: { Authorization: `Bearer ${token}` },
  });

  if (res.status === 401) {
    clearToken();
    throw new Error("Session expired — please log in again.");
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Could not load chat history.");
  }
  return res.json();
}

export async function downloadArtifact(download) {
  const token = getToken();
  if (!token) throw new Error("Not authenticated");

  const filename = download.filename;
  const res = await fetch(`${API_BASE}${download.url}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (res.status === 401) {
    clearToken();
    throw new Error("Session expired — please log in again.");
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Could not download the file.");
  }

  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}
