"use client";

import { useMemo } from "react";
import { useCategories } from "@/lib/useCategories";

interface Props {
  /** id selezionato (può essere quello di un top-level o di una sub) */
  value: number | null;
  onChange: (next: number | null) => void;
  /** Etichetta opzionale, default "Categoria" */
  label?: string;
}

/**
 * Picker a due dropdown: Categoria (obbligatorio per filtrare) e
 * Sottocategoria (opzionale). Restituisce sempre l'id più specifico
 * scelto dall'utente (sub se selezionata, altrimenti top-level).
 */
export function CategoryPicker({ value, onChange, label = "Categoria" }: Props) {
  const { tree, byId, loading } = useCategories();

  const { topId, subId } = useMemo(() => {
    if (value == null) return { topId: null as number | null, subId: null as number | null };
    const cat = byId[value];
    if (!cat) return { topId: null, subId: null };
    if (cat.parent_id == null) return { topId: cat.id, subId: null };
    return { topId: cat.parent_id, subId: cat.id };
  }, [value, byId]);

  const subs = useMemo(() => {
    if (topId == null) return [];
    const top = tree.find((n) => n.id === topId);
    return top?.children ?? [];
  }, [topId, tree]);

  function handleTopChange(next: string) {
    const n = next === "" ? null : Number(next);
    onChange(n);
  }

  function handleSubChange(next: string) {
    if (next === "") {
      onChange(topId);
    } else {
      onChange(Number(next));
    }
  }

  return (
    <div className="grid sm:grid-cols-2 gap-3">
      <label className="block">
        <span className="text-xs font-bold uppercase tracking-wider text-ink-soft">
          {label}
        </span>
        <select
          value={topId ?? ""}
          onChange={(e) => handleTopChange(e.target.value)}
          disabled={loading}
          className="input mt-1"
        >
          <option value="">— nessuna —</option>
          {tree.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
      </label>

      <label className="block">
        <span className="text-xs font-bold uppercase tracking-wider text-ink-soft">
          Sottocategoria <span className="text-ink-soft/60 normal-case font-normal">(opzionale)</span>
        </span>
        <select
          value={subId ?? ""}
          onChange={(e) => handleSubChange(e.target.value)}
          disabled={loading || topId == null || subs.length === 0}
          className="input mt-1"
        >
          <option value="">— nessuna —</option>
          {subs.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name}
            </option>
          ))}
        </select>
      </label>
    </div>
  );
}
