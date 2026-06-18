"use client";

import { useEffect, useMemo, useState } from "react";
import { AdminShell } from "@/components/admin/AdminShell";
import { VenditeNav } from "@/components/admin/VenditeNav";
import { adminApi } from "@/lib/admin-api";
import { usePlatforms } from "@/lib/usePlatforms";
import type {
  ConsignmentListResponse,
  ConsignmentSale,
  ConsignorBreakdown,
} from "@/lib/types";

const PEOPLE = ["", "C", "D"];
const DEFAULT_COMMISSION_PCT = "10";

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

function todayYear() { return new Date().getFullYear(); }
function todayISO() { return new Date().toISOString().slice(0, 10); }

export default function ContovenditaPage() {
  const { items: platformList } = usePlatforms();
  const platformNames = ["", ...platformList.map((p) => p.name)];

  const [items, setItems] = useState<ConsignmentSale[]>([]);
  const [totals, setTotals] = useState({
    sales: "0", commission: "0", owed: "0", paid: "0",
    byConsignor: [] as ConsignorBreakdown[],
  });
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [year, setYear] = useState<string>(String(todayYear()));
  const [consignorFilter, setConsignorFilter] = useState<string>("");
  const [paidFilter, setPaidFilter] = useState<string>("");
  const [search, setSearch] = useState("");

  async function reload() {
    setLoading(true);
    setError(null);
    try {
      const qs = new URLSearchParams();
      if (year) qs.set("year", year);
      if (consignorFilter) qs.set("consignor", consignorFilter);
      if (paidFilter === "true") qs.set("paid_out", "true");
      if (paidFilter === "false") qs.set("paid_out", "false");
      if (search.trim()) qs.set("search", search.trim());
      const data = await adminApi.get<ConsignmentListResponse>(`/api/consignment-sales/?${qs}`);
      setItems(data.items);
      setTotals({
        sales: data.total_sales,
        commission: data.total_commission,
        owed: data.total_owed,
        paid: data.total_paid,
        byConsignor: data.by_consignor,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { reload(); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, [year, consignorFilter, paidFilter]);

  const filtered = useMemo(() => items, [items]);

  const existingConsignors = useMemo(
    () => Array.from(new Set(items.map((i) => i.consignor).filter(Boolean))).sort(),
    [items],
  );

  async function handleSave(id: number, patch: Partial<ConsignmentSale>) {
    setBusy(true);
    try {
      await adminApi.patch(`/api/consignment-sales/${id}`, patch);
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleMarkPaid(id: number) {
    if (!confirm("Marcare come saldato al committente?")) return;
    setBusy(true);
    try {
      await adminApi.post(`/api/consignment-sales/${id}/mark-paid`, { payout_date: todayISO() });
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete(id: number) {
    if (!confirm("Eliminare questa vendita contovendita?")) return;
    setBusy(true);
    try {
      await adminApi.delete(`/api/consignment-sales/${id}`);
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      const form = e.target as HTMLFormElement;
      const fd = new FormData(form);
      const payload = {
        sale_date: String(fd.get("sale_date") || todayISO()),
        item: String(fd.get("item") || "").trim(),
        consignor: String(fd.get("consignor") || "").trim(),
        sale_price: Number(fd.get("sale_price") || 0),
        commission_pct: fd.get("commission_pct") ? Number(fd.get("commission_pct")) : null,
        commission_amount: fd.get("commission_amount") ? Number(fd.get("commission_amount")) : null,
        fee_amount: fd.get("fee_amount") ? Number(fd.get("fee_amount")) : null,
        shipping_cost: fd.get("shipping_cost") ? Number(fd.get("shipping_cost")) : null,
        sold_platform: String(fd.get("sold_platform") || "") || null,
        sold_by: String(fd.get("sold_by") || "") || null,
        buyer: String(fd.get("buyer") || "") || null,
        paid_out: false,
        note: String(fd.get("note") || "") || null,
      };
      if (!payload.item) throw new Error("Descrizione obbligatoria");
      if (!payload.consignor) throw new Error("Committente obbligatorio");
      if (payload.sale_price <= 0) throw new Error("Prezzo > 0 obbligatorio");
      await adminApi.post("/api/consignment-sales/", payload);
      form.reset();
      (form.elements.namedItem("item") as HTMLInputElement)?.focus();
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <AdminShell>
      <VenditeNav active="contovendita" />

      <p className="text-ink-soft text-sm mb-4">
        Vendo per conto di altre persone (committenti). Tengo una commissione
        (% o importo fisso) e giro il resto al committente. Marca <em>Saldato</em>
        quando hai effettivamente trasferito il dovuto.
      </p>

      {error && <div className="card p-4 mb-4 text-pink-deep font-semibold">⚠ {error}</div>}

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-2 mb-4">
        <Kpi label="Vendite" value={fmtMoney(totals.sales)} sub={`${items.length} pezzi`} color="bg-mint" />
        <Kpi label="Commissione mia" value={fmtMoney(totals.commission)} color="bg-mint" accent />
        <Kpi
          label="Da girare"
          value={fmtMoney(totals.owed)}
          sub="ai committenti"
          color={Number(totals.owed) > 0 ? "bg-pink" : "bg-ink/5"}
          accent={Number(totals.owed) > 0}
        />
        <Kpi label="Già pagato" value={fmtMoney(totals.paid)} color="bg-lilac-soft" />
      </div>

      {totals.byConsignor.length > 0 && (
        <div className="card p-4 mb-4">
          <h2 className="display text-base text-ink mb-2">Per committente</h2>
          <table className="w-full text-xs">
            <thead className="text-ink-soft uppercase tracking-wider">
              <tr>
                <th className="text-left py-1">Nome</th>
                <th className="text-right py-1">Vendite</th>
                <th className="text-right py-1">Ricavi</th>
                <th className="text-right py-1">Mia comm.</th>
                <th className="text-right py-1">Da girare</th>
                <th className="text-right py-1">Già pagato</th>
              </tr>
            </thead>
            <tbody>
              {totals.byConsignor.map((r) => (
                <tr key={r.name} className="border-t border-ink/5">
                  <td className="py-1.5 font-semibold">{r.name}</td>
                  <td className="py-1.5 text-right tabular-nums">{r.sales_count}</td>
                  <td className="py-1.5 text-right tabular-nums">{fmtMoney(r.sales_total)}</td>
                  <td className="py-1.5 text-right tabular-nums text-mint-deep">{fmtMoney(r.commission_kept)}</td>
                  <td className={`py-1.5 text-right tabular-nums ${Number(r.owed) > 0 ? "text-pink-deep font-bold" : "text-ink-soft"}`}>{fmtMoney(r.owed)}</td>
                  <td className="py-1.5 text-right tabular-nums text-ink-soft">{fmtMoney(r.paid_already)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="card p-3 mb-4 grid sm:grid-cols-[120px_200px_160px_1fr] gap-2">
        <select value={year} onChange={(e) => setYear(e.target.value)} className="input">
          <option value="">Tutti gli anni</option>
          {[todayYear(), todayYear() - 1, todayYear() - 2, todayYear() - 3].map((y) => (
            <option key={y} value={y}>{y}</option>
          ))}
        </select>
        <input
          list="existing-consignors"
          value={consignorFilter}
          onChange={(e) => setConsignorFilter(e.target.value)}
          placeholder="Committente…"
          className="input"
        />
        <datalist id="existing-consignors">
          {existingConsignors.map((c) => <option key={c} value={c} />)}
        </datalist>
        <select value={paidFilter} onChange={(e) => setPaidFilter(e.target.value)} className="input">
          <option value="">Tutti</option>
          <option value="false">Da pagare</option>
          <option value="true">Già pagati</option>
        </select>
        <input
          type="search"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && reload()}
          placeholder="🔎 Cerca testo libero…"
          className="input"
        />
      </div>

      <form onSubmit={handleAdd} className="card p-4 mb-4">
        <h2 className="display text-base text-ink mb-3">+ Nuova vendita contovendita</h2>
        <div className="grid sm:grid-cols-6 gap-2">
          <input name="sale_date" type="date" defaultValue={todayISO()} className="input" />
          <input name="item" placeholder="Cosa hai venduto *" required className="input col-span-2" />
          <input name="consignor" placeholder="Committente *" required list="existing-consignors-form" className="input col-span-2" />
          <datalist id="existing-consignors-form">
            {existingConsignors.map((c) => <option key={c} value={c} />)}
          </datalist>
          <input name="sale_price" type="number" step="0.01" min="0" placeholder="Prezzo €" required className="input" />
        </div>
        <div className="grid sm:grid-cols-6 gap-2 mt-2">
          <input name="commission_pct" type="number" step="0.5" min="0" max="100" defaultValue={DEFAULT_COMMISSION_PCT} placeholder="% mia" className="input" title="Default 10%" />
          <input name="commission_amount" type="number" step="0.01" min="0" placeholder="O imp. fisso €" className="input" title="Sovrascrive il %" />
          <input name="fee_amount" type="number" step="0.01" min="0" placeholder="Fee €" className="input" />
          <input name="shipping_cost" type="number" step="0.01" min="0" placeholder="Sped. €" className="input" />
          <select name="sold_platform" className="input">
            {platformNames.map((p) => <option key={p || "_"} value={p}>{p || "Pf."}</option>)}
          </select>
          <select name="sold_by" className="input">
            {PEOPLE.map((p) => <option key={p || "_"} value={p}>{p || "Chi vende"}</option>)}
          </select>
        </div>
        <div className="grid sm:grid-cols-6 gap-2 mt-2">
          <input name="buyer" placeholder="Compratore (opz.)" className="input col-span-2" />
          <input name="note" placeholder="Note (opz.)" className="input col-span-3" />
          <button type="submit" disabled={busy} className="btn btn-primary text-sm">
            {busy ? "..." : "Aggiungi"}
          </button>
        </div>
      </form>

      {loading && <p className="text-ink-soft">Caricamento…</p>}

      {!loading && filtered.length === 0 && (
        <div className="card p-10 text-center text-ink-soft">Nessuna vendita.</div>
      )}

      {!loading && filtered.length > 0 && (
        <div className="card overflow-x-auto">
          <table className="min-w-full text-xs">
            <thead className="bg-white/60 backdrop-blur border-b border-ink/10 text-ink-soft uppercase tracking-wider">
              <tr>
                <Th>Data</Th>
                <Th>Oggetto</Th>
                <Th>Committente</Th>
                <Th className="text-right">€ vend.</Th>
                <Th className="text-right">% mia</Th>
                <Th className="text-right">Comm. €</Th>
                <Th className="text-right">Fee</Th>
                <Th className="text-right">Sped.</Th>
                <Th className="text-right">Al comm.</Th>
                <Th>Pf.</Th>
                <Th>Chi</Th>
                <Th>Stato</Th>
                <Th></Th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((s) => (
                <Row
                  key={s.id}
                  sale={s}
                  busy={busy}
                  platformNames={platformNames}
                  consignors={existingConsignors}
                  onSave={(p) => handleSave(s.id, p)}
                  onMarkPaid={() => handleMarkPaid(s.id)}
                  onDelete={() => handleDelete(s.id)}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}

      <p className="text-xs text-ink-soft mt-3">
        {filtered.length} righe. <strong>% mia</strong> applicato automaticamente al
        prezzo. Se metti <strong>Comm. €</strong> diretta, prevale sul %.
      </p>

      <style>{styles}</style>
    </AdminShell>
  );
}

function Row({
  sale, busy, platformNames, consignors, onSave, onMarkPaid, onDelete,
}: {
  sale: ConsignmentSale;
  busy: boolean;
  platformNames: string[];
  consignors: string[];
  onSave: (p: Partial<ConsignmentSale>) => void;
  onMarkPaid: () => void;
  onDelete: () => void;
}) {
  const [saleDate, setSaleDate] = useState(sale.sale_date);
  const [item, setItem] = useState(sale.item);
  const [consignor, setConsignor] = useState(sale.consignor);
  const [salePrice, setSalePrice] = useState(sale.sale_price);
  const [commPct, setCommPct] = useState(sale.commission_pct ?? "");
  const [commAmt, setCommAmt] = useState(sale.commission_amount ?? "");
  const [fee, setFee] = useState(sale.fee_amount ?? "");
  const [shipping, setShipping] = useState(sale.shipping_cost ?? "");
  const [soldPlatform, setSoldPlatform] = useState(sale.sold_platform ?? "");
  const [soldBy, setSoldBy] = useState(sale.sold_by ?? "");

  function maybe(key: keyof ConsignmentSale, current: unknown, original: unknown) {
    if (current === original) return;
    if (typeof current === "string" && current === "" && (original === null || original === "")) return;
    onSave({ [key]: (current === "" ? null : current) as never });
  }

  return (
    <tr className={`border-b border-ink/5 hover:bg-pink-soft/20 ${sale.paid_out ? "opacity-60" : ""}`}>
      <Td>
        <input type="date" value={saleDate} onChange={(e) => setSaleDate(e.target.value)}
          onBlur={() => maybe("sale_date", saleDate, sale.sale_date)}
          className="cell-input text-[11px] w-28" />
      </Td>
      <Td>
        <input value={item} onChange={(e) => setItem(e.target.value)}
          onBlur={() => maybe("item", item, sale.item)}
          className="cell-input font-semibold text-ink min-w-[160px]" />
      </Td>
      <Td>
        <input list="row-consignors" value={consignor} onChange={(e) => setConsignor(e.target.value)}
          onBlur={() => maybe("consignor", consignor, sale.consignor)}
          className="cell-input min-w-[120px]" />
        <datalist id="row-consignors">
          {consignors.map((c) => <option key={c} value={c} />)}
        </datalist>
      </Td>
      <Td className="text-right">
        <input type="number" step="0.01" min="0" value={salePrice}
          onChange={(e) => setSalePrice(e.target.value)}
          onBlur={() => maybe("sale_price", salePrice, sale.sale_price)}
          className="cell-input text-right tabular-nums w-20 font-semibold" />
      </Td>
      <Td className="text-right">
        <input type="number" step="0.5" min="0" max="100" value={commPct ?? ""}
          onChange={(e) => setCommPct(e.target.value)}
          onBlur={() => maybe("commission_pct", commPct, sale.commission_pct)}
          className="cell-input text-right tabular-nums w-16" />
      </Td>
      <Td className="text-right">
        <input type="number" step="0.01" min="0" value={commAmt ?? ""}
          onChange={(e) => setCommAmt(e.target.value)}
          onBlur={() => maybe("commission_amount", commAmt, sale.commission_amount)}
          className="cell-input text-right tabular-nums w-16 text-mint-deep font-semibold"
          placeholder={sale.commission_effective}
          title={`Effettivo: ${sale.commission_effective} €`}
        />
      </Td>
      <Td className="text-right">
        <input type="number" step="0.01" min="0" value={fee ?? ""}
          onChange={(e) => setFee(e.target.value)}
          onBlur={() => maybe("fee_amount", fee, sale.fee_amount)}
          className="cell-input text-right tabular-nums w-14" />
      </Td>
      <Td className="text-right">
        <input type="number" step="0.01" min="0" value={shipping ?? ""}
          onChange={(e) => setShipping(e.target.value)}
          onBlur={() => maybe("shipping_cost", shipping, sale.shipping_cost)}
          className="cell-input text-right tabular-nums w-14" />
      </Td>
      <Td className={`text-right tabular-nums font-bold ${Number(sale.consignor_share) > 0 && !sale.paid_out ? "text-pink-deep" : "text-ink-soft"}`}>
        {fmtMoney(sale.consignor_share)}
      </Td>
      <Td>
        <select value={soldPlatform} onChange={(e) => {
          setSoldPlatform(e.target.value);
          if (e.target.value !== (sale.sold_platform ?? "")) onSave({ sold_platform: (e.target.value || null) as never });
        }} className="cell-input text-[11px] w-24">
          {platformNames.map((p) => <option key={p || "_"} value={p}>{p || "—"}</option>)}
        </select>
      </Td>
      <Td>
        <select value={soldBy} onChange={(e) => {
          setSoldBy(e.target.value);
          if (e.target.value !== (sale.sold_by ?? "")) onSave({ sold_by: (e.target.value || null) as never });
        }} className="cell-input text-[11px] w-12">
          {PEOPLE.map((p) => <option key={p || "_"} value={p}>{p || "—"}</option>)}
        </select>
      </Td>
      <Td>
        {sale.paid_out ? (
          <span className="text-[10px] px-2 py-0.5 rounded-full bg-mint-deep text-white font-semibold" title={`Pagato il ${sale.payout_date || "—"}`}>
            ✓ Saldato
          </span>
        ) : (
          <button
            type="button"
            onClick={onMarkPaid}
            disabled={busy}
            className="text-[10px] px-2 py-1 rounded-full bg-pink-soft text-pink-deep hover:bg-pink hover:text-white font-semibold transition-colors"
            title="Marca come saldato al committente"
          >
            Salda ora
          </button>
        )}
      </Td>
      <Td>
        <button type="button" onClick={onDelete} disabled={busy}
          className="btn btn-ghost text-[10px] px-2 py-1" title="Elimina">🗑</button>
      </Td>
    </tr>
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

function Th({ children, className = "" }: { children?: React.ReactNode; className?: string }) {
  return <th className={`text-left py-2 px-2 font-semibold whitespace-nowrap ${className}`}>{children}</th>;
}

function Td({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <td className={`py-1 px-1 align-middle ${className}`}>{children}</td>;
}

const styles = `
  .input {
    display: block;
    width: 100%;
    padding: 0.4rem 0.6rem;
    border: 1px solid rgba(61, 42, 92, 0.12);
    border-radius: 10px;
    background: #fffaf3;
    color: #3d2a5c;
    font-family: "Manrope", sans-serif;
    font-size: 0.85rem;
    outline: none;
  }
  .input:focus {
    box-shadow: 0 0 0 2px rgba(248, 168, 200, 0.45);
    border-color: #e879a8;
  }
  .cell-input {
    background: transparent;
    border: none;
    outline: none;
    padding: 0.25rem 0.4rem;
    width: 100%;
    font: inherit;
    color: inherit;
    border-radius: 4px;
  }
  .cell-input:focus {
    background: #fffaf3;
    box-shadow: 0 0 0 2px rgba(168, 144, 216, 0.35);
  }
`;
