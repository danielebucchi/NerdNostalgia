"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { AdminShell } from "@/components/admin/AdminShell";
import { VenditeNav } from "@/components/admin/VenditeNav";
import { adminApi } from "@/lib/admin-api";
import { usePlatforms } from "@/lib/usePlatforms";
import type {
  PersonalCard,
  PersonalCardListResponse,
} from "@/lib/types";

const PEOPLE = ["", "C", "D", "C+D"];
const FINISHES = ["", "normal", "holo", "reverse", "full art", "secret", "rainbow", "textured", "altre"];
const LANGUAGES = ["IT", "EN", "JP", "DE", "FR", "ES"];
const CONDITIONS = ["", "M", "NM", "EX", "LP", "MP", "HP", "DMG"];
const ORIGINS = ["", "acquisto", "sbustamento", "regalo", "scambio", "altro"];

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

function todayISO() { return new Date().toISOString().slice(0, 10); }
function todayYear() { return new Date().getFullYear(); }

export default function CarteNoFlippingPage() {
  const { items: platformList } = usePlatforms();
  const platformNames = ["", ...platformList.map((p) => p.name)];
  const [items, setItems] = useState<PersonalCard[]>([]);
  const [totals, setTotals] = useState({
    sold_count: 0,
    sold_revenue: "0",
    sold_profit: "0",
    purchase_cost: "0",
  });
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [year, setYear] = useState<string>(String(todayYear()));
  const [ownedBy, setOwnedBy] = useState<string>("");
  const [originFilter, setOriginFilter] = useState<string>("");
  const [search, setSearch] = useState("");

  async function reload() {
    setLoading(true);
    setError(null);
    try {
      const qs = new URLSearchParams();
      qs.set("status", "SOLD");
      if (ownedBy) qs.set("owned_by", ownedBy);
      if (search.trim()) qs.set("search", search.trim());
      const data = await adminApi.get<PersonalCardListResponse>(`/api/personal-cards/?${qs}`);
      const filtered = data.items.filter((c) => {
        if (year && c.sold_date) {
          if (!c.sold_date.startsWith(year)) return false;
        }
        if (originFilter && c.purchase_source !== originFilter) return false;
        return true;
      });
      setItems(filtered);
      let revenue = 0, profit = 0, cost = 0;
      for (const c of filtered) {
        revenue += Number(c.sale_price || 0);
        profit += Number(c.profit || 0);
        cost += Number(c.purchase_cost || 0) * c.quantity;
      }
      setTotals({
        sold_count: filtered.reduce((s, c) => s + c.quantity, 0),
        sold_revenue: String(revenue),
        sold_profit: String(profit),
        purchase_cost: String(cost),
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [year, ownedBy, originFilter]);

  async function handleSave(id: number, patch: Partial<PersonalCard>) {
    setBusy(true);
    try {
      await adminApi.patch(`/api/personal-cards/${id}`, patch);
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete(id: number) {
    if (!confirm("Eliminare questa vendita?")) return;
    setBusy(true);
    try {
      await adminApi.delete(`/api/personal-cards/${id}`);
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
        name: String(fd.get("name") || "").trim(),
        collection: String(fd.get("collection") || "") || null,
        card_number: String(fd.get("card_number") || "") || null,
        finish: String(fd.get("finish") || "") || null,
        language: String(fd.get("language") || "IT"),
        condition: String(fd.get("condition") || "") || null,
        grading: String(fd.get("grading") || "") || null,
        owned_by: String(fd.get("owned_by") || "") || null,
        quantity: Number(fd.get("quantity") || 1),
        purchase_source: String(fd.get("purchase_source") || "") || null,
        purchase_cost: fd.get("purchase_cost") ? Number(fd.get("purchase_cost")) : null,
        sold_date: String(fd.get("sold_date") || todayISO()),
        sale_price: fd.get("sale_price") ? Number(fd.get("sale_price")) : null,
        fee_amount: fd.get("fee_amount") ? Number(fd.get("fee_amount")) : null,
        shipping_cost: fd.get("shipping_cost") ? Number(fd.get("shipping_cost")) : null,
        sold_platform: String(fd.get("sold_platform") || "") || null,
        sold_by: String(fd.get("sold_by") || "") || null,
        status: "SOLD" as const,
      };
      if (!payload.name) throw new Error("Nome carta obbligatorio");
      if (payload.sale_price == null || payload.sale_price <= 0) throw new Error("Prezzo vendita obbligatorio");
      await adminApi.post("/api/personal-cards/", payload);
      form.reset();
      (form.elements.namedItem("name") as HTMLInputElement)?.focus();
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  const byOrigin = useMemo(() => {
    const m: Record<string, { count: number; revenue: number }> = {};
    for (const c of items) {
      const k = c.purchase_source || "—";
      const e = m[k] ?? { count: 0, revenue: 0 };
      e.count += c.quantity;
      e.revenue += Number(c.sale_price || 0);
      m[k] = e;
    }
    return m;
  }, [items]);

  return (
    <AdminShell>
      <VenditeNav active="carte" />

      <p className="text-ink-soft text-sm mb-4">
        Log delle vendite di carte singole (comprate al kg, sbustate, ecc).
        I costi bulk vanno in <Link href="/admin/spese" className="underline">Spese</Link>
        {" "}con flag <em>carte</em>, e vengono sottratti dal profitto netto in dashboard.
      </p>

      {error && (
        <div className="card p-4 mb-4 text-pink-deep font-semibold">⚠ {error}</div>
      )}

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-2 mb-4">
        <Kpi label="Vendute" value={String(totals.sold_count)} sub={`${items.length} righe`} color="bg-mint" />
        <Kpi label="Ricavi" value={fmtMoney(totals.sold_revenue)} color="bg-mint" />
        <Kpi
          label="Profitto lordo"
          value={fmtMoney(totals.sold_profit)}
          sub="senza costi bulk"
          color={Number(totals.sold_profit) >= 0 ? "bg-mint" : "bg-pink"}
          accent
        />
        <Kpi
          label="Costi assegnati"
          value={fmtMoney(totals.purchase_cost)}
          sub="solo costi per-carta"
          color="bg-pink-soft"
        />
      </div>

      {Object.keys(byOrigin).length > 0 && (
        <div className="card p-3 mb-4 flex flex-wrap gap-3 items-center">
          <span className="text-xs text-ink-soft uppercase tracking-wider">Per origine:</span>
          {Object.entries(byOrigin).map(([orig, v]) => (
            <span key={orig} className="text-sm">
              <strong className="text-ink capitalize">{orig}</strong>{" "}
              <span className="text-ink-soft">{v.count} · {fmtMoney(v.revenue)}</span>
            </span>
          ))}
        </div>
      )}

      <div className="card p-3 mb-4 grid sm:grid-cols-[120px_140px_140px_1fr] gap-2">
        <select value={year} onChange={(e) => setYear(e.target.value)} className="input">
          <option value="">Tutti gli anni</option>
          {[todayYear(), todayYear() - 1, todayYear() - 2, todayYear() - 3].map((y) => (
            <option key={y} value={y}>{y}</option>
          ))}
        </select>
        <select value={ownedBy} onChange={(e) => setOwnedBy(e.target.value)} className="input">
          <option value="">Tutti i prop.</option>
          {PEOPLE.filter(Boolean).map((p) => <option key={p} value={p}>{p}</option>)}
        </select>
        <select value={originFilter} onChange={(e) => setOriginFilter(e.target.value)} className="input">
          <option value="">Tutte le origini</option>
          {ORIGINS.filter(Boolean).map((o) => <option key={o} value={o}>{o}</option>)}
        </select>
        <input
          type="search"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && reload()}
          placeholder="🔎 Cerca nome, collezione, numero…"
          className="input"
        />
      </div>

      <form onSubmit={handleAdd} className="card p-4 mb-4">
        <h2 className="display text-base text-ink mb-3">+ Registra vendita</h2>

        <div className="grid sm:grid-cols-6 gap-2">
          <input name="name" placeholder="Nome carta *" required className="input col-span-2" />
          <input name="collection" placeholder="Collezione" className="input col-span-2" />
          <input name="card_number" placeholder="N°" className="input" />
          <input name="quantity" type="number" min="1" defaultValue="1" placeholder="Qty" className="input" />
        </div>

        <div className="grid sm:grid-cols-6 gap-2 mt-2">
          <select name="finish" className="input">
            {FINISHES.map((f) => <option key={f || "_"} value={f}>{f || "Finish"}</option>)}
          </select>
          <select name="language" className="input" defaultValue="IT">
            {LANGUAGES.map((l) => <option key={l} value={l}>{l}</option>)}
          </select>
          <select name="condition" className="input">
            {CONDITIONS.map((c) => <option key={c || "_"} value={c}>{c || "Cond."}</option>)}
          </select>
          <input name="grading" placeholder="PSA / BGS…" className="input" />
          <select name="owned_by" className="input">
            {PEOPLE.map((p) => <option key={p || "_"} value={p}>{p || "Prop."}</option>)}
          </select>
          <select name="purchase_source" className="input">
            {ORIGINS.map((o) => <option key={o || "_"} value={o}>{o || "Origine"}</option>)}
          </select>
        </div>

        <div className="grid sm:grid-cols-6 gap-2 mt-2 pt-2 border-t border-ink/10">
          <input name="sold_date" type="date" defaultValue={todayISO()} className="input" />
          <input name="sale_price" type="number" step="0.01" required placeholder="Prezzo vend. € *" className="input" />
          <input name="fee_amount" type="number" step="0.01" placeholder="Fee €" className="input" />
          <input name="shipping_cost" type="number" step="0.01" placeholder="Sped. €" className="input" />
          <select name="sold_platform" className="input">
            {platformNames.map((p) => <option key={p || "_"} value={p}>{p || "Pf. vend."}</option>)}
          </select>
          <select name="sold_by" className="input">
            {PEOPLE.map((p) => <option key={p || "_"} value={p}>{p || "Chi vende"}</option>)}
          </select>
        </div>

        <div className="grid sm:grid-cols-6 gap-2 mt-2">
          <input
            name="purchase_cost"
            type="number"
            step="0.01"
            placeholder="Costo carta € (se noto)"
            className="input col-span-2"
            title="Lascia vuoto se la carta è da bulk/booster"
          />
          <button type="submit" disabled={busy} className="btn btn-primary text-sm col-span-4">
            {busy ? "..." : "Registra vendita"}
          </button>
        </div>
      </form>

      {loading && <p className="text-ink-soft">Caricamento…</p>}

      {!loading && items.length === 0 && (
        <div className="card p-10 text-center">
          <p className="text-ink-soft">Nessuna vendita registrata con questi filtri.</p>
        </div>
      )}

      {!loading && items.length > 0 && (
        <div className="card overflow-x-auto">
          <table className="min-w-full text-xs">
            <thead className="bg-white/60 backdrop-blur border-b border-ink/10 text-ink-soft uppercase tracking-wider">
              <tr>
                <Th>Data vend.</Th>
                <Th>Carta</Th>
                <Th>Coll. / N°</Th>
                <Th>Finish</Th>
                <Th>L/C/G</Th>
                <Th>Origine</Th>
                <Th>Prop.</Th>
                <Th className="text-right">Qty</Th>
                <Th className="text-right">Costo</Th>
                <Th className="text-right">€ vend.</Th>
                <Th className="text-right">Fee</Th>
                <Th className="text-right">Sped.</Th>
                <Th>Pf.</Th>
                <Th>Chi vend.</Th>
                <Th className="text-right">Profitto</Th>
                <Th></Th>
              </tr>
            </thead>
            <tbody>
              {items.map((c) => (
                <Row
                  key={c.id}
                  card={c}
                  busy={busy}
                  platformNames={platformNames}
                  onSave={(p) => handleSave(c.id, p)}
                  onDelete={() => handleDelete(c.id)}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}

      <p className="text-xs text-ink-soft mt-3">
        {items.length} vendite · Profitto qui è <strong>lordo</strong>.
        I costi bulk (kg, booster, ecc.) si sottraggono globalmente dalla
        sezione <Link href="/admin/spese" className="underline">Spese</Link> con flag <em>carte</em>.
      </p>

      <style>{styles}</style>
    </AdminShell>
  );
}

function Row({
  card, busy, platformNames, onSave, onDelete,
}: {
  card: PersonalCard;
  busy: boolean;
  platformNames: string[];
  onSave: (p: Partial<PersonalCard>) => void;
  onDelete: () => void;
}) {
  const [name, setName] = useState(card.name);
  const [collection, setCollection] = useState(card.collection ?? "");
  const [number, setNumber] = useState(card.card_number ?? "");
  const [finish, setFinish] = useState(card.finish ?? "");
  const [language, setLanguage] = useState(card.language ?? "IT");
  const [condition, setCondition] = useState(card.condition ?? "");
  const [grading, setGrading] = useState(card.grading ?? "");
  const [origin, setOrigin] = useState(card.purchase_source ?? "");
  const [ownedBy, setOwnedBy] = useState(card.owned_by ?? "");
  const [quantity, setQuantity] = useState(card.quantity);
  const [cost, setCost] = useState(card.purchase_cost ?? "");
  const [soldDate, setSoldDate] = useState(card.sold_date ?? "");
  const [salePrice, setSalePrice] = useState(card.sale_price ?? "");
  const [fee, setFee] = useState(card.fee_amount ?? "");
  const [shipping, setShipping] = useState(card.shipping_cost ?? "");
  const [soldPlatform, setSoldPlatform] = useState(card.sold_platform ?? "");
  const [soldBy, setSoldBy] = useState(card.sold_by ?? "");

  function maybe(key: keyof PersonalCard, current: unknown, original: unknown) {
    if (current === original) return;
    if (typeof current === "string" && current === "" && (original === null || original === "")) return;
    onSave({ [key]: (current === "" ? null : current) as never });
  }

  return (
    <tr className="border-b border-ink/5 hover:bg-pink-soft/20">
      <Td>
        <input type="date" value={soldDate} onChange={(e) => setSoldDate(e.target.value)}
          onBlur={() => maybe("sold_date", soldDate, card.sold_date)}
          className="cell-input text-[11px] w-28" />
      </Td>
      <Td>
        <input value={name} onChange={(e) => setName(e.target.value)}
          onBlur={() => maybe("name", name, card.name)}
          className="cell-input font-semibold text-ink min-w-[140px]" />
      </Td>
      <Td>
        <div className="flex gap-1">
          <input value={collection} onChange={(e) => setCollection(e.target.value)}
            onBlur={() => maybe("collection", collection, card.collection)}
            className="cell-input min-w-[90px] text-[11px]" placeholder="Coll." />
          <input value={number} onChange={(e) => setNumber(e.target.value)}
            onBlur={() => maybe("card_number", number, card.card_number)}
            className="cell-input w-12 text-[11px]" placeholder="N°" />
        </div>
      </Td>
      <Td>
        <select value={finish} onChange={(e) => {
          setFinish(e.target.value);
          if (e.target.value !== (card.finish ?? "")) onSave({ finish: (e.target.value || null) as never });
        }} className="cell-input w-20 text-[11px]">
          {FINISHES.map((f) => <option key={f || "_"} value={f}>{f || "—"}</option>)}
        </select>
      </Td>
      <Td>
        <div className="flex gap-1">
          <select value={language} onChange={(e) => {
            setLanguage(e.target.value);
            if (e.target.value !== (card.language ?? "IT")) onSave({ language: e.target.value as never });
          }} className="cell-input w-12 text-[10px]">
            {LANGUAGES.map((l) => <option key={l} value={l}>{l}</option>)}
          </select>
          <select value={condition} onChange={(e) => {
            setCondition(e.target.value);
            if (e.target.value !== (card.condition ?? "")) onSave({ condition: (e.target.value || null) as never });
          }} className="cell-input w-12 text-[10px]">
            {CONDITIONS.map((c) => <option key={c || "_"} value={c}>{c || "—"}</option>)}
          </select>
          <input value={grading} onChange={(e) => setGrading(e.target.value)}
            onBlur={() => maybe("grading", grading, card.grading)}
            className="cell-input w-14 text-[10px]" placeholder="grad" />
        </div>
      </Td>
      <Td>
        <select value={origin} onChange={(e) => {
          setOrigin(e.target.value);
          if (e.target.value !== (card.purchase_source ?? "")) onSave({ purchase_source: (e.target.value || null) as never });
        }} className="cell-input w-24 text-[11px]">
          {ORIGINS.map((o) => <option key={o || "_"} value={o}>{o || "—"}</option>)}
        </select>
      </Td>
      <Td>
        <select value={ownedBy} onChange={(e) => {
          setOwnedBy(e.target.value);
          if (e.target.value !== (card.owned_by ?? "")) onSave({ owned_by: (e.target.value || null) as never });
        }} className="cell-input w-14 text-[11px]">
          {PEOPLE.map((p) => <option key={p || "_"} value={p}>{p || "—"}</option>)}
        </select>
      </Td>
      <Td className="text-right">
        <input type="number" min="1" value={quantity}
          onChange={(e) => setQuantity(Number(e.target.value))}
          onBlur={() => maybe("quantity", quantity, card.quantity)}
          className="cell-input text-right tabular-nums w-12" />
      </Td>
      <Td className="text-right">
        <input type="number" step="0.01" value={cost ?? ""}
          onChange={(e) => setCost(e.target.value)}
          onBlur={() => maybe("purchase_cost", cost, card.purchase_cost)}
          className="cell-input text-right tabular-nums w-16" />
      </Td>
      <Td className="text-right">
        <input type="number" step="0.01" value={salePrice ?? ""}
          onChange={(e) => setSalePrice(e.target.value)}
          onBlur={() => maybe("sale_price", salePrice, card.sale_price)}
          className="cell-input text-right tabular-nums w-20 font-semibold" />
      </Td>
      <Td className="text-right">
        <input type="number" step="0.01" value={fee ?? ""}
          onChange={(e) => setFee(e.target.value)}
          onBlur={() => maybe("fee_amount", fee, card.fee_amount)}
          className="cell-input text-right tabular-nums w-14" />
      </Td>
      <Td className="text-right">
        <input type="number" step="0.01" value={shipping ?? ""}
          onChange={(e) => setShipping(e.target.value)}
          onBlur={() => maybe("shipping_cost", shipping, card.shipping_cost)}
          className="cell-input text-right tabular-nums w-14" />
      </Td>
      <Td>
        <select value={soldPlatform} onChange={(e) => {
          setSoldPlatform(e.target.value);
          if (e.target.value !== (card.sold_platform ?? "")) onSave({ sold_platform: (e.target.value || null) as never });
        }} className="cell-input w-24 text-[11px]">
          {platformNames.map((p) => <option key={p || "_"} value={p}>{p || "—"}</option>)}
        </select>
      </Td>
      <Td>
        <select value={soldBy} onChange={(e) => {
          setSoldBy(e.target.value);
          if (e.target.value !== (card.sold_by ?? "")) onSave({ sold_by: (e.target.value || null) as never });
        }} className="cell-input w-12 text-[11px]">
          {PEOPLE.map((p) => <option key={p || "_"} value={p}>{p || "—"}</option>)}
        </select>
      </Td>
      <Td className="text-right tabular-nums">
        <span className={
          Number(card.profit ?? 0) > 0 ? "text-mint-deep font-bold"
          : Number(card.profit ?? 0) < 0 ? "text-pink-deep font-bold"
          : "text-ink-soft"
        }>
          {fmtMoney(card.profit)}
        </span>
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
