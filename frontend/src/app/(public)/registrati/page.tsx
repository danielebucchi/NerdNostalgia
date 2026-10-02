"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { registerCustomer } from "@/lib/customer-auth";

export default function RegistratiPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  // Spunta separata e spenta di default: il consenso promozionale non può
  // essere una conseguenza dell'iscrizione, deve essere una scelta a parte.
  const [consent, setConsent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await registerCustomer({
        email: email.trim(),
        password,
        full_name: fullName.trim() || undefined,
        marketing_consent: consent,
      });
      router.push("/profilo");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setBusy(false);
    }
  }

  return (
    <article className="max-w-md mx-auto">
      <h1 className="display text-3xl text-ink mb-2">Crea il tuo profilo</h1>
      <p className="text-ink-soft text-sm mb-6 leading-relaxed">
        Ti serve per seguire gli ordini: ci trovi il codice di tracciamento
        delle spedizioni in corso e lo storico di quelli passati. Se hai già
        comprato come ospite con questa email, quegli ordini compariranno da
        soli.
      </p>

      <form onSubmit={handleSubmit} className="card p-6 space-y-4">
        {error && <p className="text-pink-deep text-sm">⚠ {error}</p>}

        <label className="block">
          <span className="text-xs font-bold uppercase tracking-wider text-ink-soft">
            Nome (facoltativo)
          </span>
          <input
            type="text"
            autoComplete="name"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            className="input mt-1"
          />
        </label>

        <label className="block">
          <span className="text-xs font-bold uppercase tracking-wider text-ink-soft">
            Email *
          </span>
          <input
            type="email"
            required
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="input mt-1"
          />
        </label>

        <label className="block">
          <span className="text-xs font-bold uppercase tracking-wider text-ink-soft">
            Password *
          </span>
          <input
            type="password"
            required
            minLength={8}
            autoComplete="new-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="input mt-1"
          />
          <span className="text-[11px] text-ink-soft">Almeno 8 caratteri.</span>
        </label>

        <label className="flex items-start gap-3 cursor-pointer rounded-xl bg-ink/4 ring-1 ring-ink/10 p-3">
          <input
            type="checkbox"
            checked={consent}
            onChange={(e) => setConsent(e.target.checked)}
            className="mt-0.5 w-5 h-5 flex-shrink-0 accent-pink-deep cursor-pointer"
          />
          <span className="text-sm leading-snug">
            Voglio ricevere le novità del sito via email
            <span className="block text-xs text-ink-soft mt-1">
              Ti scrivo quando arrivano pezzi interessanti, e puoi
              disiscriverti quando vuoi dal link in fondo a ogni email.
            </span>
          </span>
        </label>

        <button
          type="submit"
          disabled={busy}
          className="btn btn-primary w-full text-base font-bold px-6 py-3"
        >
          {busy ? "Creo il profilo…" : "Crea il profilo"}
        </button>

        <p className="text-xs text-ink-soft text-center">
          Hai già un profilo?{" "}
          <Link href="/accedi" className="underline font-semibold">
            Accedi
          </Link>
        </p>
        <p className="text-[11px] text-ink-soft text-center leading-snug">
          Creando il profilo accetti la{" "}
          <Link href="/privacy" className="underline">
            privacy policy
          </Link>
          .
        </p>
      </form>
    </article>
  );
}
