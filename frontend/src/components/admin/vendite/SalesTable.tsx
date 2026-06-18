"use client";

import { useEffect, useMemo, useState } from "react";
import { adminApi } from "@/lib/admin-api";
import type { MiscSale, MiscSaleKind, MiscSaleListResponse } from "@/lib/types";

const PEOPLE = ["", "C", "D"];

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

export function SalesTable({
  kind, year, platformNames,
}: {
  kind: MiscSaleKind;
  year: string;
  platformNames: string[];
}) {
  const [items, setItems] = useState<MiscSale[]>([]);
  const [totals, setTotals] = useState({ amount: "0", paid: "0", unpaid: "0", material: "0" });
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sellerFilter, setSellerFilter] = useState<string>("");
  const [query, setQuery] = useState("");

  async function reload() {
    setLoading(true);
    setError(null);
    try {
      const qs = new URLSearchParams();
      qs.set("kind", kind);
      if (year) qs.set("year", year);
      if (sellerFilter) qs.set("seller", sellerFilter);
      const data = await adminApi.get<MiscSaleListResponse>(`/api/misc-sales/?${qs}`);
      setItems(data.items);
      setTotals({
        amount: data.total_amount,
        paid: data.total_paid,
        unpaid: data.total_unpaid,
        material: data.total_material_cost,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { reload(); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, [kind, year, sellerFilter]);

  const filtered = useMemo(() => {
    if (!query.trim()) return items;
    const q = query.toLowerCase();
    return items.filter((i) =>
      [i.item, i.note, i.seller, i.platform].filter(Boolean).join(" ").toLowerCase().includes(q),
    );
  }, [items, query]);

  async function handleSave(id: number, patch: Partial<MiscSale>) {
    setBusy(true);
    try {
      await adminApi.patch(`/api/misc-sales/${id}`, patch);
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
      await adminApi.delete(`/api/misc-sales/${id}`);
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
      const payload: Record<string, unknown> = {
        sale_date: String(fd.get("sale_date") || todayISO()),
        item: String(fd.get("item") || "").trim(),
        amount: Number(fd.get("amount") || 0),
        seller: String(fd.get("seller") || "") || null,
        platform: String(fd.get("platform") || "") || null,
        paid_by_buyer: fd.get("paid_by_buyer") === "on",
        note: String(fd.get("note") || "") || null,
        kind,
      };
      if (kind === "creation") {
        payload.material_cost = fd.get("material_cost") ? Number(fd.get("material_cost")) : null;
      }
      if (!payload.item) throw new Error("Descrizione obbligatoria");
      await adminApi.post("/api/misc-sales/", payload);
      form.reset();
      (form.elements.namedItem("item") as HTMLInputElement)?.focus();
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  const isCreation = kind === "creation";
  const grossProfit = isCreation ? Number(totals.amount) - Number(totals.material) : 0;

  return (
    <>
      {error && <div className="card p-4 mb-4 text-pink-deep font-semibold">⚠ {error}</div>}

      {isCreation ? (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-2 mb-4">
          <Kpi label="Ricavi" value={fmtMoney(totals.amount)} sub={`${items.length} pezzi`} color="bg-mint" />
          <Kpi label="Costo materiali" value={fmtMoney(totals.material)} color="bg-pink-soft" />
          <Kpi label="Profitto lordo" value={fmtMoney(grossProfit)} sub="prima delle Altre spese" color={grossProfit >= 0 ? "bg-mint" : "bg-pink"} accent />
          <Kpi label="Da incassare" value={fmtMoney(totals.unpaid)} color={Number(totals.unpaid) > 0 ? "bg-pink" : "bg-ink/5"} />
        </div>
      ) : (
        <div className="grid grid-cols-3 gap-2 mb-4">
          <Kpi label="Incasso totale" value={fmtMoney(totals.amount)} color="bg-mint" />
          <Kpi label="Già incassato" value={fmtMoney(totals.paid)} color="bg-lilac-soft" />
          <Kpi label="Da incassare" value={fmtMoney(totals.unpaid)} color={Number(totals.unpaid) > 0 ? "bg-pink" : "bg-ink/5"} accent={Number(totals.unpaid) > 0} />
        </div>
      )}

      <div className="card p-3 mb-4 grid sm:grid-cols-[120px_1fr] gap-2">
        <select value={sellerFilter} onChange={(e) => setSellerFilter(e.target.value)} className="input">
          <option value="">Tutti</option>
          <option value="C">Solo C</option>
          <option value="D">Solo D</option>
        </select>
        <input type="search" value={query} onChange={(e) => setQuery(e.target.value)}
          placeholder="🔎 Cerca testo libero…" className="input" />
      </div>

      <form onSubmit={handleAdd} className="card p-4 mb-4">
        <h2 className="display text-base text-ink mb-3">
          + Nuova {isCreation ? "creazione venduta" : "vendita"}
        </h2>
        <div className="grid sm:grid-cols-6 gap-2">
          <input name="sale_date" type="date" defaultValue={todayISO()} className="input" />
          <input name="item" placeholder={isCreation ? "Cosa hai creato *" : "Cosa hai venduto *"} required className="input col-span-2" />
          <input name="amount" type="number" step="0.01" min="0" placeholder="Prezzo €" required className="input" />
          <select name="seller" className="input">
            {PEOPLE.map((p) => <option key={p || "_"} value={p}>{p || "Chi vende"}</option>)}
          </select>
          <select name="platform" className="input">
            {platformNames.map((p) => <option key={p || "_"} value={p}>{p || "Pf."}</option>)}
          </select>
        </div>
        <div className="grid sm:grid-cols-6 gap-2 mt-2">
          {isCreation && (
            <input name="material_cost" type="number" step="0.01" min="0" placeholder="Costo materiali €" className="input" />
          )}
          <label className={`flex items-center gap-2 text-sm text-ink-soft ${isCreation ? "col-span-1" : "col-span-2"}`}>
            <input name="paid_by_buyer" type="checkbox" defaultChecked />
            <span>Già incassato</span>
          </label>
          <input name="note" placeholder="Note (opzionale)" className="input col-span-3" />
          <button type="submit" disabled={busy} className="btn btn-primary text-sm">
            {busy ? "..." : "Aggiungi"}
          </button>
        </div>
      </form>

      {loading && <p className="text-ink-soft">Caricamento…</p>}

      {!loading && filtered.length === 0 && (
        <div className="card p-10 text-center">
          <p className="text-ink-soft">Nessuna {isCreation ? "creazione" : "vendita"} registrata.</p>
        </div>
      )}

      {!loading && filtered.length > 0 && (
        <div className="card overflow-x-auto">
          <table className="min-w-full text-xs">
            <thead className="bg-white/60 backdrop-blur border-b border-ink/10 text-ink-soft uppercase tracking-wider">
              <tr>
                <Th>Data</Th>
                <Th>{isCreation ? "Creazione" : "Oggetto"}</Th>
                <Th className="text-right">€</Th>
                {isCreation && <Th className="text-right">Materiali</Th>}
                {isCreation && <Th className="text-right">Profitto</Th>}
                <Th>Chi vende</Th>
                <Th>Piattaforma</Th>
                <Th>Pagato?</Th>
                <Th>Note</Th>
                <Th></Th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((s) => (
                <Row key={s.id} item={s} busy={busy} isCreation={isCreation}
                  platformNames={platformNames}
                  onSave={(p) => handleSave(s.id, p)} onDelete={() => handleDelete(s.id)} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}

function Row({ item, busy, isCreation, platformNames, onSave, onDelete }: {
  item: MiscSale; busy: boolean; isCreation: boolean; platformNames: string[];
  onSave: (p: Partial<MiscSale>) => void; onDelete: () => void;
}) {
  const [saleDate, setSaleDate] = useState(item.sale_date ?? "");
  const [name, setName] = useState(item.item);
  const [amount, setAmount] = useState(item.amount);
  const [material, setMaterial] = useState(item.material_cost ?? "");
  const [seller, setSeller] = useState(item.seller ?? "");
  const [platform, setPlatform] = useState(item.platform ?? "");
  const [note, setNote] = useState(item.note ?? "");

  function maybe(key: keyof MiscSale, current: unknown, original: unknown) {
    if (current === original) return;
    if (typeof current === "string" && current === "" && (original === null || original === "")) return;
    onSave({ [key]: (current === "" ? null : current) as never });
  }

  const profit = Number(item.amount || 0) - Number(item.material_cost || 0);

  return (
    <tr className="border-b border-ink/5 hover:bg-pink-soft/20">
      <Td>
        <input type="date" value={saleDate} onChange={(e) => setSaleDate(e.target.value)}
          onBlur={() => maybe("sale_date", saleDate, item.sale_date)}
          className="cell-input text-[11px] w-28" />
      </Td>
      <Td>
        <input value={name} onChange={(e) => setName(e.target.value)}
          onBlur={() => maybe("item", name, item.item)}
          className="cell-input font-semibold text-ink min-w-[200px]" />
      </Td>
      <Td className="text-right">
        <input type="number" step="0.01" min="0" value={amount}
          onChange={(e) => setAmount(e.target.value)}
          onBlur={() => maybe("amount", amount, item.amount)}
          className="cell-input text-right tabular-nums w-24 font-semibold" />
      </Td>
      {isCreation && (
        <Td className="text-right">
          <input type="number" step="0.01" min="0" value={material ?? ""}
            onChange={(e) => setMaterial(e.target.value)}
            onBlur={() => maybe("material_cost", material, item.material_cost)}
            className="cell-input text-right tabular-nums w-20" />
        </Td>
      )}
      {isCreation && (
        <Td className="text-right tabular-nums">
          <span className={profit > 0 ? "text-mint-deep font-bold" : profit < 0 ? "text-pink-deep font-bold" : "text-ink-soft"}>
            {fmtMoney(profit)}
          </span>
        </Td>
      )}
      <Td>
        <select value={seller} onChange={(e) => {
          setSeller(e.target.value);
          if (e.target.value !== (item.seller ?? "")) onSave({ seller: (e.target.value || null) as never });
        }} className="cell-input text-[11px] w-14">
          {PEOPLE.map((p) => <option key={p || "_"} value={p}>{p || "—"}</option>)}
        </select>
      </Td>
      <Td>
        <select value={platform} onChange={(e) => {
          setPlatform(e.target.value);
          if (e.target.value !== (item.platform ?? "")) onSave({ platform: (e.target.value || null) as never });
        }} className="cell-input text-[11px] w-24">
          {platformNames.map((p) => <option key={p || "_"} value={p}>{p || "—"}</option>)}
        </select>
      </Td>
      <Td>
        <input type="checkbox" checked={item.paid_by_buyer}
          onChange={(e) => onSave({ paid_by_buyer: e.target.checked as never })} disabled={busy} />
      </Td>
      <Td>
        <input value={note} onChange={(e) => setNote(e.target.value)}
          onBlur={() => maybe("note", note, item.note)}
          className="cell-input text-[11px] min-w-[180px]" />
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
