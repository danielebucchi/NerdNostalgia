"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { customerFetch, useCustomer } from "@/lib/customer-auth";

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
  PAID: { label: "Pagato — lo preparo", chip: "chip-mint" },
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
          <h1 className="display text-3xl text-ink">Il tuo profilo</h1>
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

      {orders === null && !error && <p className="text-ink-soft">Carico i tuoi ordini…</p>}

      {orders !== null && orders.length === 0 && (
        <div className="card p-8 text-center">
          <p className="text-ink-soft mb-4">
            Non hai ancora ordini. Quando ne farai uno lo trovi qui, con il
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
    </article>
  );
}

function OrderCard({ order: o }: { order: MyOrder }) {
  const stato = STATO[o.status];
  const data = new Date(o.created_at).toLocaleDateString("it-IT", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });

  return (
    <div className="card p-4">
      <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
        <div>
          <span className="display text-lg text-ink">Ordine #{o.id}</span>
          <span className="text-xs text-ink-soft ml-2">{data}</span>
        </div>
        <div className="flex items-center gap-3">
          <span className={`chip ${stato.chip} text-[11px]`}>{stato.label}</span>
          <span className="display text-lg text-pink-deep">
            € {Number(o.grand_total).toFixed(2)}
          </span>
        </div>
      </div>

      <ul className="text-sm text-ink-soft space-y-0.5 mb-2">
        {o.items.map((it) => (
          <li key={it.id}>
            {it.article_id ? (
              <Link
                href={`/articles/${it.article_id}`}
                className="hover:text-pink-deep transition-colors"
              >
                {it.title_snapshot}
              </Link>
            ) : (
              it.title_snapshot
            )}
            {it.quantity > 1 ? ` × ${it.quantity}` : ""}
          </li>
        ))}
      </ul>

      {o.tracking_code && (
        <div className="rounded-xl bg-sky-soft/40 ring-1 ring-sky-deep/30 px-3 py-2 text-sm leading-snug">
          📦 Spedizione{o.tracking_carrier ? ` con ${o.tracking_carrier}` : ""}:{" "}
          <strong className="text-ink">{o.tracking_code}</strong>
          {o.tracking_url && (
            <>
              {" — "}
              <a
                href={o.tracking_url}
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
