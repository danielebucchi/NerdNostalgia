"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { AdminShell } from "@/components/admin/AdminShell";
import { BulkMarkupPanel } from "@/components/admin/BulkMarkupPanel";
import { BulkPublishPanel } from "@/components/admin/BulkPublishPanel";
import { Sortable } from "@/components/admin/Sortable";
import { SwipeRow } from "@/components/admin/SwipeRow";
import { useUndo } from "@/components/admin/useUndo";
import { adminApi } from "@/lib/admin-api";
import { formatPrice } from "@/lib/api";
import type { Article, ArticleListResponse } from "@/lib/types";

const STATUS_OPTIONS = ["", "DRAFT", "PUBLISHED", "SOLD", "ARCHIVED"] as const;

// Filtro "non collegati": gli articoli che mancano su un marketplace (o su
// tutti e tre), per sapere cosa resta da mettere in vendita altrove.
const UNLINKED_OPTIONS: { value: string; label: string }[] = [
  { value: "", label: "Tutti" },
  { value: "all", label: "Su nessun marketplace" },
  { value: "vinted", label: "Senza Vinted" },
  { value: "ebay", label: "Senza eBay" },
  { value: "cardtrader", label: "Senza CardTrader" },
];

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
  const [unlinked, setUnlinked] = useState<string>(search.get("unlinked") ?? "");
  const [debouncedQuery, setDebouncedQuery] = useState<string>(query);
  const [items, setItems] = useState<Article[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // I filtri della lista, da `skip` in poi (le pagine sono da 100).
  function filtri(skip: number): URLSearchParams {
    const qs = new URLSearchParams({ limit: "100", skip: String(skip), include_reserved: "true" });
    if (status) qs.set("status", status);
    if (debouncedQuery) qs.set("search", debouncedQuery);
    if (unlinked) qs.set("unlinked", unlinked);
    return qs;
  }

  const [loadingMore, setLoadingMore] = useState(false);
  async function caricaAltri() {
    setLoadingMore(true);
    try {
      const data = await adminApi.get<ArticleListResponse>(`/api/articles/?${filtri(items.length)}`);
      setItems((curr) => {
        const visti = new Set(curr.map((a) => a.id));
        return [...curr, ...data.items.filter((a) => !visti.has(a.id))];
      });
      setTotal(data.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoadingMore(false);
    }
  }

  // Debounce della query (300ms)
  useEffect(() => {
    const t = setTimeout(() => setDebouncedQuery(query.trim()), 300);
    return () => clearTimeout(t);
  }, [query]);

  // Filtri client-side: marca, modello, sku, categoria
  const [extraFiltered, setExtraFiltered] = useState<Article[]>([]);

  // Bump per ricaricare la lista dopo operazioni che cambiano i dati
  // (es. il rincaro di listino), senza duplicare la fetch.
  const [reloadBump, setReloadBump] = useState(0);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        // include_reserved: in admin devono comparire anche i pezzi
        // impegnati da un ordine in attesa, altrimenti spariscono proprio
        // quando serve guardarli per confermare o annullare.
        const data = await adminApi.get<ArticleListResponse>(`/api/articles/?${filtri(0)}`);
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
  }, [status, debouncedQuery, unlinked, reloadBump]);

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
  // Selezione per la pubblicazione in blocco: riordino e swipe si spengono.
  const [seleziona, setSeleziona] = useState(false);
  const [scelti, setScelti] = useState<Set<number>>(new Set());
  const articoliScelti = useMemo(() => {
    // Con la ricerca attiva gli articoli mostrati vengono da extraFiltered.
    const perId = new Map([...items, ...extraFiltered].map((a) => [a.id, a]));
    return [...perId.values()].filter((a) => scelti.has(a.id));
  }, [items, extraFiltered, scelti]);
  const reorderEnabled = !debouncedQuery && !status && !unlinked && !seleziona;
  function scegli(id: number, si: boolean) {
    setScelti((s) => {
      const n = new Set(s);
      if (si) n.add(id);
      else n.delete(id);
      return n;
    });
  }

  // Azioni swipe (mobile): ← elimina, → segna venduto. Ottimistiche con
  // ANNULLA (5s): piu' veloci e piu' sicure dei confirm.
  const { perform: performUndoable, snackbar } = useUndo();

  function swipeDelete(a: Article) {
    const prev = items;
    performUndoable({
      message: `"${a.title.slice(0, 24)}" eliminato`,
      apply: () => {
        setItems((curr) => curr.filter((x) => x.id !== a.id));
        setTotal((t) => Math.max(0, t - 1));
      },
      revert: () => {
        setItems(prev);
        setTotal((t) => t + 1);
      },
      commit: async () => {
        await adminApi.delete(`/api/articles/${a.id}`);
      },
      onCommitError: () => setError("Eliminazione non riuscita (rete?) — ricarica la pagina."),
    });
  }

  function swipeSold(a: Article) {
    if (a.status === "SOLD") return;
    const prevStatus = a.status;
    performUndoable({
      message: `"${a.title.slice(0, 24)}" → VENDUTO`,
      apply: () =>
        setItems((curr) =>
          curr.map((x) => (x.id === a.id ? { ...x, status: "SOLD" } : x)),
        ),
      revert: () =>
        setItems((curr) =>
          curr.map((x) => (x.id === a.id ? { ...x, status: prevStatus } : x)),
        ),
      commit: async () => {
        await adminApi.post(`/api/articles/${a.id}/sell`);
      },
      onCommitError: () => setError("Segna-venduto non riuscito (rete?) — ricarica la pagina."),
    });
  }

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
        <div className="flex gap-2">
          <button type="button" className={`btn text-sm ${seleziona ? "btn-primary" : "btn-ghost"}`}
            onClick={() => {
              setSeleziona((v) => !v);
              setScelti(new Set());
            }}>
            {seleziona ? "Fine" : "☑️ Seleziona"}
          </button>
          <Link href="/admin/articles/new" className="btn btn-primary">
            ➕ Nuovo
          </Link>
        </div>
      </div>

      {seleziona && (
        <div className="mb-4 flex flex-wrap items-center gap-3 text-sm">
          <span className="text-ink">{scelti.size} selezionat{scelti.size === 1 ? "o" : "i"}</span>
          <button type="button" className="underline text-lilac-deep"
            onClick={() => setScelti(new Set(visible.map((a) => a.id)))}>
            tutti quelli visibili ({visible.length})
          </button>
          {scelti.size > 0 && (
            <button type="button" className="underline text-ink-soft" onClick={() => setScelti(new Set())}>
              nessuno
            </button>
          )}
        </div>
      )}
      {seleziona && articoliScelti.length > 0 && (
        <BulkPublishPanel articoli={articoliScelti} onFinito={() => setReloadBump((b) => b + 1)} />
      )}

      {/* Rincaro di listino: pannello chiuso di default, si apre al bisogno */}
      <div className="mb-4">
        <BulkMarkupPanel onApplied={() => setReloadBump((b) => b + 1)} />
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

      <div className="flex gap-2 mb-6 -mt-3 flex-wrap items-center">
        <span className="text-xs text-ink-soft font-semibold">Marketplace:</span>
        {UNLINKED_OPTIONS.map((o) => (
          <button
            key={o.value || "all-links"}
            type="button"
            onClick={() => setUnlinked(o.value)}
            className={`chip cursor-pointer ${unlinked === o.value ? "chip-pink" : ""}`}
          >
            {o.label}
          </button>
        ))}
        {unlinked && !loading && (
          <span className="text-xs text-ink-soft">
            {total} articol{total === 1 ? "o" : "i"}
            {total > items.length ? ` (ne vedi ${items.length})` : ""}
          </span>
        )}
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
        <p className="text-xs text-ink-soft mb-3 hidden sm:block">
          Trascina la maniglia ⋮⋮ per riordinare il catalogo.
        </p>
      )}
      {visible.length > 0 && (
        <p className="text-xs text-ink-soft mb-3 sm:hidden">
          💰 swipe a destra = venduto · swipe a sinistra = elimina 🗑
        </p>
      )}

      {seleziona ? (
        <div className="space-y-3">
          {visible.map((a) => (
            <ArticleRow key={a.id} article={a} scelto={scelti.has(a.id)} onScelto={(v) => scegli(a.id, v)} />
          ))}
        </div>
      ) : reorderEnabled ? (
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
            <SwipeRow
              rightAction={
                a.status !== "SOLD"
                  ? { label: "Venduto", icon: "💰", onTrigger: () => swipeSold(a) }
                  : undefined
              }
              leftAction={{ label: "Elimina", icon: "🗑", onTrigger: () => swipeDelete(a) }}
            >
              <ArticleRow article={a} isDragging={isDragging} dragProps={{ listeners, attributes }} />
            </SwipeRow>
          )}
        />
      ) : (
        <div className="space-y-3">
          {visible.map((a) => (
            <SwipeRow
              key={a.id}
              rightAction={
                a.status !== "SOLD"
                  ? { label: "Venduto", icon: "💰", onTrigger: () => swipeSold(a) }
                  : undefined
              }
              leftAction={{ label: "Elimina", icon: "🗑", onTrigger: () => swipeDelete(a) }}
            >
              <ArticleRow article={a} />
            </SwipeRow>
          ))}
        </div>
      )}

      {!loading && items.length < total && (
        <div className="text-center mt-6">
          <button type="button" className="btn btn-ghost text-sm" disabled={loadingMore} onClick={caricaAltri}>
            {loadingMore ? "Caricamento…" : `Carica altri (${items.length} di ${total})`}
          </button>
        </div>
      )}

      {snackbar}

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
  scelto,
  onScelto,
}: {
  article: Article;
  isDragging?: boolean;
  dragProps?: DragProps;
  /** In modalità selezione: la casella al posto del link alla scheda. */
  scelto?: boolean;
  onScelto?: (v: boolean) => void;
}) {
  const contenuto = (
    <>
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
      {(a.ebay_status === "LISTED" || a.cardtrader_product_id || a.vinted_url) && (
        <span className="hidden sm:inline-flex gap-1 text-[10px] font-semibold">
          {a.vinted_url && <span className="chip chip-sky" title="Collegato a Vinted">Vinted</span>}
          {a.ebay_status === "LISTED" && <span className="chip chip-sky" title="In vendita su eBay">eBay</span>}
          {a.cardtrader_product_id && <span className="chip chip-sky" title="In vendita su CardTrader">CT</span>}
        </span>
      )}
      {a.reserved && (
        <span
          className="chip chip-lilac hidden sm:inline-flex whitespace-nowrap"
          title="Ordine in attesa su questo pezzo: non è in vendita sul sito finché non confermi o annulli l'ordine"
        >
          ⏳ RISERVATO
        </span>
      )}
      <span className={`chip ${STATUS_CHIP[a.status] ?? ""} hidden sm:inline-flex`}>{a.status}</span>
      <span className="display text-lg text-pink-deep w-20 sm:w-24 text-right flex-shrink-0">{formatPrice(a)}</span>
    </>
  );
  if (onScelto) {
    return (
      <label className={"card p-3 sm:p-4 flex items-center gap-3 sm:gap-4 cursor-pointer " +
        (scelto ? "ring-2 ring-lilac-deep/50" : "")}>
        <input type="checkbox" className="h-5 w-5 accent-lilac-deep flex-shrink-0" checked={!!scelto}
          onChange={(e) => onScelto(e.target.checked)} aria-label={`Seleziona ${a.title}`} />
        {contenuto}
      </label>
    );
  }
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
        {contenuto}
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
