"use client";

import { useEffect, useState } from "react";
import { AdminShell } from "@/components/admin/AdminShell";
import { adminApi } from "@/lib/admin-api";

interface Review {
  id: number;
  order_id: number;
  author_name: string;
  rating: number;
  body: string | null;
  reply: string | null;
  status: "PENDING" | "APPROVED" | "REJECTED";
  created_at: string;
  moderated_at: string | null;
}

const CHIP: Record<Review["status"], string> = {
  PENDING: "chip-star",
  APPROVED: "chip-mint",
  REJECTED: "chip-pink",
};
const LABEL: Record<Review["status"], string> = {
  PENDING: "Da leggere",
  APPROVED: "Pubblicata",
  REJECTED: "Rifiutata",
};

export default function AdminRecensioniPage() {
  const [items, setItems] = useState<Review[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<number | null>(null);
  const [replies, setReplies] = useState<Record<number, string>>({});

  async function reload() {
    setLoading(true);
    try {
      setItems(await adminApi.get<Review[]>("/api/reviews/admin"));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    reload();
  }, []);

  async function moderate(id: number, payload: Record<string, unknown>) {
    setBusy(id);
    setError(null);
    try {
      const updated = await adminApi.patch<Review>(`/api/reviews/${id}`, payload);
      setItems((prev) => prev.map((r) => (r.id === id ? updated : r)));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(null);
    }
  }

  const daLeggere = items.filter((r) => r.status === "PENDING");

  return (
    <AdminShell>
      <h1 className="display text-3xl text-ink mb-1">Recensioni</h1>
      <p className="text-ink-soft mb-6 text-sm">
        Niente va online da solo: quello che pubblichi qui compare sul sito con
        il nome di chi l&apos;ha scritto.
        {daLeggere.length > 0 && (
          <strong className="text-pink-deep">
            {" "}
            {daLeggere.length} da leggere.
          </strong>
        )}
      </p>

      {error && <div className="card p-4 mb-4 text-pink-deep">⚠ {error}</div>}
      {loading && <p className="text-ink-soft">Caricamento…</p>}
      {!loading && items.length === 0 && (
        <div className="card p-8 text-center text-ink-soft">
          Ancora nessuna recensione. Arrivano quando segni un ordine come
          completato: al cliente parte l&apos;invito via email.
        </div>
      )}

      <div className="space-y-3">
        {items.map((r) => (
          <div key={r.id} className="card p-4">
            <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
              <div>
                <span className="text-star-deep text-lg tracking-tight">
                  {"★".repeat(r.rating)}
                  <span className="text-ink/20">{"★".repeat(5 - r.rating)}</span>
                </span>
                <span className="display text-base text-ink ml-2">
                  {r.author_name}
                </span>
                <span className="text-xs text-ink-soft ml-2">
                  ordine #{r.order_id}
                </span>
              </div>
              <span className={`chip ${CHIP[r.status]} text-[11px]`}>
                {LABEL[r.status]}
              </span>
            </div>

            {r.body && (
              <p className="text-sm text-ink bg-ink/4 rounded-xl p-3 mb-3 leading-relaxed">
                {r.body}
              </p>
            )}

            <label className="block mb-3">
              <span className="text-[11px] text-ink-soft">
                La tua risposta pubblica (facoltativa)
              </span>
              <input
                type="text"
                placeholder="Grazie!…"
                value={replies[r.id] ?? r.reply ?? ""}
                onChange={(e) =>
                  setReplies((p) => ({ ...p, [r.id]: e.target.value }))
                }
                className="input mt-0.5"
              />
            </label>

            <div className="flex flex-wrap gap-2">
              {r.status !== "APPROVED" && (
                <button
                  type="button"
                  disabled={busy === r.id}
                  onClick={() =>
                    moderate(r.id, {
                      status: "APPROVED",
                      reply: replies[r.id] ?? r.reply ?? "",
                    })
                  }
                  className="btn btn-primary text-sm"
                >
                  ✓ Pubblica
                </button>
              )}
              {r.status !== "REJECTED" && (
                <button
                  type="button"
                  disabled={busy === r.id}
                  onClick={() => moderate(r.id, { status: "REJECTED" })}
                  className="btn btn-ghost text-sm"
                >
                  Rifiuta
                </button>
              )}
              {r.status === "APPROVED" && (replies[r.id] ?? "") !== (r.reply ?? "") && (
                <button
                  type="button"
                  disabled={busy === r.id}
                  onClick={() => moderate(r.id, { reply: replies[r.id] ?? "" })}
                  className="btn btn-ghost text-sm"
                >
                  Salva risposta
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </AdminShell>
  );
}
