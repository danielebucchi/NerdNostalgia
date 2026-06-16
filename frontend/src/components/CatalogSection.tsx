"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { listArticles, type ListArticlesParams } from "@/lib/api";
import { ArticleCard } from "@/components/ArticleCard";
import type { Article, ArticleCondition } from "@/lib/types";

const CONDITION_LABEL: Record<ArticleCondition, string> = {
  NEW: "Nuovo",
  USED: "Usato",
  REFURBISHED: "Revisionato",
  FOR_PARTS: "Per pezzi",
};

interface FilterState {
  search: string;
  category: string | null;
  condition: ArticleCondition | null;
  minPrice: string;
  maxPrice: string;
}

const EMPTY: FilterState = {
  search: "",
  category: null,
  condition: null,
  minPrice: "",
  maxPrice: "",
};

interface Props {
  initialArticles: Article[];
}

export function CatalogSection({ initialArticles }: Props) {
  const [articles, setArticles] = useState<Article[]>(initialArticles);
  const [loading, setLoading] = useState(false);
  const [filters, setFilters] = useState<FilterState>(EMPTY);
  const [mobileOpen, setMobileOpen] = useState(false);

  // Categorie e brand inferiti dagli articoli iniziali (per popolare le pillole)
  const { categories, hasAnyFilter } = useMemo(() => {
    const cats = new Set<string>();
    for (const a of initialArticles) {
      if (a.category) cats.add(a.category);
    }
    return {
      categories: Array.from(cats).sort(),
      hasAnyFilter:
        filters.search !== "" ||
        filters.category !== null ||
        filters.condition !== null ||
        filters.minPrice !== "" ||
        filters.maxPrice !== "",
    };
  }, [initialArticles, filters]);

  // Debounce: aspetta 300ms prima di rifare fetch quando si scrive
  const debounceTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (debounceTimer.current) clearTimeout(debounceTimer.current);
    debounceTimer.current = setTimeout(async () => {
      // Se nessun filtro attivo, usa direttamente gli initial (no refetch)
      if (
        !filters.search &&
        !filters.category &&
        !filters.condition &&
        !filters.minPrice &&
        !filters.maxPrice
      ) {
        setArticles(initialArticles);
        setLoading(false);
        return;
      }
      setLoading(true);
      try {
        const params: ListArticlesParams = {
          status: "PUBLISHED",
          limit: 60,
        };
        if (filters.search) params.search = filters.search;
        if (filters.category) params.category = filters.category;
        if (filters.condition) params.condition = filters.condition;
        if (filters.minPrice) params.min_price = Number(filters.minPrice);
        if (filters.maxPrice) params.max_price = Number(filters.maxPrice);
        const data = await listArticles(params);
        setArticles(data.items);
      } catch {
        setArticles([]);
      } finally {
        setLoading(false);
      }
    }, 300);
    return () => {
      if (debounceTimer.current) clearTimeout(debounceTimer.current);
    };
  }, [filters, initialArticles]);

  function reset() {
    setFilters(EMPTY);
  }

  function update<K extends keyof FilterState>(key: K, value: FilterState[K]) {
    setFilters((f) => ({ ...f, [key]: value }));
  }

  return (
    <>
      <CatalogFilters
        filters={filters}
        categories={categories}
        hasAnyFilter={hasAnyFilter}
        onUpdate={update}
        onReset={reset}
        mobileOpen={mobileOpen}
        onToggleMobile={() => setMobileOpen((v) => !v)}
      />

      {loading && (
        <p className="text-ink-soft text-sm mb-4">Aggiorno il catalogo…</p>
      )}

      {!loading && articles.length === 0 && (
        <div className="card p-10 text-center">
          <p className="display text-xl text-ink mb-2">Nessun articolo</p>
          <p className="text-ink-soft text-sm">
            {hasAnyFilter
              ? "Nessun match con i filtri attivi. Prova ad allargare la ricerca."
              : "Nessun articolo ancora pubblicato."}
          </p>
          {hasAnyFilter && (
            <button type="button" className="btn btn-ghost mt-6" onClick={reset}>
              Azzera filtri
            </button>
          )}
        </div>
      )}

      {articles.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5 sm:gap-6">
          {articles.map((article) => (
            <ArticleCard key={article.id} article={article} />
          ))}
        </div>
      )}
    </>
  );
}

interface FiltersProps {
  filters: FilterState;
  categories: string[];
  hasAnyFilter: boolean;
  onUpdate: <K extends keyof FilterState>(key: K, value: FilterState[K]) => void;
  onReset: () => void;
  mobileOpen: boolean;
  onToggleMobile: () => void;
}

