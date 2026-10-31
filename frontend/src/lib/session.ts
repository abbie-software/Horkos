import { setToken } from "./api";
import type { User } from "./types";

const KEY = "horkos-session";

export function saveSession(token: string, user: User) {
  try {
    localStorage.setItem(KEY, JSON.stringify({ token, user }));
  } catch {}
  setToken(token);
}

export function loadSession(): { token: string; user: User } | null {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return null;
    const saved = JSON.parse(raw) as { token: string; user: User };
    if (!saved.token || !saved.user) return null;
    setToken(saved.token);
    return saved;
  } catch {
    return null;
  }
}

export function clearSession() {
  try {
    localStorage.removeItem(KEY);
  } catch {}
  setToken(null);
}