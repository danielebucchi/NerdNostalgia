"use client";

import { useEffect, useRef, useState } from "react";
import { ArticleCard } from "@/components/ArticleCard";
import { getCatalog, type CatalogFacets, type CatalogPage } from "@/lib/api";
import type { Article, ArticleCondition } from "@/lib/types";

// Persistenza preferenza aperto/chiuso del pannello filtri.
// Default su primo accesso: CHIUSO (si vede subito il catalogo).
// v2: bump della chiave quando e' cambiato il default aperto→chiuso,
// cosi' anche i visitatori con la vecchia preferenza ripartono chiusi.
const PANEL_STORAGE_KEY = "nn:catalog-filters-open:v2";

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

type SortKey = "recent" | "price_asc" | "price_desc" | "title";

const SORT_LABEL: Record<SortKey, string> = {
  recent: "Più recenti",
  price_asc: "Prezzo ↑",
  price_desc: "Prezzo ↓",
  title: "Titolo A-Z",
};

const PAGE = 24;

interface Props {
  /** Prima pagina e conteggi, gia' pronti dal server (SSR). */
  initial: CatalogPage;
}

export function CatalogSection({ initial }: Props) {
  const [filters, setFilters] = useState<FilterState>(EMPTY);
  const [sort, setSort] = useState<SortKey>("recent");
  // Pannello filtri: CHIUSO di default (si vede subito il catalogo),
  // preferenza persistita in localStorage. Vale per tutti i breakpoint.
  const [panelOpen, setPanelOpen] = useState(false);
  const [hydrated, setHydrated] = useState(false);
  // Ricerca, filtri e conteggi li fa il server: qui c'e' solo la pagina
  // (o le pagine, con "Mostra altri") di quello che si sta guardando.
  const [items, setItems] = useState<Article[]>(initial.items);
  const [total, setTotal] = useState(initial.total);
  const [facets, setFacets] = useState<CatalogFacets>(initial.facets);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const first = useRef(true);

  useEffect(() => {
    try {
      const saved = window.localStorage.getItem(PANEL_STORAGE_KEY);
      if (saved !== null) {
        setPanelOpen(saved === "1");
      }
    } catch {
      // ignore: storage non disponibile (private mode)
    }
    // Deep-link ricerca: /?search=snes (dalla SearchBox in header o link
    // esterni). Letto da window per non richiedere Suspense/useSearchParams.
    try {
      const q = new URLSearchParams(window.location.search).get("search");
      if (q) setFilters((f) => ({ ...f, search: q }));
    } catch {
      // ignore
    }
    setHydrated(true);
  }, []);

  // La SearchBox nell'header notifica le ricerche fatte mentre siamo GIA'
  // sulla home (router.push con sola query non rimonta il client tree).
  useEffect(() => {
    function onSearch(e: Event) {
      const q = (e as CustomEvent<string>).detail ?? "";
      setFilters((f) => ({ ...f, search: q }));
      document.getElementById("catalogo")?.scrollIntoView({ behavior: "smooth" });
    }
    window.addEventListener("nn:catalog-search", onSearch);
    return () => window.removeEventListener("nn:catalog-search", onSearch);
  }, []);

  function query(skip: number) {
    return {
      search: filters.search,
      category: filters.category,
      subcategory: filters.subcategory,
      condition: filters.condition,
      brand: filters.brand,
      min_price: filters.minPrice,
      max_price: filters.maxPrice,
      sort,
      skip,
      limit: PAGE,
    };
  }

  // Ogni cambio di filtri o ordine riparte dalla prima pagina. La ricerca
  // aspetta che si smetta di scrivere; le richieste superate si annullano.
  useEffect(() => {
    if (first.current) {
      first.current = false;
      return; // la prima pagina e' gia' arrivata dal server
    }
    const ctrl = new AbortController();
    const t = window.setTimeout(() => {
      setLoading(true);
      setError(null);
      getCatalog(query(0), ctrl.signal)
        .then((r) => {
          setItems(r.items);
          setTotal(r.total);
          setFacets(r.facets);
        })
        .catch((e) => {
          if (!ctrl.signal.aborted) setError(e instanceof Error ? e.message : String(e));
        })
        .finally(() => {
          if (!ctrl.signal.aborted) setLoading(false);
        });
    }, 250);
    return () => {
      window.clearTimeout(t);
      ctrl.abort();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters, sort]);

  async function loadMore() {
    setLoading(true);
    try {
      const r = await getCatalog(query(items.length));
      setItems((prev) => [...prev, ...r.items.filter((a) => !prev.some((p) => p.id === a.id))]);
      setTotal(r.total);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

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

  // Dai conteggi del server alle prop del pannello filtri (invariato).
  const categoryNames: Record<string, string> = {};
  const catCounts: Record<string, number> = {};
  for (const [slug, c] of Object.entries(facets.categories)) {
    categoryNames[slug] = c.name;
    catCounts[slug] = c.count;
  }
  const subNames: Record<string, string> = {};
  const subCounts: Record<string, number> = {};
  for (const [slug, c] of Object.entries(facets.subcategories)) {
    subNames[slug] = c.name;
    subCounts[slug] = c.count;
  }
  const conditions = Object.keys(facets.conditions) as ArticleCondition[];

  return (
    <>
      <Filters
        filters={filters}
        catCounts={catCounts}
        categoryNames={categoryNames}
        subCounts={subCounts}
        subNames={subNames}
        totalAllSubs={facets.total_all_subcategories}
        condCounts={facets.conditions as Partial<Record<ArticleCondition, number>>}
        brandCounts={facets.brands}
        topBrands={Object.keys(facets.brands)}
        conditions={conditions}
        totalAllCats={facets.total_all_categories}
        totalAllConds={facets.total_all_conditions}
        totalAllBrands={facets.total_all_brands}
        priceMin={facets.price_min}
        priceMax={facets.price_max}
        hasAnyFilter={hasAnyFilter}
        activeFilterCount={activeFilterCount}
        onUpdate={update}
        onReset={reset}
        panelOpen={panelOpen}
        hydrated={hydrated}
        onTogglePanel={togglePanel}
        resultsCount={total}
        sort={sort}
        onSort={setSort}
      />

      {error && <p className="text-pink-deep text-sm mb-4">⚠ {error}</p>}

      {items.length === 0 && !loading ? (
        <div className="card p-10 text-center">
          <p className="display text-xl text-ink mb-2">Nessun articolo</p>
          <p className="text-ink-soft text-sm">
            {hasAnyFilter
              ? "Nessun risultato con i filtri attivi. Provi ad allargare la ricerca."
              : "Nessun articolo ancora pubblicato."}
          </p>
          {hasAnyFilter && (
            <button type="button" className="btn btn-ghost mt-6" onClick={reset}>
              Azzera filtri
            </button>
          )}
        </div>
      ) : (
        <>
          {/* 2 colonne gia' da mobile (stile marketplace): densita' doppia */}
          <div
            className={
              "grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3 sm:gap-6 transition-opacity " +
              (loading ? "opacity-60" : "")
            }
          >
            {items.map((article) => (
              <ArticleCard key={article.id} article={article} />
            ))}
          </div>
          {items.length < total && (
            <div className="text-center mt-8">
              <button type="button" className="btn btn-ghost" onClick={loadMore} disabled={loading}>
                {loading ? "Carico…" : `Mostra altri (${total - items.length})`}
              </button>
            </div>
          )}
        </>
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
  sort: SortKey;
  onSort: (s: SortKey) => void;
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
  sort,
  onSort,
}: FiltersProps) {
  // Prima dell'hydration teniamo il pannello CHIUSO (coerente col nuovo
  // default): niente flash di filtri aperti al primo paint.
  const panelVisible = hydrated ? panelOpen : false;

  // Su mobile il pannello e' un bottom-sheet: blocca lo scroll sotto
  useEffect(() => {
    if (!panelVisible) return;
    if (!window.matchMedia("(max-width: 639px)").matches) return;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = "";
    };
  }, [panelVisible]);

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
            // Logica colore invertita: chiuso = primary (invita ad aprire),
            // aperto = ghost (azione neutra). Il badge col numero indica
            // gia' se ci sono filtri attivi, niente bisogno di tinta extra.
            (panelVisible ? "btn-ghost" : "btn-primary")
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
                "inline-flex items-center justify-center min-w-[18px] h-[18px] px-1 rounded-full bg-white text-ink text-[10px] font-bold tabular-nums ring-1 ring-ink/15 shadow-soft " +
                // Su mobile il badge sta in alto a destra del quadrato; su sm+ inline
                "absolute -top-1 -right-1 sm:static sm:shadow-none"
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

        {/* Ordinamento: inline accanto ai filtri da sm+; su mobile vive
            dentro il pannello collassabile (vedi FilterRow "Ordina") */}
        <select
          value={sort}
          onChange={(e) => onSort(e.target.value as SortKey)}
          aria-label="Ordina risultati"
          className="filter-input hidden sm:block text-sm flex-shrink-0"
        >
          {(Object.keys(SORT_LABEL) as SortKey[]).map((k) => (
            <option key={k} value={k}>{SORT_LABEL[k]}</option>
          ))}
        </select>

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

      {/* Backdrop del bottom-sheet (solo mobile) */}
      {panelVisible && (
        <div
          className="sm:hidden fixed inset-0 z-40 bg-ink/40 backdrop-blur-sm"
          onClick={onTogglePanel}
          aria-hidden="true"
        />
      )}

      {/* Pannello filtri: su mobile e' un bottom-sheet fisso che sale dal
          basso (stesso DOM, presentazione diversa); su sm+ resta inline. */}
      <div
        id="catalog-filters-panel"
        className={
          panelVisible
            ? "fixed inset-x-0 bottom-0 z-50 max-h-[85vh] overflow-y-auto rounded-t-3xl p-4 pb-5 shadow-2xl bg-[#fbf7f4] sm:static sm:z-auto sm:max-h-none sm:overflow-visible sm:rounded-none sm:p-0 sm:shadow-none sm:bg-transparent"
            : "hidden"
        }
      >
        {/* Header sheet (solo mobile) */}
        <div className="sm:hidden flex items-center justify-between mb-3">
          <h3 className="display text-lg text-ink">Filtri &amp; ordinamento</h3>
          <button
            type="button"
            onClick={onTogglePanel}
            className="w-8 h-8 rounded-full border-2 border-ink flex items-center justify-center text-ink"
            aria-label="Chiudi filtri"
          >
            ✕
          </button>
        </div>

        {/* Ordinamento (solo mobile): card separata dai filtri per non
            confonderlo con essi — su sm+ la select sta accanto ai filtri */}
        <div className="sm:hidden card p-4 mb-3">
          <p className="text-xs font-bold uppercase tracking-wider text-ink-soft mb-2">
            ↕ Ordinamento
          </p>
          <div className="flex flex-wrap items-center gap-2">
            {(Object.keys(SORT_LABEL) as SortKey[]).map((k) => (
              <button
                key={k}
                type="button"
                onClick={() => onSort(k)}
                className={
                  "inline-flex items-center px-3 py-1.5 rounded-full text-xs font-semibold transition-all " +
                  (sort === k
                    ? "bg-gradient-to-br from-pink to-lilac-deep text-white shadow-soft"
                    : "bg-white/70 text-ink ring-1 ring-ink/10 hover:bg-white hover:ring-ink/20")
                }
              >
                {SORT_LABEL[k]}
              </button>
            ))}
          </div>
        </div>

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

          {/* Riassunto risultati (solo desktop: su mobile c'e' la CTA) */}
          <div className="hidden sm:flex items-center justify-between pt-3 border-t border-ink/8">
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

        {/* CTA chiusura sheet (solo mobile) */}
        <button
          type="button"
          onClick={onTogglePanel}
          className="sm:hidden btn btn-primary w-full mt-3"
        >
          Mostra {resultsCount} risultat{resultsCount === 1 ? "o" : "i"}
        </button>
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
