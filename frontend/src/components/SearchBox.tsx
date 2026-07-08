"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { PUBLIC_API_BASE, formatPrice } from "@/lib/api";
import type { Article } from "@/lib/types";

/**
 * Ricerca istantanea nell'header: digiti e (debounce 250ms) appare un
 * dropdown con i primi 5 risultati (thumb + titolo + prezzo). Click →
 * pagina articolo. Enter → catalogo homepage con la ricerca precompilata
 * (?search=... letto da CatalogSection).
 */

function thumbFor(url: string | undefined): string | null {
  if (!url) return null;
  if (url.endsWith(".webp") && !url.endsWith(".thumb.webp")) {
    return url.slice(0, -".webp".length) + ".thumb.webp";
  }
  return url;
}

export function SearchBox({ className = "" }: { className?: string }) {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Article[]>([]);
  const [total, setTotal] = useState(0);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const boxRef = useRef<HTMLDivElement>(null);

  // Debounced fetch
  useEffect(() => {
    const q = query.trim();
    if (q.length < 2) {
      setResults([]);
      setTotal(0);
      setOpen(false);
      return;
    }
    setLoading(true);
    const handle = setTimeout(() => {
      fetch(
        `${PUBLIC_API_BASE}/api/articles/?status=PUBLISHED&limit=5&search=${encodeURIComponent(q)}`,
      )
        .then((r) => (r.ok ? r.json() : null))
        .then((data: { items: Article[]; total: number } | null) => {
          if (!data) return;
          setResults(data.items);
          setTotal(data.total);
          setOpen(true);
        })
        .catch(() => {})
        .finally(() => setLoading(false));
    }, 250);
    return () => clearTimeout(handle);
  }, [query]);

  // Chiudi al click fuori
  useEffect(() => {
    function onDown(e: MouseEvent) {
      if (boxRef.current && !boxRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", onDown);
    return () => document.removeEventListener("mousedown", onDown);
  }, []);

  function goToCatalog() {
    const q = query.trim();
    if (!q) return;
    setOpen(false);
    router.push(`/?search=${encodeURIComponent(q)}#catalogo`);
    // Se siamo GIA' sulla home, il push cambia solo la query e il client
    // tree non rimonta: notifica CatalogSection direttamente.
    window.dispatchEvent(new CustomEvent("nn:catalog-search", { detail: q }));
  }

  return (
    <div ref={boxRef} className={`relative ${className}`}>
      <div className="relative">
        <span
          aria-hidden="true"
          className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-soft/60 text-sm"
        >
          🔎
        </span>
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => {
            if (results.length > 0) setOpen(true);
          }}
          onKeyDown={(e) => {
            if (e.key === "Enter") goToCatalog();
            if (e.key === "Escape") setOpen(false);
          }}
          placeholder="Cerca nel catalogo…"
          aria-label="Cerca nel catalogo"
          className="w-full pl-9 pr-3 py-2 rounded-full border border-ink/12 bg-white/85 text-sm text-ink placeholder:text-ink-soft/60 outline-none focus:ring-2 focus:ring-pink/60 focus:border-pink-deep/40 transition-shadow"
        />
      </div>

      {open && (
        <div className="absolute left-0 right-0 top-full mt-2 z-50 card p-2 shadow-hover max-h-[70vh] overflow-y-auto">
          {results.length === 0 ? (
            <p className="text-sm text-ink-soft px-3 py-2">
              {loading ? "Cerco…" : "Nessun risultato"}
            </p>
          ) : (
            <>
              <ul>
                {results.map((a) => {
                  const thumb = thumbFor(a.images?.[0]);
                  return (
                    <li key={a.id}>
                      <Link
                        href={`/articles/${a.id}`}
                        onClick={() => setOpen(false)}
                        className="flex items-center gap-3 px-2 py-1.5 rounded-lg hover:bg-pink-soft/40 transition-colors"
                      >
                        <span className="w-10 h-10 rounded-md overflow-hidden bg-ink/5 ring-1 ring-ink/10 flex-shrink-0 flex items-center justify-center">
                          {thumb ? (
                            // eslint-disable-next-line @next/next/no-img-element
                            <img
                              src={thumb}
                              alt=""
                              loading="lazy"
                              className="w-full h-full object-cover"
                            />
                          ) : (
                            <span className="text-lg" aria-hidden="true">🎮</span>
                          )}
                        </span>
                        <span className="min-w-0 flex-1">
                          <span className="block text-sm text-ink font-semibold truncate">
                            {a.title}
                          </span>
                          <span className="block text-xs text-ink-soft">
                            {formatPrice(a)}
                          </span>
                        </span>
                      </Link>
                    </li>
                  );
                })}
              </ul>
              {total > results.length && (
                <button
                  type="button"
                  onClick={goToCatalog}
                  className="w-full text-center text-xs font-bold text-lilac-deep hover:underline px-3 py-2"
                >
                  Vedi tutti i {total} risultati →
                </button>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
