"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AddressBook } from "@/components/AddressBook";
import { DeleteAccount } from "@/components/DeleteAccount";
import {
  customerFetch,
  getMarketingConsent,
  setMarketingConsent,
  useCustomer,
} from "@/lib/customer-auth";

interface OrderItem {
  id: number;
  article_id: number | null;
  title_snapshot: string;
  price_snapshot: string;
  quantity: number;
}

interface MyOrder {
  id: number;
  status: "PENDING" | "PAID" | "SHIPPED" | "COMPLETED" | "CANCELLED";
  grand_total: string;
  currency: string;
  created_at: string;
  shipped_at: string | null;
  tracking_carrier?: string | null;
  tracking_code?: string | null;
  tracking_url?: string | null;
  items: OrderItem[];
}

const STATO: Record<MyOrder["status"], { label: string; chip: string }> = {
  PENDING: { label: "In attesa di pagamento", chip: "chip-star" },
  PAID: { label: "In preparazione", chip: "chip-mint" },
  SHIPPED: { label: "Spedito", chip: "chip-sky" },
  COMPLETED: { label: "Completato", chip: "chip-lilac" },
  CANCELLED: { label: "Annullato", chip: "chip-pink" },
};

// In corso = c'è ancora qualcosa da aspettare. Il resto è storico.
const IN_CORSO: MyOrder["status"][] = ["PENDING", "PAID", "SHIPPED"];

export default function ProfiloPage() {
  const router = useRouter();
  const { user, loading: loadingUser, logout } = useCustomer();
  const [orders, setOrders] = useState<MyOrder[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (loadingUser) return;
    if (!user) {
      router.replace("/accedi");
      return;
    }
    customerFetch<MyOrder[]>("/api/orders/mine")
      .then(setOrders)
      .catch((err) => setError(err instanceof Error ? err.message : String(err)));
  }, [user, loadingUser, router]);

  if (loadingUser || (!user && !error)) {
    return <p className="text-ink-soft">Caricamento…</p>;
  }

  const inCorso = (orders ?? []).filter((o) => IN_CORSO.includes(o.status));
  const passati = (orders ?? []).filter((o) => !IN_CORSO.includes(o.status));

  return (
    <article>
      <div className="flex items-start justify-between gap-4 mb-6">
        <div>
          <h1 className="display text-3xl text-ink">Il mio profilo</h1>
          <p className="text-ink-soft text-sm mt-1">
            {user?.full_name || user?.email}
          </p>
        </div>
        <button
          type="button"
          onClick={() => {
            logout();
            router.push("/");
          }}
          className="btn btn-ghost text-sm"
        >
          Esci
        </button>
      </div>

      {error && <p className="text-pink-deep text-sm mb-4">⚠ {error}</p>}

      {orders === null && !error && <p className="text-ink-soft">Caricamento degli ordini in corso…</p>}

      {orders !== null && orders.length === 0 && (
        <div className="card p-8 text-center">
          <p className="text-ink-soft mb-4">
            Non risultano ordini. Il primo acquisto comparirà qui, con il
            codice per seguire la spedizione.
          </p>
          <Link href="/" className="btn btn-primary text-sm inline-flex">
            Sfoglia il catalogo
          </Link>
        </div>
      )}

      {inCorso.length > 0 && (
        <section className="mb-8">
          <h2 className="display text-xl text-ink mb-3">Ordini in corso</h2>
          <div className="space-y-3">
            {inCorso.map((o) => (
              <OrderCard key={o.id} order={o} />
            ))}
          </div>
        </section>
      )}

      {passati.length > 0 && (
        <section>
          <h2 className="display text-xl text-ink mb-3">Ordini passati</h2>
          <div className="space-y-3">
            {passati.map((o) => (
              <OrderCard key={o.id} order={o} />
            ))}
          </div>
        </section>
      )}

      <AddressBook />

      <ConsensoPromozionale />

      <DeleteAccount />
    </article>
  );
}

/** Link del corriere, reso assoluto.
 *
 *  Il backend ora normalizza quando si salva, ma gli ordini gia' in
 *  archivio hanno ancora il valore com'era: senza schema il browser lo
 *  legge come un percorso del sito e porta su /brt.it/... invece che dal
 *  corriere. Qui non si inventa niente, si aggiunge solo "https://".
 */
