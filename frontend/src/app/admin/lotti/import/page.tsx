"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { AdminShell } from "@/components/admin/AdminShell";
import { adminApi } from "@/lib/admin-api";
import { useCategories } from "@/lib/useCategories";
import type { Category, Lot } from "@/lib/types";

// ---------------------------------------------------------------------------
// Import CSV completo: lotti + item.
//
// Formato: righe tab-separated (o CSV), una riga per item. La prima colonna
// e' un LABEL locale del lotto (arbitrario, es. "Bundle Aprile") che serve
// solo a raggruppare — righe con stesso label finiscono nello stesso lotto,
// e la creazione avviene una sola volta.
//
// Colonne (in ordine):
//   0  label_lotto          (obbligatorio — chiave di raggruppamento)
//   1  data_acquisto        (YYYY-MM-DD, opzionale)
//   2  piattaforma_acq      (nome libero, opzionale)
//   3  chi_compra           (C, D o vuoto)
//   4  costo_tot_lotto      (numero, opzionale)
//   5  titolo_item          (obbligatorio se la riga rappresenta un item;
//                            se vuoto la riga vale solo per creare il lotto
//                            senza item)
//   6  categoria            (nome, match case-insensitive)
//   7  costo_item
//   8  listino
//   9  qty                  (default 1)
//   10 collezione
//   11 numero_carta
//   12 note_item
//
// In Excel: si usa Ctrl+D per riempire in basso label_lotto + metadata sulle
// righe successive appartenenti allo stesso lotto (i valori sono i "primi
// visti" per quel lotto, le occorrenze successive vengono ignorate).
// ---------------------------------------------------------------------------

interface ParsedItem {
  title: string;
  category_id: number | null;
  category_hint: string | null;
  cost: number | null;
  list_price: number | null;
  quantity: number;
  card_collection: string | null;
  card_number: string | null;
  notes: string | null;
}

interface ParsedGroup {
  label: string;
  purchase_date: string | null;
  purchase_platform: string | null;
  bought_by: string | null;
  total_cost: number | null;
  items: ParsedItem[];
}

function parseImportText(raw: string, categories: Category[]): ParsedGroup[] {
  const lines = raw
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter((l) => l.length > 0);
  if (lines.length === 0) return [];

  const first = lines[0];
  const delimiter = first.includes("\t") ? "\t" : first.includes(";") ? ";" : ",";

  const header = first.toLowerCase();
  const startIndex =
    header.includes("lotto") ||
    header.includes("label") ||
    header.includes("titolo") ||
    header.includes("oggetto")
      ? 1
      : 0;

  const byName = new Map<string, number>();
  for (const c of categories) byName.set(c.name.trim().toLowerCase(), c.id);

  const num = (s: string): number | null => {
    const t = s.trim().replace(",", ".");
    if (t === "") return null;
    const n = Number(t);
    return Number.isFinite(n) ? n : null;
  };

  const groups = new Map<string, ParsedGroup>();
  for (let i = startIndex; i < lines.length; i++) {
    const cells = lines[i].split(delimiter).map((c) => c.trim());
    const label = cells[0] || "";
    if (!label) continue;

    if (!groups.has(label)) {
      groups.set(label, {
        label,
        purchase_date: cells[1] || null,
        purchase_platform: cells[2] || null,
        bought_by: cells[3] || null,
        total_cost: cells[4] ? num(cells[4]) : null,
        items: [],
      });
    }
    const g = groups.get(label)!;

    const itemTitle = cells[5] || "";
    if (!itemTitle) continue;
    const catName = cells[6] || "";
    const matched = catName ? byName.get(catName.toLowerCase()) ?? null : null;
    g.items.push({
      title: itemTitle,
      category_id: matched,
      category_hint: catName && !matched ? catName : null,
      cost: cells[7] ? num(cells[7]) : null,
      list_price: cells[8] ? num(cells[8]) : null,
      quantity: cells[9] ? Math.max(1, Math.floor(num(cells[9]) ?? 1)) : 1,
      card_collection: cells[10] || null,
      card_number: cells[11] || null,
      notes: cells[12] || null,
    });
  }
  return Array.from(groups.values());
}

