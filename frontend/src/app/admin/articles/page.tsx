"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { AdminShell } from "@/components/admin/AdminShell";
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

      <div className="space-y-3">
        {items.map((a) => (
          <Link
            key={a.id}
            href={`/admin/articles/${a.id}`}
            className="card card-clickable p-4 flex items-center gap-4"
          >
            <div className="w-16 h-16 rounded-xl border-2 border-ink/15 overflow-hidden bg-cream flex-shrink-0">
              {a.images?.[0] && (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={a.images[0]} alt="" className="w-full h-full object-cover" />
              )}
            </div>
            <div className="flex-1 min-w-0">
              <p className="display text-base text-ink truncate">{a.title}</p>
              <p className="text-xs text-ink-soft">
                #{a.id} · {a.category ?? "—"} · {a.condition}
                {a.sku ? ` · SKU ${a.sku}` : ""}
              </p>
            </div>
            <span className={`chip ${STATUS_CHIP[a.status] ?? ""}`}>{a.status}</span>
            <span className="display text-lg text-pink-deep w-24 text-right">
              {formatPrice(a)}
            </span>
          </Link>
        ))}
      </div>
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
