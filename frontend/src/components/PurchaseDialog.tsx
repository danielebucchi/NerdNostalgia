"use client";

import { useEffect, useRef, useState } from "react";
import { AddressAutocomplete } from "@/components/AddressAutocomplete";
import {
  InpostGeowidget,
  type InpostPoint,
} from "@/components/InpostGeowidget";
import { PaypalButtons } from "@/components/PaypalButtons";
import {
  createOrder,
  createStripeCheckout,
  getInpostConfig,
  type AddressSuggestion,
} from "@/lib/api";
import {
  baseShippingFor,
  defaultInsured,
  INSURANCE_FEE,
  insuranceFeeFor,
  insuranceIsIncluded,
  setPendingOrder,
} from "@/lib/cart";
import { useSettings } from "@/lib/settings-context";
import type { Article } from "@/lib/types";

interface Props {
  open: boolean;
  onClose: () => void;
  /** Articoli in checkout (1 per articolo singolo, N per carrello). */
  articles: Article[];
  /** Spedizione calcolata dal chiamante. Serve solo come valore iniziale:
   *  dentro al dialog viene ricalcolata in tempo reale, perche' qui si
   *  sceglie se assicurare. */
  shippingTotal: number;
  /** Scelta sull'assicurazione gia' fatta nel carrello. Omessa (acquisto da
   *  scheda articolo) = default della fascia. */
  initialInsured?: boolean;
}

