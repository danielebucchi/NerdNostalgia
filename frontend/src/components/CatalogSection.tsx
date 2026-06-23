"use client";

import { useEffect, useMemo, useState } from "react";
import { ArticleCard } from "@/components/ArticleCard";
import type { Article, ArticleCondition } from "@/lib/types";

// Persistenza preferenza aperto/chiuso del pannello filtri.
// Default su primo accesso: aperto (utente nuovo vede subito le opzioni).
const PANEL_STORAGE_KEY = "nn:catalog-filters-open:v1";

/** Slug top-level di un articolo (sé stesso se categoria top, altrimenti il parent). */
function topSlugOf(article: Article): string | null {
  if (!article.category) return null;
  if (article.category.parent_id == null) return article.category.slug;
  return article.parent_category?.slug ?? null;
}

/** Slug della sottocategoria (null se l'articolo ha solo categoria top-level). */
function subSlugOf(article: Article): string | null {
  if (!article.category) return null;
  if (article.category.parent_id == null) return null;
  return article.category.slug;
}

const CONDITION_LABEL: Record<ArticleCondition, string> = {
  NEW: "Nuovo",
  USED: "Usato",
  REFURBISHED: "Revisionato",
  FOR_PARTS: "Per pezzi",
};

interface FilterState {
  search: string;
  /** slug top-level (es. "carte"). null = tutte. */
  category: string | null;
  /** slug sottocategoria (es. "pokemon"). null = qualsiasi sotto la top. */
  subcategory: string | null;
  condition: ArticleCondition | null;
  brand: string | null;
  minPrice: string;
  maxPrice: string;
}

const EMPTY: FilterState = {
  search: "",
  category: null,
  subcategory: null,
  condition: null,
  brand: null,
  minPrice: "",
  maxPrice: "",
};

type Dim = "search" | "category" | "subcategory" | "condition" | "brand" | "price";

interface Props {
  initialArticles: Article[];
}

