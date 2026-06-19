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
  const [query, setQuery] = useState<string>(search.get("search") ?? "");
  const [debouncedQuery, setDebouncedQuery] = useState<string>(query);
  const [items, setItems] = useState<Article[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Debounce della query (300ms)
  useEffect(() => {
    const t = setTimeout(() => setDebouncedQuery(query.trim()), 300);
    return () => clearTimeout(t);
  }, [query]);

  // Filtri client-side: marca, modello, sku, categoria
  const [extraFiltered, setExtraFiltered] = useState<Article[]>([]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const qs = new URLSearchParams({ limit: "100" });
        if (status) qs.set("status", status);
        if (debouncedQuery) qs.set("search", debouncedQuery);
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
  }, [status, debouncedQuery]);

  // Filtro ulteriore client-side sui campi che il backend non cerca
  // (brand, model, sku, category name): l'utente può digitare anche queste.
  useEffect(() => {
    if (!debouncedQuery) {
      setExtraFiltered(items);
      return;
    }
    const q = debouncedQuery.toLowerCase();
    const filtered = items.filter((a) => {
      const hay = [
        a.title,
        a.description,
        a.brand,
        a.model,
        a.sku,
        a.category?.name,
        a.parent_category?.name,
        a.card_collection,
        a.lotto,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      return hay.includes(q);
    });
    setExtraFiltered(filtered);
  }, [items, debouncedQuery]);

  const visible = debouncedQuery ? extraFiltered : items;
  const reorderEnabled = !debouncedQuery && !status;

  return (
    <AdminShell>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="display text-3xl text-ink">Articoli</h1>
          <p className="text-ink-soft mt-1 text-sm">
            {debouncedQuery
              ? `${visible.length} risultat${visible.length === 1 ? "o" : "i"} per "${debouncedQuery}"`
              : `${total} totali`}
          </p>
        </div>
        <Link href="/admin/articles/new" className="btn btn-primary">
          ➕ Nuovo
        </Link>
      </div>

      {/* Search */}
      <div className="relative mb-4">
        <span className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-soft text-lg pointer-events-none">
          🔎
        </span>
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Cerca per titolo, descrizione, marca, modello, SKU, categoria…"
          className="search-input pl-10 w-full"
        />
        {query && (
          <button
            type="button"
            onClick={() => setQuery("")}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-ink-soft hover:text-ink text-sm"
            aria-label="Azzera ricerca"
          >
            ✕
          </button>
        )}
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

      {!loading && visible.length === 0 && (
        <div className="card p-10 text-center">
          <p className="text-ink-soft">
            {debouncedQuery
              ? `Nessun articolo che corrisponde a "${debouncedQuery}".`
              : "Nessun articolo trovato."}
          </p>
        </div>
      )}

      {reorderEnabled && visible.length > 1 && (
        <p className="text-xs text-ink-soft mb-3">
          Trascina la maniglia ⋮⋮ per riordinare il catalogo.
        </p>
      )}

      {reorderEnabled ? (
        <Sortable
          items={visible}
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
            <ArticleRow article={a} isDragging={isDragging} dragProps={{ listeners, attributes }} />
          )}
        />
      ) : (
        <div className="space-y-3">
          {visible.map((a) => (
            <ArticleRow key={a.id} article={a} />
          ))}
        </div>
      )}

      <style>{`
        .search-input {
          padding: 0.7rem 2.5rem;
          border-radius: 16px;
          border: 1px solid rgba(61, 42, 92, 0.12);
          background: rgba(255, 255, 255, 0.78);
          backdrop-filter: blur(8px);
          color: #3d2a5c;
          font-family: "Manrope", sans-serif;
          font-size: 0.95rem;
          outline: none;
          transition: box-shadow 150ms, border-color 150ms;
        }
        .search-input:focus {
          border-color: var(--lilac-deep);
          box-shadow: 0 0 0 3px rgba(168, 144, 216, 0.25);
        }
      `}</style>
    </AdminShell>
  );
}

interface DragProps {
  listeners?: React.HTMLAttributes<HTMLButtonElement>;
  attributes?: React.HTMLAttributes<HTMLButtonElement>;
}

function ArticleRow({
  article: a,
  isDragging,
  dragProps,
}: {
  article: Article;
  isDragging?: boolean;
  dragProps?: DragProps;
}) {
  return (
    <div
      className={
        "card p-3 sm:p-4 flex items-center gap-3 sm:gap-4 transition-all " +
        (isDragging ? "ring-2 ring-lilac-deep/40 " : "")
      }
    >
      {dragProps && (
        <button
          type="button"
          {...dragProps.attributes}
          {...dragProps.listeners}
          className="text-ink-soft/50 text-xl cursor-grab active:cursor-grabbing select-none px-1 hover:text-ink"
          aria-label="Trascina per riordinare"
          title="Trascina per riordinare"
        >
          ⋮⋮
        </button>
      )}
      <Link
        href={`/admin/articles/${a.id}`}
        className="flex items-center gap-3 sm:gap-4 flex-1 min-w-0"
      >
        <div className="w-14 h-14 sm:w-16 sm:h-16 rounded-2xl ring-1 ring-ink/8 overflow-hidden bg-white/60 flex-shrink-0">
          {a.images?.[0] && (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={a.images[0]} alt="" className="w-full h-full object-cover" loading="lazy" decoding="async" />
          )}
        </div>
        <div className="flex-1 min-w-0">
          <p className="display text-base text-ink truncate">{a.title}</p>
          <p className="text-xs text-ink-soft truncate">
            #{a.id} · {a.category?.name ?? "—"} · {a.condition}
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
  );
}

export default function AdminArticlesPage() {
  return (
    <Suspense fallback={<AdminShell><p className="text-ink-soft">Caricamento…</p></AdminShell>}>
      <ArticlesListContent />
    </Suspense>
  );
}
