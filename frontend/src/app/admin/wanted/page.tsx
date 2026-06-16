"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { AdminShell } from "@/components/admin/AdminShell";
import { Sortable } from "@/components/admin/Sortable";
import { adminApi } from "@/lib/admin-api";
import { formatMaxPrice } from "@/lib/api";
import type { WantedItem, WantedListResponse, WantedStatus } from "@/lib/types";

const STATUS_OPTIONS = ["", "ACTIVE", "FULFILLED", "CLOSED"] as const;

const STATUS_CHIP: Record<WantedStatus, string> = {
  ACTIVE: "chip-mint",
  FULFILLED: "chip-pink",
  CLOSED: "chip-sky",
};

function WantedListContent() {
  const search = useSearchParams();
  const [status, setStatus] = useState<string>(search.get("status") ?? "");
  const [items, setItems] = useState<WantedItem[]>([]);
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
        const data = await adminApi.get<WantedListResponse>(`/api/wanted/?${qs}`);
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

  return (
    <AdminShell>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="display text-3xl text-ink">Cerco/Compro</h1>
          <p className="text-ink-soft mt-1">{total} totali</p>
        </div>
        <Link href="/admin/wanted/new" className="btn btn-primary">
          ➕ Nuovo
        </Link>
      </div>

      <div className="flex gap-2 mb-6 flex-wrap">
        {STATUS_OPTIONS.map((s) => (
          <button
            key={s || "all"}
            type="button"
            onClick={() => setStatus(s)}
            className={`chip cursor-pointer ${status === s ? "chip-pink" : ""}`}
          >
            {s || "Tutti"}
          </button>
        ))}
      </div>

      {error && <p className="text-pink-deep">⚠ {error}</p>}
      {loading && <p className="text-ink-soft">Caricamento…</p>}
      {!loading && items.length === 0 && (
        <div className="card p-10 text-center">
          <p className="text-ink-soft">Nessun wanted.</p>
        </div>
      )}

      {items.length > 1 && (
        <p className="text-xs text-ink-soft mb-3">
          Trascina la maniglia ⋮⋮ per riordinare per priorità (la prima ha
          priority più alta).
        </p>
      )}

      <Sortable
        items={items}
        getKey={(w) => String(w.id)}
        onReorder={async (next) => {
          setItems(next);
          try {
            await adminApi.post("/api/wanted/reorder", {
              order: next.map((w) => w.id),
            });
          } catch (err) {
            setError(err instanceof Error ? err.message : String(err));
          }
        }}
        strategy="vertical"
        className="space-y-3"
        renderItem={(w, _idx, { listeners, attributes, isDragging }) => (
          <div
            className={
              "card p-3 sm:p-4 flex items-center gap-3 sm:gap-4 transition-all " +
              (isDragging ? "ring-2 ring-lilac-deep/40 " : "")
            }
          >
            <button
              type="button"
              {...attributes}
              {...listeners}
              className="text-ink-soft/50 text-xl cursor-grab active:cursor-grabbing select-none px-1 hover:text-ink"
              aria-label="Trascina per riordinare"
              title="Trascina per riordinare"
            >
              ⋮⋮
            </button>
            <Link
              href={`/admin/wanted/${w.id}`}
              className="flex items-center gap-3 sm:gap-4 flex-1 min-w-0"
            >
              <span className="display text-lg sm:text-xl text-ink-soft w-8 sm:w-10 text-right flex-shrink-0">
                {w.priority}
              </span>
              <div className="flex-1 min-w-0">
                <p className="display text-base text-ink truncate">{w.title}</p>
                <p className="text-xs text-ink-soft truncate">
                  #{w.id} · {w.category?.name ?? "—"}
                  {w.preferred_condition ? ` · ${w.preferred_condition}` : ""}
                </p>
              </div>
              <span
                className={`chip ${STATUS_CHIP[w.status]} hidden sm:inline-flex`}
              >
                {w.status}
              </span>
              <span className="display text-base sm:text-lg text-pink-deep w-24 sm:w-32 text-right flex-shrink-0">
                {formatMaxPrice(w) ?? "—"}
              </span>
            </Link>
          </div>
        )}
      />
    </AdminShell>
  );
}

export default function AdminWantedListPage() {
  return (
    <Suspense fallback={<AdminShell><p className="text-ink-soft">Caricamento…</p></AdminShell>}>
      <WantedListContent />
    </Suspense>
  );
}
