"use client";

import { useEffect, useMemo, useState } from "react";
import { AdminShell } from "@/components/admin/AdminShell";
import { adminApi } from "@/lib/admin-api";
import type {
  Category,
  CategoryListResponse,
  CategoryNode,
  Platform,
  PlatformListResponse,
} from "@/lib/types";

type Tab = "categories" | "platforms";

export default function TassonomiaPage() {
  const [tab, setTab] = useState<Tab>("categories");

  return (
    <AdminShell>
      <div className="mb-3">
        <h1 className="display text-3xl text-ink">🏷 Tassonomia</h1>
        <p className="text-ink-soft mt-1 text-sm">
          Dati di riferimento del sistema: categorie articoli e piattaforme
          (le stesse vengono usate sia per acquisti che per vendite).
        </p>
      </div>

      <div className="flex gap-1 mb-4 border-b border-ink/10 flex-wrap">
        <button
          type="button"
          onClick={() => setTab("categories")}
          className={`px-4 py-2 text-sm font-semibold border-b-2 transition-colors ${
            tab === "categories" ? "border-pink-deep text-ink" : "border-transparent text-ink-soft hover:text-ink"
          }`}
        >
          🏷 Categorie
        </button>
        <button
          type="button"
          onClick={() => setTab("platforms")}
          className={`px-4 py-2 text-sm font-semibold border-b-2 transition-colors ${
            tab === "platforms" ? "border-pink-deep text-ink" : "border-transparent text-ink-soft hover:text-ink"
          }`}
        >
          🛒 Piattaforme
        </button>
      </div>

      {tab === "categories" ? <CategoriesTab /> : <PlatformsTab />}

      <style>{styles}</style>
    </AdminShell>
  );
}

// ============================================================
// CATEGORIES TAB
// ============================================================
function buildTree(flat: Category[]): CategoryNode[] {
  const byId: Record<number, CategoryNode> = {};
  flat.forEach((c) => { byId[c.id] = { ...c, children: [] }; });
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
  return s.toLowerCase().trim()
    .replace(/[àáâãä]/g, "a")
    .replace(/[èéêë]/g, "e")
    .replace(/[ìíîï]/g, "i")
    .replace(/[òóôõö]/g, "o")
    .replace(/[ùúûü]/g, "u")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "");
}

