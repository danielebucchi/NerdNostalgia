"use client";

import Link from "next/link";
import { useState } from "react";
import { requestPasswordReset } from "@/lib/customer-auth";

export default function PasswordDimenticataPage() {
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [esito, setEsito] = useState<string | null>(null);
  const [errore, setErrore] = useState<string | null>(null);

  async function invia(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErrore(null);
    try {
      setEsito(await requestPasswordReset(email.trim()));
    } catch (err) {
      setErrore(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="max-w-md mx-auto py-6">
      <h1 className="display text-3xl text-ink mb-2">Password dimenticata</h1>
      <p className="text-ink-soft mb-6 leading-snug">
        Scrivi l&apos;email del tuo profilo: ti mando un link per sceglierne
        una nuova.
      </p>

      {esito ? (
        <>
          {/* Lo stesso messaggio vale anche per un indirizzo mai iscritto:
              una risposta diversa direbbe a chiunque chi ha un account qui. */}
          <div className="card p-5 mb-6">
            <p className="text-ink leading-snug">📬 {esito}</p>
          </div>
          <Link href="/accedi" className="btn btn-primary">
            Torna ad accedere
          </Link>
        </>
      ) : (
        <form onSubmit={invia} className="card p-5 space-y-4">
          <label className="block">
            <span className="text-xs font-bold uppercase tracking-wider text-ink-soft">
              Email
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

          {errore && <p className="text-pink-deep text-sm">⚠ {errore}</p>}

          <button
            type="submit"
            disabled={busy}
            className="btn btn-primary w-full disabled:opacity-50"
          >
            {busy ? "Mando…" : "Mandami il link"}
          </button>

          <p className="text-sm text-ink-soft text-center">
            Te la sei ricordata?{" "}
            <Link href="/accedi" className="underline font-semibold">
              Accedi
            </Link>
          </p>
        </form>
      )}
    </div>
  );
}
