"use client";

/**
 * Dropdown ricercabile delle espansioni CardTrader (input di autocompletamento).
 * Precarica la lista ufficiale del gioco predefinito (Pokémon) e filtra
 * client-side mentre digiti. Il testo resta libero: scegliere un suggerimento
 * imposta il nome esatto dell'espansione (così l'auto-match backend lo aggancia).
 *
 * Best-effort: se CardTrader è offline/non configurato, resta un input di testo
 * normale senza dropdown (non deve rompere i flussi che lo montano).
 */
import { useEffect, useMemo, useState } from "react";
import { adminApi } from "@/lib/admin-api";

export interface Expansion { id: number; game_id: number; code: string; name: string }

interface Props {
  value: string;
  onChange: (text: string) => void;
  onSelect?: (exp: Expansion) => void;
  /** Gioco di cui caricare le espansioni. undefined = usa il default da /status. */
  gameId?: number | null;
  placeholder?: string;
  className?: string;
  ariaLabel?: string;
}

// Cache a livello di modulo: le espansioni cambiano di rado. Evita di
// riscaricarle a ogni mount (più istanze / riaperture del dialog).
const _expCache: Record<string, Expansion[]> = {};

export function ExpansionCombobox({
  value,
  onChange,
  onSelect,
  gameId,
  placeholder,
  className,
  ariaLabel,
}: Props) {
  const [all, setAll] = useState<Expansion[]>([]);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        let gid: number | null | undefined = gameId;
        if (gid === undefined) {
          const s = await adminApi.get<{ ok: boolean; default_game_id?: number | null }>(
            "/api/cardtrader/status",
          );
          if (!s.ok) return; // offline → resta input libero
          gid = s.default_game_id ?? 5;
        }
        const key = String(gid ?? "all");
        if (_expCache[key]) {
          if (!cancelled) setAll(_expCache[key]);
          return;
        }
        const qs = gid != null ? `?game_id=${gid}&limit=5000` : "?limit=5000";
        const exps = await adminApi.get<Expansion[]>(`/api/cardtrader/expansions${qs}`);
        _expCache[key] = exps;
        if (!cancelled) setAll(exps);
      } catch {
        // nessun dropdown, resta input libero
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [gameId]);

  const matches = useMemo(() => {
    if (!all.length) return [];
    const q = value.trim().toLowerCase();
    // Testo che combacia esattamente con un'espansione → niente lista
    if (q && all.some((e) => e.name.toLowerCase() === q)) return [];
    if (!q) return all.slice(0, 50);
    return all
      .filter((e) => e.name.toLowerCase().includes(q) || (e.code ?? "").toLowerCase().includes(q))
      .slice(0, 50);
  }, [value, all]);

  return (
    <div className="relative">
      <input
        value={value}
        onChange={(e) => {
          onChange(e.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
        placeholder={placeholder}
        className={className}
        aria-label={ariaLabel}
        autoComplete="off"
      />
      {open && matches.length > 0 && (
        <div className="absolute z-20 left-0 right-0 mt-1 max-h-52 overflow-y-auto bg-white rounded-xl ring-1 ring-ink/15 shadow-hover">
          {matches.map((e) => (
            <button
              key={e.id}
              type="button"
              onMouseDown={(ev) => ev.preventDefault()}
              onClick={() => {
                onChange(e.name);
                onSelect?.(e);
                setOpen(false);
              }}
              className="w-full text-left px-3 py-2 hover:bg-pink-soft/40 text-sm"
            >
              <span className="text-ink font-semibold">{e.name}</span>
              {e.code && <span className="text-ink-soft/60 text-[10px]"> ({e.code})</span>}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
