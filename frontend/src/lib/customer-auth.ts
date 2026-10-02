"use client";

import { useCallback, useEffect, useState } from "react";
import { PUBLIC_API_BASE } from "@/lib/api";

/* Sessione del CLIENTE, tenuta separata da quella dell'admin.
 *
 * Chiavi diverse apposta: se condividessero lo storage, entrare nel pannello
 * admin ti farebbe comparire anche come cliente sul sito pubblico (e
 * viceversa), con due identita' sovrapposte e nessun modo di uscire da una
 * sola delle due. */
const TOKEN_KEY = "nn:customer-token";
const USER_KEY = "nn:customer-user";
const EVENT = "nn:customer-auth-change";

export interface CustomerUser {
  id: number;
  username: string;
  email: string;
  full_name: string | null;
  role: string;
}

export function getCustomerToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setCustomerSession(token: string, user: CustomerUser): void {
  window.localStorage.setItem(TOKEN_KEY, token);
  window.localStorage.setItem(USER_KEY, JSON.stringify(user));
  window.dispatchEvent(new Event(EVENT));
}

export function clearCustomerSession(): void {
  window.localStorage.removeItem(TOKEN_KEY);
  window.localStorage.removeItem(USER_KEY);
  window.dispatchEvent(new Event(EVENT));
}

function readUser(): CustomerUser | null {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as CustomerUser;
  } catch {
    return null;
  }
}

/** Sessione corrente. `loading` evita di mostrare "Accedi" per un istante
 *  a chi è già dentro, allo stesso modo del carrello. */
export function useCustomer(): {
  user: CustomerUser | null;
  loading: boolean;
  logout: () => void;
} {
  const [user, setUser] = useState<CustomerUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setUser(readUser());
    setLoading(false);
    function onChange() {
      setUser(readUser());
    }
    window.addEventListener(EVENT, onChange);
    window.addEventListener("storage", onChange);
    return () => {
      window.removeEventListener(EVENT, onChange);
      window.removeEventListener("storage", onChange);
    };
  }, []);

  const logout = useCallback(() => clearCustomerSession(), []);
  return { user, loading, logout };
}

async function parseError(res: Response): Promise<string> {
  try {
    const body = await res.json();
    if (body?.detail) {
      return typeof body.detail === "string"
        ? body.detail
        : "Controlla i dati inseriti.";
    }
  } catch {
    /* corpo non JSON */
  }
  return `Errore ${res.status}`;
}

async function loadProfile(token: string): Promise<CustomerUser> {
  const res = await fetch(`${PUBLIC_API_BASE}/api/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  if (!res.ok) throw new Error(await parseError(res));
  return (await res.json()) as CustomerUser;
}

export async function registerCustomer(input: {
  email: string;
  password: string;
  full_name?: string;
  marketing_consent: boolean;
}): Promise<CustomerUser> {
  const res = await fetch(`${PUBLIC_API_BASE}/api/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!res.ok) throw new Error(await parseError(res));
  const { access_token } = await res.json();
  const user = await loadProfile(access_token);
  setCustomerSession(access_token, user);
  return user;
}

export async function loginCustomer(
  email: string,
  password: string,
): Promise<CustomerUser> {
  // Il login usa il form OAuth2: username = email
  const body = new URLSearchParams({ username: email, password });
  const res = await fetch(`${PUBLIC_API_BASE}/api/auth/login`, {
    method: "POST",
    body,
  });
  if (!res.ok) {
    throw new Error(
      res.status === 401
        ? "Email o password non corretti."
        : await parseError(res),
    );
  }
  const { access_token } = await res.json();
  const user = await loadProfile(access_token);
  setCustomerSession(access_token, user);
  return user;
}

/** Chiamata autenticata come cliente. Se il token è scaduto pulisce la
 *  sessione, così l'interfaccia non resta a mostrare dati di nessuno. */
export async function customerFetch<T>(path: string): Promise<T> {
  const token = getCustomerToken();
  if (!token) throw new Error("Non autenticato");
  const res = await fetch(`${PUBLIC_API_BASE}${path}`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  if (res.status === 401) {
    clearCustomerSession();
    throw new Error("Sessione scaduta, accedi di nuovo.");
  }
  if (!res.ok) throw new Error(await parseError(res));
  return (await res.json()) as T;
}
