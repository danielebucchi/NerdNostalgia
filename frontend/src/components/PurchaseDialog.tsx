"use client";

import { useEffect, useRef, useState } from "react";
import { createOrder } from "@/lib/api";
import { paypalUrl } from "@/lib/paypal";
import type { Article } from "@/lib/types";

interface Props {
  open: boolean;
  onClose: () => void;
  /** Articoli in checkout (1 per articolo singolo, N per carrello). */
  articles: Article[];
  /** Spedizione aggregata gia' calcolata. Comunicata anche al backend per consistency. */
  shippingTotal: number;
  /** Callback opzionale dopo successo (es. svuotare il carrello). */
  onSuccess?: () => void;
}

interface FormState {
  buyer_name: string;
  buyer_email: string;
  buyer_phone: string;
  ship_street: string;
  ship_city: string;
  ship_postal_code: string;
  ship_province: string;
  ship_country: string;
  notes: string;
  website: string; // honeypot
}

const empty: FormState = {
  buyer_name: "",
  buyer_email: "",
  buyer_phone: "",
  ship_street: "",
  ship_city: "",
  ship_postal_code: "",
  ship_province: "",
  ship_country: "Italia",
  notes: "",
  website: "",
};

export function PurchaseDialog({
  open,
  onClose,
  articles,
  shippingTotal,
  onSuccess,
}: Props) {
  const [state, setState] = useState<FormState>(empty);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const dialogRef = useRef<HTMLDivElement>(null);

  const subtotal = articles.reduce(
    (acc, a) => acc + Number(a.price || 0),
    0,
  );
  const grandTotal = subtotal + shippingTotal;
  const currency = articles[0]?.currency || "EUR";

  // Reset alla chiusura
  useEffect(() => {
    if (!open) {
      setState(empty);
      setError(null);
    }
  }, [open]);

  // Esc per chiudere
  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  function set<K extends keyof FormState>(k: K, v: FormState[K]) {
    setState((s) => ({ ...s, [k]: v }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await createOrder({
        buyer_name: state.buyer_name.trim(),
        buyer_email: state.buyer_email.trim(),
        buyer_phone: state.buyer_phone.trim() || undefined,
        ship_street: state.ship_street.trim(),
        ship_city: state.ship_city.trim(),
        ship_postal_code: state.ship_postal_code.trim(),
        ship_province: state.ship_province.trim() || undefined,
        ship_country: state.ship_country.trim() || "Italia",
        notes: state.notes.trim() || undefined,
        website: state.website,
        items: articles.map((a) => ({ article_id: a.id, quantity: 1 })),
      });

      // Apri paypal.me col totale in una nuova tab
      const url = paypalUrl(grandTotal, currency);
      if (url) {
        window.open(url, "_blank", "noopener,noreferrer");
      }

      if (onSuccess) onSuccess();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="purchase-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-ink/40 backdrop-blur-sm overflow-y-auto"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        ref={dialogRef}
        className="card relative w-full max-w-2xl my-8 p-6 sm:p-8 max-h-[90vh] overflow-y-auto"
      >
        <button
          type="button"
          onClick={onClose}
          aria-label="Chiudi"
          className="absolute top-3 right-3 w-9 h-9 rounded-full bg-ink/10 hover:bg-ink/20 text-ink flex items-center justify-center font-bold"
        >
          ✕
        </button>

        <h2 id="purchase-title" className="display text-2xl sm:text-3xl text-ink mb-2">
          Conferma acquisto
        </h2>
        <p className="text-ink-soft text-sm mb-5">
          Inserisci i tuoi dati e l&apos;indirizzo di spedizione. Dopo aver
          confermato verrai reindirizzato a PayPal per il pagamento. Ti scriverò
          per confermare la spedizione.
        </p>

        {/* Recap ordine */}
        <div className="card-soft p-4 mb-5 bg-pink-soft/30">
          <h3 className="text-xs font-bold uppercase tracking-wider text-ink-soft mb-2">
            Riepilogo ordine
          </h3>
          <ul className="text-sm space-y-1 mb-3">
            {articles.map((a) => (
              <li key={a.id} className="flex justify-between gap-3">
                <span className="text-ink truncate">{a.title}</span>
                <span className="text-ink-soft tabular-nums">
                  € {Number(a.price).toFixed(2)}
                </span>
              </li>
            ))}
          </ul>
          <div className="text-sm space-y-1 border-t border-ink/10 pt-2">
            <div className="flex justify-between">
              <span className="text-ink-soft">Subtotale</span>
              <span className="tabular-nums">€ {subtotal.toFixed(2)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-ink-soft">Spedizione</span>
              <span className="tabular-nums">€ {shippingTotal.toFixed(2)}</span>
            </div>
            <div className="flex justify-between font-bold text-base text-pink-deep pt-1 border-t border-ink/10">
              <span>Totale</span>
              <span className="tabular-nums">
                € {grandTotal.toFixed(2)} {currency}
              </span>
            </div>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Honeypot anti-bot, hidden ai veri umani */}
          <div className="absolute -left-[9999px] pointer-events-none">
            <label>
              Website
              <input
                type="text"
                tabIndex={-1}
                autoComplete="off"
                value={state.website}
                onChange={(e) => set("website", e.target.value)}
              />
            </label>
          </div>

          <div className="grid sm:grid-cols-2 gap-3">
            <Field label="Nome e cognome *">
              <input
                type="text"
                required
                value={state.buyer_name}
                onChange={(e) => set("buyer_name", e.target.value)}
                className="input"
              />
            </Field>
            <Field label="Email *">
              <input
                type="email"
                required
                value={state.buyer_email}
                onChange={(e) => set("buyer_email", e.target.value)}
                className="input"
              />
            </Field>
          </div>

          <Field label="Telefono (opzionale)">
            <input
              type="tel"
              value={state.buyer_phone}
              onChange={(e) => set("buyer_phone", e.target.value)}
              className="input"
            />
          </Field>

          <Field label="Indirizzo (via e numero civico) *">
            <input
              type="text"
              required
              placeholder="es. Via Roma 12"
              value={state.ship_street}
              onChange={(e) => set("ship_street", e.target.value)}
              className="input"
            />
          </Field>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <Field label="CAP *">
              <input
                type="text"
                required
                inputMode="numeric"
                maxLength={20}
                value={state.ship_postal_code}
                onChange={(e) => set("ship_postal_code", e.target.value)}
                className="input"
              />
            </Field>
            <Field label="Città *">
              <input
                type="text"
                required
                value={state.ship_city}
                onChange={(e) => set("ship_city", e.target.value)}
                className="input"
              />
            </Field>
            <Field label="Provincia">
              <input
                type="text"
                placeholder="es. RM"
                value={state.ship_province}
                onChange={(e) => set("ship_province", e.target.value)}
                className="input"
              />
            </Field>
          </div>

          <Field label="Paese *">
            <input
              type="text"
              required
              value={state.ship_country}
              onChange={(e) => set("ship_country", e.target.value)}
              className="input"
            />
          </Field>

          <Field label="Note (opzionale)">
            <textarea
              rows={2}
              placeholder="Richieste particolari, preferenze di spedizione, ecc."
              value={state.notes}
              onChange={(e) => set("notes", e.target.value)}
              className="input"
            />
          </Field>

          {error && (
            <p className="text-pink-deep text-sm">⚠ {error}</p>
          )}

          {/* Istruzione F&F visibile prima del submit */}
          <div className="rounded-xl bg-[#ffc439]/15 border border-[#ffc439]/40 p-3 text-sm leading-snug">
            <strong className="text-[#003087]">Su PayPal seleziona &quot;A un amico o familiare&quot;</strong>{" "}
            <span className="text-ink-soft">
              per evitare le commissioni. Trovi l&apos;opzione subito dopo aver inserito l&apos;importo.
            </span>
          </div>

          <div className="flex flex-col sm:flex-row gap-3 pt-1">
            <button
              type="button"
              onClick={onClose}
              className="btn btn-ghost text-sm"
              disabled={submitting}
            >
              Annulla
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="btn btn-paypal text-base font-bold flex-1 px-6 py-3.5 inline-flex items-center justify-center gap-2"
            >
              {submitting ? (
                <>
                  <span className="inline-block h-4 w-4 rounded-full border-2 border-white/40 border-t-white animate-spin" />
                  Invio…
                </>
              ) : (
                <>Conferma e paga € {grandTotal.toFixed(2)} →</>
              )}
            </button>
          </div>
          <p className="text-xs text-ink-soft text-center">
            Ti arriverà una conferma via email. Il pagamento PayPal apre in una
            nuova scheda.
          </p>
        </form>

        <style>{`
          .input {
            display: block;
            width: 100%;
            padding: 0.55rem 0.75rem;
            border: 1px solid rgba(61, 42, 92, 0.15);
            border-radius: 12px;
            background: #fffaf3;
            color: #3d2a5c;
            font-family: inherit;
            font-size: 0.92rem;
            outline: none;
            transition: box-shadow 200ms, border-color 200ms;
          }
          .input:focus {
            box-shadow: 0 0 0 3px rgba(248, 168, 200, 0.45);
            border-color: #e879a8;
          }
          .card-soft {
            background: rgba(255, 255, 255, 0.6);
            border-radius: 14px;
            border: 1px solid rgba(61, 42, 92, 0.08);
          }
        `}</style>
      </div>
    </div>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <label className="block">
      <span className="text-xs font-bold uppercase tracking-wider text-ink-soft">
        {label}
      </span>
      <div className="mt-1">{children}</div>
    </label>
  );
}