interface FormState {
  buyer_name: string;
  buyer_email: string;
  buyer_phone: string;
  /** Via digitata. Col locker serve a centrare la mappa sulla zona; a
   *  domicilio e' l'indirizzo vero di consegna. */
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
  initialInsured,
}: Props) {
  const [state, setState] = useState<FormState>(empty);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // CAP/citta'/provincia si compilano scegliendo un suggerimento, non a mano:
  // cosi' arrivano sempre coerenti fra loro. Resta pero' uno sblocco esplicito,
  // perche' chi abita dove OpenStreetMap non arriva deve poter comprare lo
  // stesso (e i CAP delle frazioni dal fornitore arrivano spesso sbagliati).
  // null = sto ancora chiedendo al backend se la mappa locker e' attiva.
  // true  = si ritira al locker. false = si spedisce a casa (fallback finche'
  // non arriva il token InPost, cosi' il sito continua a vendere).
  const [lockerMode, setLockerMode] = useState<boolean | null>(null);
  // Compilazione manuale di CAP/citta'/provincia (solo consegna a domicilio)
  const [manualAddress, setManualAddress] = useState(false);
  // Locker scelto sulla mappa: e' lui la destinazione dell'ordine.
  const [point, setPoint] = useState<InpostPoint | null>(null);
  // Coordinate dell'indirizzo cercato, per centrare la mappa
  const [center, setCenter] = useState<{ lat: number; lon: number } | null>(null);
  const [lockerUnavailable, setLockerUnavailable] = useState(false);
  // Assicurazione: parte dal default della fascia, poi decide il compratore
  const [insured, setInsured] = useState(false);
  const formRef = useRef<HTMLFormElement>(null);
  // null = non lo sappiamo ancora (config in arrivo dal backend)
  const [paypalAvailable, setPaypalAvailable] = useState<boolean | null>(null);
  const dialogRef = useRef<HTMLDivElement>(null);
  const { stripeEnabled, freeShippingAll } = useSettings();

  const subtotal = articles.reduce(
    (acc, a) => acc + Number(a.price || 0),
    0,
  );
  // Ricalcolo in tempo reale: la casella assicurazione cambia subito il
  // totale, senza aspettare il server.
  const insuranceIncluded = freeShippingAll || insuranceIsIncluded(subtotal);
  const effectiveInsured = insuranceIncluded || insured;
  const baseShipping = freeShippingAll ? 0 : baseShippingFor(subtotal);
  const insuranceCost = freeShippingAll
    ? 0
    : insuranceFeeFor(subtotal, effectiveInsured);
  const effectiveShipping = baseShipping + insuranceCost;
  const grandTotal = subtotal + effectiveShipping;
  const currency = articles[0]?.currency || "EUR";

  // Reset alla chiusura
  useEffect(() => {
    if (!open) {
      setState(empty);
      setError(null);
      setPoint(null);
      setCenter(null);
      setManualAddress(false);
    } else {
      // All'apertura: la scelta gia' fatta nel carrello, o il default della
      // fascia se si compra direttamente dalla scheda articolo.
      setInsured(initialInsured ?? defaultInsured(subtotal));
    }
  }, [open]);

  // Modalita' di consegna: la decide la presenza del token InPost lato
  // server, non una scelta del compratore. Cosi' il giorno in cui il token
  // arriva il sito passa al locker da solo, senza deploy.
  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    getInpostConfig().then((c) => {
      if (!cancelled) setLockerMode(!!c?.configured);
    });
    return () => {
      cancelled = true;
    };
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

  /** Suggerimento scelto. Compila i campi (servono alla consegna a
   *  domicilio) e intanto memorizza le coordinate, che col locker attivo
   *  centrano la mappa sulla zona del compratore. */
  function applySuggestion(sug: AddressSuggestion) {
    setState((s) => ({
      ...s,
      // Mai ripiegare sull'etichetta completa: contiene citta', provincia e
      // nazione, e finirebbero tutte nel campo della via.
      ship_street: sug.street || s.ship_street,
      ship_postal_code: sug.postal_code || s.ship_postal_code,
      ship_city: sug.city || s.ship_city,
      ship_province: sug.province || s.ship_province,
      ship_country: sug.country || s.ship_country,
    }));
    if (sug.lat != null && sug.lon != null) {
      setCenter({ lat: sug.lat, lon: sug.lon });
    }
  }

  /**
   * Valida e crea il NOSTRO ordine (PENDING). Lancia se i dati non vanno:
   * cosi' il popup PayPal non si apre nemmeno. Il carrello NON si svuota —
   * lo fara' la conferma di pagamento.
   */
  async function buildOrder() {
    if (formRef.current && !formRef.current.reportValidity()) {
      throw new Error("Controlla i campi del modulo");
    }
    if (lockerMode && !point) {
      const msg =
        "Scegli sulla mappa il locker InPost dove vuoi ritirare il pacco.";
      setError(msg);
      throw new Error(msg);
    }
    if (!lockerMode && !manualAddress &&
        (!state.ship_postal_code.trim() || !state.ship_city.trim())) {
      const msg =
        "Scegli l'indirizzo dall'elenco dei suggerimenti: CAP, città e " +
        "provincia si compilano da soli. Se il tuo indirizzo non c'è, usa " +
        "«Il mio indirizzo non è nell'elenco».";
      setError(msg);
      throw new Error(msg);
    }

    const order = await createOrder({
      buyer_name: state.buyer_name.trim(),
      buyer_email: state.buyer_email.trim(),
      buyer_phone: state.buyer_phone.trim() || undefined,
      // Destinazione: il locker se la mappa e' attiva, altrimenti casa.
      inpost_point_id: point?.id,
      inpost_point_name: point?.name || undefined,
      ship_street: point ? point.street || point.name : state.ship_street.trim(),
      ship_city: point ? point.city : state.ship_city.trim(),
      ship_postal_code: point ? point.postal_code : state.ship_postal_code.trim(),
      ship_province: point
        ? point.province || undefined
        : state.ship_province.trim() || undefined,
      ship_country: point ? "Italia" : state.ship_country.trim() || "Italia",
      notes: state.notes.trim() || undefined,
      insured: effectiveInsured,
      website: state.website,
      items: articles.map((a) => ({ article_id: a.id, quantity: 1 })),
    });
    setPendingOrder(order.id, order.public_token);
    return order;
  }

  /** Stripe: creiamo l'ordine e mandiamo alla pagina di pagamento ospitata. */
  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const order = await buildOrder();
      const url = await createStripeCheckout(order.id);
      window.location.href = url;
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setSubmitting(false);
    }
  }

  /** PayPal: il bottone ufficiale chiama questa per avere l'ordine da pagare. */
  async function handlePaypalCreate(): Promise<number> {
    setError(null);
    const order = await buildOrder();
    return order.id;
  }

  function handlePaypalPaid(orderId: number) {
    // Il backend ha gia' incassato e marcato PAGATO: andiamo alla conferma,
    // dove il carrello si svuota da solo.
    window.location.href = `/ordine/grazie?order=${orderId}`;
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
              <span className="tabular-nums">
                {baseShipping === 0 ? (
                  <strong className="text-mint-deep">GRATIS</strong>
                ) : (
                  `€ ${baseShipping.toFixed(2)}`
                )}
              </span>
            </div>
            {effectiveInsured && (
              <div className="flex justify-between">
                <span className="text-ink-soft">🛡 Assicurazione</span>
                <span className="tabular-nums">
                  {insuranceCost === 0 ? (
                    <strong className="text-mint-deep">INCLUSA</strong>
                  ) : (
                    `€ ${insuranceCost.toFixed(2)}`
                  )}
                </span>
              </div>
            )}
            <div className="flex justify-between font-bold text-base text-pink-deep pt-1 border-t border-ink/10">
              <span>Totale</span>
              <span className="tabular-nums">
                € {grandTotal.toFixed(2)} {currency}
              </span>
            </div>
          </div>
        </div>

        {/* Assicurazione: il totale qui sopra si aggiorna all'istante. Sopra
            la soglia di spedizione gratuita e' inclusa e non si toglie. */}
        <div
          className={
            "rounded-xl p-3 mb-5 transition-colors " +
            (effectiveInsured
              ? "bg-mint-soft/60 ring-1 ring-mint-deep/40"
              : "bg-ink/4 ring-1 ring-ink/10")
          }
        >
          <label
            className={
              "flex items-start gap-3 " +
              (insuranceIncluded ? "cursor-default" : "cursor-pointer")
            }
          >
            <input
              type="checkbox"
              checked={effectiveInsured}
              disabled={insuranceIncluded}
              onChange={(e) => setInsured(e.target.checked)}
              className="mt-0.5 w-5 h-5 flex-shrink-0 accent-mint-deep cursor-pointer disabled:cursor-default"
            />
            <span className="flex-1">
              <span className="block text-sm font-bold text-ink">
                🛡 Assicura la spedizione
                {insuranceIncluded ? (
                  <span className="text-mint-deep"> — inclusa</span>
                ) : (
                  <span className="text-ink-soft font-normal">
                    {" "}
                    (+ € {INSURANCE_FEE.toFixed(2)})
                  </span>
                )}
              </span>
              <span className="block text-xs text-ink-soft mt-1 leading-snug">
                {insuranceIncluded
                  ? "Su questo ordine è compresa: un pacco di questo valore non viaggia scoperto."
                  : effectiveInsured
                    ? "Se il pacco si perde o arriva danneggiato, ti rimborso il valore degli articoli. Senza assicurazione il corriere risponde solo di 1 € al kg."
                    : "Senza assicurazione, in caso di smarrimento il corriere rimborsa solo 1 € al kg (per legge). Spuntala per essere coperto sul valore reale."}
              </span>
            </span>
          </label>
        </div>

        <form ref={formRef} onSubmit={handleSubmit} className="space-y-4">
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
                autoComplete="name"
                value={state.buyer_name}
                onChange={(e) => set("buyer_name", e.target.value)}
                className="input"
              />
            </Field>
            <Field label="Email *">
              <input
                type="email"
                required
                autoComplete="email"
                value={state.buyer_email}
                onChange={(e) => set("buyer_email", e.target.value)}
                className="input"
              />
            </Field>
          </div>

          {/* Telefono: formalmente facoltativo, ma lo consigliamo con forza —
              senza numero il corriere non ha modo di avvisare e il pacco
              torna indietro. Il banner resta finche' il campo e' vuoto. */}
          <Field label="Telefono (consigliato)">
            <input
              type="tel"
              autoComplete="tel"
              placeholder="es. 333 1234567"
              value={state.buyer_phone}
              onChange={(e) => set("buyer_phone", e.target.value)}
              className="input"
            />
            {!state.buyer_phone.trim() && (
              <p className="mt-2 flex items-start gap-2 rounded-xl bg-sky-soft/50 ring-1 ring-sky-deep/30 px-3 py-2 text-sm leading-snug text-ink">
                <span aria-hidden="true" className="text-base leading-none">
                  🚚
                </span>
                <span>
                  Lascia il numero di telefono così il corriere può contattarti
                  in caso di problemi con la consegna.
                </span>
              </p>
            )}
          </Field>

          {/* ── Dove consegniamo ──
              La modalita' la decide il server: con il token InPost si ritira
              al locker, senza si spedisce a casa. Il compratore non sceglie,
              vede solo il percorso attivo. */}
          {lockerMode === null && (
            <p className="text-sm text-ink-soft">Carico le opzioni di consegna…</p>
          )}

          {lockerMode === true && (
            <>
              <div className="rounded-xl bg-lilac-deep/10 ring-1 ring-lilac-deep/35 px-3 py-2.5 text-sm leading-snug text-ink flex items-start gap-2">
                <span aria-hidden="true" className="text-base leading-none">📦</span>
                <span>
                  <strong>Il pacco si ritira in un locker InPost.</strong>{" "}
                  Scrivi la tua via e scegli il suggerimento: la mappa si
                  sposta sulla tua zona e ti mostra i locker più vicini. Poi
                  clicca quello che preferisci.
                </span>
              </div>

              <Field label="La tua zona (per trovare i locker vicini)">
                <AddressAutocomplete
                  placeholder="es. Via Alberto Profeti 271 Cascina"
                  value={state.ship_street}
                  onChange={(v) => set("ship_street", v)}
                  onSelect={applySuggestion}
                />
              </Field>

              {lockerUnavailable ? (
                <p className="text-sm text-pink-deep leading-snug">
                  ⚠ La mappa dei locker non è al momento disponibile.{" "}
                  <a href="/contatti" className="underline font-semibold">
                    Scrivimi
                  </a>{" "}
                  e concordiamo la consegna.
                </p>
              ) : (
                <InpostGeowidget
                  center={center}
                  onSelect={(p) => {
                    setPoint(p);
                    setError(null);
                  }}
                  onUnavailable={() => setLockerUnavailable(true)}
                />
              )}

              {point ? (
                <div className="rounded-xl bg-mint-soft/60 ring-1 ring-mint-deep/40 px-3 py-2.5 text-sm leading-snug">
                  <span className="font-bold text-ink">📍 Ritiri qui:</span>{" "}
                  <strong>{point.name}</strong>
                  <span className="block text-ink-soft text-xs mt-0.5">
                    {[point.street, point.postal_code, point.city]
                      .filter(Boolean)
                      .join(" · ")}{" "}
                    — codice <code>{point.id}</code>
                  </span>
                </div>
              ) : (
                !lockerUnavailable && (
                  <p className="text-[11px] text-ink-soft leading-snug">
                    Nessun locker selezionato: clicca un punto sulla mappa per
                    scegliere dove ritirare.
                  </p>
                )
              )}
            </>
          )}

          {lockerMode === false && (
            <>
              <div className="rounded-xl bg-lilac-deep/10 ring-1 ring-lilac-deep/35 px-3 py-2.5 text-sm leading-snug text-ink flex items-start gap-2">
                <span aria-hidden="true" className="text-base leading-none">👆</span>
                <span>
                  <strong>Scrivi la via e clicca sul suggerimento</strong> che
                  compare: CAP, città e provincia si compilano da soli e non
                  vanno scritti a mano. Serve il nome completo della via (es.
                  «Via Alberto Profeti», non «Via Profeti»).
                </span>
              </div>

              <Field label="Indirizzo (via e numero civico) *">
                <AddressAutocomplete
                  required
                  placeholder="es. Via Roma 12"
                  value={state.ship_street}
                  onChange={(v) => set("ship_street", v)}
                  onSelect={applySuggestion}
                />
              </Field>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <Field label="CAP *">
                  <input
                    type="text"
                    required
                    inputMode="numeric"
                    maxLength={20}
                    autoComplete="postal-code"
                    readOnly={!manualAddress}
                    aria-readonly={!manualAddress}
                    value={state.ship_postal_code}
                    onChange={(e) => set("ship_postal_code", e.target.value)}
                    className={manualAddress ? "input" : "input input-locked"}
                  />
                </Field>
                <Field label="Città *">
                  <input
                    type="text"
                    required
                    autoComplete="address-level2"
                    readOnly={!manualAddress}
                    aria-readonly={!manualAddress}
                    value={state.ship_city}
                    onChange={(e) => set("ship_city", e.target.value)}
                    className={manualAddress ? "input" : "input input-locked"}
                  />
                </Field>
                <Field label="Provincia">
                  <input
                    type="text"
                    placeholder={manualAddress ? "es. RM" : ""}
                    autoComplete="address-level1"
                    readOnly={!manualAddress}
                    aria-readonly={!manualAddress}
                    value={state.ship_province}
                    onChange={(e) => set("ship_province", e.target.value)}
                    className={manualAddress ? "input" : "input input-locked"}
                  />
                </Field>
              </div>

              {!manualAddress ? (
                <p className="text-[11px] text-ink-soft leading-snug -mt-1">
                  Questi tre campi si compilano da soli.{" "}
                  <button
                    type="button"
                    onClick={() => setManualAddress(true)}
                    className="underline decoration-dotted hover:text-pink-deep"
                  >
                    Il mio indirizzo non è nell&apos;elenco →
                  </button>
                </p>
              ) : (
                <p className="text-[11px] text-ink-soft leading-snug -mt-1">
                  Compilazione manuale attiva: controlla bene CAP e città.{" "}
                  <button
                    type="button"
                    onClick={() => setManualAddress(false)}
                    className="underline decoration-dotted hover:text-pink-deep"
                  >
                    Torna ai suggerimenti
                  </button>
                </p>
              )}

              <Field label="Paese *">
                <input
                  type="text"
                  required
                  autoComplete="country-name"
                  value={state.ship_country}
                  onChange={(e) => set("ship_country", e.target.value)}
                  className="input"
                />
              </Field>
            </>
          )}

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

          <div className="flex flex-col gap-2 pt-1">
            {stripeEnabled && (
              <button
                type="submit"
                disabled={submitting}
                className="btn btn-primary text-base font-bold w-full px-6 py-3.5 inline-flex items-center justify-center gap-2"
              >
                {submitting ? (
                  <>
                    <span className="inline-block h-4 w-4 rounded-full border-2 border-white/40 border-t-white animate-spin" />
                    Invio…
                  </>
                ) : (
                  <>💳 Paga con carta € {grandTotal.toFixed(2)}</>
                )}
              </button>
            )}
            {/* Bottoni PayPal ufficiali: il pagamento si apre nella finestra
                PayPal e torna qui confermato. Si nascondono da soli se PayPal
                non e' configurato lato server. */}
            <PaypalButtons
              createOurOrder={handlePaypalCreate}
              onPaid={handlePaypalPaid}
              onError={setError}
              currency={currency}
              disabled={submitting}
              onAvailability={setPaypalAvailable}
            />

            {/* Nessun metodo attivo: meglio dirlo che lasciare un modulo
                compilato davanti a un solo bottone "Annulla". */}
            {!stripeEnabled && paypalAvailable === false && (
              <p className="text-sm text-pink-deep text-center leading-snug">
                I pagamenti online non sono al momento disponibili.{" "}
                <a href="/contatti" className="underline font-semibold">
                  Scrivimi
                </a>{" "}
                e concordiamo il pagamento.
              </p>
            )}
            <button
              type="button"
              onClick={onClose}
              className="btn btn-ghost text-sm"
              disabled={submitting}
            >
              Annulla
            </button>
          </div>
          <p className="text-xs text-ink-soft text-center">
            Ti arriverà una conferma via email — se non la vedi,{" "}
            <strong>controlla nello spam</strong>. Il pagamento si apre nella
            finestra sicura di {stripeEnabled ? "Stripe o PayPal" : "PayPal"}: i
            dati della carta non passano mai da questo sito.
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
          .input-locked {
            background: rgba(61, 42, 92, 0.05);
            color: #6b5b8a;
            cursor: not-allowed;
          }
          .input-locked:focus {
            box-shadow: none;
            border-color: rgba(61, 42, 92, 0.15);
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
