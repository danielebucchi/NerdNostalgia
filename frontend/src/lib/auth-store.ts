import { useEffect, useState } from "react";

const TOKEN_KEY = "nn_admin_token";
const USER_KEY = "nn_admin_user";
const EVENT = "nn:admin-auth-change";

export interface AdminUser {
  id: number;
  username: string;
  email: string;
  full_name: string | null;
  role: string;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
  updated_at: string;
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  window.localStorage.setItem(TOKEN_KEY, token);
  window.dispatchEvent(new Event(EVENT));
}

export function clearToken(): void {
  window.localStorage.removeItem(TOKEN_KEY);
  window.localStorage.removeItem(USER_KEY);
  window.dispatchEvent(new Event(EVENT));
}

export function getStoredUser(): AdminUser | null {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as AdminUser;
  } catch {
    return null;
  }
}

export function setStoredUser(user: AdminUser): void {
  window.localStorage.setItem(USER_KEY, JSON.stringify(user));
  window.dispatchEvent(new Event(EVENT));
}

function readIsAdmin(): boolean {
  return Boolean(getToken()) && getStoredUser()?.role === "ADMIN";
}

/** True se in questo browser c'e' una sessione admin: sul sito pubblico
 *  serve a mostrare gli strumenti di modifica solo a chi gestisce il
 *  negozio. E' solo una scelta d'interfaccia: i permessi veri li controlla
 *  il backend su ogni chiamata. */
export function useIsAdmin(): boolean {
  const [isAdmin, setIsAdmin] = useState(false);
  useEffect(() => {
    const update = () => setIsAdmin(readIsAdmin());
    update();
    window.addEventListener(EVENT, update);
    window.addEventListener("storage", update);
    return () => {
      window.removeEventListener(EVENT, update);
      window.removeEventListener("storage", update);
    };
  }, []);
  return isAdmin;
}
