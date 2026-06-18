"use client";

import { useEffect, useMemo, useState } from "react";
import { AdminShell } from "@/components/admin/AdminShell";
import { adminApi } from "@/lib/admin-api";
import type {
  CardPurchase,
  CardPurchaseListResponse,
  Expense,
  ExpenseListResponse,
} from "@/lib/types";

const PEOPLE = ["", "C", "D"];
const CATEGORIES = ["", "spedizioni", "materiali", "sleeves", "deck box", "fee account", "viaggi", "marketing", "altro"];

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

type Tab = "cards" | "other";

export default function SpesePage() {
  const [tab, setTab] = useState<Tab>("cards");
  const [year, setYear] = useState<string>(String(todayYear()));

  return (
    <AdminShell>
      <div className="flex items-end justify-between mb-3 gap-3 flex-wrap">
        <div>
          <h1 className="display text-3xl text-ink">💰 Spese</h1>
          <p className="text-ink-soft mt-1 text-sm">
            Unifica i fogli &quot;Spese carte&quot; (bulk kg, booster, ecc) e
            &quot;Spese&quot; generiche (spedizioni, materiali, fee, viaggi).
            Le voci marcate <em>related_to_cards</em> nella tab Altre Spese si
            sommano alle Spese carte nel calcolo del profitto netto carte.
          </p>
        </div>
        <select
          value={year}
          onChange={(e) => setYear(e.target.value)}
          className="input"
          style={{ maxWidth: 160 }}
        >
          <option value="">Tutti gli anni</option>
          {[todayYear(), todayYear() - 1, todayYear() - 2, todayYear() - 3].map((y) => (
            <option key={y} value={y}>Anno {y}</option>
          ))}
        </select>
      </div>

      <div className="flex gap-1 mb-4 border-b border-ink/10">
        <button
          type="button"
          onClick={() => setTab("cards")}
          className={`px-4 py-2 text-sm font-semibold border-b-2 transition-colors ${
            tab === "cards" ? "border-pink-deep text-ink" : "border-transparent text-ink-soft hover:text-ink"
          }`}
        >
          🎴 Spese carte
        </button>
        <button
          type="button"
          onClick={() => setTab("other")}
          className={`px-4 py-2 text-sm font-semibold border-b-2 transition-colors ${
            tab === "other" ? "border-pink-deep text-ink" : "border-transparent text-ink-soft hover:text-ink"
          }`}
        >
          📦 Altre spese
        </button>
      </div>

      {tab === "cards" ? <CardPurchasesTab year={year} /> : <ExpensesTab year={year} />}

      <style>{styles}</style>
    </AdminShell>
  );
}