export default function AdminLotsImportPage() {
  const { flat: categories } = useCategories();
  const [text, setText] = useState("");
  const groups = useMemo(() => parseImportText(text, categories), [text, categories]);

  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState<{ phase: string; done: number; total: number } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [createdLots, setCreatedLots] = useState<{ id: number; label: string; itemsCount: number }[]>([]);

  const totalItems = useMemo(() => groups.reduce((n, g) => n + g.items.length, 0), [groups]);
  const unmatchedCats = useMemo(() => {
    const s = new Set<string>();
    for (const g of groups) for (const it of g.items) if (it.category_hint) s.add(it.category_hint);
    return Array.from(s);
  }, [groups]);

  async function handleImport() {
    if (groups.length === 0) return;
    setBusy(true);
    setError(null);
    const created: typeof createdLots = [];
    const totalOps = groups.length + totalItems;
    let doneOps = 0;
    setProgress({ phase: "Creo lotti", done: 0, total: totalOps });
    try {
      for (const g of groups) {
        const lot = await adminApi.post<Lot>("/api/lots/", {
          title: g.label,
          purchase_date: g.purchase_date,
          purchase_platform: g.purchase_platform,
          bought_by: g.bought_by,
          total_cost: g.total_cost,
        });
        doneOps += 1;
        setProgress({ phase: `Creo item per ${g.label}`, done: doneOps, total: totalOps });
        for (const it of g.items) {
          await adminApi.post("/api/inventory/", {
            lot_id: lot.id,
            title: it.title,
            category_id: it.category_id,
            cost: it.cost,
            list_price: it.list_price,
            quantity: it.quantity,
            card_collection: it.card_collection,
            card_number: it.card_number,
            notes: it.notes,
          });
          doneOps += 1;
          setProgress({ phase: `Creo item per ${g.label}`, done: doneOps, total: totalOps });
        }
        created.push({ id: lot.id, label: g.label, itemsCount: g.items.length });
        setCreatedLots([...created]);
      }
    } catch (err) {
      setError(
        `${err instanceof Error ? err.message : String(err)}\n` +
          `Creati ${created.length} lotti su ${groups.length}. I lotti gia' importati restano.`,
      );
    } finally {
      setBusy(false);
      setProgress(null);
    }
  }

  return (
    <AdminShell>
      <div className="mb-3">
        <Link href="/admin/lotti" className="text-xs text-ink-soft hover:text-ink">← Tutti i lotti</Link>
      </div>

      <div className="mb-5">
        <h1 className="display text-3xl text-ink">📤 Import lotti + item da CSV</h1>
        <p className="text-sm text-ink-soft mt-1">
          Incolla una tabella con colonna &quot;lotto&quot; ripetuta per raggruppare gli item.
          I lotti vengono creati una sola volta anche se il label appare su più righe.
        </p>
      </div>

      <details className="mb-3">
        <summary className="text-xs font-bold text-ink-soft cursor-pointer hover:text-ink">
          📖 Formato colonne (in ordine)
        </summary>
        <div className="mt-2 p-2 rounded bg-ink/5 text-xs text-ink-soft font-mono leading-relaxed overflow-x-auto whitespace-nowrap">
          lotto{"\t"}data_acq{"\t"}piatt{"\t"}chi{"\t"}costo_tot{"\t"}titolo{"\t"}categoria{"\t"}costo{"\t"}listino{"\t"}qty{"\t"}collezione{"\t"}numero{"\t"}note
        </div>
        <p className="text-xs text-ink-soft mt-1.5 leading-relaxed">
          <strong>lotto</strong> è la chiave di raggruppamento (label libero,
          es. &quot;Bundle Aprile&quot;). Le colonne 1-4 sono metadata del lotto e vengono
          lette dalla PRIMA riga di quel label (le successive per lo stesso
          lotto ignorano quelle colonne). Se il titolo è vuoto, la riga vale
          solo come dichiarazione del lotto senza item.
        </p>
      </details>

      {error && (
        <div className="card p-4 mb-4 text-pink-deep font-semibold whitespace-pre-line">⚠ {error}</div>
      )}

      {createdLots.length > 0 && !busy && (
        <div className="card p-4 mb-4 bg-mint/30">
          <p className="text-mint-deep font-semibold mb-2">
            ✓ Import completato — {createdLots.length} lotti creati
          </p>
          <ul className="text-xs space-y-1 mb-3">
            {createdLots.map((l) => (
              <li key={l.id}>
                <Link href={`/admin/lotti/${l.id}`} className="text-lilac-deep underline">
                  {l.label}
                </Link>{" "}
                <span className="text-ink-soft">— {l.itemsCount} item</span>
              </li>
            ))}
          </ul>
          <div className="flex gap-2">
            <Link href="/admin/lotti" className="btn btn-primary text-sm">
              Vai alla lista lotti
            </Link>
            <button
              type="button"
              onClick={() => {
                setCreatedLots([]);
                setText("");
              }}
              className="btn btn-ghost text-sm"
            >
              Import di un altro CSV
            </button>
          </div>
        </div>
      )}

      {createdLots.length === 0 && (
        <>
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            disabled={busy}
            rows={12}
            placeholder={`Es. (tab-separated):\nBundle Aprile\t2026-04-01\tVinted\tD\t80\tCharizard\tCarte\t5\t40\t1\nBundle Aprile\t\t\t\t\tBlastoise\tCarte\t5\t35\t1\nBundle Maggio\t2026-05-10\tSubito\tC\t50\tGoombas\tGiochi\t20\t45\t1`}
            className="w-full p-3 rounded-lg border border-ink/15 bg-white/80 font-mono text-xs leading-relaxed focus:outline-none focus:ring-2 focus:ring-pink-deep/40"
          />

          <div className="mt-3 flex items-baseline justify-between gap-3 flex-wrap">
            <span className="text-sm font-semibold text-ink">
              {groups.length === 0
                ? "Nessun lotto rilevato"
                : `Anteprima: ${groups.length} lotti · ${totalItems} item`}
            </span>
            {unmatchedCats.length > 0 && (
              <span className="text-[11px] text-pink-deep">
                ⚠ Categorie non trovate: {unmatchedCats.join(", ")}
              </span>
            )}
          </div>

          {groups.length > 0 && (
            <div className="mt-2 space-y-3 max-h-[50vh] overflow-y-auto">
              {groups.map((g, gi) => (
                <div key={gi} className="border border-ink/10 rounded-lg overflow-hidden">
                  <div className="bg-lilac-soft/40 px-3 py-2 flex flex-wrap items-baseline gap-x-4 gap-y-1 text-xs">
                    <strong className="text-ink text-sm">{g.label}</strong>
                    {g.purchase_date && <span>📅 {g.purchase_date}</span>}
                    {g.purchase_platform && <span>🛒 {g.purchase_platform}</span>}
                    {g.bought_by && <span>👤 {g.bought_by}</span>}
                    {g.total_cost != null && <span>💰 {g.total_cost}</span>}
                    <span className="ml-auto text-ink-soft">{g.items.length} item</span>
                  </div>
                  {g.items.length > 0 && (
                    <table className="min-w-full text-xs">
                      <thead className="bg-white/70 border-b border-ink/10 text-ink-soft uppercase tracking-wider">
                        <tr>
                          <th className="text-left py-1 px-2">Titolo</th>
                          <th className="text-left py-1 px-2">Cat.</th>
                          <th className="text-right py-1 px-2">Costo</th>
                          <th className="text-right py-1 px-2">Listino</th>
                          <th className="text-right py-1 px-2">Qty</th>
                        </tr>
                      </thead>
                      <tbody>
                        {g.items.map((it, i) => (
                          <tr key={i} className="border-t border-ink/5">
                            <td className="py-1 px-2">{it.title}</td>
                            <td className="py-1 px-2">
                              {it.category_id
                                ? categories.find((c) => c.id === it.category_id)?.name ?? "—"
                                : it.category_hint
                                  ? <span className="text-pink-deep">? {it.category_hint}</span>
                                  : "—"}
                            </td>
                            <td className="py-1 px-2 text-right tabular-nums">{it.cost ?? "—"}</td>
                            <td className="py-1 px-2 text-right tabular-nums">{it.list_price ?? "—"}</td>
                            <td className="py-1 px-2 text-right tabular-nums">{it.quantity}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>
              ))}
            </div>
          )}

          {progress && (
            <p className="mt-3 text-sm text-ink-soft">
              {progress.phase} — {progress.done} / {progress.total}…
            </p>
          )}

          <div className="mt-4 flex justify-end gap-2">
            <Link href="/admin/lotti" className="btn btn-ghost text-sm">
              Annulla
            </Link>
            <button
              type="button"
              onClick={handleImport}
              disabled={busy || groups.length === 0}
              className="btn btn-primary text-sm"
            >
              {busy
                ? "Import in corso…"
                : `Importa ${groups.length} lotti (${totalItems} item)`}
            </button>
          </div>
        </>
      )}
    </AdminShell>
  );
}
