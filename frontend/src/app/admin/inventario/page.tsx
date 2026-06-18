"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { AdminShell } from "@/components/admin/AdminShell";
import { adminApi } from "@/lib/admin-api";
import { useCategories } from "@/lib/useCategories";
import type { Article, ArticleListResponse, Category } from "@/lib/types";

const PURCHASE_PLATFORMS = ["Vinted", "mercato", "Subito", "eBay", "Wallapop", "Regalo", "Altro"];
const SALE_PLATFORMS = ["Vinted", "eBay", "Wallapop", "Subito", "CardTrader", "mercato", "Altro"];
const PEOPLE = ["C", "D"];

function todayYear() {
  return new Date().getFullYear();
}

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

export default function AdminInventarioPage() {
  const { flat: categories } = useCategories();
  const [items, setItems] = useState<Article[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [year, setYear] = useState<string>(String(todayYear()));
  const [categoryFilter, setCategoryFilter] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("");

  async function reload() {
    setLoading(true);
    setError(null);
    try {
      const qs = new URLSearchParams({ limit: "100" });
      if (statusFilter) qs.set("status", statusFilter);
      if (categoryFilter) qs.set("category_id", categoryFilter);
      const data = await adminApi.get<ArticleListResponse>(`/api/articles/?${qs}`);
      setItems(data.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter, categoryFilter]);

  const filtered = useMemo(() => {
    if (!year) return items;
    const y = Number(year);
    return items.filter((a) => {
      const pY = a.purchase_date ? new Date(a.purchase_date).getFullYear() : null;
      const sY = a.sold_at ? new Date(a.sold_at).getFullYear() : null;
      return pY === y || sY === y || pY == null;
    });
  }, [items, year]);

  const totals = useMemo(() => {
    let revenue = 0;
    let cost = 0;
    let netRev = 0;
    let profit = 0;
    let immob = 0;
    for (const a of filtered) {
      const sold = a.status === "SOLD";
      const p = Number(a.price || 0);
      const c = Number(a.cost || 0);
      const f = Number(a.fee_amount || 0);
      const s = Number(a.shipping_cost || 0);
      if (sold) {
        revenue += p;
        cost += c;
        netRev += p - f - s;
        profit += p - f - s - c;
      } else if (c > 0) {
        immob += c;
      }
    }
    return { revenue, cost, netRev, profit, immob };
  }, [filtered]);

  return (
    <AdminShell>
      <div className="flex items-end justify-between mb-6 gap-3 flex-wrap">
        <div>
          <h1 className="display text-3xl text-ink">Inventario</h1>
          <p className="text-ink-soft mt-1 text-sm">
            Clone di "Flipping Inventario" + "Carte Pokemon Inventario". Click su una
            riga per aprire la scheda articolo completa.
          </p>
        </div>
        <Link href="/admin/articles/new" className="btn btn-primary">
          ➕ Nuovo articolo
        </Link>
      </div>

      {error && <p className="text-pink-deep mb-4">⚠ {error}</p>}

      {/* Filtri */}
      <div className="card p-4 mb-4 grid sm:grid-cols-4 gap-3">
        <label className="block">
          <span className="text-xs font-bold uppercase tracking-wider text-ink-soft">
            Anno
          </span>
          <select
            value={year}
            onChange={(e) => setYear(e.target.value)}
            className="input mt-1"
          >
            <option value="">Tutti</option>
            {[todayYear(), todayYear() - 1, todayYear() - 2].map((y) => (
              <option key={y} value={y}>
                {y}
              </option>
            ))}
          </select>
        </label>
        <label className="block">
          <span className="text-xs font-bold uppercase tracking-wider text-ink-soft">
            Categoria
          </span>
          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            className="input mt-1"
          >
            <option value="">Tutte</option>
            {renderCategoryOptions(categories)}
          </select>
        </label>
        <label className="block">
          <span className="text-xs font-bold uppercase tracking-wider text-ink-soft">
            Stato
          </span>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="input mt-1"
          >
            <option value="">Tutti</option>
            <option value="DRAFT">Bozza</option>
            <option value="PUBLISHED">Online</option>
            <option value="SOLD">Venduto</option>
            <option value="ARCHIVED">Archiviato</option>
          </select>
        </label>
        <div className="flex items-end">
          <button
            type="button"
            onClick={reload}
            className="btn btn-ghost text-sm w-full"
            disabled={loading}
          >
            ↻ Aggiorna
          </button>
        </div>
      </div>

      {/* Totali riepilogo */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 mb-4">
        <TotalCard label="Ricavi (venduti)" value={fmtMoney(totals.revenue)} color="bg-mint" />
        <TotalCard label="Costi (venduti)" value={fmtMoney(totals.cost)} color="bg-pink-soft" />
        <TotalCard label="Ricavo netto" value={fmtMoney(totals.netRev)} color="bg-sky" />
        <TotalCard label="Profitto" value={fmtMoney(totals.profit)} color="bg-mint" />
        <TotalCard label="Immobilizzato" value={fmtMoney(totals.immob)} color="bg-lilac-soft" />
      </div>

      {loading && <p className="text-ink-soft">Caricamento…</p>}

      {!loading && filtered.length === 0 && (
        <div className="card p-10 text-center">
          <p className="text-ink-soft">Nessun articolo con i filtri correnti.</p>
        </div>
      )}

      {!loading && filtered.length > 0 && (
        <div className="card overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="bg-white/60 backdrop-blur border-b border-ink/10 text-ink-soft text-[11px] uppercase tracking-wider">
              <tr>
                <Th>Lotto</Th>
                <Th>Oggetto</Th>
                <Th>Categoria</Th>
                <Th className="hidden md:table-cell">Acquisto</Th>
                <Th className="text-right">Costo</Th>
                <Th className="hidden md:table-cell">Pf. acq</Th>
                <Th className="hidden lg:table-cell">Compra</Th>
                <Th className="hidden md:table-cell">Vendita</Th>
                <Th className="text-right">Ricavo</Th>
                <Th className="text-right hidden lg:table-cell">Fee</Th>
                <Th className="text-right hidden lg:table-cell">Sped.</Th>
                <Th className="text-right">Profitto</Th>
                <Th className="text-right hidden md:table-cell">Immob.</Th>
                <Th>Stato</Th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((a) => {
                const sold = a.status === "SOLD";
                return (
                  <tr
                    key={a.id}
                    className="border-b border-ink/5 hover:bg-pink-soft/30 transition-colors"
                  >
                    <Td>
                      <Link
                        href={`/admin/articles/${a.id}`}
                        className="font-mono text-xs text-pink-deep hover:underline"
                      >
                        {a.lotto || `#${a.id}`}
                      </Link>
                    </Td>
                    <Td>
                      <Link
                        href={`/admin/articles/${a.id}`}
                        className="text-ink font-semibold hover:underline"
                      >
                        {a.title}
                      </Link>
                      {a.card_collection && (
                        <span className="block text-[10px] text-ink-soft">
                          {a.card_collection}
                          {a.card_number ? ` · ${a.card_number}` : ""}
                          {a.card_finish ? ` · ${a.card_finish}` : ""}
                        </span>
                      )}
                    </Td>
                    <Td className="text-xs text-ink-soft">
                      {a.parent_category && a.category
                        ? `${a.parent_category.name} › ${a.category.name}`
                        : a.category?.name ?? "—"}
                    </Td>
                    <Td className="hidden md:table-cell text-xs text-ink-soft">
                      {a.purchase_date ?? "—"}
                    </Td>
                    <Td className="text-right tabular-nums">{fmtMoney(a.cost)}</Td>
                    <Td className="hidden md:table-cell text-xs text-ink-soft">
                      {a.purchase_platform ?? "—"}
                    </Td>
                    <Td className="hidden lg:table-cell text-xs text-ink-soft">
                      {a.bought_by ?? "—"}
                    </Td>
                    <Td className="hidden md:table-cell text-xs text-ink-soft">
                      {a.sold_at ? a.sold_at.split("T")[0] : "—"}
                    </Td>
                    <Td className="text-right tabular-nums">
                      {sold ? fmtMoney(a.price) : "—"}
                    </Td>
                    <Td className="hidden lg:table-cell text-right text-xs tabular-nums">
                      {fmtMoney(a.fee_amount)}
                    </Td>
                    <Td className="hidden lg:table-cell text-right text-xs tabular-nums">
                      {fmtMoney(a.shipping_cost)}
                    </Td>
                    <Td className="text-right tabular-nums">
                      <span className={
                        Number(a.profit ?? 0) > 0
                          ? "text-mint-deep font-bold"
                          : Number(a.profit ?? 0) < 0
                            ? "text-pink-deep font-bold"
                            : "text-ink-soft"
                      }>
                        {sold ? fmtMoney(a.profit) : "—"}
                      </span>
                    </Td>
                    <Td className="hidden md:table-cell text-right text-xs tabular-nums">
                      {fmtMoney(a.immobilizzato)}
                    </Td>
                    <Td>
                      <span className={`chip text-[10px] ${
                        sold ? "chip-pink" :
                          a.status === "PUBLISHED" ? "chip-mint" :
                            a.status === "ARCHIVED" ? "chip-sky" :
                              "chip-lilac"
                      }`}>
                        {sold ? "Venduto" :
                          a.status === "PUBLISHED" ? "Online" :
                            a.status === "ARCHIVED" ? "Archiviato" : "Bozza"}
                      </span>
                    </Td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      <p className="text-xs text-ink-soft mt-3">
        {filtered.length} righe · Per modificare costo/fee/spedizione/lotto entra
        nella scheda articolo (click su Lotto o Oggetto).
      </p>

      <style>{`
        .input {
          display: block;
          width: 100%;
          padding: 0.5rem 0.7rem;
          border: 1px solid rgba(61, 42, 92, 0.12);
          border-radius: 12px;
          background: #fffaf3;
          color: #3d2a5c;
          font-family: "Manrope", sans-serif;
          font-size: 0.9rem;
          outline: none;
        }
        .input:focus {
          box-shadow: 0 0 0 3px rgba(248, 168, 200, 0.45);
          border-color: #e879a8;
        }
      `}</style>
    </AdminShell>
  );
}

function Th({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <th className={`text-left py-2 px-3 font-semibold ${className}`}>{children}</th>;
}

function Td({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <td className={`py-2 px-3 ${className}`}>{children}</td>;
}

function TotalCard({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div className="card p-3 relative overflow-hidden">
      <div className={`absolute -top-4 -right-4 w-16 h-16 rounded-full ${color} blur-2xl opacity-50`} />
      <span className="text-[10px] uppercase tracking-wider text-ink-soft relative block">{label}</span>
      <span className="display text-base text-ink mt-0.5 block tabular-nums relative">{value}</span>
    </div>
  );
}

function renderCategoryOptions(flat: Category[]) {
  const tops = flat.filter((c) => c.parent_id == null);
  return tops.flatMap((top) => [
    <option key={top.id} value={top.id}>
      {top.name}
    </option>,
    ...flat
      .filter((c) => c.parent_id === top.id)
      .map((sub) => (
        <option key={sub.id} value={sub.id}>
          {"  ↳ "} {sub.name}
        </option>
      )),
  ]);
}
