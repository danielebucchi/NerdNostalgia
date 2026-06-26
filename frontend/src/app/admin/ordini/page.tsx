"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AdminShell } from "@/components/admin/AdminShell";
import { adminApi } from "@/lib/admin-api";

interface OrderItem {
  id: number;
  article_id: number | null;
  title_snapshot: string;
  price_snapshot: string;
  quantity: number;
}

interface Order {
  id: number;
  buyer_name: string;
  buyer_email: string;
  buyer_phone: string | null;
  ship_street: string;
  ship_city: string;
  ship_postal_code: string;
  ship_province: string | null;
  ship_country: string;
  subtotal: string;
  shipping_total: string;
  grand_total: string;
  currency: string;
  notes: string | null;
  hand_exchange?: boolean;
  status: "PENDING" | "PAID" | "SHIPPED" | "CANCELLED";
  paid_at: string | null;
  shipped_at: string | null;
  cancelled_at: string | null;
  admin_notes: string | null;
  created_at: string;
  items: OrderItem[];
}

const STATUS_CHIP: Record<Order["status"], string> = {
  PENDING: "chip-lilac",
  PAID: "chip-mint",
  SHIPPED: "chip-sky",
  CANCELLED: "chip-pink",
};

const STATUS_LABEL: Record<Order["status"], string> = {
  PENDING: "In attesa",
  PAID: "Pagato",
  SHIPPED: "Spedito",
  CANCELLED: "Annullato",
};

/** Costruisce un URL wa.me per un numero italiano (best-effort).
 *  Tornare null se il formato non sembra italiano, così non promettiamo
 *  WhatsApp dove magari non esiste. */
function whatsappUrl(phone: string | null, text?: string): string | null {
  if (!phone) return null;
  let digits = phone.replace(/\D/g, "");
  if (digits.startsWith("00")) digits = digits.slice(2);
  if (digits.length === 10 && digits.startsWith("3")) digits = "39" + digits;
  if (digits.length !== 12 || !digits.startsWith("39")) return null;
  const base = `https://wa.me/${digits}`;
  return text ? `${base}?text=${encodeURIComponent(text)}` : base;
}

