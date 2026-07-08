"use client";

/**
 * Settings runtime lette da GET /api/settings/public.
 *
 * Sostituiscono le env NEXT_PUBLIC_* bake-ate al build-time: i valori si
 * cambiano da /admin/impostazioni e il sito li vede al prossimo page load,
 * SENZA rebuild Docker.
 *
 * Strategia fallback: il render iniziale usa i valori di build (env), poi la
 * fetch runtime sovrascrive — ma solo con valori non vuoti, cosi' un DB non
 * ancora configurato non spegne cio' che la env accende (es. paypal_me).
 */
import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { PUBLIC_API_BASE } from "@/lib/api";

interface PublicSettings {
  paypal_me: string;
  payments_enabled: string;        // "true"/"false"/"" (vuoto = fallback env)
  contact_whatsapp: string;
  contact_email: string;
  hand_exchange_cap_prefixes: string;
  hand_exchange_cities: string;
}

const ENV_DEFAULTS: PublicSettings = {
  paypal_me: (process.env.NEXT_PUBLIC_PAYPAL_ME ?? "").trim(),
  payments_enabled: (process.env.NEXT_PUBLIC_PAYMENTS_ENABLED ?? "").trim(),
  contact_whatsapp: "",
  contact_email: "nerdnostalgiaita@gmail.com",
  hand_exchange_cap_prefixes: "56,57",
  hand_exchange_cities: "Livorno/Pisa",
};

export interface SettingsValue {
  /** true dopo che la fetch runtime e' arrivata (ok o fallita). */
  loaded: boolean;
  paypalMe: string;
  paymentsEnabled: boolean;
  contactWhatsapp: string;
  contactEmail: string;
  handExchangeCapPrefixes: string[];
  handExchangeCities: string;
}

function toValue(raw: PublicSettings, loaded: boolean): SettingsValue {
  return {
    loaded,
    paypalMe: raw.paypal_me.trim(),
    paymentsEnabled: raw.payments_enabled.trim().toLowerCase() === "true",
    contactWhatsapp: raw.contact_whatsapp.trim(),
    contactEmail: raw.contact_email.trim(),
    handExchangeCapPrefixes: raw.hand_exchange_cap_prefixes
      .split(",")
      .map((p) => p.trim())
      .filter((p) => /^\d+$/.test(p)),
    handExchangeCities: raw.hand_exchange_cities.trim(),
  };
}

const SettingsContext = createContext<SettingsValue>(toValue(ENV_DEFAULTS, false));

export function SettingsProvider({ children }: { children: React.ReactNode }) {
  const [raw, setRaw] = useState<PublicSettings>(ENV_DEFAULTS);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let cancelled = false;
    fetch(`${PUBLIC_API_BASE}/api/settings/public`)
      .then((r) => (r.ok ? r.json() : null))
      .then((data: Record<string, string> | null) => {
        if (cancelled || !data) return;
        setRaw((curr) => {
          const next = { ...curr };
          for (const key of Object.keys(next) as (keyof PublicSettings)[]) {
            const v = data[key];
            if (typeof v === "string" && v.trim() !== "") next[key] = v;
          }
          return next;
        });
      })
      .catch(() => {
        /* backend giu' o offline: si resta sui default di build */
      })
      .finally(() => {
        if (!cancelled) setLoaded(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const value = useMemo(() => toValue(raw, loaded), [raw, loaded]);
  return (
    <SettingsContext.Provider value={value}>{children}</SettingsContext.Provider>
  );
}

export function useSettings(): SettingsValue {
  return useContext(SettingsContext);
}

/** Normalizza un numero italiano in URL wa.me (null se non riconosciuto). */
export function whatsappUrl(phone: string, text?: string): string | null {
  let digits = phone.replace(/\D/g, "");
  if (!digits) return null;
  if (digits.startsWith("00")) digits = digits.slice(2);
  if (digits.length === 10 && digits.startsWith("3")) digits = "39" + digits;
  if (!(digits.length === 12 && digits.startsWith("39"))) return null;
  const base = `https://wa.me/${digits}`;
  return text ? `${base}?text=${encodeURIComponent(text)}` : base;
}
