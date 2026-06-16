"use client";

import { useEffect, useMemo, useState } from "react";
import { AdminShell } from "@/components/admin/AdminShell";
import { adminApi } from "@/lib/admin-api";
import { useCategories } from "@/lib/useCategories";
import type { Category, MarketplaceFee } from "@/lib/types";

interface FeeListResp {
  items: MarketplaceFee[];
  total: number;
}

const MARKETPLACES = ["vinted", "ebay"] as const;

export default function AdminMarkupsPage() {
  const { flat: categories, byId: catById } = useCategories();
  const [fees, setFees] = useState<MarketplaceFee[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // Form state per nuovo markup
  const [marketplace, setMarketplace] = useState<string>("ebay");
  const [categoryId, setCategoryId] = useState<string>(""); // "" = default (NULL)
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
        category_id: categoryId === "" ? null : Number(categoryId),
        markup_percent: Number(percent),
        note: note.trim() || null,
      });
      setCategoryId("");
      setPercent("");
      setNote("");
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleUpdate(id: number, payload: Record<string, unknown>) {
    setBusy(true);
    setError(null);
    try {
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
            <select
              value={categoryId}
              onChange={(e) => setCategoryId(e.target.value)}
              className="input mt-1"
            >
              <option value="">— default (tutte) —</option>
              {renderCategoryOptions(categories)}
            </select>
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
              placeholder="es: commissione finale eBay collezioni"
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
                  categories={categories}
                  catById={catById}
                  onSave={(payload) => handleUpdate(f.id, payload)}
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
          border: 1px solid rgba(61, 42, 92, 0.12);
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
          {"  ↳ "} {sub.name}
        </option>
      )),
  ]);
}

function categoryLabel(catById: Record<number, Category>, id: number | null): string {
  if (id == null) return "— default —";
  const cat = catById[id];
  if (!cat) return `#${id}`;
  if (cat.parent_id == null) return cat.name;
  const parent = catById[cat.parent_id];
  return parent ? `${parent.name} › ${cat.name}` : cat.name;
}

function FeeRow({
  fee,
  busy,
  categories,
  catById,
  onSave,
  onDelete,
}: {
  fee: MarketplaceFee;
  busy: boolean;
  categories: Category[];
  catById: Record<number, Category>;
  onSave: (payload: Record<string, unknown>) => void;
  onDelete: () => void;
}) {
  const [categoryId, setCategoryId] = useState<string>(
    fee.category_id != null ? String(fee.category_id) : "",
  );
  const [percent, setPercent] = useState(fee.markup_percent);
  const [note, setNote] = useState(fee.note ?? "");

  const currentCatId = categoryId === "" ? null : Number(categoryId);
  const dirtyCat = currentCatId !== fee.category_id;
  const dirtyPercent = percent !== fee.markup_percent;
  const dirtyNote = (note.trim() || null) !== fee.note;
  const anyDirty = dirtyCat || dirtyPercent || dirtyNote;

  const labelPreview = useMemo(
    () => categoryLabel(catById, currentCatId),
    [catById, currentCatId],
  );

  function saveAll() {
    const payload: Record<string, unknown> = {};
    if (dirtyCat) payload.category_id = currentCatId;
    if (dirtyPercent) payload.markup_percent = Number(percent);
    if (dirtyNote) payload.note = note.trim() || null;
    onSave(payload);
  }

  return (
    <div className="card p-3 grid sm:grid-cols-[1.5fr_1fr_2fr_auto] items-center gap-2">
      <div>
        <select
          value={categoryId}
          onChange={(e) => setCategoryId(e.target.value)}
          className="input"
          title={labelPreview}
        >
          <option value="">— default (tutte) —</option>
          {renderCategoryOptions(categories)}
        </select>
      </div>
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
