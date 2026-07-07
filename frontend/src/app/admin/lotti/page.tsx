"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { AdminShell } from "@/components/admin/AdminShell";
import { adminApi } from "@/lib/admin-api";
import { usePlatforms } from "@/lib/usePlatforms";
import type {
  InventoryItem,
  InventoryItemStatus,
  InventoryListResponse,
  Lot,
  LotListResponse,
  LotStatus,
} from "@/lib/types";

function fmtMoney(v: string | number | null | undefined): string {
  if (v == null || v === "") return "—";
  const n = typeof v === "number" ? v : Number(v);
  if (!Number.isFinite(n)) return "—";
  return new Intl.NumberFormat("it-IT", {
    style: "currency",
    currency: "EUR",
    maximumFractionDigits: 2,
  }).format(n);
}

const STATUS_LABEL: Record<string, string> = {
  DRAFT: "Bozza",
  LINKED: "Article DRAFT",
  LISTED: "Pubblicato",
  RESERVED: "Riservato",
  SOLD: "Venduto",
  ARCHIVED: "Archiviato",
};

const STATUS_COLOR: Record<string, string> = {
  DRAFT: "bg-ink/10 text-ink",
  LINKED: "bg-lilac-soft text-lilac-deep",
  LISTED: "bg-mint text-mint-deep",
  RESERVED: "bg-pink-soft text-pink-deep",
  SOLD: "bg-mint-deep text-white",
  ARCHIVED: "bg-ink/20 text-ink-soft",
};

const PEOPLE = ["", "C", "D"];

export default function AdminLottiListPage() {
  const { items: platformList } = usePlatforms();
  const platformNames = ["", ...platformList.map((p) => p.name)];
  const [lots, setLots] = useState<Lot[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<LotStatus | "">("");
  const [search, setSearch] = useState("");

  // Ricerca articolo globale (independente dai lotti)
  const [itemQuery, setItemQuery] = useState("");
  const [itemResults, setItemResults] = useState<InventoryItem[]>([]);
  const [itemBusy, setItemBusy] = useState(false);

  async function reload() {
    setLoading(true);
    setError(null);
    try {
      const qs = new URLSearchParams();
      if (statusFilter) qs.set("status", statusFilter);
      if (search.trim()) qs.set("search", search.trim());
      const data = await adminApi.get<LotListResponse>(`/api/lots/?${qs}`);
      setLots(data.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter]);

  // Debounced item search
  useEffect(() => {
    const q = itemQuery.trim();
    if (q.length < 2) {
      setItemResults([]);
      return;
    }
    let cancelled = false;
    const t = setTimeout(async () => {
      setItemBusy(true);
      try {
        const data = await adminApi.get<InventoryListResponse>(
          `/api/inventory/?search=${encodeURIComponent(q)}&limit=50`,
        );
        if (!cancelled) setItemResults(data.items);
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err));
      } finally {
        if (!cancelled) setItemBusy(false);
      }
    }, 250);
    return () => { cancelled = true; clearTimeout(t); };
  }, [itemQuery]);

  async function saveItem(id: number, patch: Partial<InventoryItem>) {
    try {
      await adminApi.patch(`/api/inventory/${id}`, patch);
      // Re-run search to refresh state
      if (itemQuery.trim().length >= 2) {
        const data = await adminApi.get<InventoryListResponse>(
          `/api/inventory/?search=${encodeURIComponent(itemQuery.trim())}&limit=50`,
        );
        setItemResults(data.items);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  const totals = useMemo(() => {
    const acc = { cost: 0, revenue: 0, profit: 0, immobilizzato: 0, items: 0 };
    for (const lot of lots) {
      acc.cost += Number(lot.cost_sum || 0);
      acc.revenue += Number(lot.revenue_sum || 0);
      acc.profit += Number(lot.profit_sum || 0);
      acc.immobilizzato += Number(lot.immobilizzato || 0);
      acc.items += lot.items_count;
    }
    return acc;
  }, [lots]);

  return (
    <AdminShell>
      <div className="flex items-end justify-between mb-4 gap-3 flex-wrap">
        <div>
          <h1 className="display text-3xl text-ink">📦 Lotti</h1>
          <p className="text-ink-soft mt-1 text-sm">
            Gestione interna: ogni lotto è un container di item con metadati di
            acquisto comuni (data, piattaforma, costo totale). Click su un lotto
            per vedere/modificare gli item.
          </p>
        </div>
        <div className="flex gap-2 flex-wrap">
          <Link href="/admin/lotti/import" className="btn btn-ghost text-sm" title="Import CSV completo: lotti + item raggruppati">
            📤 CSV
          </Link>
          <Link href="/admin/lotti/bulk" className="btn btn-ghost text-sm" title="Crea piu' lotti in un colpo (solo anagrafica)">
            📥 Bulk
          </Link>
          <Link href="/admin/lotti/new" className="btn btn-primary text-sm">
            + Nuovo lotto
          </Link>
        </div>
      </div>

      {error && (
        <div className="card p-4 mb-4 text-pink-deep font-semibold">⚠ {error}</div>
      )}

      {/* Ricerca globale articolo (cross-lotti) */}
      <ItemSearchPanel
        query={itemQuery}
        onQuery={setItemQuery}
        results={itemResults}
        busy={itemBusy}
        platformNames={platformNames}
        onSave={saveItem}
      />

      <div className="grid grid-cols-2 lg:grid-cols-5 gap-2 mb-4">
        <TotalCard label="Lotti" value={String(lots.length)} color="bg-pink-soft" />
        <TotalCard label="Pezzi totali" value={String(totals.items)} color="bg-lilac-soft" />
        <TotalCard label="Costo" value={fmtMoney(totals.cost)} color="bg-pink-soft" />
        <TotalCard label="Profitto" value={fmtMoney(totals.profit)} color={totals.profit >= 0 ? "bg-mint" : "bg-pink"} accent />
        <TotalCard label="Immobilizzato" value={fmtMoney(totals.immobilizzato)} color="bg-lilac-soft" />
      </div>

      <div className="card p-3 mb-4 grid sm:grid-cols-[1fr_200px_auto] gap-2">
        <input
          type="search"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && reload()}
          placeholder="🔎 Cerca per code o nome…"
          className="input"
        />
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value as LotStatus | "")}
          className="input"
        >
          <option value="">Tutti gli stati</option>
          <option value="OPEN">Aperto</option>
          <option value="CLOSED">Chiuso</option>
          <option value="ARCHIVED">Archiviato</option>
        </select>
        <button type="button" onClick={reload} className="btn btn-ghost text-sm">
          Cerca
        </button>
      </div>

      {loading && <p className="text-ink-soft">Caricamento…</p>}

      {!loading && lots.length === 0 && (
        <div className="card p-10 text-center">
          <p className="text-ink-soft mb-3">Nessun lotto trovato.</p>
          <Link href="/admin/lotti/new" className="btn btn-primary text-sm">
            Crea il primo lotto
          </Link>
        </div>
      )}

      <div className="grid gap-3">
        {lots.map((lot) => (
          <LotCard key={lot.id} lot={lot} />
        ))}
      </div>

      <style>{`
        .input {
          display: block;
          width: 100%;
          padding: 0.5rem 0.7rem;
          border: 1px solid rgba(61, 42, 92, 0.12);
          border-radius: 10px;
          background: #fffaf3;
          color: #3d2a5c;
          font-family: "Manrope", sans-serif;
          font-size: 0.9rem;
          outline: none;
        }
        .input:focus {
          box-shadow: 0 0 0 2px rgba(248, 168, 200, 0.45);
          border-color: #e879a8;
        }
      `}</style>
    </AdminShell>
  );
}

