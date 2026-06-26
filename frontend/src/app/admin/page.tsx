"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { AdminShell } from "@/components/admin/AdminShell";
import { CollapsibleSection } from "@/components/admin/CollapsibleSection";
import { adminApi } from "@/lib/admin-api";
import type {
  ArticleListResponse,
  CollectionRecap,
  ConsignmentRecap,
  CreationsRecap,
  ExpensesRecap,
  ExternalSalesRecap,
  InquiryStatus,
  InventoryTotali,
  WantedListResponse,
} from "@/lib/types";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ComposedChart,
  Legend,
  Line,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const COLORS = [
  "#e879a8", "#a890d8", "#7dd3c0", "#f4b860",
  "#f87171", "#60a5fa", "#9ca3af",
];

const NUM_FMT = new Intl.NumberFormat("it-IT", { maximumFractionDigits: 0 });

function fmtMoney(v: string | number | null | undefined, digits = 0): string {
  if (v == null || v === "") return "—";
  const n = typeof v === "number" ? v : Number(v);
  if (!Number.isFinite(n)) return "—";
  return new Intl.NumberFormat("it-IT", {
    style: "currency",
    currency: "EUR",
    maximumFractionDigits: digits,
    minimumFractionDigits: digits,
  }).format(n);
}

function todayYear() { return new Date().getFullYear(); }

interface InquiryListLite {
  total: number;
  items: { id: number; status: InquiryStatus }[];
}

