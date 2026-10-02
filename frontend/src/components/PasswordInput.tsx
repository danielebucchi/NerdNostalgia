"use client";

import { useState } from "react";

/* Campo password con il pulsante per vederla.
 *
 * Nasconderla serve contro chi guarda lo schermo da dietro, non contro
 * chi la sta scrivendo: a chi è solo davanti al computer i pallini fanno
 * solo sbagliare a digitare e riprovare. Parte comunque nascosta — chi è
 * in treno decide da sé.
 *
 * Il pulsante è `tabIndex={-1}`: chi va avanti col tabulatore vuole
 * arrivare al bottone di invio, non inciampare nell'occhio. */

export function PasswordInput({
  value,
  onChange,
  autoComplete,
  minLength,
  required,
  id,
  className = "input mt-1",
}: {
  value: string;
  onChange: (v: string) => void;
  autoComplete?: string;
  minLength?: number;
  required?: boolean;
  id?: string;
  className?: string;
}) {
  const [visibile, setVisibile] = useState(false);

  return (
    <span className="relative block">
      <input
        id={id}
        type={visibile ? "text" : "password"}
        required={required}
        minLength={minLength}
        autoComplete={autoComplete}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className={`${className} pr-12`}
      />
      <button
        type="button"
        tabIndex={-1}
        onClick={() => setVisibile((v) => !v)}
        aria-label={visibile ? "Nascondi la password" : "Mostra la password"}
        title={visibile ? "Nascondi la password" : "Mostra la password"}
        className="absolute right-2 top-1/2 -translate-y-1/2 px-2 py-1 text-base leading-none rounded-lg text-ink-soft hover:text-ink hover:bg-ink/5 transition-colors"
      >
        {visibile ? "🙈" : "👁"}
      </button>
    </span>
  );
}