function CategoriesTab() {
  const [items, setItems] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const [newName, setNewName] = useState("");
  const [newSlug, setNewSlug] = useState("");
  const [newParentId, setNewParentId] = useState<string>("");

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

  useEffect(() => { reload(); }, []);

  const tree = useMemo(() => buildTree(items), [items]);
  const tops = useMemo(() => items.filter((c) => c.parent_id == null), [items]);

  function handleNameChange(value: string) {
    setNewName(value);
    if (!newSlug || newSlug === slugify(newName)) setNewSlug(slugify(value));
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
      setNewName(""); setNewSlug(""); setNewParentId("");
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleSave(id: number, payload: Record<string, unknown>) {
    setBusy(true); setError(null);
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
      ? "Eliminare la categoria e TUTTE le sue sottocategorie?"
      : "Eliminare la categoria?";
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
    <>
      {error && <div className="card p-4 mb-4 text-pink-deep font-semibold">⚠ {error}</div>}

      <form onSubmit={handleCreate} className="card p-5 mb-6">
        <h2 className="display text-lg text-ink mb-3">+ Nuova categoria</h2>
        <div className="grid sm:grid-cols-4 gap-3">
          <label className="block">
            <span className="text-xs font-bold uppercase tracking-wider text-ink-soft">Genitore</span>
            <select value={newParentId} onChange={(e) => setNewParentId(e.target.value)} className="input mt-1">
              <option value="">— top-level —</option>
              {tops.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
            </select>
          </label>
          <label className="block">
            <span className="text-xs font-bold uppercase tracking-wider text-ink-soft">Nome *</span>
            <input type="text" required value={newName} onChange={(e) => handleNameChange(e.target.value)} placeholder="es. Pokémon" className="input mt-1" />
          </label>
          <label className="block">
            <span className="text-xs font-bold uppercase tracking-wider text-ink-soft">Slug *</span>
            <input type="text" required value={newSlug} onChange={(e) => setNewSlug(e.target.value)} placeholder="pokemon" pattern="[a-z0-9-]+" className="input mt-1" />
          </label>
          <div className="flex items-end">
            <button type="submit" className="btn btn-primary text-sm w-full" disabled={busy || !newName.trim()}>
              {busy ? "Salvataggio…" : "Aggiungi"}
            </button>
          </div>
        </div>
      </form>

      {loading && <p className="text-ink-soft">Caricamento…</p>}

      {!loading && tree.length === 0 && (
        <div className="card p-10 text-center">
          <p className="text-ink-soft">Nessuna categoria.</p>
        </div>
      )}

      <div className="space-y-4">
        {tree.map((top) => (
          <div key={top.id} className="card p-4">
            <CategoryRow category={top} busy={busy} isTop hasChildren={top.children.length > 0}
              onSave={(p) => handleSave(top.id, p)} onDelete={() => handleDelete(top.id, top.children.length > 0)} />
            {top.children.length > 0 && (
              <div className="mt-3 pl-6 border-l-2 border-dashed border-ink/15 space-y-2">
                {top.children.map((sub) => (
                  <CategoryRow key={sub.id} category={sub} busy={busy} isTop={false} hasChildren={false}
                    onSave={(p) => handleSave(sub.id, p)} onDelete={() => handleDelete(sub.id, false)} />
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </>
  );
}

function CategoryRow({ category, busy, isTop, hasChildren, onSave, onDelete }: {
  category: Category; busy: boolean; isTop: boolean; hasChildren: boolean;
  onSave: (payload: Record<string, unknown>) => void; onDelete: () => void;
}) {
  const [name, setName] = useState(category.name);
  const [slug, setSlug] = useState(category.slug);
  const [order, setOrder] = useState(String(category.display_order));
  const dirty = name !== category.name || slug !== category.slug || Number(order) !== category.display_order;
  function save() {
    const payload: Record<string, unknown> = {};
    if (name !== category.name) payload.name = name.trim();
    if (slug !== category.slug) payload.slug = slug.trim();
    if (Number(order) !== category.display_order) payload.display_order = Number(order);
    onSave(payload);
  }
  return (
    <div className="grid sm:grid-cols-[auto_2fr_2fr_auto_auto] items-center gap-2">
      <span className={`text-xl ${isTop ? "text-pink-deep" : "text-ink-soft/60"}`}>{isTop ? "🏷" : "↳"}</span>
      <input type="text" value={name} onChange={(e) => setName(e.target.value)} className="input" placeholder="Nome" />
      <input type="text" value={slug} onChange={(e) => setSlug(e.target.value)} className="input font-mono text-xs" placeholder="slug" pattern="[a-z0-9-]+" />
      <input type="number" min="0" value={order} onChange={(e) => setOrder(e.target.value)} className="input w-20" title="Ordinamento" />
      <div className="flex gap-1">
        {dirty && <button type="button" className="btn btn-primary text-xs px-3 py-1" onClick={save} disabled={busy}>Salva</button>}
        <button type="button" className="btn btn-ghost text-xs px-3 py-1" onClick={onDelete} disabled={busy} title={hasChildren ? "Eliminerà anche le sottocategorie" : "Elimina"}>🗑</button>
      </div>
    </div>
  );
}

// ============================================================
// PLATFORMS TAB
// ============================================================
function PlatformsTab() {
  const [items, setItems] = useState<Platform[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function reload() {
    setLoading(true);
    setError(null);
    try {
      const data = await adminApi.get<PlatformListResponse>("/api/platforms/");
      setItems(data.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { reload(); }, []);

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true); setError(null);
    try {
      const form = e.target as HTMLFormElement;
      const fd = new FormData(form);
      const payload = {
        name: String(fd.get("name") || "").trim(),
        slug: String(fd.get("slug") || "") || null,
        icon: String(fd.get("icon") || "") || null,
        display_order: Number(fd.get("display_order") || 0),
        is_active: true,
        note: String(fd.get("note") || "") || null,
      };
      if (!payload.name) throw new Error("Nome obbligatorio");
      await adminApi.post("/api/platforms/", payload);
      form.reset();
      (form.elements.namedItem("name") as HTMLInputElement)?.focus();
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleSave(id: number, patch: Partial<Platform>) {
    setBusy(true);
    try {
      await adminApi.patch(`/api/platforms/${id}`, patch);
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete(id: number, name: string) {
    if (!confirm(`Eliminare definitivamente "${name}"?\n\nSe ci sono record storici che la usano resteranno con il nome di stringa, ma scomparirà dai dropdown futuri. Se vuoi nasconderla senza cancellarla, deseleziona "attiva".`)) return;
    setBusy(true);
    try {
      await adminApi.delete(`/api/platforms/${id}`);
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

      <p className="text-xs text-ink-soft mb-3">
        Le piattaforme inserite qui compaiono in TUTTI i dropdown (acquisto/vendita).
        Disattiva una piattaforma per nasconderla dai dropdown futuri senza
        perdere i record storici. <code>display_order</code> controlla l&apos;ordine
        nei menu.
      </p>

      <form onSubmit={handleAdd} className="card p-5 mb-6">
        <h2 className="display text-lg text-ink mb-3">+ Nuova piattaforma</h2>
        <div className="grid sm:grid-cols-5 gap-3">
          <input name="name" required placeholder="Nome (es. Vinted)" className="input" />
          <input name="slug" placeholder="slug (auto)" className="input font-mono text-xs" />
          <input name="icon" placeholder="Icona (emoji)" maxLength={10} className="input" />
          <input name="display_order" type="number" defaultValue="50" placeholder="Order" className="input" />
          <button type="submit" className="btn btn-primary text-sm" disabled={busy}>
            {busy ? "..." : "Aggiungi"}
          </button>
        </div>
        <input name="note" placeholder="Note (opzionale)" className="input mt-2" />
      </form>

      {loading && <p className="text-ink-soft">Caricamento…</p>}

      {!loading && items.length === 0 && (
        <div className="card p-10 text-center">
          <p className="text-ink-soft">Nessuna piattaforma.</p>
        </div>
      )}

      <div className="space-y-2">
        {items.map((p) => (
          <PlatformRow key={p.id} platform={p} busy={busy}
            onSave={(patch) => handleSave(p.id, patch)}
            onDelete={() => handleDelete(p.id, p.name)} />
        ))}
      </div>
    </>
  );
}

function PlatformRow({ platform, busy, onSave, onDelete }: {
  platform: Platform; busy: boolean;
  onSave: (patch: Partial<Platform>) => void; onDelete: () => void;
}) {
  const [name, setName] = useState(platform.name);
  const [slug, setSlug] = useState(platform.slug);
  const [icon, setIcon] = useState(platform.icon ?? "");
  const [order, setOrder] = useState(String(platform.display_order));
  const [note, setNote] = useState(platform.note ?? "");

  function maybe(key: keyof Platform, current: unknown, original: unknown) {
    if (current === original) return;
    if (typeof current === "string" && current === "" && (original === null || original === "")) return;
    onSave({ [key]: (current === "" ? null : current) as never });
  }

  return (
    <div className={`card p-3 grid sm:grid-cols-[auto_2fr_2fr_auto_auto_2fr_auto_auto] items-center gap-2 ${
      !platform.is_active ? "opacity-50" : ""
    }`}>
      <span className="text-xl w-8 text-center">{platform.icon ?? "🛒"}</span>
      <input
        value={name}
        onChange={(e) => setName(e.target.value)}
        onBlur={() => maybe("name", name, platform.name)}
        className="input font-semibold"
        placeholder="Nome"
      />
      <input
        value={slug}
        onChange={(e) => setSlug(e.target.value)}
        onBlur={() => maybe("slug", slug, platform.slug)}
        className="input font-mono text-xs"
        placeholder="slug"
        pattern="[a-z0-9-]+"
      />
      <input
        value={icon}
        onChange={(e) => setIcon(e.target.value)}
        onBlur={() => maybe("icon", icon, platform.icon)}
        className="input w-16 text-center"
        maxLength={10}
        placeholder="🛒"
        title="Icona (emoji)"
      />
      <input
        type="number"
        min="0"
        value={order}
        onChange={(e) => setOrder(e.target.value)}
        onBlur={() => maybe("display_order", Number(order), platform.display_order)}
        className="input w-20"
        title="Ordinamento"
      />
      <input
        value={note}
        onChange={(e) => setNote(e.target.value)}
        onBlur={() => maybe("note", note, platform.note)}
        className="input text-xs"
        placeholder="Note (opzionale)"
      />
      <label className="flex items-center gap-1 text-xs">
        <input
          type="checkbox"
          checked={platform.is_active}
          onChange={(e) => onSave({ is_active: e.target.checked as never })}
          disabled={busy}
        />
        Attiva
      </label>
      <button
        type="button"
        onClick={onDelete}
        disabled={busy}
        className="btn btn-ghost text-xs px-3 py-1"
        title="Elimina"
      >🗑</button>
    </div>
  );
}

const styles = `
  .input {
    display: block;
    width: 100%;
    padding: 0.45rem 0.7rem;
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
`;
