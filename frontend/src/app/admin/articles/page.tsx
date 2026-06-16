"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { AdminShell } from "@/components/admin/AdminShell";
import { Sortable } from "@/components/admin/Sortable";
import { adminApi } from "@/lib/admin-api";
import { formatPrice } from "@/lib/api";
import type { Article, ArticleListResponse } from "@/lib/types";

const STATUS_OPTIONS = ["", "DRAFT", "PUBLISHED", "SOLD", "ARCHIVED"] as const;

const STATUS_CHIP: Record<string, string> = {
  DRAFT: "chip-lilac",
  PUBLISHED: "chip-mint",
  SOLD: "chip-pink",
  ARCHIVED: "chip-sky",
};

function ArticlesListContent() {
  const search = useSearchParams();
  const [status, setStatus] = useState<string>(search.get("status") ?? "");
  const [items, setItems] = useState<Article[]>([]);
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
        const data = await adminApi.get<ArticleListResponse>(`/api/articles/?${qs}`);
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
          <h1 className="display text-3xl text-ink">Articoli</h1>
          <p className="text-ink-soft mt-1">{total} totali</p>
        </div>
        <Link href="/admin/articles/new" className="btn btn-primary">
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
          <p className="text-ink-soft">Nessun articolo trovato.</p>
        </div>
      )}

      {items.length > 1 && (
        <p className="text-xs text-ink-soft mb-3">
          Trascina la maniglia ⋮⋮ per riordinare il catalogo.
        </p>
      )}

      <Sortable
        items={items}
        getKey={(a) => String(a.id)}
        onReorder={async (next) => {
          setItems(next);
          try {
            await adminApi.post("/api/articles/reorder", {
              order: next.map((a) => a.id),
            });
          } catch (err) {
            setError(err instanceof Error ? err.message : String(err));
          }
        }}
        strategy="vertical"
        className="space-y-3"
        renderItem={(a, _idx, { listeners, attributes, isDragging }) => (
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
              href={`/admin/articles/${a.id}`}
              className="flex items-center gap-3 sm:gap-4 flex-1 min-w-0"
            >
              <div className="w-14 h-14 sm:w-16 sm:h-16 rounded-2xl ring-1 ring-ink/8 overflow-hidden bg-white/60 flex-shrink-0">
                {a.images?.[0] && (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={a.images[0]}
                    alt=""
                    className="w-full h-full object-cover"
                  />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <p className="display text-base text-ink truncate">{a.title}</p>
                <p className="text-xs text-ink-soft truncate">
                  #{a.id} · {a.category ?? "—"} · {a.condition}
                  {a.sku ? ` · ${a.sku}` : ""}
                </p>
              </div>
              <span
                className={`chip ${STATUS_CHIP[a.status] ?? ""} hidden sm:inline-flex`}
              >
                {a.status}
              </span>
              <span className="display text-lg text-pink-deep w-20 sm:w-24 text-right flex-shrink-0">
                {formatPrice(a)}
              </span>
            </Link>
          </div>
        )}
      />
    </AdminShell>
  );
}

export default function AdminArticlesPage() {
  return (
    <Suspense fallback={<AdminShell><p className="text-ink-soft">Caricamento…</p></AdminShell>}>
      <ArticlesListContent />
    </Suspense>
  );
}
