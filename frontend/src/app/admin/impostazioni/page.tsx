"use client";

import { useEffect, useState } from "react";
import { AdminShell } from "@/components/admin/AdminShell";
import { adminApi } from "@/lib/admin-api";

interface SettingEntry {
  key: string;
  value: string;      // salvato ("" = usa default/fallback)
  effective: string;  // valore effettivo
  default: string;
  public: boolean;
  label: string;
  help: string | null;
}

export default function AdminSettingsPage() {
  const [entries, setEntries] = useState<SettingEntry[]>([]);
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savedAt, setSavedAt] = useState<number | null>(null);

  useEffect(() => {
    adminApi
      .get<SettingEntry[]>("/api/settings/")
      .then((data) => {
        setEntries(data);
        setDraft(Object.fromEntries(data.map((e) => [e.key, e.value])));
      })
      .catch((err) => setError(err instanceof Error ? err.message : String(err)))
      .finally(() => setLoading(false));
  }, []);

  const dirty = entries.some((e) => (draft[e.key] ?? "") !== e.value);

  async function handleSave() {
    setSaving(true);
    setError(null);
    try {
      const changed = Object.fromEntries(
        entries
          .filter((e) => (draft[e.key] ?? "") !== e.value)
          .map((e) => [e.key, draft[e.key] ?? ""]),
      );
      const updated = await adminApi.put<SettingEntry[]>("/api/settings/", {
        values: changed,
      });
      setEntries(updated);
      setDraft(Object.fromEntries(updated.map((e) => [e.key, e.value])));
      setSavedAt(Date.now());
      setTimeout(() => setSavedAt(null), 2500);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <AdminShell>
      <div className="mb-5">
        <h1 className="display text-3xl text-ink">⚙️ Impostazioni</h1>
        <p className="text-sm text-ink-soft mt-1 max-w-2xl">
          Configurazione runtime del sito: i valori si applicano al prossimo
          caricamento di pagina, <strong>senza rebuild Docker</strong>. Campo
          vuoto = usa il default (mostrato sotto al campo).
        </p>
      </div>

      {error && (
        <div className="card p-4 mb-4 text-pink-deep font-semibold">⚠ {error}</div>
      )}

      {loading ? (
        <div className="card p-10 text-center text-ink-soft">Caricamento…</div>
      ) : (
        <div className="card p-5 sm:p-6 max-w-3xl space-y-5">
          {entries.map((e) => (
            <label key={e.key} className="block">
              <span className="flex items-baseline gap-2 flex-wrap">
                <span className="text-sm font-bold text-ink">{e.label}</span>
                <code className="text-[10px] text-ink-soft">{e.key}</code>
                {e.public ? (
                  <span className="chip chip-mint text-[10px]" title="Letta dal sito pubblico senza login">
                    pubblica
                  </span>
                ) : (
                  <span className="chip chip-lilac text-[10px]" title="Visibile solo qui in admin">
                    admin
                  </span>
                )}
              </span>
              {e.key.startsWith("marketplace_footer") ? (
                <textarea
                  rows={3}
                  value={draft[e.key] ?? ""}
                  onChange={(ev) => setDraft((d) => ({ ...d, [e.key]: ev.target.value }))}
                  placeholder={e.default}
                  className="input mt-1.5 font-mono text-xs"
                  disabled={saving}
                />
              ) : (
                <input
                  type="text"
                  value={draft[e.key] ?? ""}
                  onChange={(ev) => setDraft((d) => ({ ...d, [e.key]: ev.target.value }))}
                  placeholder={e.default || "(vuoto)"}
                  className="input mt-1.5"
                  disabled={saving}
                />
              )}
              {e.help && (
                <span className="block text-xs text-ink-soft mt-1 leading-snug">
                  {e.help}
                </span>
              )}
            </label>
          ))}

          <div className="flex items-center gap-3 pt-2 border-t border-ink/10">
            <button
              type="button"
              onClick={handleSave}
              disabled={saving || !dirty}
              className="btn btn-primary text-sm"
            >
              {saving ? "Salvataggio…" : "Salva impostazioni"}
            </button>
            {savedAt && (
              <span className="text-sm text-mint-deep font-semibold">✓ Salvate</span>
            )}
            {dirty && !savedAt && (
              <span className="text-xs text-ink-soft">Modifiche non salvate</span>
            )}
          </div>
        </div>
      )}

      <style>{`
        .input {
          display: block;
          width: 100%;
          padding: 0.55rem 0.8rem;
          border: 1px solid rgba(61, 42, 92, 0.12);
          border-radius: 12px;
          background: #fffaf3;
          color: #3d2a5c;
          font-size: 0.92rem;
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
