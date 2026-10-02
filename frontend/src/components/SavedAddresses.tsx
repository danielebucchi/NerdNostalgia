"use client";

import { type Address, formatAddress } from "@/lib/addresses";

/* Scelta dell'indirizzo fra quelli già in rubrica, al checkout.
 *
 * Compare solo a chi è registrato e ha almeno un indirizzo salvato: per
 * tutti gli altri il checkout resta quello di prima, con i campi da
 * compilare. L'ultima voce apre quei campi anche a chi la rubrica ce
 * l'ha, perché un regalo si spedisce a casa d'altri. */

export const NUOVO = -1;

export function SavedAddresses({
  addresses,
  selectedId,
  onSelect,
}: {
  addresses: Address[];
  selectedId: number;
  onSelect: (id: number) => void;
}) {
  if (addresses.length === 0) return null;

  return (
    <fieldset className="space-y-2">
      <legend className="text-xs font-bold tracking-wide uppercase text-ink-soft mb-2">
        Spedisci a
      </legend>

      {addresses.map((a) => {
        const scelto = a.id === selectedId;
        return (
          <label
            key={a.id}
            className={
              "flex items-start gap-3 rounded-xl px-3 py-2.5 cursor-pointer transition-colors ring-1 " +
              (scelto
                ? "bg-lilac-deep/10 ring-lilac-deep/50"
                : "bg-white/60 ring-ink/10 hover:ring-lilac-deep/30")
            }
          >
            <input
              type="radio"
              name="indirizzo-salvato"
              checked={scelto}
              onChange={() => onSelect(a.id)}
              className="mt-1 h-4 w-4 flex-shrink-0 accent-lilac-deep"
            />
            <span className="text-sm leading-snug">
              <span className="font-semibold text-ink">
                {a.label || a.full_name}
              </span>
              {a.is_default && (
                <span className="ml-2 text-[10px] uppercase tracking-wide font-bold text-lilac-deep">
                  predefinito
                </span>
              )}
              <span className="block text-ink-soft">{formatAddress(a)}</span>
              {a.phone && (
                <span className="block text-ink-soft text-xs mt-0.5">
                  ☎ {a.phone}
                </span>
              )}
            </span>
          </label>
        );
      })}

      <label
        className={
          "flex items-center gap-3 rounded-xl px-3 py-2.5 cursor-pointer transition-colors ring-1 " +
          (selectedId === NUOVO
            ? "bg-lilac-deep/10 ring-lilac-deep/50"
            : "bg-white/60 ring-ink/10 hover:ring-lilac-deep/30")
        }
      >
        <input
          type="radio"
          name="indirizzo-salvato"
          checked={selectedId === NUOVO}
          onChange={() => onSelect(NUOVO)}
          className="h-4 w-4 flex-shrink-0 accent-lilac-deep"
        />
        <span className="text-sm font-semibold text-ink">
          Spedisci a un altro indirizzo
        </span>
      </label>
    </fieldset>
  );
}
