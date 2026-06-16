"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArticleCard } from "@/components/ArticleCard";
import { getArticle } from "@/lib/api";
import { useWishlist } from "@/lib/useWishlist";
import type { Article } from "@/lib/types";

export default function WishlistPage() {
  const { ids, clear, hydrated, count } = useWishlist();
  const [articles, setArticles] = useState<Article[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!hydrated) return;
    if (ids.length === 0) {
      setArticles([]);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    (async () => {
      try {
        const results = await Promise.all(ids.map((id) => getArticle(id).catch(() => null)));
        if (!cancelled) {
          setArticles(results.filter((a): a is Article => a != null));
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
  }, [ids, hydrated]);

  return (
    <div>
      <div className="flex items-end justify-between mb-6 gap-3 flex-wrap">
        <div>
          <h1 className="display text-3xl sm:text-4xl text-ink">I tuoi preferiti</h1>
          <p className="text-ink-soft mt-1 text-sm">
            {hydrated && count > 0
              ? `${count} articol${count === 1 ? "o" : "i"} salvati nel tuo browser.`
              : "Aggiungi pezzi al cuore ♥ per ritrovarli qui."}
          </p>
        </div>
        {hydrated && count > 0 && (
          <button
            type="button"
            onClick={() => {
              if (confirm("Vuoi davvero svuotare la lista dei preferiti?")) {
                clear();
              }
            }}
            className="btn btn-ghost text-sm"
          >
            ✕ Svuota lista
          </button>
        )}
      </div>

      {!hydrated || loading ? (
        <p className="text-ink-soft">Caricamento…</p>
      ) : error ? (
        <p className="text-pink-deep font-semibold">⚠ {error}</p>
      ) : articles.length === 0 ? (
        <div className="card p-10 text-center">
          <p className="display text-2xl text-ink mb-2">Lista vuota</p>
          <p className="text-ink-soft text-sm mb-6">
            Non hai ancora salvato nessun articolo. Vai al catalogo e clicca il
            cuore ♥ sui pezzi che ti interessano.
          </p>
          <Link href="/" className="btn btn-primary">
            Vai al catalogo
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5 sm:gap-6">
          {articles.map((article) => (
            <ArticleCard key={article.id} article={article} />
          ))}
        </div>
      )}
    </div>
  );
}