// ============================================================
// TAB 1: Spese carte (CardPurchase)
// ============================================================
function CardPurchasesTab({ year }: { year: string }) {
  const [items, setItems] = useState<CardPurchase[]>([]);
  const [total, setTotal] = useState("0");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");

  async function reload() {
    setLoading(true);
    setError(null);
    try {
      const qs = new URLSearchParams();
      if (year) qs.set("year", year);
      const data = await adminApi.get<CardPurchaseListResponse>(`/api/card-purchases/?${qs}`);
      setItems(data.items);
      setTotal(data.total_amount);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { reload(); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, [year]);

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      const form = e.target as HTMLFormElement;
      const fd = new FormData(form);
      const payload = {
        purchase_date: String(fd.get("purchase_date") || todayISO()),
        item: String(fd.get("item") || "").trim(),
        amount: Number(fd.get("amount") || 0),
        note: String(fd.get("note") || "") || null,
      };
      if (!payload.item) throw new Error("Descrizione obbligatoria");
      await adminApi.post("/api/card-purchases/", payload);
      form.reset();
      (form.elements.namedItem("item") as HTMLInputElement)?.focus();
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleSave(id: number, patch: Partial<CardPurchase>) {
    setBusy(true);
    try {
      await adminApi.patch(`/api/card-purchases/${id}`, patch);
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete(id: number) {
    if (!confirm("Eliminare questa spesa carte?")) return;
    setBusy(true);
    try {
      await adminApi.delete(`/api/card-purchases/${id}`);
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  const filtered = useMemo(() => {
    if (!search.trim()) return items;
    const q = search.toLowerCase();
    return items.filter((i) =>
      [i.item, i.note].filter(Boolean).join(" ").toLowerCase().includes(q),
    );
  }, [items, search]);

  return (
    <>
      {error && <div className="card p-4 mb-4 text-pink-deep font-semibold">⚠ {error}</div>}

      <div className="grid grid-cols-2 gap-2 mb-4">
        <Kpi label="Totale spese carte" value={fmtMoney(total)} color="bg-pink-soft" accent />
        <Kpi label="Voci" value={String(items.length)} color="bg-lilac-soft" />
      </div>

      <p className="text-xs text-ink-soft mb-3">
        Acquisti bulk legati alle carte: kg di carte miste, booster, deck box,
        ecc. Si sommano al costo del foglio Carte (no flipping) nel bilancio.
      </p>

      <input
        type="search"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        placeholder="🔎 Cerca testo libero…"
        className="input mb-3"
      />

      <form onSubmit={handleAdd} className="card p-4 mb-4">
        <h2 className="display text-base text-ink mb-3">+ Nuova spesa carte</h2>
        <div className="grid sm:grid-cols-6 gap-2">
          <input name="purchase_date" type="date" defaultValue={todayISO()} className="input" />
          <input name="item" placeholder="Cosa hai comprato *" required className="input col-span-2" />
          <input name="amount" type="number" step="0.01" min="0" placeholder="€" required className="input" />
          <input name="note" placeholder="Note (opzionale)" className="input col-span-2" />
        </div>
        <div className="mt-2">
          <button type="submit" disabled={busy} className="btn btn-primary text-sm">
            {busy ? "..." : "Aggiungi"}
          </button>
        </div>
      </form>

      {loading ? <p className="text-ink-soft">Caricamento…</p> : (
        filtered.length === 0 ? (
          <div className="card p-10 text-center text-ink-soft">Nessuna spesa carte.</div>
        ) : (
          <div className="card overflow-x-auto">
            <table className="min-w-full text-xs">
              <thead className="bg-white/60 backdrop-blur border-b border-ink/10 text-ink-soft uppercase tracking-wider">
                <tr>
                  <Th>Data</Th>
                  <Th>Oggetto</Th>
                  <Th className="text-right">€</Th>
                  <Th>Note</Th>
                  <Th></Th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((it) => (
                  <CardPurchaseRow key={it.id} item={it} busy={busy} onSave={(p) => handleSave(it.id, p)} onDelete={() => handleDelete(it.id)} />
                ))}
              </tbody>
            </table>
          </div>
        )
      )}
    </>
  );
}

function CardPurchaseRow({
  item, busy, onSave, onDelete,
}: {
  item: CardPurchase; busy: boolean;
  onSave: (p: Partial<CardPurchase>) => void;
  onDelete: () => void;
}) {
  const [date, setDate] = useState(item.purchase_date ?? "");
  const [name, setName] = useState(item.item);
  const [amount, setAmount] = useState(item.amount);
  const [note, setNote] = useState(item.note ?? "");

  function maybe(key: keyof CardPurchase, current: unknown, original: unknown) {
    if (current === original) return;
    if (typeof current === "string" && current === "" && (original === null || original === "")) return;
    onSave({ [key]: (current === "" ? null : current) as never });
  }

  return (
    <tr className="border-b border-ink/5 hover:bg-pink-soft/20">
      <Td>
        <input type="date" value={date} onChange={(e) => setDate(e.target.value)}
          onBlur={() => maybe("purchase_date", date, item.purchase_date)}
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
      <Td>
        <input value={note} onChange={(e) => setNote(e.target.value)}
          onBlur={() => maybe("note", note, item.note)}
          className="cell-input text-[11px] min-w-[200px]" />
      </Td>
      <Td>
        <button type="button" onClick={onDelete} disabled={busy}
          className="btn btn-ghost text-[10px] px-2 py-1" title="Elimina">🗑</button>
      </Td>
    </tr>
  );
}

// ============================================================
// TAB 2: Altre spese (Expense)
// ============================================================
function ExpensesTab({ year }: { year: string }) {
  const [items, setItems] = useState<Expense[]>([]);
  const [totals, setTotals] = useState({ amount: "0", cardRelated: "0", creationRelated: "0", byCategory: {} as Record<string, string> });
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [categoryFilter, setCategoryFilter] = useState<string>("");
  const [paidByFilter, setPaidByFilter] = useState<string>("");
  const [search, setSearch] = useState("");

  async function reload() {
    setLoading(true);
    setError(null);
    try {
      const qs = new URLSearchParams();
      if (year) qs.set("year", year);
      if (categoryFilter) qs.set("category", categoryFilter);
      if (paidByFilter) qs.set("paid_by", paidByFilter);
      if (search.trim()) qs.set("search", search.trim());
      const data = await adminApi.get<ExpenseListResponse>(`/api/expenses/?${qs}`);
      setItems(data.items);
      setTotals({
        amount: data.total_amount,
        cardRelated: data.total_card_related,
        creationRelated: data.total_creation_related,
        byCategory: data.by_category,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { reload(); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, [year, categoryFilter, paidByFilter]);

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      const form = e.target as HTMLFormElement;
      const fd = new FormData(form);
      const payload = {
        spend_date: String(fd.get("spend_date") || todayISO()),
        item: String(fd.get("item") || "").trim(),
        category: String(fd.get("category") || "") || null,
        amount: Number(fd.get("amount") || 0),
        paid_by: String(fd.get("paid_by") || "") || null,
        related_to_cards: fd.get("related_to_cards") === "on",
        related_to_creations: fd.get("related_to_creations") === "on",
        note: String(fd.get("note") || "") || null,
      };
      if (!payload.item) throw new Error("Descrizione obbligatoria");
      await adminApi.post("/api/expenses/", payload);
      form.reset();
      (form.elements.namedItem("item") as HTMLInputElement)?.focus();
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleSave(id: number, patch: Partial<Expense>) {
    setBusy(true);
    try {
      await adminApi.patch(`/api/expenses/${id}`, patch);
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete(id: number) {
    if (!confirm("Eliminare questa spesa?")) return;
    setBusy(true);
    try {
      await adminApi.delete(`/api/expenses/${id}`);
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      {error && <div className="card p-4 mb-4 text-pink-deep font-semibold">⚠ {error}</div>}

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-2 mb-4">
        <Kpi label="Totale altre spese" value={fmtMoney(totals.amount)} color="bg-pink-soft" accent />
        <Kpi label="Card-related" value={fmtMoney(totals.cardRelated)} sub="sommate a Spese carte" color="bg-mint" />
        <Kpi label="Creation-related" value={fmtMoney(totals.creationRelated)} sub="sommate alle Creazioni" color="bg-lilac" />
        <Kpi label="Voci" value={String(items.length)} color="bg-lilac-soft" />
      </div>

      {Object.keys(totals.byCategory).length > 0 && (
        <div className="card p-3 mb-4 flex flex-wrap gap-3 items-center">
          <span className="text-xs text-ink-soft uppercase tracking-wider">Per categoria:</span>
          {Object.entries(totals.byCategory).map(([cat, amt]) => (
            <span key={cat} className="text-sm">
              <strong className="text-ink capitalize">{cat}</strong>{" "}
              <span className="text-ink-soft">{fmtMoney(amt)}</span>
            </span>
          ))}
        </div>
      )}

      <div className="card p-3 mb-4 grid sm:grid-cols-[180px_120px_1fr] gap-2">
        <select value={categoryFilter} onChange={(e) => setCategoryFilter(e.target.value)} className="input">
          <option value="">Tutte le cat.</option>
          {CATEGORIES.filter(Boolean).map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
        <select value={paidByFilter} onChange={(e) => setPaidByFilter(e.target.value)} className="input">
          <option value="">Tutti</option>
          {PEOPLE.filter(Boolean).map((p) => <option key={p} value={p}>{p}</option>)}
        </select>
        <input
          type="search"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && reload()}
          placeholder="🔎 Cerca…"
          className="input"
        />
      </div>

      <form onSubmit={handleAdd} className="card p-4 mb-4">
        <h2 className="display text-base text-ink mb-3">+ Nuova spesa</h2>
        <div className="grid sm:grid-cols-6 gap-2">
          <input name="spend_date" type="date" defaultValue={todayISO()} className="input" />
          <input name="item" placeholder="Descrizione *" required className="input col-span-2" />
          <input name="amount" type="number" step="0.01" min="0" placeholder="€" required className="input" />
          <select name="category" className="input">
            {CATEGORIES.map((c) => <option key={c || "_"} value={c}>{c || "Categoria"}</option>)}
          </select>
          <select name="paid_by" className="input">
            {PEOPLE.map((p) => <option key={p || "_"} value={p}>{p || "Pagato da"}</option>)}
          </select>
        </div>
        <div className="grid sm:grid-cols-6 gap-2 mt-2">
          <label className="flex items-center gap-2 text-xs text-ink-soft col-span-2">
            <input type="checkbox" name="related_to_cards" />
            <span><strong>Carte</strong> (somma a Spese carte)</span>
          </label>
          <label className="flex items-center gap-2 text-xs text-ink-soft col-span-2">
            <input type="checkbox" name="related_to_creations" />
            <span><strong>Creazioni</strong> (somma alle Creazioni)</span>
          </label>
          <input name="note" placeholder="Note (opzionale)" className="input col-span-1" />
          <button type="submit" disabled={busy} className="btn btn-primary text-sm">
            {busy ? "..." : "Aggiungi"}
          </button>
        </div>
      </form>

      {loading ? <p className="text-ink-soft">Caricamento…</p> : (
        items.length === 0 ? (
          <div className="card p-10 text-center text-ink-soft">Nessuna spesa.</div>
        ) : (
          <div className="card overflow-x-auto">
            <table className="min-w-full text-xs">
              <thead className="bg-white/60 backdrop-blur border-b border-ink/10 text-ink-soft uppercase tracking-wider">
                <tr>
                  <Th>Data</Th>
                  <Th>Descrizione</Th>
                  <Th>Categoria</Th>
                  <Th className="text-right">€</Th>
                  <Th>Pagato da</Th>
                  <Th>Carte?</Th>
                  <Th>Creaz.?</Th>
                  <Th>Note</Th>
                  <Th></Th>
                </tr>
              </thead>
              <tbody>
                {items.map((it) => (
                  <ExpenseRow key={it.id} item={it} busy={busy} onSave={(p) => handleSave(it.id, p)} onDelete={() => handleDelete(it.id)} />
                ))}
              </tbody>
            </table>
          </div>
        )
      )}
    </>
  );
}

function ExpenseRow({
  item, busy, onSave, onDelete,
}: {
  item: Expense; busy: boolean;
  onSave: (p: Partial<Expense>) => void;
  onDelete: () => void;
}) {
  const [date, setDate] = useState(item.spend_date);
  const [name, setName] = useState(item.item);
  const [category, setCategory] = useState(item.category ?? "");
  const [amount, setAmount] = useState(item.amount);
  const [paidBy, setPaidBy] = useState(item.paid_by ?? "");
  const [note, setNote] = useState(item.note ?? "");

  function maybe(key: keyof Expense, current: unknown, original: unknown) {
    if (current === original) return;
    if (typeof current === "string" && current === "" && (original === null || original === "")) return;
    onSave({ [key]: (current === "" ? null : current) as never });
  }

  return (
    <tr className="border-b border-ink/5 hover:bg-pink-soft/20">
      <Td>
        <input type="date" value={date} onChange={(e) => setDate(e.target.value)}
          onBlur={() => maybe("spend_date", date, item.spend_date)}
          className="cell-input text-[11px] w-28" />
      </Td>
      <Td>
        <input value={name} onChange={(e) => setName(e.target.value)}
          onBlur={() => maybe("item", name, item.item)}
          className="cell-input font-semibold text-ink min-w-[180px]" />
      </Td>
      <Td>
        <select value={category} onChange={(e) => {
          setCategory(e.target.value);
          if (e.target.value !== (item.category ?? "")) onSave({ category: (e.target.value || null) as never });
        }} className="cell-input text-[11px] w-28">
          {CATEGORIES.map((c) => <option key={c || "_"} value={c}>{c || "—"}</option>)}
        </select>
      </Td>
      <Td className="text-right">
        <input type="number" step="0.01" min="0" value={amount}
          onChange={(e) => setAmount(e.target.value)}
          onBlur={() => maybe("amount", amount, item.amount)}
          className="cell-input text-right tabular-nums w-24 font-semibold" />
      </Td>
      <Td>
        <select value={paidBy} onChange={(e) => {
          setPaidBy(e.target.value);
          if (e.target.value !== (item.paid_by ?? "")) onSave({ paid_by: (e.target.value || null) as never });
        }} className="cell-input text-[11px] w-14">
          {PEOPLE.map((p) => <option key={p || "_"} value={p}>{p || "—"}</option>)}
        </select>
      </Td>
      <Td>
        <input
          type="checkbox"
          checked={item.related_to_cards}
          onChange={(e) => onSave({ related_to_cards: e.target.checked as never })}
          disabled={busy}
          title="Spesa relativa alle carte → si somma alle Spese carte"
        />
      </Td>
      <Td>
        <input
          type="checkbox"
          checked={item.related_to_creations}
          onChange={(e) => onSave({ related_to_creations: e.target.checked as never })}
          disabled={busy}
          title="Spesa relativa alle creazioni → si somma alle Creazioni"
        />
      </Td>
      <Td>
        <input value={note} onChange={(e) => setNote(e.target.value)}
          onBlur={() => maybe("note", note, item.note)}
          className="cell-input text-[11px] min-w-[160px]" />
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
