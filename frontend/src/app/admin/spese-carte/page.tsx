"use client";

import { useEffect, useState } from "react";
import { AdminShell } from "@/components/admin/AdminShell";
import { adminApi } from "@/lib/admin-api";
import type { CardPurchase, CardPurchaseListResponse } from "@/lib/types";

function fmtMoney(v: string | number | null | undefined): string {
  if (v == null || v === "") return "—";
  const n = typeof v === "number" ? v : Number(v);
  if (!Number.isFinite(n)) return "—";
  return new Intl.NumberFormat("it-IT", {
    style: "currency",
    currency: "EUR",
  }).format(n);
}

export default function AdminCardPurchasesPage() {
  const [items, setItems] = useState<CardPurchase[]>([]);
  const [totalAmount, setTotalAmount] = useState<string>("0");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [year, setYear] = useState<string>(String(new Date().getFullYear()));

  // Form nuovo
  const [date, setDate] = useState("");
  const [item, setItem] = useState("");
  const [amount, setAmount] = useState("");
  const [note, setNote] = useState("");

  async function reload() {
    setLoading(true);
    setError(null);
    try {
      const qs = new URLSearchParams();
      if (year) qs.set("year", year);
      const data = await adminApi.get<CardPurchaseListResponse>(
        `/api/card-purchases/?${qs}`,
      );
      setItems(data.items);
      setTotalAmount(data.total_amount);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [year]);

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await adminApi.post("/api/card-purchases/", {
        purchase_date: date || null,
        item: item.trim(),
        amount: Number(amount),
        note: note.trim() || null,
      });
      setDate("");
      setItem("");
      setAmount("");
      setNote("");
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
      await adminApi.delete(`/api/card-purchases/${id}`);
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleSaveField(
    id: number,
    payload: Record<string, unknown>,
  ) {
    setBusy(true);
    try {
      await adminApi.patch(`/api/card-purchases/${id}`, payload);
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <AdminShell>
      <h1 className="display text-3xl text-ink mb-1">🃏 Spese carte</h1>
      <p className="text-ink-soft mb-6 text-sm">
        Acquisti carte all'ingrosso (bustine, lotti). Clone del foglio "Spese carte".
      </p>

      {error && (
        <div className="card p-4 mb-4 text-pink-deep font-semibold">⚠ {error}</div>
      )}

      <div className="flex items-end gap-3 mb-4 flex-wrap">
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
            {[
              new Date().getFullYear(),
              new Date().getFullYear() - 1,
              new Date().getFullYear() - 2,
            ].map((y) => (
              <option key={y} value={y}>{y}</option>
            ))}
          </select>
        </label>
        <div className="card px-4 py-2">
          <span className="text-[10px] uppercase tracking-wider text-ink-soft block">
            Totale anno
          </span>
          <span className="display text-2xl text-pink-deep tabular-nums">
            {fmtMoney(totalAmount)}
          </span>
        </div>
      </div>

      <form onSubmit={handleAdd} className="card p-4 mb-6">
        <h2 className="display text-base text-ink mb-3">+ Aggiungi spesa</h2>
        <div className="grid sm:grid-cols-5 gap-3">
          <label className="block">
            <span className="text-xs font-bold uppercase tracking-wider text-ink-soft">
              Data
            </span>
            <input
              type="date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
              className="input mt-1"
            />
          </label>
          <label className="block sm:col-span-2">
            <span className="text-xs font-bold uppercase tracking-wider text-ink-soft">
              Oggetto *
            </span>
            <input
              type="text"
              required
              value={item}
              onChange={(e) => setItem(e.target.value)}
              placeholder="10 bustine Avventure Insieme"
              className="input mt-1"
            />
          </label>
          <label className="block">
            <span className="text-xs font-bold uppercase tracking-wider text-ink-soft">
              Importo *
            </span>
            <input
              type="number"
              step="0.01"
              min="0"
              required
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              className="input mt-1"
            />
          </label>
          <div className="flex items-end">
            <button
              type="submit"
              className="btn btn-primary text-sm w-full"
              disabled={busy}
            >
              {busy ? "..." : "Aggiungi"}
            </button>
          </div>
        </div>
        <input
          type="text"
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="Nota (opzionale)"
          className="input mt-3"
        />
      </form>

      {loading && <p className="text-ink-soft">Caricamento…</p>}

      {!loading && items.length === 0 && (
        <div className="card p-10 text-center">
          <p className="text-ink-soft">Nessuna spesa per questo anno.</p>
        </div>
      )}

      {!loading && items.length > 0 && (
        <div className="card overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="bg-white/60 backdrop-blur border-b border-ink/10 text-ink-soft text-[11px] uppercase tracking-wider">
              <tr>
                <th className="text-left py-2 px-3">Data</th>
                <th className="text-left py-2 px-3">Oggetto</th>
                <th className="text-right py-2 px-3">Importo</th>
                <th className="text-left py-2 px-3 hidden md:table-cell">Nota</th>
                <th className="py-2 px-3"></th>
              </tr>
            </thead>
            <tbody>
              {items.map((p) => (
                <Row
                  key={p.id}
                  item={p}
                  busy={busy}
                  onSave={(payload) => handleSaveField(p.id, payload)}
                  onDelete={() => handleDelete(p.id)}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}

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

function Row({
  item,
  busy,
  onSave,
  onDelete,
}: {
  item: CardPurchase;
  busy: boolean;
  onSave: (p: Record<string, unknown>) => void;
  onDelete: () => void;
}) {
  const [date, setDate] = useState(item.purchase_date ?? "");
  const [name, setName] = useState(item.item);
  const [amount, setAmount] = useState(item.amount);
  const [note, setNote] = useState(item.note ?? "");

  const dirty =
    (date || null) !== (item.purchase_date || null) ||
    name !== item.item ||
    amount !== item.amount ||
    (note.trim() || null) !== (item.note || null);

  function save() {
    onSave({
      purchase_date: date || null,
      item: name.trim(),
      amount: Number(amount),
      note: note.trim() || null,
    });
  }

  return (
    <tr className="border-b border-ink/5 hover:bg-pink-soft/30">
      <td className="py-2 px-3">
        <input
          type="date"
          value={date}
          onChange={(e) => setDate(e.target.value)}
          className="input"
        />
      </td>
      <td className="py-2 px-3">
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="input"
        />
      </td>
      <td className="py-2 px-3 text-right">
        <input
          type="number"
          step="0.01"
          min="0"
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
          className="input text-right tabular-nums"
        />
      </td>
      <td className="py-2 px-3 hidden md:table-cell">
        <input
          type="text"
          value={note}
          onChange={(e) => setNote(e.target.value)}
          className="input"
          placeholder="nota"
        />
      </td>
      <td className="py-2 px-3 whitespace-nowrap">
        <div className="flex gap-1">
          {dirty && (
            <button
              type="button"
              className="btn btn-primary text-xs px-3 py-1"
              onClick={save}
              disabled={busy}
            >
              Salva
            </button>
          )}
          <button
            type="button"
            className="btn btn-ghost text-xs px-3 py-1"
            onClick={onDelete}
            disabled={busy}
          >
            🗑
          </button>
        </div>
      </td>
    </tr>
  );
}
