"use client";

import { useEffect, useId, useRef, useState } from "react";
import { fetchAddressSuggestions, type AddressSuggestion } from "@/lib/api";

interface Props {
  /** Testo della via (campo controllato dal form chiamante). */
  value: string;
  /** Digitazione libera: il campo resta usabile anche senza suggerimenti. */
  onChange: (value: string) => void;
  /** Scelta di un suggerimento: il chiamante compila anche CAP/citta'/prov. */
  onSelect: (suggestion: AddressSuggestion) => void;
  required?: boolean;
  placeholder?: string;
  className?: string;
}

const DEBOUNCE_MS = 300;

/**
 * Campo indirizzo con suggerimenti dal backend (proxy Geoapify).
 *
 * Principio: i suggerimenti sono un acceleratore, mai un vincolo. Se il
 * servizio non e' configurato, e' giu', o non trova nulla, resta un normale
 * input testuale e l'ordine si completa lo stesso. Per questo non c'e' nessuna
 * validazione che obblighi a scegliere una voce dalla lista.
 */
export function AddressAutocomplete({
  value,
  onChange,
  onSelect,
  required,
  placeholder,
  className = "input",
}: Props) {
  const [suggestions, setSuggestions] = useState<AddressSuggestion[]>([]);
  const [open, setOpen] = useState(false);
  const [highlighted, setHighlighted] = useState(-1);
  const [loading, setLoading] = useState(false);
  // true dopo una ricerca conclusa: distingue "non ho ancora cercato" da
  // "ho cercato e non c'e' niente", che meritano messaggi diversi.
  const [searched, setSearched] = useState(false);
  // Evita di ri-suggerire subito dopo che l'utente ha scelto una voce
  const justPickedRef = useRef(false);
  const wrapRef = useRef<HTMLDivElement>(null);
  const listId = useId();

  useEffect(() => {
    if (justPickedRef.current) {
      justPickedRef.current = false;
      return;
    }
    const query = value.trim();
    if (query.length < 3) {
      setSuggestions([]);
      setOpen(false);
      setSearched(false);
      return;
    }
    const controller = new AbortController();
    const timer = setTimeout(async () => {
      setLoading(true);
      const results = await fetchAddressSuggestions(query, controller.signal);
      if (controller.signal.aborted) return;
      setSuggestions(results);
      setHighlighted(-1);
      setOpen(results.length > 0);
      setLoading(false);
      setSearched(true);
    }, DEBOUNCE_MS);

    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [value]);

  // Click fuori = chiudi la tendina
  useEffect(() => {
    if (!open) return;
    function onDocClick(e: MouseEvent) {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, [open]);

  function pick(suggestion: AddressSuggestion) {
    justPickedRef.current = true;
    onSelect(suggestion);
    setOpen(false);
    setSuggestions([]);
    setHighlighted(-1);
    setSearched(false);
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (!open || suggestions.length === 0) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setHighlighted((i) => (i + 1) % suggestions.length);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setHighlighted((i) => (i <= 0 ? suggestions.length - 1 : i - 1));
    } else if (e.key === "Enter") {
      // Invio su una voce evidenziata sceglie invece di inviare il form
      if (highlighted >= 0) {
        e.preventDefault();
        pick(suggestions[highlighted]);
      }
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  }

  return (
    <div ref={wrapRef} className="relative">
      <input
        type="text"
        required={required}
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={onKeyDown}
        onFocus={() => suggestions.length > 0 && setOpen(true)}
        className={className}
        // Lasciamo attivo anche l'autofill nativo del browser: su mobile e'
        // spesso piu' veloce dei suggerimenti remoti.
        autoComplete="street-address"
        role="combobox"
        aria-expanded={open}
        aria-controls={listId}
        aria-autocomplete="list"
        aria-activedescendant={
          highlighted >= 0 ? `${listId}-${highlighted}` : undefined
        }
      />
      {loading && (
        <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-ink-soft">
          …
        </span>
      )}
      {searched && !loading && suggestions.length === 0 && (
        <p className="mt-1 text-[11px] text-ink-soft leading-snug">
          Nessun suggerimento per questo testo. Serve il nome completo della via
          (es. &quot;Via Alberto Profeti&quot;, non &quot;Via Profeti&quot;),
          meglio se col numero civico e la città. Se proprio non compare, usa
          &laquo;Il mio indirizzo non è nell&apos;elenco&raquo; qui sotto.
        </p>
      )}
      {open && suggestions.length > 0 && (
        <ul
          id={listId}
          role="listbox"
          className="absolute z-10 left-0 right-0 mt-1 max-h-60 overflow-y-auto rounded-xl bg-white shadow-lg ring-1 ring-ink/10 py-1"
        >
          {suggestions.map((s, i) => (
            <li
              key={`${s.label}-${i}`}
              id={`${listId}-${i}`}
              role="option"
              aria-selected={i === highlighted}
              onMouseEnter={() => setHighlighted(i)}
              onMouseDown={(e) => {
                // mousedown: il blur dell'input chiuderebbe la lista prima del click
                e.preventDefault();
                pick(s);
              }}
              className={`px-3 py-2 text-sm cursor-pointer ${
                i === highlighted ? "bg-pink-soft/50 text-ink" : "text-ink-soft"
              }`}
            >
              {s.label}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
