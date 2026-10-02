"use client";

import { useState } from "react";
import { adminApi } from "@/lib/admin-api";

interface Change {
  id: number;
  title: string;
  old_price: number;
  new_price: number;
  delta: number;
}

interface Result {
  dry_run: boolean;
  percent: number;
  articles_considered: number;
  articles_changed: number;
  total_delta: number;
  changes: Change[];
}

/**
 * Rincaro percentuale su tutto il listino.
 *
 * Serve a incorporare nel prezzo le commissioni di incasso senza passare
 * articolo per articolo. È un'operazione che riscrive centinaia di prezzi,
 * quindi il percorso è obbligato: prima l'anteprima, poi una conferma
 * separata con scritto quanti articoli verranno toccati.
 */
export function BulkMarkupPanel({ onApplied }: { onApplied: () => void }) {
  const [open, setOpen] = useState(false);
  const [percent, setPercent] = useState("3.5");
  const [preview, setPreview] = useState<Result | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState<Result | null>(null);

  async function run(dryRun: boolean) {
    setBusy(true);
    setError(null);
    try {
      const res = await adminApi.post<Result>("/api/articles/bulk-markup", {
        percent: Number(percent),
        dry_run: dryRun,
      });
      if (dryRun) {
        setPreview(res);
        setDone(null);
      } else {
        setDone(res);
        setPreview(null);
        onApplied();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="btn btn-ghost text-sm"
      >
        💶 Rincara listino…
      </button>
    );
  }

  return (
    <div className="card p-4 mb-4 ring-2 ring-lilac-deep/40">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="display text-lg text-ink">Rincara listino</h2>
          <p className="text-xs text-ink-soft mt-0.5 leading-snug max-w-xl">
            Alza di una percentuale il prezzo di tutti gli articoli pubblicati.
            Serve a incorporare le commissioni di incasso. I pezzi{" "}
            <strong>venduti non si toccano</strong>: quel prezzo è storia.
          </p>
        </div>
        <button
          type="button"
          onClick={() => {
            setOpen(false);
            setPreview(null);
            setDone(null);
            setError(null);
          }}
          className="btn btn-ghost text-xs px-3 py-1"
        >
          Chiudi
        </button>
      </div>

      {error && <p className="text-pink-deep text-sm mt-3">⚠ {error}</p>}

      <div className="flex flex-wrap items-end gap-3 mt-4">
        <label className="block">
          <span className="text-xs font-bold uppercase tracking-wider text-ink-soft">
            Percentuale
          </span>
          <div className="flex items-center gap-1 mt-1">
            <input
              type="number"
              step="0.1"
              min="0.1"
              max="50"
              value={percent}
              onChange={(e) => {
                setPercent(e.target.value);
                setPreview(null);
              }}
              className="input w-28"
            />
            <span className="text-ink-soft">%</span>
          </div>
        </label>
        <button
          type="button"
          onClick={() => run(true)}
          disabled={busy || !percent}
          className="btn btn-ghost text-sm"
        >
          {busy && !preview ? "Calcolo…" : "Calcola anteprima"}
        </button>
      </div>

      {done && (
        <div className="mt-4 rounded-xl bg-mint-soft/60 ring-1 ring-mint-deep/40 p-3 text-sm">
          ✅ Fatto: <strong>{done.articles_changed}</strong> prezzi aggiornati
          del {done.percent}%.
        </div>
      )}

      {preview && (
        <div className="mt-4">
          {preview.articles_changed === 0 ? (
            <p className="text-sm text-ink-soft">
              Nessun prezzo cambierebbe con questa percentuale.
            </p>
          ) : (
            <>
              <div className="rounded-xl bg-ink/4 ring-1 ring-ink/10 p-3 text-sm">
                <strong>{preview.articles_changed}</strong> articoli su{" "}
                {preview.articles_considered} cambierebbero prezzo. Vendendoli
                tutti incasseresti{" "}
                <strong className="text-mint-deep">
                  + € {preview.total_delta.toFixed(2)}
                </strong>
                .
              </div>

              <div className="mt-3 max-h-60 overflow-y-auto rounded-xl ring-1 ring-ink/10">
                <table className="w-full text-sm">
                  <tbody>
                    {preview.changes.map((c) => (
                      <tr key={c.id} className="border-b border-ink/5 last:border-0">
                        <td className="px-3 py-1.5 text-ink-soft truncate max-w-xs">
                          {c.title}
                        </td>
                        <td className="px-3 py-1.5 text-right tabular-nums text-ink-soft">
                          € {c.old_price.toFixed(2)}
                        </td>
                        <td className="px-3 py-1.5 text-right tabular-nums font-semibold">
                          → € {c.new_price.toFixed(2)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <button
                type="button"
                onClick={() => run(false)}
                disabled={busy}
                className="btn btn-primary text-sm mt-3"
              >
                {busy
                  ? "Applico…"
                  : `Applica a ${preview.articles_changed} articoli`}
              </button>
              <p className="text-[11px] text-ink-soft mt-2">
                Non è reversibile con un clic: per tornare indietro servirebbe
                un rincaro negativo, e gli arrotondamenti non tornerebbero
                esatti al centesimo.
              </p>
            </>
          )}
        </div>
      )}
    </div>
  );
}
