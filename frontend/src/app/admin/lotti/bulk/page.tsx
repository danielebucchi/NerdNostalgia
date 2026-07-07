"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AdminShell } from "@/components/admin/AdminShell";
import { adminApi } from "@/lib/admin-api";
import { usePlatforms } from "@/lib/usePlatforms";
import type { Lot } from "@/lib/types";

// Riga vuota della tabella spreadsheet. `key` locale per il render, tutto il
// resto e' il payload che diventera' un POST /api/lots/.
interface DraftLot {
  key: string;
  title: string;
  purchase_date: string;
  purchase_platform: string;
  bought_by: string;
  total_cost: string;
  notes: string;
}

const PEOPLE = ["", "C", "D"];

let seq = 0;
function makeDraft(): DraftLot {
  seq += 1;
  return {
    key: `draft-${seq}`,
    title: "",
    purchase_date: "",
    purchase_platform: "",
    bought_by: "",
    total_cost: "",
    notes: "",
  };
}

export default function AdminLotsBulkPage() {
  const router = useRouter();
  const { items: platforms } = usePlatforms();
  const platformNames = useMemo(
    () => ["", ...platforms.map((p) => p.name)],
    [platforms],
  );

  const [rows, setRows] = useState<DraftLot[]>(() =>
    Array.from({ length: 3 }, () => makeDraft()),
  );
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState<{ done: number; total: number } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [createdIds, setCreatedIds] = useState<number[]>([]);

  const validRows = rows.filter(
    (r) =>
      r.title.trim() ||
      r.purchase_date ||
      r.purchase_platform ||
      r.bought_by ||
      r.total_cost.trim(),
  );

  function updateRow(key: string, patch: Partial<DraftLot>) {
    setRows((curr) => curr.map((r) => (r.key === key ? { ...r, ...patch } : r)));
  }

  function addRow() {
    setRows((curr) => [...curr, makeDraft()]);
  }

  function removeRow(key: string) {
    setRows((curr) => (curr.length > 1 ? curr.filter((r) => r.key !== key) : curr));
  }

  async function handleSubmit() {
    if (validRows.length === 0) {
      setError("Nessuna riga da creare — compila almeno un campo su una riga.");
      return;
    }
    setBusy(true);
    setError(null);
    setProgress({ done: 0, total: validRows.length });
    const ids: number[] = [];
    try {
      for (const row of validRows) {
        const payload: Record<string, unknown> = {
          title: row.title.trim() || null,
          purchase_date: row.purchase_date || null,
          purchase_platform: row.purchase_platform.trim() || null,
          bought_by: row.bought_by || null,
          total_cost: row.total_cost.trim() ? Number(row.total_cost) : null,
          notes: row.notes.trim() || null,
        };
        const lot = await adminApi.post<Lot>("/api/lots/", payload);
        ids.push(lot.id);
        setProgress({ done: ids.length, total: validRows.length });
      }
      setCreatedIds(ids);
    } catch (err) {
      setError(
        `${err instanceof Error ? err.message : String(err)}\n` +
          `Creati ${ids.length} di ${validRows.length}. Riprova con le righe restanti.`,
      );
      setCreatedIds(ids);
    } finally {
      setBusy(false);
    }
  }

  return (
    <AdminShell>
      <div className="mb-3">
        <Link href="/admin/lotti" className="text-xs text-ink-soft hover:text-ink">← Tutti i lotti</Link>
      </div>

      <div className="flex items-baseline justify-between mb-5 gap-3 flex-wrap">
        <div>
          <h1 className="display text-3xl text-ink">📥 Nuovi lotti in bulk</h1>
          <p className="text-sm text-ink-soft mt-1">
            Crea più lotti in un colpo — solo anagrafica. Gli item li aggiungi
            dopo aprendo il singolo lotto (c&apos;è &quot;📥 Importa da incolla&quot; anche lì).
          </p>
        </div>
      </div>

      {error && (
        <div className="card p-4 mb-4 text-pink-deep font-semibold whitespace-pre-line">⚠ {error}</div>
      )}

      {createdIds.length > 0 && (
        <div className="card p-4 mb-4 bg-mint/30">
          <p className="text-mint-deep font-semibold mb-2">
            ✓ Creati {createdIds.length} lotti
          </p>
          <div className="flex flex-wrap gap-2">
            {createdIds.map((id) => (
              <Link
                key={id}
                href={`/admin/lotti/${id}`}
                className="chip chip-mint text-xs"
              >
                Lotto #{id} ↗
              </Link>
            ))}
          </div>
          <div className="mt-3 flex gap-2">
            <Link href="/admin/lotti" className="btn btn-primary text-sm">
              Vai alla lista lotti
            </Link>
            <button
              type="button"
              onClick={() => {
                setCreatedIds([]);
                setRows(Array.from({ length: 3 }, () => makeDraft()));
              }}
              className="btn btn-ghost text-sm"
            >
              Crea altri
            </button>
          </div>
        </div>
      )}

      {createdIds.length === 0 && (
        <>
          <div className="card overflow-x-auto mb-3">
            <table className="min-w-full text-xs">
              <thead className="bg-white/60 backdrop-blur border-b border-ink/10 text-ink-soft uppercase tracking-wider">
                <tr>
                  <th className="text-left py-2 px-2">#</th>
                  <th className="text-left py-2 px-2">Nome lotto</th>
                  <th className="text-left py-2 px-2">Data acq.</th>
                  <th className="text-left py-2 px-2">Piattaforma</th>
                  <th className="text-left py-2 px-2">Chi</th>
                  <th className="text-right py-2 px-2">Costo tot. €</th>
                  <th className="text-left py-2 px-2">Note</th>
                  <th className="w-8"></th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r, i) => (
                  <tr key={r.key} className="border-b border-ink/5">
                    <td className="py-1 px-2 text-ink-soft tabular-nums">{i + 1}</td>
                    <td className="py-1 px-2">
                      <input
                        value={r.title}
                        onChange={(e) => updateRow(r.key, { title: e.target.value })}
                        placeholder="(opz.)"
                        className="cell-input min-w-[180px]"
                        disabled={busy}
                      />
                    </td>
                    <td className="py-1 px-2">
                      <input
                        type="date"
                        value={r.purchase_date}
                        onChange={(e) => updateRow(r.key, { purchase_date: e.target.value })}
                        className="cell-input w-32"
                        disabled={busy}
                      />
                    </td>
                    <td className="py-1 px-2">
                      <select
                        value={r.purchase_platform}
                        onChange={(e) => updateRow(r.key, { purchase_platform: e.target.value })}
                        className="cell-input"
                        disabled={busy}
                      >
                        {platformNames.map((p) => (
                          <option key={p || "_"} value={p}>{p || "—"}</option>
                        ))}
                      </select>
                    </td>
                    <td className="py-1 px-2">
                      <select
                        value={r.bought_by}
                        onChange={(e) => updateRow(r.key, { bought_by: e.target.value })}
                        className="cell-input w-16"
                        disabled={busy}
                      >
                        {PEOPLE.map((p) => (
                          <option key={p || "_"} value={p}>{p || "—"}</option>
                        ))}
                      </select>
                    </td>
                    <td className="py-1 px-2">
                      <input
                        type="number"
                        step="0.01"
                        min="0"
                        value={r.total_cost}
                        onChange={(e) => updateRow(r.key, { total_cost: e.target.value })}
                        className="cell-input text-right tabular-nums w-24"
                        disabled={busy}
                      />
                    </td>
                    <td className="py-1 px-2">
                      <input
                        value={r.notes}
                        onChange={(e) => updateRow(r.key, { notes: e.target.value })}
                        className="cell-input min-w-[160px]"
                        disabled={busy}
                      />
                    </td>
                    <td className="py-1 px-1 text-center">
                      <button
                        type="button"
                        onClick={() => removeRow(r.key)}
                        disabled={busy || rows.length <= 1}
                        className="text-ink-soft hover:text-pink-deep disabled:opacity-30"
                        title="Elimina riga"
                      >
                        🗑
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="flex items-center gap-3 flex-wrap">
            <button
              type="button"
              onClick={addRow}
              disabled={busy}
              className="btn btn-ghost text-xs"
            >
              + Aggiungi riga
            </button>
            <button
              type="button"
              onClick={handleSubmit}
              disabled={busy || validRows.length === 0}
              className="btn btn-primary text-sm ml-auto"
            >
              {busy
                ? `Creo… ${progress?.done ?? 0}/${progress?.total ?? 0}`
                : `Crea ${validRows.length} lott${validRows.length === 1 ? "o" : "i"}`}
            </button>
          </div>
        </>
      )}

      <style>{`
        .cell-input {
          background: transparent;
          border: 1px solid transparent;
          border-radius: 6px;
          padding: 0.3rem 0.45rem;
          font-family: inherit;
          font-size: 0.75rem;
          width: 100%;
          outline: none;
          transition: background 120ms ease, border-color 120ms ease;
        }
        .cell-input:hover:not(:disabled) { background: rgba(248,168,200,0.12); }
        .cell-input:focus:not(:disabled) {
          background: white;
          border-color: rgba(232,121,168,0.4);
          box-shadow: 0 0 0 2px rgba(248,168,200,0.35);
        }
        .cell-input:disabled { opacity: 0.6; }
      `}</style>
    </AdminShell>
  );
}