function CatalogFilters({
  filters,
  categories,
  hasAnyFilter,
  onUpdate,
  onReset,
  mobileOpen,
  onToggleMobile,
}: FiltersProps) {
  return (
    <div className="mb-6 sm:mb-8">
      {/* Riga sempre visibile: search + bottone filtri mobile */}
      <div className="flex gap-2 mb-3">
        <div className="relative flex-1">
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-soft text-lg pointer-events-none">
            🔎
          </span>
          <input
            type="search"
            value={filters.search}
            onChange={(e) => onUpdate("search", e.target.value)}
            placeholder="Cerca per titolo, marca, console…"
            className="filter-input pl-10 w-full"
          />
        </div>
        <button
          type="button"
          onClick={onToggleMobile}
          className="btn btn-ghost text-sm sm:hidden whitespace-nowrap"
          aria-expanded={mobileOpen}
        >
          ⚙ Filtri
          {hasAnyFilter && (
            <span className="ml-1 inline-flex items-center justify-center w-5 h-5 rounded-full bg-pink-deep text-white text-[10px] font-bold">
              !
            </span>
          )}
        </button>
        {hasAnyFilter && (
          <button
            type="button"
            onClick={onReset}
            className="btn btn-ghost text-sm hidden sm:inline-flex whitespace-nowrap"
          >
            ✕ Azzera
          </button>
        )}
      </div>

      {/* Pillole filtri: sempre visibili da sm+, collassabili su mobile */}
      <div className={`${mobileOpen ? "block" : "hidden"} sm:block`}>
        <div className="card p-4 sm:p-5 space-y-4">
          {/* Categoria */}
          {categories.length > 0 && (
            <FilterRow label="Categoria">
              <FilterPill
                active={filters.category === null}
                onClick={() => onUpdate("category", null)}
              >
                Tutte
              </FilterPill>
              {categories.map((c) => (
                <FilterPill
                  key={c}
                  active={filters.category === c}
                  onClick={() => onUpdate("category", c)}
                >
                  {c.replace(/-/g, " ")}
                </FilterPill>
              ))}
            </FilterRow>
          )}

          {/* Condizione */}
          <FilterRow label="Condizione">
            <FilterPill
              active={filters.condition === null}
              onClick={() => onUpdate("condition", null)}
            >
              Tutte
            </FilterPill>
            {(Object.keys(CONDITION_LABEL) as ArticleCondition[]).map((c) => (
              <FilterPill
                key={c}
                active={filters.condition === c}
                onClick={() => onUpdate("condition", c)}
              >
                {CONDITION_LABEL[c]}
              </FilterPill>
            ))}
          </FilterRow>

          {/* Prezzo */}
          <FilterRow label="Prezzo">
            <div className="flex items-center gap-2 flex-1">
              <input
                type="number"
                inputMode="decimal"
                min="0"
                placeholder="Min €"
                value={filters.minPrice}
                onChange={(e) => onUpdate("minPrice", e.target.value)}
                className="filter-input w-24 sm:w-28"
              />
              <span className="text-ink-soft">–</span>
              <input
                type="number"
                inputMode="decimal"
                min="0"
                placeholder="Max €"
                value={filters.maxPrice}
                onChange={(e) => onUpdate("maxPrice", e.target.value)}
                className="filter-input w-24 sm:w-28"
              />
            </div>
          </FilterRow>

          {hasAnyFilter && (
            <div className="sm:hidden pt-1">
              <button
                type="button"
                onClick={onReset}
                className="btn btn-ghost text-sm w-full justify-center"
              >
                ✕ Azzera tutti i filtri
              </button>
            </div>
          )}
        </div>
      </div>

      <style>{`
        .filter-input {
          padding: 0.55rem 0.85rem;
          border-radius: 14px;
          border: 1px solid rgba(61, 42, 92, 0.12);
          background: rgba(255, 255, 255, 0.78);
          backdrop-filter: blur(8px);
          color: #3d2a5c;
          font-family: "Manrope", sans-serif;
          font-size: 0.92rem;
          outline: none;
          transition:
            box-shadow 150ms ease,
            border-color 150ms ease;
        }
        .filter-input:focus {
          border-color: var(--lilac-deep);
          box-shadow: 0 0 0 3px rgba(168, 144, 216, 0.25);
        }
      `}</style>
    </div>
  );
}

function FilterRow({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-3">
      <span className="text-xs font-bold uppercase tracking-wider text-ink-soft sm:w-28 sm:flex-shrink-0">
        {label}
      </span>
      <div className="flex flex-wrap items-center gap-2">{children}</div>
    </div>
  );
}

function FilterPill({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={
        "px-3 py-1.5 rounded-full text-xs font-semibold transition-all " +
        (active
          ? "bg-gradient-to-br from-pink to-lilac-deep text-white shadow-soft"
          : "bg-white/70 text-ink ring-1 ring-ink/10 hover:bg-white")
      }
    >
      {children}
    </button>
  );
}