function linkEsterno(url: string | null | undefined): string | null {
  const u = (url || "").trim();
  if (!u) return null;
  if (/^https?:\/\//i.test(u)) return u;
  // Qualsiasi altro schema (javascript:, data:) non diventa un link.
  if (u.includes("://") || /^[a-z]+:/i.test(u)) return null;
  return `https://${u}`;
}

function OrderCard({ order: o }: { order: MyOrder }) {
  const stato = STATO[o.status];
  // Con molti pezzi il titolo diventerebbe illeggibile: dopo i primi tre
  // si dice quanti altri ce n'erano.
  const tracking = linkEsterno(o.tracking_url);
  const nomi = o.items.map((it) => it.title_snapshot);
  const titolo =
    nomi.length > 3
      ? `${nomi.slice(0, 3).join(", ")} e altri ${nomi.length - 3}`
      : nomi.join(", ") || `#${o.id}`;
  // L'elenco sotto ha senso solo se aggiunge qualcosa al titolo: con un
  // pezzo solo in copia unica direbbe la stessa cosa due volte.
  const elencoUtile =
    nomi.length > 3 || o.items.some((it) => it.quantity > 1);
  const data = new Date(o.created_at).toLocaleDateString("it-IT", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });

  return (
    <div className="card p-4">
      <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
        <div className="min-w-0">
          {/* Il numero d'ordine dice qualcosa a me, non a chi ha comprato:
              lui riconosce il suo pacco dal nome di quello che ha preso. */}
          <span className="display text-lg text-ink">
            Ordine — {titolo}
          </span>
          <span className="text-xs text-ink-soft ml-2">{data}</span>
        </div>
        <div className="flex items-center gap-3">
          <span className={`chip ${stato.chip} text-[11px]`}>{stato.label}</span>
          <span className="display text-lg text-pink-deep">
            € {Number(o.grand_total).toFixed(2)}
          </span>
        </div>
      </div>

      {/* Niente link alla scheda: il pezzo che ha comprato e' venduto, e
          mandarlo su una pagina "non disponibile" non lo aiuta. */}
      {elencoUtile && (
      <ul className="text-sm text-ink-soft space-y-0.5 mb-2">
        {o.items.map((it) => (
          <li key={it.id}>
            {it.title_snapshot}
            {it.quantity > 1 ? ` × ${it.quantity}` : ""}
          </li>
        ))}
      </ul>
      )}

      {/* A ordine completato il pacco e' arrivato: il tracking non serve
          piu' a nessuno e i corrieri smettono comunque di aggiornarlo,
          quindi il link porterebbe a una pagina vuota o scaduta. */}
      {o.tracking_code && o.status !== "COMPLETED" && (
        <div className="rounded-xl bg-sky-soft/40 ring-1 ring-sky-deep/30 px-3 py-2 text-sm leading-snug">
          📦 Spedizione{o.tracking_carrier ? ` con ${o.tracking_carrier}` : ""}:{" "}
          <strong className="text-ink">{o.tracking_code}</strong>
          {tracking && (
            <>
              {" — "}
              <a
                href={tracking}
                target="_blank"
                rel="noopener noreferrer"
                className="underline font-semibold text-pink-deep"
              >
                segui il pacco ↗
              </a>
            </>
          )}
        </div>
      )}
    </div>
  );
}


/** La spunta delle email promozionali.
 *
 * Sta qui perche' l'email di benvenuto dice "se cambi idea la trovi nel tuo
 * profilo": finche' non c'era, quella frase era una promessa a vuoto. In
 * fondo alla pagina di proposito — chi apre il profilo viene per gli ordini.
 */
function ConsensoPromozionale() {
  const [consenso, setConsenso] = useState<boolean | null>(null);
  const [busy, setBusy] = useState(false);
  const [errore, setErrore] = useState<string | null>(null);
  const [salvato, setSalvato] = useState(false);

  useEffect(() => {
    getMarketingConsent()
      .then((c) => setConsenso(c.marketing_consent))
      .catch(() => setConsenso(null));
  }, []);

  async function cambia(valore: boolean) {
    setBusy(true);
    setErrore(null);
    try {
      const c = await setMarketingConsent(valore);
      setConsenso(c.marketing_consent);
      setSalvato(true);
      window.setTimeout(() => setSalvato(false), 2500);
    } catch (err) {
      setErrore(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  if (consenso === null) return null;

  return (
    <section className="mt-10 pt-6 border-t border-ink/10">
      <h2 className="display text-xl text-ink mb-3">Email promozionali</h2>
      <label className="flex items-start gap-3 cursor-pointer">
        <input
          type="checkbox"
          checked={consenso}
          disabled={busy}
          onChange={(e) => cambia(e.target.checked)}
          className="mt-1 h-4 w-4 accent-lilac-deep"
        />
        <span className="text-ink-soft text-sm leading-snug">
          Avvisami quando arrivano pezzi interessanti.
          {salvato && (
            <span className="text-ink font-semibold"> — salvato ✓</span>
          )}
        </span>
      </label>
      <p className="text-ink-soft/70 text-xs mt-2">
        Le email relative ai Suoi ordini (conferma, spedizione, tracciamento) vengono
        comunque.
      </p>
      {errore && <p className="text-pink-deep text-sm mt-2">⚠ {errore}</p>}
    </section>
  );
}