export function CatalogSection({ initialArticles }: Props) {
  const [filters, setFilters] = useState<FilterState>(EMPTY);
  // Pannello filtri: aperto di default, preferenza persistita in localStorage.
  // Vale per tutti i breakpoint (mobile + desktop): l'utente comanda.
  const [panelOpen, setPanelOpen] = useState(true);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    try {
      const saved = window.localStorage.getItem(PANEL_STORAGE_KEY);
      if (saved !== null) {
        setPanelOpen(saved === "1");
      }
    } catch {
      // ignore: storage non disponibile (private mode)
    }
    setHydrated(true);
  }, []);

  function togglePanel() {
    setPanelOpen((v) => {
      const next = !v;
      try {
        window.localStorage.setItem(PANEL_STORAGE_KEY, next ? "1" : "0");
      } catch {
        // ignore
      }
      return next;
    });
  }

  /** Match completo, eventualmente escludendo una dimensione (per i counter). */
  function matches(article: Article, exclude: Dim | null = null): boolean {
    if (exclude !== "search" && filters.search.trim()) {
      const q = filters.search.toLowerCase();
      const hay = [
        article.title,
        article.description,
        article.brand,
        article.model,
        article.category?.name,
        article.parent_category?.name,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      if (!hay.includes(q)) return false;
    }
    if (exclude !== "category" && filters.category) {
      if (topSlugOf(article) !== filters.category) return false;
    }
    if (exclude !== "subcategory" && filters.subcategory) {
      if (subSlugOf(article) !== filters.subcategory) return false;
    }
    if (exclude !== "condition" && filters.condition) {
      if (article.condition !== filters.condition) return false;
    }
    if (exclude !== "brand" && filters.brand) {
      if (article.brand !== filters.brand) return false;
    }
    if (exclude !== "price") {
      const p = Number(article.price);
      if (filters.minPrice && p < Number(filters.minPrice)) return false;
      if (filters.maxPrice && p > Number(filters.maxPrice)) return false;
    }
    return true;
  }

  /** Articoli che soddisfano TUTTI i filtri correnti. */
  const filtered = useMemo(
    () => initialArticles.filter((a) => matches(a, null)),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [initialArticles, filters],
  );

  /**
   * Per ogni opzione di una dimensione (es. category=videogames) conta gli
   * articoli che soddisfano TUTTI gli altri filtri + quella opzione.
   * Questo dà il classico facet count: "Pokemon (3)", "Funko (1)"...
   */
  function countFor(dim: Dim, predicate: (a: Article) => boolean): number {
    let n = 0;
    for (const a of initialArticles) {
      if (matches(a, dim) && predicate(a)) n++;
    }
    return n;
  }

  // Faccette ricavate dai dati. category = top-level slug → label.
  const facets = useMemo(() => {
    const categoryNames: Record<string, string> = {};
    const conditions: Partial<Record<ArticleCondition, number>> = {};
    const brands: Record<string, number> = {};
    let minP = Infinity;
    let maxP = 0;

    for (const a of initialArticles) {
      const slug = topSlugOf(a);
      if (slug) {
        const top = a.parent_category ?? a.category!;
        categoryNames[slug] = top.name;
      }
      conditions[a.condition] = 0;
      if (a.brand) brands[a.brand] = 0;
      const p = Number(a.price);
      if (Number.isFinite(p)) {
        if (p < minP) minP = p;
        if (p > maxP) maxP = p;
      }
    }

    return {
      categories: Object.keys(categoryNames).sort(),
      categoryNames,
      conditions: (Object.keys(conditions) as ArticleCondition[]).sort(),
      brands: Object.keys(brands).sort(),
      priceMin: Number.isFinite(minP) ? Math.floor(minP) : 0,
      priceMax: maxP > 0 ? Math.ceil(maxP) : 0,
    };
  }, [initialArticles]);

  const hasAnyFilter =
    filters.search !== "" ||
    filters.category !== null ||
    filters.subcategory !== null ||
    filters.condition !== null ||
    filters.brand !== null ||
    filters.minPrice !== "" ||
    filters.maxPrice !== "";

  // Conta dei filtri attivi (per badge sul bottone, escluso 'search'
  // che ha il suo input visibile separatamente).
  const activeFilterCount =
    (filters.category !== null ? 1 : 0) +
    (filters.subcategory !== null ? 1 : 0) +
    (filters.condition !== null ? 1 : 0) +
    (filters.brand !== null ? 1 : 0) +
    (filters.minPrice !== "" ? 1 : 0) +
    (filters.maxPrice !== "" ? 1 : 0);

  function update<K extends keyof FilterState>(key: K, value: FilterState[K]) {
    setFilters((f) => {
      // Cambiare categoria top-level resetta la sottocategoria
      if (key === "category") {
        return { ...f, category: value as string | null, subcategory: null };
      }
      return { ...f, [key]: value };
    });
  }

  function reset() {
    setFilters(EMPTY);
  }

  // Pre-calcola i count per ogni opzione (così la UI è snella)
  const catCounts: Record<string, number> = {};
  for (const c of facets.categories) {
    catCounts[c] = countFor("category", (a) => topSlugOf(a) === c);
  }

  // Sottocategorie: solo se è attiva una top-level e ci sono sub presenti
  // negli articoli che la appartengono.
  const subSlugs = new Set<string>();
  const subNames: Record<string, string> = {};
  if (filters.category) {
    for (const a of initialArticles) {
      if (topSlugOf(a) !== filters.category) continue;
      const slug = subSlugOf(a);
      if (slug && a.category) {
        subSlugs.add(slug);
        subNames[slug] = a.category.name;
      }
    }
  }
  const subCounts: Record<string, number> = {};
  for (const s of subSlugs) {
    subCounts[s] = countFor("subcategory", (a) => subSlugOf(a) === s);
  }
  const totalAllSubs = filters.category
    ? countFor("subcategory", () => true)
    : 0;

  const condCounts: Partial<Record<ArticleCondition, number>> = {};
  for (const c of facets.conditions) {
    condCounts[c] = countFor("condition", (a) => a.condition === c);
  }
  const brandCounts: Record<string, number> = {};
  for (const b of facets.brands) {
    brandCounts[b] = countFor("brand", (a) => a.brand === b);
  }
  // Brand: ordino per count desc, mostro top 8
  const topBrands = facets.brands
    .filter((b) => brandCounts[b] > 0)
    .sort((a, b) => brandCounts[b] - brandCounts[a])
    .slice(0, 8);

  // Conta totale "Tutte" (con ogni dimensione esclusa)
  const totalAllCats = countFor("category", () => true);
  const totalAllConds = countFor("condition", () => true);
  const totalAllBrands = countFor("brand", () => true);

  return (
    <>
      <Filters
        filters={filters}
        catCounts={catCounts}
        categoryNames={facets.categoryNames}
        subCounts={subCounts}
        subNames={subNames}
        totalAllSubs={totalAllSubs}
        condCounts={condCounts}
        brandCounts={brandCounts}
        topBrands={topBrands}
        conditions={facets.conditions}
        totalAllCats={totalAllCats}
        totalAllConds={totalAllConds}
        totalAllBrands={totalAllBrands}
        priceMin={facets.priceMin}
        priceMax={facets.priceMax}
        hasAnyFilter={hasAnyFilter}
        activeFilterCount={activeFilterCount}
        onUpdate={update}
        onReset={reset}
        panelOpen={panelOpen}
        hydrated={hydrated}
        onTogglePanel={togglePanel}
        resultsCount={filtered.length}
      />

      {filtered.length === 0 ? (
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
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5 sm:gap-6">
          {filtered.map((article) => (
            <ArticleCard key={article.id} article={article} />
          ))}
        </div>
      )}
    </>
  );
}

