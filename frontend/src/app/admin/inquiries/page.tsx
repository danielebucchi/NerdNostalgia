"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { AdminShell } from "@/components/admin/AdminShell";
import { SwipeRow } from "@/components/admin/SwipeRow";
import { adminApi } from "@/lib/admin-api";
import type { Inquiry, InquiryStatus } from "@/lib/types";

const STATUS_OPTIONS = ["", "NEW", "READ", "REPLIED", "CLOSED"] as const;

const STATUS_CHIP: Record<InquiryStatus, string> = {
  NEW: "chip-pink",
  READ: "chip-sky",
  REPLIED: "chip-mint",
  CLOSED: "chip-lilac",
};

interface InquiryList {
  total: number;
  items: Inquiry[];
}

function InquiriesListContent() {
  const search = useSearchParams();
  const [status, setStatus] = useState<string>(search.get("status") ?? "");
  const [items, setItems] = useState<Inquiry[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const qs = new URLSearchParams({ limit: "100" });
        if (status) qs.set("status", status);
        const data = await adminApi.get<InquiryList>(`/api/inquiries/?${qs}`);
        if (!cancelled) {
          setItems(data.items);
          setTotal(data.total);
        }
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [status]);

  async function swipeReplied(i: Inquiry) {
    if (i.status === "REPLIED") return;
    try {
      await adminApi.patch(`/api/inquiries/${i.id}`, { status: "REPLIED" });
      setItems((curr) =>
        curr.map((x) => (x.id === i.id ? { ...x, status: "REPLIED" as InquiryStatus } : x)),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  async function swipeDelete(i: Inquiry) {
    if (!confirm(`Eliminare la richiesta di ${i.name}?`)) return;
    try {
      await adminApi.delete(`/api/inquiries/${i.id}`);
      setItems((curr) => curr.filter((x) => x.id !== i.id));
      setTotal((t) => Math.max(0, t - 1));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  return (
    <AdminShell>
      <h1 className="display text-3xl text-ink mb-1">Richieste</h1>
      <p className="text-ink-soft mb-6">{total} totali</p>

      <div className="flex gap-2 mb-6 flex-wrap">
        {STATUS_OPTIONS.map((s) => (
          <button
            key={s || "all"}
            type="button"
            onClick={() => setStatus(s)}
            className={`chip cursor-pointer ${status === s ? "chip-pink" : ""}`}
          >
            {s || "Tutte"}
          </button>
        ))}
      </div>

      {error && <p className="text-pink-deep mb-3">⚠ {error}</p>}
      {loading && <p className="text-ink-soft">Caricamento…</p>}
      {!loading && items.length === 0 && (
        <div className="card p-10 text-center">
          <p className="text-ink-soft">Nessuna richiesta.</p>
        </div>
      )}

      {items.length > 0 && (
        <p className="text-[11px] text-ink-soft mb-2 sm:hidden">
          ✅ swipe destra risposta · sinistra elimina 🗑
        </p>
      )}
      <div className="space-y-3">
        {items.map((i) => (
          <SwipeRow
            key={i.id}
            rightAction={
              i.status !== "REPLIED"
                ? { label: "Risposta", icon: "✅", onTrigger: () => swipeReplied(i) }
                : undefined
            }
            leftAction={{ label: "Elimina", icon: "🗑", onTrigger: () => swipeDelete(i) }}
          >
          <Link
            href={`/admin/inquiries/${i.id}`}
            className="card card-clickable p-4 flex items-start gap-4"
          >
            <span className={`chip ${STATUS_CHIP[i.status]} flex-shrink-0`}>{i.status}</span>
            <div className="flex-1 min-w-0">
              <p className="display text-base text-ink truncate">
                {i.subject ?? "Senza oggetto"}
              </p>
              <p className="text-xs text-ink-soft truncate">
                #{i.id} · {i.name} &lt;{i.email}&gt; · {new Date(i.created_at).toLocaleString("it-IT")}
              </p>
              <p className="text-sm text-ink mt-1 line-clamp-2">{i.message}</p>
            </div>
            {i.article_id && (
              <span className="chip chip-sky flex-shrink-0">
                articolo #{i.article_id}
              </span>
            )}
          </Link>
          </SwipeRow>
        ))}
      </div>
    </AdminShell>
  );
}

export default function AdminInquiriesPage() {
  return (
    <Suspense fallback={<AdminShell><p className="text-ink-soft">Caricamento…</p></AdminShell>}>
      <InquiriesListContent />
    </Suspense>
  );
}