function fmtDateTime(s: string): string {
  try {
    return new Date(s).toLocaleString("it-IT", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return s;
  }
}

export default function AdminOrdersPage() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<number | null>(null);
  const [filterStatus, setFilterStatus] = useState<string>("");
  const [expandedId, setExpandedId] = useState<number | null>(null);

  async function reload() {
    setLoading(true);
    setError(null);
    try {
      const qs = filterStatus ? `?status=${filterStatus}` : "";
      const list = await adminApi.get<Order[]>(`/api/orders/${qs}`);
      setOrders(list);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterStatus]);

  async function setStatus(id: number, status: Order["status"]) {
    setBusy(id);
    try {
      const updated = await adminApi.patch<Order>(`/api/orders/${id}`, {
        status,
      });
      setOrders((prev) => prev.map((o) => (o.id === id ? updated : o)));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(null);
    }
  }

  async function deleteOrder(id: number) {
    if (!confirm(`Eliminare definitivamente l'ordine #${id}?`)) return;
    setBusy(id);
    try {
      await adminApi.delete(`/api/orders/${id}`);
      setOrders((prev) => prev.filter((o) => o.id !== id));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(null);
    }
  }

  return (
    <AdminShell>
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-3 mb-6">
        <div>
          <h1 className="display text-3xl text-ink">📥 Ordini</h1>
          <p className="text-ink-soft text-sm mt-1">
            Ordini ricevuti dal sito (PayPal manuale). Quando ricevi il
            pagamento PayPal, marca l&apos;ordine come <strong>Pagato</strong>.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <label className="text-xs text-ink-soft">Filtro:</label>
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="input text-sm"
          >
            <option value="">Tutti</option>
            <option value="PENDING">In attesa</option>
            <option value="PAID">Pagati</option>
            <option value="SHIPPED">Spediti</option>
            <option value="CANCELLED">Annullati</option>
          </select>
        </div>
      </div>

      {error && <p className="text-pink-deep mb-4">⚠ {error}</p>}
      {loading ? (
        <p className="text-ink-soft">Caricamento…</p>
      ) : orders.length === 0 ? (
        <div className="card p-8 text-center text-ink-soft">
          Nessun ordine{filterStatus ? ` con stato ${filterStatus}` : ""}.
        </div>
      ) : (
        <div className="space-y-3">
          {orders.map((o) => {
            const expanded = expandedId === o.id;
            return (
              <div key={o.id} className="card p-4 sm:p-5">
                <div className="flex flex-col sm:flex-row sm:items-center gap-3 sm:gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex flex-wrap items-center gap-2 mb-1">
                      <span className={`chip ${STATUS_CHIP[o.status]} text-[11px]`}>
                        {STATUS_LABEL[o.status]}
                      </span>
                      {o.hand_exchange && (
                        <span className="chip chip-lilac text-[11px]">
                          🤝 Consegna a mano
                        </span>
                      )}
                      <span className="text-ink-soft text-xs">
                        #{o.id} · {fmtDateTime(o.created_at)}
                      </span>
                    </div>
                    <p className="text-ink font-semibold">{o.buyer_name}</p>
                    <p className="text-ink-soft text-sm">
                      {o.buyer_email}
                      {o.buyer_phone && ` · ${o.buyer_phone}`}
                    </p>
                    {/* Bottoni contatto rapido */}
                    <div className="flex flex-wrap gap-1.5 mt-2">
                      <a
                        href={`mailto:${o.buyer_email}?subject=${encodeURIComponent(
                          `Ordine #${o.id} NerdNostalgia`,
                        )}`}
                        className="inline-flex items-center gap-1 text-[11px] font-semibold rounded-full bg-lilac-deep/15 text-lilac-deep px-2.5 py-1 hover:bg-lilac-deep hover:text-white transition-colors"
                        aria-label="Invia email al compratore"
                      >
                        ✉️ Email
                      </a>
                      {o.buyer_phone && (
                        <a
                          href={`tel:${o.buyer_phone}`}
                          className="inline-flex items-center gap-1 text-[11px] font-semibold rounded-full bg-mint-deep/15 text-mint-deep px-2.5 py-1 hover:bg-mint-deep hover:text-white transition-colors"
                          aria-label="Chiama il compratore"
                        >
                          📞 Chiama
                        </a>
                      )}
                      {(() => {
                        const wa = whatsappUrl(
                          o.buyer_phone,
                          `Ciao ${o.buyer_name.split(" ")[0]}, ti scrivo da NerdNostalgia per il tuo ordine #${o.id}.`,
                        );
                        if (!wa) return null;
                        return (
                          <a
                            href={wa}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 text-[11px] font-semibold rounded-full bg-[#25D366]/15 text-[#128c4f] px-2.5 py-1 hover:bg-[#25D366] hover:text-white transition-colors"
                            aria-label="Scrivi su WhatsApp"
                          >
                            💬 WhatsApp
                          </a>
                        );
                      })()}
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="display text-2xl text-pink-deep">
                      € {Number(o.grand_total).toFixed(2)}
                    </p>
                    <p className="text-xs text-ink-soft">
                      {o.items.length}{" "}
                      {o.items.length === 1 ? "articolo" : "articoli"}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => setExpandedId(expanded ? null : o.id)}
                    className="btn btn-ghost text-sm flex-shrink-0"
                  >
                    {expanded ? "Chiudi ↑" : "Dettagli ↓"}
                  </button>
                </div>

                {expanded && (
                  <div className="mt-5 pt-5 border-t border-ink/10 grid md:grid-cols-2 gap-5">
                    <div>
                      <h3 className="text-xs font-bold uppercase tracking-wider text-ink-soft mb-2">
                        Articoli
                      </h3>
                      <ul className="text-sm space-y-1">
                        {o.items.map((it) => (
                          <li
                            key={it.id}
                            className="flex justify-between gap-2"
                          >
                            <span>
                              {it.article_id ? (
                                <Link
                                  href={`/admin/articles/${it.article_id}`}
                                  className="text-lilac-deep hover:underline"
                                >
                                  {it.title_snapshot}
                                </Link>
                              ) : (
                                <span className="text-ink-soft italic">
                                  {it.title_snapshot} (eliminato)
                                </span>
                              )}{" "}
                              × {it.quantity}
                            </span>
                            <span className="tabular-nums text-ink-soft">
                              € {Number(it.price_snapshot).toFixed(2)}
                            </span>
                          </li>
                        ))}
                      </ul>
                      <dl className="mt-3 text-sm space-y-1 border-t border-ink/10 pt-3">
                        <div className="flex justify-between">
                          <dt className="text-ink-soft">Subtotale</dt>
                          <dd>€ {Number(o.subtotal).toFixed(2)}</dd>
                        </div>
                        <div className="flex justify-between">
                          <dt className="text-ink-soft">
                            Spedizione
                            {o.hand_exchange && (
                              <span className="ml-1 text-[10px] text-lilac-deep">
                                (consegna a mano)
                              </span>
                            )}
                          </dt>
                          <dd>€ {Number(o.shipping_total).toFixed(2)}</dd>
                        </div>
                        <div className="flex justify-between font-bold text-pink-deep pt-1 border-t border-ink/10">
                          <dt>Totale</dt>
                          <dd>
                            € {Number(o.grand_total).toFixed(2)} {o.currency}
                          </dd>
                        </div>
                      </dl>
                    </div>

                    <div>
                      <h3 className="text-xs font-bold uppercase tracking-wider text-ink-soft mb-2">
                        Spedizione
                      </h3>
                      <address className="text-sm not-italic bg-pink-soft/20 rounded-lg p-3 mb-3">
                        {o.buyer_name}<br />
                        {o.ship_street}<br />
                        {o.ship_postal_code} {o.ship_city}
                        {o.ship_province && ` (${o.ship_province})`}<br />
                        {o.ship_country}
                      </address>

                      {o.notes && (
                        <>
                          <h3 className="text-xs font-bold uppercase tracking-wider text-ink-soft mb-2">
                            Note compratore
                          </h3>
                          <p className="text-sm bg-ink/5 rounded-lg p-3 mb-3 whitespace-pre-line">
                            {o.notes}
                          </p>
                        </>
                      )}

                      <div className="flex flex-wrap gap-2">
                        {o.status === "PENDING" && (
                          <button
                            type="button"
                            onClick={() => setStatus(o.id, "PAID")}
                            disabled={busy === o.id}
                            className="btn btn-primary text-sm"
                          >
                            ✓ Pagato
                          </button>
                        )}
                        {o.status === "PAID" && (
                          <button
                            type="button"
                            onClick={() => setStatus(o.id, "SHIPPED")}
                            disabled={busy === o.id}
                            className="btn btn-primary text-sm"
                          >
                            📦 Spedito
                          </button>
                        )}
                        {(o.status === "PENDING" || o.status === "PAID") && (
                          <button
                            type="button"
                            onClick={() => setStatus(o.id, "CANCELLED")}
                            disabled={busy === o.id}
                            className="btn btn-ghost text-sm"
                          >
                            Annulla
                          </button>
                        )}
                        <button
                          type="button"
                          onClick={() => deleteOrder(o.id)}
                          disabled={busy === o.id}
                          className="btn btn-ghost text-sm ml-auto"
                        >
                          🗑
                        </button>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      <style>{`
        .input {
          padding: 0.4rem 0.7rem;
          border: 1px solid rgba(61, 42, 92, 0.15);
          border-radius: 12px;
          background: #fffaf3;
          color: #3d2a5c;
          font-family: inherit;
          outline: none;
        }
      `}</style>
    </AdminShell>
  );
}
