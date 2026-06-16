"use client";

import { useEffect, useState } from "react";
import { AdminShell } from "@/components/admin/AdminShell";
import { adminApi } from "@/lib/admin-api";
import type { MarketplaceFee } from "@/lib/types";

interface FeeListResp {
  items: MarketplaceFee[];
  total: number;
}

const MARKETPLACES = ["vinted", "ebay"] as const;

export default function AdminMarkupsPage() {
  const [fees, setFees] = useState<MarketplaceFee[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // Form state for new fee
  const [marketplace, setMarketplace] = useState<string>("ebay");
  const [category, setCategory] = useState("");
  const [percent, setPercent] = useState("");
  const [note, setNote] = useState("");

  async function reload() {
    setLoading(true);
    setError(null);
    try {
      const data = await adminApi.get<FeeListResp>("/api/marketplace-fees/");
      setFees(data.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    reload();
  }, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await adminApi.post("/api/marketplace-fees/", {
        marketplace,
        category: category.trim() || null,
        markup_percent: Number(percent),
        note: note.trim() || null,
      });
      setCategory("");
      setPercent("");
      setNote("");
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleUpdate(id: number, field: keyof MarketplaceFee, value: string) {
    setBusy(true);
    setError(null);
    try {
      const payload: Record<string, unknown> = {};
      if (field === "markup_percent") payload.markup_percent = Number(value);
      else if (field === "category") payload.category = value.trim() || null;
      else if (field === "note") payload.note = value.trim() || null;
      await adminApi.patch(`/api/marketplace-fees/${id}`, payload);
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete(id: number) {
    if (!confirm("Eliminare questo markup?")) return;
    setBusy(true);
    try {
      await adminApi.delete(`/api/marketplace-fees/${id}`);
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  // Raggruppa per marketplace
  const grouped: Record<string, MarketplaceFee[]> = {};
  for (const f of fees) {
    (grouped[f.marketplace] ??= []).push(f);
  }

  return (
    <AdminShell>
      <h1 className="display text-3xl text-ink mb-1">Commissioni marketplace</h1>
      <p className="text-ink-soft mb-6">
        Preset di maggiorazione che appaiono come bottoncini sotto al campo prezzo
        di Vinted ed eBay. Categoria <code>vuota</code> = default per quel marketplace.
      </p>

      {error && (
        <div className="card p-4 mb-4 text-pink-deep font-semibold">⚠ {error}</div>
      )}

      <form onSubmit={handleCreate} className="card p-5 mb-8">
        <h2 className="display text-lg text-ink mb-3">+ Nuovo markup</h2>
        <div className="grid sm:grid-cols-2 lg:grid-cols-5 gap-3">
          <label className="block">
            <span className="text-xs font-bold uppercase tracking-wider text-ink-soft">
              Marketplace
            </span>
            <select
              value={marketplace}
              onChange={(e) => setMarketplace(e.target.value)}
              className="input mt-1"
            >
              {MARKETPLACES.map((m) => (
                <option key={m} value={m}>{m}</option>
              ))}
            </select>
          </label>
          <label className="block">
            <span className="text-xs font-bold uppercase tracking-wider text-ink-soft">
              Categoria
            </span>
            <input
              type="text"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              placeholder="vuoto = default"
              className="input mt-1"
            />
          </label>
          <label className="block">
            <span className="text-xs font-bold uppercase tracking-wider text-ink-soft">
              Markup %
            </span>
            <input
              type="number"
              step="0.01"
              min="0"
              max="100"
              required
              value={percent}
              onChange={(e) => setPercent(e.target.value)}
              placeholder="11.00"
              className="input mt-1"
            />
          </label>
          <label className="block lg:col-span-2">
            <span className="text-xs font-bold uppercase tracking-wider text-ink-soft">
              Note
            </span>
            <input
              type="text"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="es: commissione finale eBay categoria collezioni"
              className="input mt-1"
            />
          </label>
        </div>
        <div className="mt-4">
          <button type="submit" className="btn btn-primary text-sm" disabled={busy}>
            {busy ? "Salvataggio…" : "Aggiungi"}
          </button>
        </div>
      </form>

      {loading && <p className="text-ink-soft">Caricamento…</p>}

      {!loading &&
        Object.entries(grouped).map(([mk, items]) => (
          <section key={mk} className="mb-8">
            <h2 className="display text-xl text-ink mb-3 capitalize">{mk}</h2>
            <div className="space-y-2">
              {items.map((f) => (
                <FeeRow
                  key={f.id}
                  fee={f}
                  busy={busy}
                  onUpdate={(field, value) => handleUpdate(f.id, field, value)}
                  onDelete={() => handleDelete(f.id)}
                />
              ))}
            </div>
          </section>
        ))}

      <style>{`
        .input {
          display: block;
          width: 100%;
          padding: 0.55rem 0.8rem;
          border: 2px solid #3d2a5c;
          border-radius: 12px;
          background: #fffaf3;
          color: #3d2a5c;
          font-family: "Manrope", sans-serif;
          font-size: 0.95rem;
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

function FeeRow({
  fee,
  busy,
  onUpdate,
  onDelete,
}: {
  fee: MarketplaceFee;
  busy: boolean;
  onUpdate: (field: keyof MarketplaceFee, value: string) => void;
  onDelete: () => void;
}) {
  const [category, setCategory] = useState(fee.category ?? "");
  const [percent, setPercent] = useState(fee.markup_percent);
  const [note, setNote] = useState(fee.note ?? "");

  const dirtyCat = (category.trim() || null) !== fee.category;
  const dirtyPercent = percent !== fee.markup_percent;
  const dirtyNote = (note.trim() || null) !== fee.note;
  const anyDirty = dirtyCat || dirtyPercent || dirtyNote;

  async function saveAll() {
    if (dirtyCat) await onUpdate("category", category);
    if (dirtyPercent) await onUpdate("markup_percent", percent);
    if (dirtyNote) await onUpdate("note", note);
  }

  return (
    <div className="card p-3 grid sm:grid-cols-[1fr_1fr_2fr_auto] items-center gap-2">
      <input
        type="text"
        value={category}
        onChange={(e) => setCategory(e.target.value)}
        placeholder="default"
        className="input"
      />
      <div className="flex items-center gap-1">
        <input
          type="number"
          step="0.01"
          min="0"
          max="100"
          value={percent}
          onChange={(e) => setPercent(e.target.value)}
          className="input"
        />
        <span className="text-ink-soft">%</span>
      </div>
      <input
        type="text"
        value={note}
        onChange={(e) => setNote(e.target.value)}
        placeholder="note"
        className="input"
      />
      <div className="flex gap-1">
        {anyDirty && (
          <button
            type="button"
            className="btn btn-primary text-xs px-3 py-1"
            onClick={saveAll}
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
    </div>
  );
}
