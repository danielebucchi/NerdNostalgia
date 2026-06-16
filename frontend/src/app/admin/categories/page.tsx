"use client";

import { useEffect, useMemo, useState } from "react";
import { AdminShell } from "@/components/admin/AdminShell";
import { adminApi } from "@/lib/admin-api";
import type { Category, CategoryListResponse, CategoryNode } from "@/lib/types";

function buildTree(flat: Category[]): CategoryNode[] {
  const byId: Record<number, CategoryNode> = {};
  flat.forEach((c) => {
    byId[c.id] = { ...c, children: [] };
  });
  const roots: CategoryNode[] = [];
  flat.forEach((c) => {
    const node = byId[c.id];
    if (c.parent_id == null) roots.push(node);
    else {
      const parent = byId[c.parent_id];
      if (parent) parent.children.push(node);
      else roots.push(node);
    }
  });
  return roots;
}

function slugify(s: string): string {
  return s
    .toLowerCase()
    .trim()
    .replace(/[àáâãä]/g, "a")
    .replace(/[èéêë]/g, "e")
    .replace(/[ìíîï]/g, "i")
    .replace(/[òóôõö]/g, "o")
    .replace(/[ùúûü]/g, "u")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "");
}

export default function AdminCategoriesPage() {
  const [items, setItems] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // Form nuovo
  const [newName, setNewName] = useState("");
  const [newSlug, setNewSlug] = useState("");
  const [newParentId, setNewParentId] = useState<string>(""); // "" = top-level

  async function reload() {
    setLoading(true);
    setError(null);
    try {
      const data = await adminApi.get<CategoryListResponse>("/api/categories/");
      setItems(data.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    reload();
  }, []);

  const tree = useMemo(() => buildTree(items), [items]);
  const tops = useMemo(() => items.filter((c) => c.parent_id == null), [items]);

  function handleNameChange(value: string) {
    setNewName(value);
    if (!newSlug || newSlug === slugify(newName)) {
      setNewSlug(slugify(value));
    }
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await adminApi.post("/api/categories/", {
        name: newName.trim(),
        slug: newSlug.trim() || slugify(newName),
        parent_id: newParentId === "" ? null : Number(newParentId),
        display_order: 0,
      });
      setNewName("");
      setNewSlug("");
      setNewParentId("");
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleSave(id: number, payload: Record<string, unknown>) {
    setBusy(true);
    setError(null);
    try {
      await adminApi.patch(`/api/categories/${id}`, payload);
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete(id: number, hasChildren: boolean) {
    const msg = hasChildren
      ? "Eliminare la categoria e TUTTE le sue sottocategorie? Gli articoli associati resteranno orfani (category_id = NULL)."
      : "Eliminare la categoria? Gli articoli associati resteranno orfani (category_id = NULL).";
    if (!confirm(msg)) return;
    setBusy(true);
    try {
      await adminApi.delete(`/api/categories/${id}`);
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <AdminShell>
      <h1 className="display text-3xl text-ink mb-1">Categorie</h1>
      <p className="text-ink-soft mb-6">
        Gerarchia categoria → sottocategoria (max 2 livelli). Lo{" "}
        <code>slug</code> viene usato per i markup e per le viste pubbliche.
      </p>

      {error && (
        <div className="card p-4 mb-4 text-pink-deep font-semibold">⚠ {error}</div>
      )}

      <form onSubmit={handleCreate} className="card p-5 mb-8">
        <h2 className="display text-lg text-ink mb-3">+ Nuova categoria</h2>
        <div className="grid sm:grid-cols-4 gap-3">
          <label className="block">
            <span className="text-xs font-bold uppercase tracking-wider text-ink-soft">
              Genitore
            </span>
            <select
              value={newParentId}
              onChange={(e) => setNewParentId(e.target.value)}
              className="input mt-1"
            >
              <option value="">— top-level —</option>
              {tops.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name}
                </option>
              ))}
            </select>
          </label>
          <label className="block">
            <span className="text-xs font-bold uppercase tracking-wider text-ink-soft">
              Nome *
            </span>
            <input
              type="text"
              required
              value={newName}
              onChange={(e) => handleNameChange(e.target.value)}
              placeholder="es. Pokémon"
              className="input mt-1"
            />
          </label>
          <label className="block">
            <span className="text-xs font-bold uppercase tracking-wider text-ink-soft">
              Slug *
            </span>
            <input
              type="text"
              required
              value={newSlug}
              onChange={(e) => setNewSlug(e.target.value)}
              placeholder="pokemon"
              pattern="[a-z0-9-]+"
              title="Solo lettere minuscole, numeri e trattini"
              className="input mt-1"
            />
          </label>
          <div className="flex items-end">
            <button
              type="submit"
              className="btn btn-primary text-sm w-full"
              disabled={busy || !newName.trim()}
            >
              {busy ? "Salvataggio…" : "Aggiungi"}
            </button>
          </div>
        </div>
      </form>

      {loading && <p className="text-ink-soft">Caricamento…</p>}

      {!loading && tree.length === 0 && (
        <div className="card p-10 text-center">
          <p className="text-ink-soft">Nessuna categoria. Aggiungine una qui sopra.</p>
        </div>
      )}

      <div className="space-y-4">
        {tree.map((top) => (
          <div key={top.id} className="card p-4">
            <CategoryRow
              category={top}
              busy={busy}
              isTop
              hasChildren={top.children.length > 0}
              onSave={(payload) => handleSave(top.id, payload)}
              onDelete={() => handleDelete(top.id, top.children.length > 0)}
            />
            {top.children.length > 0 && (
              <div className="mt-3 pl-6 border-l-2 border-dashed border-ink/15 space-y-2">
                {top.children.map((sub) => (
                  <CategoryRow
                    key={sub.id}
                    category={sub}
                    busy={busy}
                    isTop={false}
                    hasChildren={false}
                    onSave={(payload) => handleSave(sub.id, payload)}
                    onDelete={() => handleDelete(sub.id, false)}
                  />
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

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

interface RowProps {
  category: Category;
  busy: boolean;
  isTop: boolean;
  hasChildren: boolean;
  onSave: (payload: Record<string, unknown>) => void;
  onDelete: () => void;
}

function CategoryRow({ category, busy, isTop, hasChildren, onSave, onDelete }: RowProps) {
  const [name, setName] = useState(category.name);
  const [slug, setSlug] = useState(category.slug);
  const [order, setOrder] = useState(String(category.display_order));

  const dirty =
    name !== category.name ||
    slug !== category.slug ||
    Number(order) !== category.display_order;

  function save() {
    const payload: Record<string, unknown> = {};
    if (name !== category.name) payload.name = name.trim();
    if (slug !== category.slug) payload.slug = slug.trim();
    if (Number(order) !== category.display_order) payload.display_order = Number(order);
    onSave(payload);
  }

  return (
    <div className="grid sm:grid-cols-[auto_2fr_2fr_auto_auto] items-center gap-2">
      <span className={`text-xl ${isTop ? "text-pink-deep" : "text-ink-soft/60"}`}>
        {isTop ? "🏷" : "↳"}
      </span>
      <input
        type="text"
        value={name}
        onChange={(e) => setName(e.target.value)}
        className="input"
        placeholder="Nome"
      />
      <input
        type="text"
        value={slug}
        onChange={(e) => setSlug(e.target.value)}
        className="input font-mono text-xs"
        placeholder="slug"
        pattern="[a-z0-9-]+"
      />
      <input
        type="number"
        min="0"
        value={order}
        onChange={(e) => setOrder(e.target.value)}
        className="input w-20"
        title="Ordinamento"
      />
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
          title={hasChildren ? "Eliminerà anche le sottocategorie" : "Elimina"}
        >
          🗑
        </button>
      </div>
    </div>
  );
}
