"use client";

import { useEffect, useState } from "react";
import { AdminShell } from "@/components/admin/AdminShell";
import { adminApi } from "@/lib/admin-api";
import { useCategories } from "@/lib/useCategories";
import type { Category } from "@/lib/types";

interface VintedSettings {
  id: number;
  vinted_user_id: number;
  enabled: boolean;
  sync_hour: number;
  last_run_at: string | null;
}

interface VintedMapping {
  id: number;
  vinted_catalog_id: number;
  vinted_catalog_name: string;
  category_id: number | null;
  enabled: boolean;
}

interface VintedSyncLog {
  id: number;
  started_at: string;
  finished_at: string | null;
  triggered_by: string;
  items_fetched: number;
  items_imported: number;
  items_updated: number;
  items_skipped: number;
  error_message: string | null;
}

function fmtDateTime(s: string | null): string {
  if (!s) return "—";
  try {
    const d = new Date(s);
    return d.toLocaleString("it-IT", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return s;
  }
}

function duration(start: string, end: string | null): string {
  if (!end) return "in corso";
  const ms = new Date(end).getTime() - new Date(start).getTime();
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

export default function AdminImportVintedPage() {
  const { flat: categories } = useCategories();
  const [settings, setSettings] = useState<VintedSettings | null>(null);
  const [mappings, setMappings] = useState<VintedMapping[]>([]);
  const [logs, setLogs] = useState<VintedSyncLog[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form nuovo mapping
  const [newCatalogId, setNewCatalogId] = useState("");
  const [newCatalogName, setNewCatalogName] = useState("");
  const [newCategoryId, setNewCategoryId] = useState("");

  async function reload() {
    setError(null);
    try {
      const [s, m, l] = await Promise.all([
        adminApi.get<VintedSettings>("/api/vinted/settings"),
        adminApi.get<VintedMapping[]>("/api/vinted/mappings"),
        adminApi.get<VintedSyncLog[]>("/api/vinted/logs?limit=10"),
      ]);
      setSettings(s);
      setMappings(m);
      setLogs(l);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  useEffect(() => {
    reload();
  }, []);

  async function handleTriggerSync() {
    if (!confirm("Avviare ora una sync dal profilo Vinted? Può richiedere 10-30 secondi.")) return;
    setBusy(true);
    setError(null);
    try {
      const log = await adminApi.post<VintedSyncLog>("/api/vinted/sync");
      await reload();
      if (log.error_message) {
        setError(`Sync completata con errore: ${log.error_message}`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleSettingsSave(patch: Partial<VintedSettings>) {
    setBusy(true);
    try {
      const next = await adminApi.patch<VintedSettings>(
        "/api/vinted/settings",
        patch,
      );
      setSettings(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleMappingSave(id: number, patch: Partial<VintedMapping>) {
    setBusy(true);
    try {
      await adminApi.patch(`/api/vinted/mappings/${id}`, patch);
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleMappingDelete(id: number) {
    if (!confirm("Eliminare questo mapping?")) return;
    setBusy(true);
    try {
      await adminApi.delete(`/api/vinted/mappings/${id}`);
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleMappingCreate(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      await adminApi.post("/api/vinted/mappings", {
        vinted_catalog_id: Number(newCatalogId),
        vinted_catalog_name: newCatalogName.trim(),
        category_id: newCategoryId === "" ? null : Number(newCategoryId),
        enabled: true,
      });
      setNewCatalogId("");
      setNewCatalogName("");
      setNewCategoryId("");
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <AdminShell>
      <div className="flex items-end justify-between mb-6 gap-3 flex-wrap">
        <div>
          <h1 className="display text-3xl text-ink">🛍 Sync Vinted</h1>
          <p className="text-ink-soft mt-1 text-sm">
            Importa automaticamente gli annunci del tuo profilo Vinted come
            articoli DRAFT. Solo i catalog mappati e abilitati vengono importati.
          </p>
        </div>
        <button
          type="button"
          onClick={handleTriggerSync}
          disabled={busy}
          className="btn btn-primary"
        >
          {busy ? "Sync in corso…" : "↻ Sync ora"}
        </button>
      </div>

      {error && (
        <div className="card p-4 mb-4 text-pink-deep font-semibold">⚠ {error}</div>
      )}

      {/* Settings */}
      {settings && (
        <div className="card p-5 mb-6">
          <h2 className="display text-lg text-ink mb-3">Configurazione</h2>
          <div className="grid sm:grid-cols-4 gap-3 items-end">
            <label className="block">
              <span className="text-xs font-bold uppercase tracking-wider text-ink-soft">
                Vinted user_id
              </span>
              <input
                type="number"
                defaultValue={settings.vinted_user_id}
                onBlur={(e) => {
                  const v = Number(e.target.value);
                  if (v && v !== settings.vinted_user_id) {
                    handleSettingsSave({ vinted_user_id: v });
                  }
                }}
                className="input mt-1"
              />
            </label>
            <label className="block">
              <span className="text-xs font-bold uppercase tracking-wider text-ink-soft">
                Ora sync (UTC)
              </span>
              <input
                type="number"
                min="0"
                max="23"
                defaultValue={settings.sync_hour}
                onBlur={(e) => {
                  const v = Number(e.target.value);
                  if (v !== settings.sync_hour) {
                    handleSettingsSave({ sync_hour: v });
                  }
                }}
                className="input mt-1"
              />
            </label>
            <label className="block">
              <span className="text-xs font-bold uppercase tracking-wider text-ink-soft">
                Abilitata
              </span>
              <select
                value={settings.enabled ? "1" : "0"}
                onChange={(e) =>
                  handleSettingsSave({ enabled: e.target.value === "1" })
                }
                className="input mt-1"
              >
                <option value="1">Sì</option>
                <option value="0">No</option>
              </select>
            </label>
            <div>
              <span className="text-xs font-bold uppercase tracking-wider text-ink-soft block">
                Ultima sync
              </span>
              <span className="text-sm text-ink mt-1 block">
                {fmtDateTime(settings.last_run_at)}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Mappings */}
      <div className="card p-5 mb-6">
        <h2 className="display text-lg text-ink mb-3">Mapping categorie Vinted → NerdNostalgia</h2>
        <p className="text-xs text-ink-soft mb-3 leading-relaxed">
          Vengono importati solo gli annunci nei catalog mappati ed abilitati. Il fallback
          su keyword (elettronica, collezionismo, pokemon, ecc) cattura nuovi catalog non
          ancora mappati: in quel caso l&apos;articolo viene creato con categoria NULL e tu
          la imposti dopo.
        </p>

        <form onSubmit={handleMappingCreate} className="grid sm:grid-cols-4 gap-2 mb-4">
          <input
            type="number"
            required
            placeholder="catalog_id Vinted"
            value={newCatalogId}
            onChange={(e) => setNewCatalogId(e.target.value)}
            className="input"
          />
          <input
            type="text"
            required
            placeholder="Nome leggibile"
            value={newCatalogName}
            onChange={(e) => setNewCatalogName(e.target.value)}
            className="input"
          />
          <select
            value={newCategoryId}
            onChange={(e) => setNewCategoryId(e.target.value)}
            className="input"
          >
            <option value="">— categoria NN —</option>
            {renderCategoryOptions(categories)}
          </select>
          <button
            type="submit"
            disabled={busy}
            className="btn btn-primary text-sm"
          >
            ➕ Aggiungi
          </button>
        </form>

        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="border-b border-ink/10 text-ink-soft text-[11px] uppercase tracking-wider">
              <tr>
                <th className="text-left py-2 px-2">Catalog ID</th>
                <th className="text-left py-2 px-2">Nome</th>
                <th className="text-left py-2 px-2">Categoria NN</th>
                <th className="text-center py-2 px-2">Abilitato</th>
                <th className="py-2 px-2"></th>
              </tr>
            </thead>
            <tbody>
              {mappings.map((m) => (
                <MappingRow
                  key={m.id}
                  mapping={m}
                  categories={categories}
                  busy={busy}
                  onSave={(patch) => handleMappingSave(m.id, patch)}
                  onDelete={() => handleMappingDelete(m.id)}
                />
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Logs */}
      <div className="card p-5">
        <h2 className="display text-lg text-ink mb-3">Ultime sync</h2>
        {logs.length === 0 ? (
          <p className="text-ink-soft text-sm">
            Nessuna sync eseguita ancora. Clicca &quot;Sync ora&quot;.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="border-b border-ink/10 text-ink-soft text-[11px] uppercase tracking-wider">
                <tr>
                  <th className="text-left py-2 px-2">Quando</th>
                  <th className="text-left py-2 px-2">Tipo</th>
                  <th className="text-right py-2 px-2">Durata</th>
                  <th className="text-right py-2 px-2">Letti</th>
                  <th className="text-right py-2 px-2">Importati</th>
                  <th className="text-right py-2 px-2">Aggiornati</th>
                  <th className="text-right py-2 px-2">Saltati</th>
                  <th className="text-left py-2 px-2">Errore</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((l) => (
                  <tr key={l.id} className="border-b border-ink/5">
                    <td className="py-2 px-2">{fmtDateTime(l.started_at)}</td>
                    <td className="py-2 px-2 text-xs uppercase">
                      <span
                        className={`chip text-[10px] ${
                          l.triggered_by === "cron"
                            ? "chip-sky"
                            : "chip-lilac"
                        }`}
                      >
                        {l.triggered_by}
                      </span>
                    </td>
                    <td className="py-2 px-2 text-right tabular-nums">
                      {duration(l.started_at, l.finished_at)}
                    </td>
                    <td className="py-2 px-2 text-right tabular-nums">{l.items_fetched}</td>
                    <td className="py-2 px-2 text-right tabular-nums text-mint-deep font-bold">
                      {l.items_imported || "—"}
                    </td>
                    <td className="py-2 px-2 text-right tabular-nums">{l.items_updated || "—"}</td>
                    <td className="py-2 px-2 text-right tabular-nums text-ink-soft">
                      {l.items_skipped || "—"}
                    </td>
                    <td className="py-2 px-2 text-pink-deep text-xs">
                      {l.error_message ? `⚠ ${l.error_message}` : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

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

function MappingRow({
  mapping,
  categories,
  busy,
  onSave,
  onDelete,
}: {
  mapping: VintedMapping;
  categories: Category[];
  busy: boolean;
  onSave: (p: Partial<VintedMapping>) => void;
  onDelete: () => void;
}) {
  const [name, setName] = useState(mapping.vinted_catalog_name);
  const [catId, setCatId] = useState<string>(
    mapping.category_id != null ? String(mapping.category_id) : "",
  );
  const [enabled, setEnabled] = useState(mapping.enabled);

  const dirty =
    name !== mapping.vinted_catalog_name ||
    (catId === "" ? null : Number(catId)) !== mapping.category_id ||
    enabled !== mapping.enabled;

  function save() {
    onSave({
      vinted_catalog_name: name.trim(),
      category_id: catId === "" ? null : Number(catId),
      enabled,
    });
  }

  return (
    <tr className="border-b border-ink/5 hover:bg-pink-soft/30">
      <td className="py-2 px-2 font-mono text-xs">{mapping.vinted_catalog_id}</td>
      <td className="py-2 px-2">
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="input"
        />
      </td>
      <td className="py-2 px-2">
        <select
          value={catId}
          onChange={(e) => setCatId(e.target.value)}
          className="input"
        >
          <option value="">— nessuna —</option>
          {renderCategoryOptions(categories)}
        </select>
      </td>
      <td className="py-2 px-2 text-center">
        <input
          type="checkbox"
          checked={enabled}
          onChange={(e) => setEnabled(e.target.checked)}
          className="w-4 h-4 accent-pink-deep"
        />
      </td>
      <td className="py-2 px-2 whitespace-nowrap">
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
          {"  ↳ "} {sub.name}
        </option>
      )),
  ]);
}