export default function AdminDashboardPage() {
  const [year, setYear] = useState<number>(todayYear());
  const [stats, setStats] = useState<{
    articlesPublished: number;
    articlesDraft: number;
    inquiriesNew: number;
    inquiriesTotal: number;
    wantedActive: number;
  } | null>(null);
  const [totali, setTotali] = useState<InventoryTotali | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const [pub, draft, inqList, wantedList, tot] = await Promise.all([
          adminApi.get<ArticleListResponse>("/api/articles/?status=PUBLISHED&limit=1"),
          adminApi.get<ArticleListResponse>("/api/articles/?status=DRAFT&limit=1"),
          adminApi.get<InquiryListLite>("/api/inquiries/?limit=100"),
          adminApi.get<WantedListResponse>("/api/wanted/?status=ACTIVE&limit=1"),
          adminApi.get<InventoryTotali>(`/api/dashboard/totali?year=${year}`),
        ]);
        setStats({
          articlesPublished: pub.total,
          articlesDraft: draft.total,
          inquiriesNew: inqList.items.filter((i) => i.status === "NEW").length,
          inquiriesTotal: inqList.total,
          wantedActive: wantedList.total,
        });
        setTotali(tot);
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
      }
    })();
  }, [year]);

  const monthly = useMemo(() => {
    if (!totali) return [];
    return totali.monthly.map((m) => ({
      label: m.label,
      Ricavi: Number(m.revenue),
      Costi: Number(m.cost),
      Profitto: Number(m.profit),
      venduti: m.items_sold,
    }));
  }, [totali]);

  const catPie = useMemo(() => {
    if (!totali) return [];
    return totali.by_category
      .filter((c) => Number(c.revenue) > 0)
      .map((c) => ({ name: c.name, value: Number(c.revenue) }));
  }, [totali]);

  const profit = totali ? Number(totali.total_profit) : 0;
  const sideProfit = totali ? Number(totali.misc_revenue) - Number(totali.card_purchases) : 0;
  const grandProfit = profit + sideProfit;

  return (
    <AdminShell>
      <div className="flex items-end justify-between mb-1 gap-3 flex-wrap">
        <div>
          <h1 className="display text-2xl sm:text-3xl text-ink">Dashboard</h1>
          <p className="text-ink-soft mt-1 text-sm">
            Totali dall&apos;inventario (lotti + item) — clone della pagina &quot;Totali&quot; del Google Sheet.
          </p>
        </div>
        <select
          value={year}
          onChange={(e) => setYear(Number(e.target.value))}
          className="input"
          style={{ maxWidth: 140 }}
        >
          {[todayYear() + 1, todayYear(), todayYear() - 1, todayYear() - 2, todayYear() - 3].map((y) => (
            <option key={y} value={y}>Anno {y}</option>
          ))}
        </select>
      </div>

      {error && (
        <div className="card p-4 mt-4 text-pink-deep font-semibold">⚠ {error}</div>
      )}

      {/* Quick-stats operative */}
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3 mt-5">
        <Stat label="Pubblicati" value={stats?.articlesPublished} href="/admin/articles?status=PUBLISHED" tone="mint" icon="🎮" />
        <Stat label="Bozze" value={stats?.articlesDraft} href="/admin/articles?status=DRAFT" tone="lilac" icon="📝" />
        <Stat label="Richieste nuove" value={stats?.inquiriesNew} hint={stats ? `su ${stats.inquiriesTotal}` : ""} href="/admin/inquiries?status=NEW" tone="pink" icon="💬" />
        <Stat label="Wanted attivi" value={stats?.wantedActive} href="/admin/wanted" tone="sky" icon="🔍" />
      </div>

      {!totali && <p className="text-ink-soft mt-6">Caricamento totali…</p>}

      {totali && (
        <>
          {/* KPI inventario */}
          <h2 className="display text-xl text-ink mt-8 mb-3">📊 Bilancio {totali.year}</h2>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-2 mb-3">
            <Kpi label="Ricavi" value={fmtMoney(totali.total_revenue)} sub={`${totali.items_sold} venduti`} color="bg-mint" />
            <Kpi label="Costi" value={fmtMoney(totali.total_cost)} sub={`Fee+sped. ${fmtMoney(Number(totali.total_fees) + Number(totali.total_shipping))}`} color="bg-pink-soft" />
            <Kpi label="Profitto" value={fmtMoney(profit)} sub={`Lotti ${totali.lots_count}`} color={profit >= 0 ? "bg-mint" : "bg-pink"} accent />
            <Kpi label="Immobilizzato" value={fmtMoney(totali.total_immobilizzato)} sub={`${totali.items_available} disponibili`} color="bg-lilac-soft" />
          </div>

          <div className="card p-4 mb-4 grid sm:grid-cols-3 gap-3">
            <Mini label="Profitto inventario" value={fmtMoney(profit)} highlight={profit >= 0 ? "mint" : "pink"} />
            <Mini label="Vendite varie − Spese carte" value={fmtMoney(sideProfit)} highlight={sideProfit >= 0 ? "mint" : "pink"} />
            <Mini label="Profitto totale anno" value={fmtMoney(grandProfit)} highlight={grandProfit >= 0 ? "mint" : "pink"} bold />
          </div>

          {/* Charts row 1 */}
          <CollapsibleSection
            storageKey="charts-monthly-cat"
            title="📈 Andamento mensile + categorie"
            subtitle="Profitto/costi/ricavi mese per mese e split per categoria"
            defaultOpen
          >
          <div className="grid lg:grid-cols-3 gap-3 mb-2">
            <div className="card p-4 lg:col-span-2">
              <ResponsiveContainer width="100%" height={300}>
                <ComposedChart data={monthly}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(61,42,92,0.08)" />
                  <XAxis dataKey="label" tick={{ fontSize: 11, fill: "#3d2a5c" }} />
                  <YAxis tick={{ fontSize: 11, fill: "#3d2a5c" }} tickFormatter={(v) => fmtMoney(v)} width={70} />
                  <Tooltip
                    formatter={(v, name) => {
                      const n = Number(v);
                      const label = String(name ?? "");
                      return label === "venduti"
                        ? [NUM_FMT.format(n), label]
                        : [fmtMoney(n, 2), label];
                    }}
                    contentStyle={{ background: "#fffaf3", border: "1px solid rgba(61,42,92,0.12)", borderRadius: 8 }}
                  />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                  <Bar dataKey="Ricavi" fill="#7dd3c0" radius={[6, 6, 0, 0]} />
                  <Bar dataKey="Costi" fill="#f8a8c8" radius={[6, 6, 0, 0]} />
                  <Line type="monotone" dataKey="Profitto" stroke="#3d2a5c" strokeWidth={2} dot={{ r: 4 }} />
                </ComposedChart>
              </ResponsiveContainer>
            </div>

            <div className="card p-4">
              {catPie.length === 0 ? (
                <p className="text-xs text-ink-soft text-center py-12">Nessuna vendita.</p>
              ) : (
                <ResponsiveContainer width="100%" height={240}>
                  <PieChart>
                    <Pie
                      data={catPie}
                      cx="50%" cy="50%"
                      innerRadius={50} outerRadius={90}
                      paddingAngle={2}
                      dataKey="value"
                      label={({ name, percent }) => `${name} ${((percent ?? 0) * 100).toFixed(0)}%`}
                      labelLine={false}
                      style={{ fontSize: 11 }}
                    >
                      {catPie.map((_, i) => (
                        <Cell key={i} fill={COLORS[i % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(v) => fmtMoney(Number(v), 2)} />
                  </PieChart>
                </ResponsiveContainer>
              )}
              <div className="mt-2 space-y-1 text-xs">
                {totali.by_category.slice(0, 6).map((c, i) => (
                  <div key={c.slug} className="flex items-center justify-between">
                    <span className="flex items-center gap-2">
                      <span className="inline-block w-2.5 h-2.5 rounded-full" style={{ background: COLORS[i % COLORS.length] }} />
                      {c.name}
                    </span>
                    <span className="tabular-nums text-ink-soft">{fmtMoney(c.revenue)}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
          </CollapsibleSection>

          {/* Charts row 2: platforms */}
          <CollapsibleSection
            storageKey="charts-platforms"
            title="🛒 Piattaforme"
            subtitle="Ricavi per piattaforma vendita / Costi per piattaforma acquisto"
            defaultOpen={totali.by_sold_platform.length > 0 || totali.by_purchase_platform.length > 0}
          >
          <div className="grid lg:grid-cols-2 gap-3">
            <PlatformChart
              title="Ricavi per piattaforma vendita"
              data={totali.by_sold_platform.map((p) => ({ label: p.label, value: Number(p.revenue), items: p.items }))}
              colorIdx={0}
              suffix="ricavo"
            />
            <PlatformChart
              title="Costi per piattaforma acquisto"
              data={totali.by_purchase_platform.map((p) => ({ label: p.label, value: Number(p.cost), items: p.items }))}
              colorIdx={1}
              suffix="costo"
            />
          </div>
          </CollapsibleSection>

          {/* Persons */}
          <CollapsibleSection
            storageKey="persons"
            title="👥 Per persona"
            subtitle="Chi compra · chi vende"
            defaultOpen={totali.by_bought_by.length > 0 || totali.by_sold_by.length > 0}
          >
          <div className="grid lg:grid-cols-2 gap-3">
            <PersonsTable title="Chi compra" rows={totali.by_bought_by} valueKey="cost" valueLabel="Costo" />
            <PersonsTable title="Chi vende" rows={totali.by_sold_by} valueKey="revenue" valueLabel="Ricavo" />
          </div>
          </CollapsibleSection>

          {/* Category detail */}
          <CollapsibleSection
            storageKey="category-detail"
            title="🏷 Dettaglio per categoria"
            subtitle="Ricavi/costi/profitto/immobilizzato per categoria top-level"
            defaultOpen={totali.by_category.length > 0}
          >
          <div className="card overflow-x-auto">
            <table className="min-w-full text-xs">
              <thead className="bg-white/60 backdrop-blur border-y border-ink/10 text-ink-soft uppercase tracking-wider">
                <tr>
                  <Th>Categoria</Th>
                  <Th className="text-right">Ricavi</Th>
                  <Th className="text-right">Costi</Th>
                  <Th className="text-right">Profitto</Th>
                  <Th className="text-right">Immob.</Th>
                  <Th className="text-right">Venduti</Th>
                  <Th className="text-right">Disp.</Th>
                </tr>
              </thead>
              <tbody>
                {totali.by_category.map((c) => {
                  const p = Number(c.profit);
                  return (
                    <tr key={c.slug} className="border-b border-ink/5 hover:bg-pink-soft/20">
                      <Td className="font-semibold">{c.name}</Td>
                      <Td className="text-right tabular-nums">{fmtMoney(c.revenue)}</Td>
                      <Td className="text-right tabular-nums text-ink-soft">{fmtMoney(c.cost)}</Td>
                      <Td className={`text-right tabular-nums font-bold ${p > 0 ? "text-mint-deep" : p < 0 ? "text-pink-deep" : "text-ink-soft"}`}>
                        {fmtMoney(c.profit)}
                      </Td>
                      <Td className="text-right tabular-nums text-lilac-deep">{fmtMoney(c.immobilizzato)}</Td>
                      <Td className="text-right tabular-nums">{c.items_sold}</Td>
                      <Td className="text-right tabular-nums">{c.items_available}</Td>
                    </tr>
                  );
                })}
                {totali.by_category.length === 0 && (
                  <tr><Td className="text-center text-ink-soft py-6">Nessun dato.</Td></tr>
                )}
              </tbody>
            </table>
          </div>
          </CollapsibleSection>

          {/* Vendite esterne (recap dedicato) */}
          <CollapsibleSection
            storageKey="external-sales"
            title="💸 Vendite esterne"
            subtitle="Vendite NON legate al catalogo del sito"
            badge={totali.external_sales.count > 0 ? `${totali.external_sales.count}` : undefined}
            defaultOpen={totali.external_sales.count > 0}
          >
            <ExternalSalesSection data={totali.external_sales} />
          </CollapsibleSection>

          {/* Carte (no flipping) */}
          <CollapsibleSection
            storageKey="collection"
            title="🎴 Carte (no flipping)"
            subtitle="Vendite carte singole — profitto netto post-spese"
            badge={totali.collection.sold_count > 0 ? `${totali.collection.sold_count}` : undefined}
            defaultOpen={totali.collection.sold_count > 0 || totali.collection.voices_count > 0}
          >
            <CollectionSection data={totali.collection} cardsExpenses={totali.expenses.cards_total} />
          </CollapsibleSection>

          {/* Creazioni handmade */}
          <CollapsibleSection
            storageKey="creations"
            title="🎨 Creazioni handmade"
            subtitle="Vendite di creazioni fatte a mano — profitto netto"
            badge={totali.creations.count > 0 ? `${totali.creations.count}` : undefined}
            defaultOpen={totali.creations.count > 0}
          >
            <CreationsSection data={totali.creations} creationsExpenses={totali.expenses.creations_total} />
          </CollapsibleSection>

          {/* Contovendita */}
          <CollapsibleSection
            storageKey="consignment"
            title="🤝 Contovendita"
            subtitle="Vendite per conto terzi: commissione mia + saldo da girare"
            badge={Number(totali.consignment.owed) > 0 ? `${fmtMoney(totali.consignment.owed)} da girare` : undefined}
            defaultOpen={totali.consignment.count > 0}
          >
            <ConsignmentSection data={totali.consignment} />
          </CollapsibleSection>

          {/* Spese unificate */}
          <CollapsibleSection
            storageKey="expenses"
            title="💰 Spese"
            subtitle="Bulk carte + spese generiche"
            badge={Number(totali.expenses.total) > 0 ? fmtMoney(totali.expenses.total) : undefined}
            defaultOpen={Number(totali.expenses.total) > 0}
          >
            <ExpensesSection data={totali.expenses} />
          </CollapsibleSection>

        </>
      )}

      {/* Quick actions */}
      <div className="grid sm:grid-cols-2 gap-3 mt-2">
        <Link href="/admin/lotti/new" className="card card-clickable p-5 flex items-start gap-3">
          <span className="text-2xl">📦</span>
          <div>
            <h3 className="display text-base text-ink">Nuovo lotto</h3>
            <p className="text-ink-soft text-xs mt-1">Wizard creazione lotto + item.</p>
          </div>
        </Link>
        <Link href="/admin/articles/new" className="card card-clickable p-5 flex items-start gap-3">
          <span className="text-2xl">➕</span>
          <div>
            <h3 className="display text-base text-ink">Nuovo articolo</h3>
            <p className="text-ink-soft text-xs mt-1">Aggiungi pezzo al catalogo pubblico.</p>
          </div>
        </Link>
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

function CollectionSection({ data, cardsExpenses }: { data: CollectionRecap; cardsExpenses: string }) {
  const grossProfit = Number(data.sold_profit);
  const expenses = Number(cardsExpenses || 0);
  const netProfit = grossProfit - expenses;
  const hasAny = data.sold_count > 0 || data.voices_count > 0;
  return (
    <div className="card p-4">
      <div className="flex justify-end mb-2">
        <Link href="/admin/vendite/carte" className="btn btn-ghost text-xs">
          Apri vendite →
        </Link>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-2 mb-3">
        <Kpi label="Vendute (anno)" value={String(data.sold_count)} color="bg-mint" />
        <Kpi label="Ricavi" value={fmtMoney(data.sold_revenue)} color="bg-mint" />
        <Kpi
          label="− Spese carte"
          value={fmtMoney(expenses)}
          sub="bulk + card-related"
          color="bg-pink-soft"
        />
        <Kpi
          label="Profitto netto"
          value={fmtMoney(netProfit)}
          sub={`Lordo ${fmtMoney(grossProfit)}`}
          color={netProfit >= 0 ? "bg-mint" : "bg-pink"}
          accent
        />
      </div>

      {hasAny && data.by_owner.length > 0 && (
        <div>
          <p className="text-[10px] uppercase tracking-wider text-ink-soft mb-1">Per proprietario</p>
          <table className="w-full text-xs">
            <thead className="text-ink-soft">
              <tr>
                <th className="text-left py-1">Persona</th>
                <th className="text-right py-1">Vendute</th>
                <th className="text-right py-1">Ricavi</th>
                <th className="text-right py-1">Costo assegnato</th>
              </tr>
            </thead>
            <tbody>
              {data.by_owner.map((r) => (
                <tr key={r.label} className="border-t border-ink/5">
                  <td className="py-1.5 font-semibold">{r.label}</td>
                  <td className="py-1.5 text-right tabular-nums">{r.items}</td>
                  <td className="py-1.5 text-right tabular-nums text-mint-deep">{fmtMoney(r.revenue)}</td>
                  <td className="py-1.5 text-right tabular-nums text-ink-soft">{fmtMoney(r.cost)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {!hasAny && (
        <p className="text-xs text-ink-soft py-3">
          Nessuna vendita registrata. <Link href="/admin/vendite/carte" className="underline">Registrane una</Link>.
        </p>
      )}
    </div>
  );
}

function ConsignmentSection({ data }: { data: ConsignmentRecap }) {
  const owed = Number(data.owed || 0);
  const hasAny = data.count > 0;

  return (
    <div className="card p-4">
      <div className="flex justify-end mb-2">
        <Link href="/admin/vendite/contovendita" className="btn btn-ghost text-xs">
          Apri contovendita →
        </Link>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-2 mb-3">
        <Kpi label="Vendite" value={fmtMoney(data.sales_total)} sub={`${data.count} pezzi`} color="bg-mint" />
        <Kpi label="Mia commissione" value={fmtMoney(data.commission_kept)} color="bg-mint" accent />
        <Kpi
          label="Da girare"
          value={fmtMoney(data.owed)}
          sub="ai committenti"
          color={owed > 0 ? "bg-pink" : "bg-ink/5"}
          accent={owed > 0}
        />
        <Kpi label="Già pagato" value={fmtMoney(data.paid_already)} color="bg-lilac-soft" />
      </div>

      {hasAny && data.by_consignor.length > 0 && (
        <div>
          <p className="text-[10px] uppercase tracking-wider text-ink-soft mb-1">Per committente</p>
          <table className="w-full text-xs">
            <thead className="text-ink-soft">
              <tr>
                <th className="text-left py-1">Nome</th>
                <th className="text-right py-1">Pezzi</th>
                <th className="text-right py-1">Vendite</th>
                <th className="text-right py-1">Da girare</th>
              </tr>
            </thead>
            <tbody>
              {data.by_consignor.map((r) => (
                <tr key={r.label} className="border-t border-ink/5">
                  <td className="py-1.5 font-semibold">{r.label}</td>
                  <td className="py-1.5 text-right tabular-nums">{r.items}</td>
                  <td className="py-1.5 text-right tabular-nums text-mint-deep">{fmtMoney(r.revenue)}</td>
                  <td className={`py-1.5 text-right tabular-nums ${Number(r.cost) > 0 ? "text-pink-deep font-bold" : "text-ink-soft"}`}>
                    {fmtMoney(r.cost)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {!hasAny && (
        <p className="text-xs text-ink-soft py-3">
          Nessuna vendita contovendita.{" "}
          <Link href="/admin/vendite/contovendita" className="underline">Aggiungine una</Link>.
        </p>
      )}
    </div>
  );
}

function CreationsSection({ data, creationsExpenses }: { data: CreationsRecap; creationsExpenses: string }) {
  const grossProfit = Number(data.gross_profit);
  const expenses = Number(creationsExpenses || 0);
  const netProfit = grossProfit - expenses;
  const hasAny = data.count > 0;

  return (
    <div className="card p-4">
      <div className="flex justify-end mb-2">
        <Link href="/admin/vendite/creazioni" className="btn btn-ghost text-xs">
          Apri creazioni →
        </Link>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-5 gap-2 mb-3">
        <Kpi label="Vendute" value={String(data.count)} color="bg-mint" />
        <Kpi label="Ricavi" value={fmtMoney(data.revenue)} color="bg-mint" />
        <Kpi label="− Materiali" value={fmtMoney(data.material_cost)} color="bg-pink-soft" />
        <Kpi label="− Altre spese" value={fmtMoney(expenses)} sub="related-to-creations" color="bg-pink-soft" />
        <Kpi
          label="Profitto netto"
          value={fmtMoney(netProfit)}
          sub={`Lordo ${fmtMoney(grossProfit)}`}
          color={netProfit >= 0 ? "bg-mint" : "bg-pink"}
          accent
        />
      </div>

      {hasAny && data.by_seller.length > 0 && (
        <div>
          <p className="text-[10px] uppercase tracking-wider text-ink-soft mb-1">Per chi crea / vende</p>
          <table className="w-full text-xs">
            <thead className="text-ink-soft">
              <tr>
                <th className="text-left py-1">Persona</th>
                <th className="text-right py-1">Pezzi</th>
                <th className="text-right py-1">Ricavi</th>
                <th className="text-right py-1">Materiali</th>
              </tr>
            </thead>
            <tbody>
              {data.by_seller.map((r) => (
                <tr key={r.label} className="border-t border-ink/5">
                  <td className="py-1.5 font-semibold">{r.label}</td>
                  <td className="py-1.5 text-right tabular-nums">{r.items}</td>
                  <td className="py-1.5 text-right tabular-nums text-mint-deep">{fmtMoney(r.revenue)}</td>
                  <td className="py-1.5 text-right tabular-nums text-ink-soft">{fmtMoney(r.cost)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {!hasAny && (
        <p className="text-xs text-ink-soft py-3">
          Nessuna creazione venduta nell&apos;anno.{" "}
          <Link href="/admin/vendite/creazioni" className="underline">Aggiungine una</Link>.
        </p>
      )}
    </div>
  );
}

function ExpensesSection({ data }: { data: ExpensesRecap }) {
  const cats = Object.entries(data.by_category).filter(([, v]) => Number(v) !== 0);
  return (
    <div className="card p-4">
      <div className="flex justify-end mb-2">
        <Link href="/admin/spese" className="btn btn-ghost text-xs">
          Apri spese →
        </Link>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-5 gap-2 mb-3">
        <Kpi label="Spese carte" value={fmtMoney(data.card_purchases)} sub={`${data.card_purchases_count} voci`} color="bg-pink-soft" />
        <Kpi label="Altre spese" value={fmtMoney(data.other_expenses)} sub={`${data.other_expenses_count} voci`} color="bg-pink-soft" />
        <Kpi label="→ Carte" value={fmtMoney(data.card_related_other)} sub="da altre spese" color="bg-lilac-soft" />
        <Kpi label="→ Creazioni" value={fmtMoney(data.creation_related)} sub="da altre spese" color="bg-lilac-soft" />
        <Kpi label="Totale uscite" value={fmtMoney(data.total)} color="bg-pink" accent />
      </div>

      {cats.length > 0 && (
        <div>
          <p className="text-[10px] uppercase tracking-wider text-ink-soft mb-1">Altre spese per categoria</p>
          <div className="flex flex-wrap gap-1.5">
            {cats.map(([cat, amt]) => (
              <span key={cat} className="text-[11px] px-2 py-1 rounded-full bg-ink/5 text-ink">
                <strong className="capitalize">{cat}</strong> {fmtMoney(amt)}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function ExternalSalesSection({ data }: { data: ExternalSalesRecap }) {
  const monthly = data.monthly.map((m) => ({
    label: m.label,
    Vendite: Number(m.revenue),
    count: m.items_sold,
  }));
  const hasAny = Number(data.total) > 0 || data.count > 0;

  return (
    <div className="card p-4">
      <div className="flex justify-end mb-2">
        <Link href="/admin/vendite/esterne" className="btn btn-ghost text-xs">
          Apri tabella →
        </Link>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-2 mb-3">
        <Kpi label="Totale" value={fmtMoney(data.total)} sub={`${data.count} vendite`} color="bg-mint" accent />
        <Kpi label="Incassato" value={fmtMoney(data.paid)} color="bg-mint" />
        <Kpi label="Da incassare" value={fmtMoney(data.unpaid)} color={Number(data.unpaid) > 0 ? "bg-pink" : "bg-ink/5"} accent={Number(data.unpaid) > 0} />
        <Kpi label="Vendite/mese" value={data.count > 0 ? (data.count / 12).toFixed(1) : "0"} color="bg-lilac-soft" />
      </div>

      {hasAny ? (
        <div className="grid lg:grid-cols-3 gap-3">
          <div className="lg:col-span-2">
            <p className="text-[10px] uppercase tracking-wider text-ink-soft mb-1">Mensile</p>
            <ResponsiveContainer width="100%" height={180}>
              <BarChart data={monthly}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(61,42,92,0.08)" />
                <XAxis dataKey="label" tick={{ fontSize: 11, fill: "#3d2a5c" }} />
                <YAxis tick={{ fontSize: 11, fill: "#3d2a5c" }} tickFormatter={(v) => fmtMoney(v)} width={70} />
                <Tooltip
                  formatter={(v) => [fmtMoney(Number(v), 2), "vendite"] as [string, string]}
                  contentStyle={{ background: "#fffaf3", border: "1px solid rgba(61,42,92,0.12)", borderRadius: 8 }}
                />
                <Bar dataKey="Vendite" fill="#7dd3c0" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div>
            <p className="text-[10px] uppercase tracking-wider text-ink-soft mb-1">Chi vende</p>
            {data.by_seller.length === 0 ? (
              <p className="text-xs text-ink-soft py-2">—</p>
            ) : (
              <table className="w-full text-xs mb-3">
                <tbody>
                  {data.by_seller.map((r) => (
                    <tr key={r.label} className="border-t border-ink/5">
                      <td className="py-1.5 font-semibold">{r.label}</td>
                      <td className="py-1.5 text-right tabular-nums">{fmtMoney(r.revenue)}</td>
                      <td className="py-1.5 text-right text-ink-soft">{r.items}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}

            <p className="text-[10px] uppercase tracking-wider text-ink-soft mb-1">Per piattaforma</p>
            {data.by_platform.length === 0 ? (
              <p className="text-xs text-ink-soft py-2">—</p>
            ) : (
              <table className="w-full text-xs">
                <tbody>
                  {data.by_platform.slice(0, 5).map((r) => (
                    <tr key={r.label} className="border-t border-ink/5">
                      <td className="py-1.5 font-semibold">{r.label}</td>
                      <td className="py-1.5 text-right tabular-nums">{fmtMoney(r.revenue)}</td>
                      <td className="py-1.5 text-right text-ink-soft">{r.items}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      ) : (
        <p className="text-xs text-ink-soft py-3">
          Nessuna vendita esterna nell&apos;anno. <Link href="/admin/vendite/esterne" className="underline">Aggiungine una</Link>.
        </p>
      )}
    </div>
  );
}

function PlatformChart({ title, data, colorIdx, suffix }: {
  title: string;
  data: { label: string; value: number; items: number }[];
  colorIdx: number;
  suffix: string;
}) {
  const filtered = data.filter((d) => d.value > 0).slice(0, 8);
  return (
    <div className="card p-4">
      <h3 className="display text-base text-ink mb-3">{title}</h3>
      {filtered.length === 0 ? (
        <p className="text-xs text-ink-soft text-center py-12">Nessun dato.</p>
      ) : (
        <ResponsiveContainer width="100%" height={Math.max(180, filtered.length * 32)}>
          <BarChart data={filtered} layout="vertical" margin={{ left: 50 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(61,42,92,0.08)" />
            <XAxis type="number" tick={{ fontSize: 11, fill: "#3d2a5c" }} tickFormatter={(v) => fmtMoney(v)} />
            <YAxis type="category" dataKey="label" tick={{ fontSize: 11, fill: "#3d2a5c" }} width={90} />
            <Tooltip
              formatter={(v) => [fmtMoney(Number(v), 2), suffix] as [string, string]}
              contentStyle={{ background: "#fffaf3", border: "1px solid rgba(61,42,92,0.12)", borderRadius: 8 }}
            />
            <Bar dataKey="value" fill={COLORS[colorIdx]} radius={[0, 6, 6, 0]} />
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}

function PersonsTable({ title, rows, valueKey, valueLabel }: {
  title: string;
  rows: { label: string; revenue: string; cost: string; items: number }[];
  valueKey: "revenue" | "cost";
  valueLabel: string;
}) {
  return (
    <div className="card p-4">
      <h3 className="display text-base text-ink mb-2">{title}</h3>
      {rows.length === 0 ? (
        <p className="text-xs text-ink-soft py-4">Nessun dato.</p>
      ) : (
        <table className="w-full text-xs">
          <thead className="text-ink-soft uppercase tracking-wider">
            <tr>
              <th className="text-left py-1">Persona</th>
              <th className="text-right py-1">{valueLabel}</th>
              <th className="text-right py-1">Item</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.label} className="border-t border-ink/5">
                <td className="py-1.5 font-semibold">{r.label}</td>
                <td className="py-1.5 text-right tabular-nums">{fmtMoney(r[valueKey])}</td>
                <td className="py-1.5 text-right tabular-nums text-ink-soft">{r.items}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

function Kpi({ label, value, sub, color, accent }: { label: string; value: string; sub?: string; color: string; accent?: boolean }) {
  return (
    <div className="card p-3 relative overflow-hidden">
      <div className={`absolute -top-4 -right-4 w-20 h-20 rounded-full ${color} blur-2xl opacity-60`} />
      <span className="text-[10px] uppercase tracking-wider text-ink-soft relative block">{label}</span>
      <span className={`display block tabular-nums relative ${accent ? "text-2xl text-pink-deep" : "text-xl text-ink"}`}>
        {value}
      </span>
      {sub && <span className="text-[10px] text-ink-soft block relative mt-0.5">{sub}</span>}
    </div>
  );
}

function Mini({ label, value, highlight, bold }: { label: string; value: string; highlight: "mint" | "pink"; bold?: boolean }) {
  const color = highlight === "mint" ? "text-mint-deep" : "text-pink-deep";
  return (
    <div>
      <div className="text-[10px] uppercase tracking-wider text-ink-soft">{label}</div>
      <div className={`tabular-nums ${color} ${bold ? "text-2xl font-bold" : "text-lg font-semibold"}`}>{value}</div>
    </div>
  );
}

const TONE_BG: Record<string, string> = {
  pink: "from-pink/30 to-pink-soft",
  mint: "from-mint/30 to-mint-soft",
  sky: "from-sky/30 to-sky-soft",
  lilac: "from-lilac/30 to-lilac-soft",
};

function Stat({ label, value, hint, href, tone, icon }: {
  label: string;
  value: number | undefined;
  hint?: string;
  href: string;
  tone: "pink" | "mint" | "sky" | "lilac";
  icon: string;
}) {
  return (
    <Link href={href} className="card card-clickable p-4 block relative overflow-hidden">
      <div className={`absolute -top-6 -right-6 w-24 h-24 rounded-full bg-gradient-to-br ${TONE_BG[tone]} blur-xl pointer-events-none`} />
      <div className="relative">
        <div className="flex items-center justify-between mb-1">
          <p className="text-xs uppercase tracking-wider text-ink-soft">{label}</p>
          <span className="text-lg opacity-60">{icon}</span>
        </div>
        <p className="display text-3xl text-ink leading-none">{value ?? "…"}</p>
        {hint && <p className="text-xs text-ink-soft mt-1">{hint}</p>}
      </div>
    </Link>
  );
}

function Th({ children, className = "" }: { children?: React.ReactNode; className?: string }) {
  return <th className={`py-2 px-3 font-semibold whitespace-nowrap ${className}`}>{children}</th>;
}

function Td({ children, className = "" }: { children?: React.ReactNode; className?: string }) {
  return <td className={`py-1.5 px-3 align-middle ${className}`}>{children}</td>;
}
