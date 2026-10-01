"use client";

import { useEffect, useRef, useState } from "react";
import { getInpostConfig, type InpostConfig } from "@/lib/api";

/** Locker scelto, normalizzato nei campi che ci servono per spedire. */
export interface InpostPoint {
  id: string;
  name: string;
  street: string;
  city: string;
  postal_code: string;
  province: string;
}

interface Props {
  /** Dove centrare la mappa: le coordinate dell'indirizzo cercato. */
  center?: { lat: number; lon: number } | null;
  onSelect: (point: InpostPoint) => void;
  onUnavailable?: () => void;
}

// Evento custom con cui il widget ci passa il punto. Il nome lo decidiamo noi
// e lo dichiariamo nell'attributo `onpoint`.
const POINT_EVENT = "nnInpostPointSelected";

let assetsPromise: Promise<void> | null = null;

function loadAssets(scriptUrl: string, styleUrl: string): Promise<void> {
  if (assetsPromise) return assetsPromise;
  assetsPromise = new Promise((resolve, reject) => {
    if (!document.querySelector(`link[href="${styleUrl}"]`)) {
      const link = document.createElement("link");
      link.rel = "stylesheet";
      link.href = styleUrl;
      document.head.appendChild(link);
    }
    const existing = document.querySelector(`script[src="${scriptUrl}"]`);
    if (existing) {
      resolve();
      return;
    }
    const script = document.createElement("script");
    script.src = scriptUrl;
    script.defer = true;
    script.onload = () => resolve();
    script.onerror = () => {
      assetsPromise = null; // consenti un nuovo tentativo
      reject(new Error("Geowidget InPost non caricato"));
    };
    document.head.appendChild(script);
  });
  return assetsPromise;
}

function text(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}

/**
 * Normalizza il punto che arriva dal widget.
 *
 * La documentazione InPost non garantisce tutti i campi, e la forma cambia fra
 * mercati: leggiamo piu' alternative e accettiamo che qualcosa manchi, invece
 * di rompere il checkout per una chiave con un nome diverso del previsto.
 */
export function normalisePoint(raw: Record<string, unknown>): InpostPoint | null {
  if (!raw) return null;
  const details = (raw.address_details ?? {}) as Record<string, unknown>;
  const address = (raw.address ?? {}) as Record<string, unknown>;

  const id = text(raw.name) || text(raw.id);
  if (!id) return null;

  const street = [text(details.street), text(details.building_number)]
    .filter(Boolean)
    .join(" ");

  return {
    id,
    name:
      text(raw.location_description) ||
      text(address.line1) ||
      text(raw.name),
    street: street || text(address.line1),
    city: text(details.city) || text(address.line2),
    postal_code: text(details.post_code),
    province: text(details.province),
  };
}

/**
 * Mappa ufficiale InPost per scegliere il locker di ritiro.
 *
 * Il token e' pubblico ma legato al dominio: senza token configurato il
 * componente non si monta e lo dice al chiamante, che mostrera' un messaggio
 * invece di una mappa vuota.
 */
export function InpostGeowidget({ center, onSelect, onUnavailable }: Props) {
  const [config, setConfig] = useState<InpostConfig | null>(null);
  const [failed, setFailed] = useState(false);
  const [ready, setReady] = useState(false);
  const holder = useRef<HTMLDivElement>(null);
  const apiRef = useRef<{ changePosition?: (p: object, z?: number) => void } | null>(null);
  const onSelectRef = useRef(onSelect);
  onSelectRef.current = onSelect;
  const onUnavailableRef = useRef(onUnavailable);
  onUnavailableRef.current = onUnavailable;

  useEffect(() => {
    let cancelled = false;
    getInpostConfig().then((c) => {
      if (cancelled) return;
      setConfig(c);
      if (!c?.configured) onUnavailableRef.current?.();
    });
    return () => {
      cancelled = true;
    };
  }, []);

  // Il punto scelto arriva come evento sul document
  useEffect(() => {
    function handler(e: Event) {
      const detail =
        (e as CustomEvent).detail ??
        // la documentazione InPost usa `details` in un esempio: accettiamo
        // entrambe le grafie invece di scommettere su una
        (e as unknown as { details?: unknown }).details;
      const point = normalisePoint(detail as Record<string, unknown>);
      if (point) onSelectRef.current(point);
    }
    document.addEventListener(POINT_EVENT, handler);
    return () => document.removeEventListener(POINT_EVENT, handler);
  }, []);

  // Montaggio del widget
  useEffect(() => {
    if (!config?.configured || !holder.current) return;
    let cancelled = false;

    loadAssets(config.script_url, config.style_url)
      .then(() => {
        if (cancelled || !holder.current) return;
        holder.current.innerHTML = "";
        const el = document.createElement("inpost-geowidget");
        el.setAttribute("token", config.token);
        el.setAttribute("language", config.language);
        el.setAttribute("config", config.widget_config);
        el.setAttribute("onpoint", POINT_EVENT);
        el.style.display = "block";
        el.style.width = "100%";
        el.style.height = "100%";
        el.addEventListener("inpost.geowidget.init", (event: Event) => {
          const api = (event as CustomEvent).detail?.api;
          apiRef.current = api ?? null;
          setReady(true);
          applyCenter();
        });
        holder.current.appendChild(el);
      })
      .catch(() => {
        if (cancelled) return;
        setFailed(true);
        onUnavailableRef.current?.();
      });

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [config]);

  function applyCenter() {
    const api = apiRef.current;
    if (!api?.changePosition || !center) return;
    try {
      api.changePosition({ latitude: center.lat, longitude: center.lon }, 15);
    } catch {
      /* il widget non e' pronto: pazienza, resta sulla vista di default */
    }
  }

  // Centra la mappa quando cambia l'indirizzo cercato
  useEffect(() => {
    if (ready) applyCenter();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [center?.lat, center?.lon, ready]);

  if (config && !config.configured) return null;
  if (failed) {
    return (
      <p className="text-sm text-pink-deep leading-snug">
        ⚠ Non riesco a caricare la mappa dei locker. Riprova fra poco oppure{" "}
        <a href="/contatti" className="underline font-semibold">scrivimi</a> e
        concordiamo la consegna.
      </p>
    );
  }

  return (
    <div className="rounded-xl overflow-hidden ring-1 ring-ink/15 bg-white">
      <div ref={holder} style={{ height: 380 }} />
      {!ready && (
        <p className="text-xs text-ink-soft text-center py-3">
          Carico la mappa dei locker…
        </p>
      )}
    </div>
  );
}