function ItemSearchPanel({
  query, onQuery, results, busy, platformNames, onSave,
}: {
  query: string;
  onQuery: (q: string) => void;
  results: InventoryItem[];
  busy: boolean;
  platformNames: string[];
  onSave: (id: number, patch: Partial<InventoryItem>) => void | Promise<void>;
}) {
  return (
    <div className="card p-4 mb-4 bg-mint/10">
      <div className="flex items-end justify-between mb-2 flex-wrap gap-2">
        <div>
          <h2 className="display text-base text-ink">🔎 Cerca articolo (cross-lotti)</h2>
          <p className="text-xs text-ink-soft">
            Non ricordi in che lotto è un articolo che hai venduto? Cercalo
            qui per titolo, collezione o numero — poi marca venduto senza
            navigare nel lotto.
          </p>
        </div>
        {busy && <span className="text-xs text-ink-soft">Cerco…</span>}
      </div>
      <input
        type="search"
        value={query}
        onChange={(e) => onQuery(e.target.value)}
        placeholder="Almeno 2 caratteri… (es. pikachu, charizard, base set)"
        className="input"
        autoFocus={false}
      />

      {query.trim().length >= 2 && (
        <div className="mt-3">
          {results.length === 0 && !busy && (
            <p className="text-xs text-ink-soft py-2">Nessun articolo trovato.</p>
          )}
          {results.length > 0 && (
            <div className="overflow-x-auto rounded-lg border border-ink/8">
              <table className="min-w-full text-xs bg-white/70">
                <thead className="bg-white/80 text-ink-soft uppercase tracking-wider">
                  <tr>
                    <th className="text-left py-2 px-2">Articolo</th>
                    <th className="text-left py-2 px-2">Lotto</th>
                    <th className="text-left py-2 px-2">Stato</th>
                    <th className="text-left py-2 px-2">Data vend.</th>
                    <th className="text-right py-2 px-2">Prezzo</th>
                    <th className="text-right py-2 px-2">Fee</th>
                    <th className="text-right py-2 px-2">Sped.</th>
                    <th className="text-left py-2 px-2">Pf.</th>
                    <th className="text-left py-2 px-2">Chi</th>
                  </tr>
                </thead>
                <tbody>
                  {results.map((it) => (
                    <SearchRow key={it.id} item={it} platformNames={platformNames} onSave={onSave} />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function SearchRow({
  item, platformNames, onSave,
}: {
  item: InventoryItem;
  platformNames: string[];
  onSave: (id: number, patch: Partial<InventoryItem>) => void | Promise<void>;
}) {
  const [soldDate, setSoldDate] = useState(item.sold_date ?? "");
  const [salePrice, setSalePrice] = useState(item.sale_price ?? "");
  const [fee, setFee] = useState(item.fee_amount ?? "");
  const [shipping, setShipping] = useState(item.shipping_cost ?? "");
  const [soldPlatform, setSoldPlatform] = useState(item.sold_platform ?? "");
  const [soldBy, setSoldBy] = useState(item.sold_by ?? "");

  function maybe(key: keyof InventoryItem, current: unknown, original: unknown) {
    if (current === original) return;
    if (typeof current === "string" && current === "" && (original === null || original === "")) return;
    const patch: Partial<InventoryItem> = { [key]: (current === "" ? null : current) as never };
    // Auto-status SOLD quando metti un prezzo di vendita
    if (key === "sale_price" && current !== "" && item.status !== "SOLD") {
      patch.status = "SOLD";
      if (!item.sold_date) patch.sold_date = new Date().toISOString().slice(0, 10) as never;
    }
    onSave(item.id, patch);
  }

  const STATUS_COLOR: Record<InventoryItemStatus, string> = {
    DRAFT: "bg-ink/10 text-ink",
    LINKED: "bg-lilac-soft text-lilac-deep",
    LISTED: "bg-mint text-mint-deep",
    RESERVED: "bg-pink-soft text-pink-deep",
    SOLD: "bg-mint-deep text-white",
    ARCHIVED: "bg-ink/20 text-ink-soft",
  };

  return (
    <tr className="border-t border-ink/5 hover:bg-pink-soft/20">
      <td className="px-2 py-1.5">
        <div className="font-semibold text-ink">{item.title}</div>
        {item.card_collection && (
          <div className="text-[10px] text-ink-soft">
            {item.card_collection}{item.card_number ? ` · #${item.card_number}` : ""}
          </div>
        )}
      </td>
      <td className="px-2 py-1.5">
        <Link
          href={`/admin/lotti/${item.lot_id}`}
          className="font-mono text-[10px] px-2 py-0.5 rounded-full bg-lilac-soft text-lilac-deep hover:underline"
        >
          {item.lot_code ?? `#${item.lot_id}`}
        </Link>
      </td>
      <td className="px-2 py-1.5">
        <select
          value={item.status}
          onChange={(e) => onSave(item.id, { status: e.target.value as InventoryItemStatus })}
          className={`cell-input text-[10px] font-semibold rounded-full px-2 ${STATUS_COLOR[item.status]}`}
        >
          <option value="DRAFT">Bozza</option>
          <option value="LINKED">Linked</option>
          <option value="LISTED">Pubbl.</option>
          <option value="RESERVED">Risev.</option>
          <option value="SOLD">Venduto</option>
          <option value="ARCHIVED">Archiv.</option>
        </select>
      </td>
      <td className="px-2 py-1.5">
        <input
          type="date"
          value={soldDate}
          onChange={(e) => setSoldDate(e.target.value)}
          onBlur={() => maybe("sold_date", soldDate, item.sold_date)}
          className="cell-input text-[11px] w-28"
        />
      </td>
      <td className="px-2 py-1.5 text-right">
        <input
          type="number" step="0.01"
          value={salePrice ?? ""}
          onChange={(e) => setSalePrice(e.target.value)}
          onBlur={() => maybe("sale_price", salePrice, item.sale_price)}
          className="cell-input text-right tabular-nums w-20 font-semibold"
        />
      </td>
      <td className="px-2 py-1.5 text-right">
        <input
          type="number" step="0.01"
          value={fee ?? ""}
          onChange={(e) => setFee(e.target.value)}
          onBlur={() => maybe("fee_amount", fee, item.fee_amount)}
          className="cell-input text-right tabular-nums w-14"
        />
      </td>
      <td className="px-2 py-1.5 text-right">
        <input
          type="number" step="0.01"
          value={shipping ?? ""}
          onChange={(e) => setShipping(e.target.value)}
          onBlur={() => maybe("shipping_cost", shipping, item.shipping_cost)}
          className="cell-input text-right tabular-nums w-14"
        />
      </td>
      <td className="px-2 py-1.5">
        <select
          value={soldPlatform}
          onChange={(e) => {
            setSoldPlatform(e.target.value);
            if (e.target.value !== (item.sold_platform ?? ""))
              onSave(item.id, { sold_platform: (e.target.value || null) as never });
          }}
          className="cell-input text-[11px] w-24"
        >
          {platformNames.map((p) => <option key={p || "_"} value={p}>{p || "—"}</option>)}
        </select>
      </td>
      <td className="px-2 py-1.5">
        <select
          value={soldBy}
          onChange={(e) => {
            setSoldBy(e.target.value);
            if (e.target.value !== (item.sold_by ?? ""))
              onSave(item.id, { sold_by: (e.target.value || null) as never });
          }}
          className="cell-input text-[11px] w-12"
        >
          {PEOPLE.map((p) => <option key={p || "_"} value={p}>{p || "—"}</option>)}
        </select>
      </td>
    </tr>
  );
}

function LotCard({ lot }: { lot: Lot }) {
  const breakdown = lot.status_breakdown || {};
  const profit = Number(lot.profit_sum || 0);

  return (
    <Link
      href={`/admin/lotti/${lot.id}`}
      className="card p-4 hover:shadow-soft transition-all"
    >
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div className="min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="font-mono text-xs px-2 py-0.5 rounded-full bg-lilac-soft text-lilac-deep">
              {lot.code}
            </span>
            <span className={`text-[10px] px-2 py-0.5 rounded-full uppercase tracking-wider ${
              lot.status === "OPEN" ? "bg-mint text-mint-deep"
              : lot.status === "CLOSED" ? "bg-ink/10 text-ink"
              : "bg-ink/20 text-ink-soft"
            }`}>
              {lot.status === "OPEN" ? "Aperto" : lot.status === "CLOSED" ? "Chiuso" : "Archiviato"}
            </span>
            <h2 className="display text-lg text-ink truncate">{lot.title || "(senza nome)"}</h2>
          </div>
          <div className="flex flex-wrap gap-x-3 gap-y-1 text-xs text-ink-soft">
            {lot.purchase_date && <span>📅 {lot.purchase_date}</span>}
            {lot.purchase_platform && <span>🛒 {lot.purchase_platform}</span>}
            {lot.bought_by && <span>👤 {lot.bought_by}</span>}
            <span>📦 {lot.items_count} item · {lot.quantity_total} pezzi</span>
          </div>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-right">
          <div>
            <div className="text-[10px] uppercase tracking-wider text-ink-soft">Costo</div>
            <div className="text-sm font-semibold tabular-nums">{fmtMoney(lot.cost_sum)}</div>
          </div>
          <div>
            <div className="text-[10px] uppercase tracking-wider text-ink-soft">Ricavi</div>
            <div className="text-sm font-semibold tabular-nums">{fmtMoney(lot.revenue_sum)}</div>
          </div>
          <div>
            <div className="text-[10px] uppercase tracking-wider text-ink-soft">Profitto</div>
            <div className={`text-sm font-bold tabular-nums ${
              profit > 0 ? "text-mint-deep" : profit < 0 ? "text-pink-deep" : "text-ink-soft"
            }`}>
              {fmtMoney(lot.profit_sum)}
            </div>
          </div>
          <div>
            <div className="text-[10px] uppercase tracking-wider text-ink-soft">Immob.</div>
            <div className="text-sm font-semibold tabular-nums text-lilac-deep">{fmtMoney(lot.immobilizzato)}</div>
          </div>
        </div>
      </div>

      {Object.keys(breakdown).length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {Object.entries(breakdown).map(([s, n]) => (
            <span
              key={s}
              className={`text-[10px] px-2 py-0.5 rounded-full font-semibold ${STATUS_COLOR[s] ?? "bg-ink/10 text-ink"}`}
            >
              {STATUS_LABEL[s] ?? s}: {n}
            </span>
          ))}
        </div>
      )}
    </Link>
  );
}

function TotalCard({ label, value, color, accent }: { label: string; value: string; color: string; accent?: boolean }) {
  return (
    <div className="card p-3 relative overflow-hidden">
      <div className={`absolute -top-4 -right-4 w-16 h-16 rounded-full ${color} blur-2xl opacity-60`} />
      <span className="text-[10px] uppercase tracking-wider text-ink-soft relative block">{label}</span>
      <span className={`display mt-0.5 block tabular-nums relative ${accent ? "text-xl text-pink-deep" : "text-lg text-ink"}`}>
        {value}
      </span>
    </div>
  );
}