interface FiltersProps {
  filters: FilterState;
  catCounts: Record<string, number>;
  categoryNames: Record<string, string>;
  subCounts: Record<string, number>;
  subNames: Record<string, string>;
  totalAllSubs: number;
  condCounts: Partial<Record<ArticleCondition, number>>;
  brandCounts: Record<string, number>;
  topBrands: string[];
  conditions: ArticleCondition[];
  totalAllCats: number;
  totalAllConds: number;
  totalAllBrands: number;
  priceMin: number;
  priceMax: number;
  hasAnyFilter: boolean;
  activeFilterCount: number;
  onUpdate: <K extends keyof FilterState>(key: K, value: FilterState[K]) => void;
  onReset: () => void;
  panelOpen: boolean;
  hydrated: boolean;
  onTogglePanel: () => void;
  resultsCount: number;
}

function Filters({
  filters,
  catCounts,
  categoryNames,
  subCounts,
  subNames,
  totalAllSubs,
  condCounts,
  brandCounts,
  topBrands,
  conditions,
  totalAllCats,
  totalAllConds,
  totalAllBrands,
  priceMin,
  priceMax,
  hasAnyFilter,
  activeFilterCount,
  onUpdate,
  onReset,
  panelOpen,
  hydrated,
  onTogglePanel,
  resultsCount,
}: FiltersProps) {
  // Prima dell'hydration, il pannello va renderizzato per evitare flash;
  // useremo la sua preferenza salvata appena disponibile.
  const panelVisible = hydrated ? panelOpen : true;

  return (
    <div className="mb-6 sm:mb-8">
      {/* Riga compatta: search prende tutto, bottone filtri solo icona
          su mobile, label completa da sm+ */}
      <div className="mb-3 flex items-stretch gap-2">
        <div className="relative flex-1 min-w-0">
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-soft text-lg pointer-events-none">
            🔎
          </span>
          <input
            type="search"
            value={filters.search}
            onChange={(e) => onUpdate("search", e.target.value)}
            placeholder="Cerca…"
            className="filter-input pl-10 w-full"
          />
        </div>

        <button
          type="button"
          onClick={onTogglePanel}
          aria-expanded={panelVisible}
          aria-controls="catalog-filters-panel"
          aria-label={panelVisible ? "Nascondi filtri" : "Mostra filtri"}
          className={
            "btn text-sm flex-shrink-0 inline-flex items-center justify-center gap-1.5 relative " +
            // Mobile: quadrato compatto; sm+: padding standard + label
            "w-11 px-0 sm:w-auto sm:px-4 " +
            (panelVisible || activeFilterCount > 0 ? "btn-primary" : "btn-ghost")
          }
        >
          {/* Su mobile il glifo cambia in base allo stato (+/−) */}
          <span aria-hidden="true" className="sm:hidden text-lg leading-none font-bold">
            {panelVisible ? "−" : "+"}
          </span>
          <span aria-hidden="true" className="hidden sm:inline">⚙</span>
          <span className="hidden sm:inline">
            {panelVisible ? "Nascondi filtri" : "Mostra filtri"}
          </span>
          {activeFilterCount > 0 && (
            <span
              className={
                "inline-flex items-center justify-center min-w-[18px] h-[18px] px-1 rounded-full bg-white/30 text-[10px] font-bold tabular-nums " +
                // Su mobile il badge sta in alto a destra del quadrato; su sm+ inline
                "absolute -top-1 -right-1 sm:static sm:bg-white/30"
              }
            >
              {activeFilterCount}
            </span>
          )}
          <span
            aria-hidden="true"
            className={`hidden sm:inline transition-transform duration-200 ${
              panelVisible ? "rotate-180" : "rotate-0"
            }`}
          >
            ▾
          </span>
        </button>

        {hasAnyFilter && (
          <button
            type="button"
            onClick={onReset}
            className="btn btn-ghost text-sm whitespace-nowrap flex-shrink-0 w-11 px-0 sm:w-auto sm:px-4"
            aria-label="Azzera filtri"
            title="Azzera filtri"
          >
            <span className="sm:hidden text-lg leading-none">✕</span>
            <span className="hidden sm:inline">✕ Azzera</span>
          </button>
        )}
      </div>

      {/* Pannello filtri: collassabile sempre, persistito in localStorage */}
      <div
        id="catalog-filters-panel"
        className={panelVisible ? "block" : "hidden"}
      >
        <div className="card p-4 sm:p-5 space-y-4">
          {/* Categoria */}
          {Object.keys(catCounts).length > 0 && (
            <FilterRow label="Categoria">
              <FilterPill
                active={filters.category === null}
                onClick={() => onUpdate("category", null)}
                count={totalAllCats}
              >
                Tutte
              </FilterPill>
              {Object.keys(catCounts).map((c) => (
                <FilterPill
                  key={c}
                  active={filters.category === c}
                  onClick={() => onUpdate("category", c)}
                  count={catCounts[c]}
                  disabled={catCounts[c] === 0 && filters.category !== c}
                >
                  {categoryNames[c] ?? c.replace(/-/g, " ")}
                </FilterPill>
              ))}
            </FilterRow>
          )}

          {/* Sottocategoria: solo se una top-level è selezionata e ci sono sub */}
          {filters.category && Object.keys(subCounts).length > 0 && (
            <FilterRow label="Sottocategoria">
              <FilterPill
                active={filters.subcategory === null}
                onClick={() => onUpdate("subcategory", null)}
                count={totalAllSubs}
              >
                Tutte
              </FilterPill>
              {Object.keys(subCounts).map((s) => (
                <FilterPill
                  key={s}
                  active={filters.subcategory === s}
                  onClick={() => onUpdate("subcategory", s)}
                  count={subCounts[s]}
                  disabled={subCounts[s] === 0 && filters.subcategory !== s}
                >
                  {subNames[s] ?? s.replace(/-/g, " ")}
                </FilterPill>
              ))}
            </FilterRow>
          )}

          {/* Condizione */}
          {conditions.length > 0 && (
            <FilterRow label="Condizione">
              <FilterPill
                active={filters.condition === null}
                onClick={() => onUpdate("condition", null)}
                count={totalAllConds}
              >
                Tutte
              </FilterPill>
              {conditions.map((c) => (
                <FilterPill
                  key={c}
                  active={filters.condition === c}
                  onClick={() => onUpdate("condition", c)}
                  count={condCounts[c] ?? 0}
                  disabled={(condCounts[c] ?? 0) === 0 && filters.condition !== c}
                >
                  {CONDITION_LABEL[c]}
                </FilterPill>
              ))}
            </FilterRow>
          )}

          {/* Brand */}
          {topBrands.length > 0 && (
            <FilterRow label="Marca">
              <FilterPill
                active={filters.brand === null}
                onClick={() => onUpdate("brand", null)}
                count={totalAllBrands}
              >
                Tutte
              </FilterPill>
              {topBrands.map((b) => (
                <FilterPill
                  key={b}
                  active={filters.brand === b}
                  onClick={() => onUpdate("brand", b)}
                  count={brandCounts[b]}
                  disabled={brandCounts[b] === 0 && filters.brand !== b}
                >
                  {b}
                </FilterPill>
              ))}
            </FilterRow>
          )}

          {/* Prezzo */}
          {priceMax > 0 && (
            <FilterRow label="Prezzo">
              <div className="flex items-center gap-2 flex-1">
                <input
                  type="number"
                  inputMode="decimal"
                  min="0"
                  placeholder={`Min €${priceMin}`}
                  value={filters.minPrice}
                  onChange={(e) => onUpdate("minPrice", e.target.value)}
                  className="filter-input w-28 sm:w-32"
                />
                <span className="text-ink-soft">–</span>
                <input
                  type="number"
                  inputMode="decimal"
                  min="0"
                  placeholder={`Max €${priceMax}`}
                  value={filters.maxPrice}
                  onChange={(e) => onUpdate("maxPrice", e.target.value)}
                  className="filter-input w-28 sm:w-32"
                />
                <span className="text-xs text-ink-soft hidden md:inline ml-2">
                  range catalogo: €{priceMin}–€{priceMax}
                </span>
              </div>
            </FilterRow>
          )}

          {/* Riassunto risultati */}
          <div className="flex items-center justify-between pt-3 border-t border-ink/8">
            <span className="text-xs text-ink-soft">
              <strong className="text-ink">{resultsCount}</strong>{" "}
              risultat{resultsCount === 1 ? "o" : "i"}
              {activeFilterCount > 0 && (
                <span className="ml-2">
                  · {activeFilterCount}{" "}
                  filtr{activeFilterCount === 1 ? "o" : "i"} attiv
                  {activeFilterCount === 1 ? "o" : "i"}
                </span>
              )}
            </span>
          </div>
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
  count,
  disabled,
  children,
}: {
  active: boolean;
  onClick: () => void;
  count: number;
  disabled?: boolean;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={
        "inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold transition-all " +
        (active
          ? "bg-gradient-to-br from-pink to-lilac-deep text-white shadow-soft"
          : disabled
            ? "bg-white/40 text-ink-soft ring-1 ring-ink/5 cursor-not-allowed opacity-50"
            : "bg-white/70 text-ink ring-1 ring-ink/10 hover:bg-white hover:ring-ink/20")
      }
    >
      <span>{children}</span>
      <span
        className={
          "text-[10px] font-bold tabular-nums px-1.5 py-0.5 rounded-full " +
          (active
            ? "bg-white/25"
            : "bg-ink/8 text-ink-soft")
        }
      >
        {count}
      </span>
    </button>
  );
}
