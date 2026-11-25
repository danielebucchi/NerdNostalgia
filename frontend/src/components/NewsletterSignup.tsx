"use client";

import Link from "next/link";
import { useState } from "react";
import { PUBLIC_API_BASE } from "@/lib/api";

/* Iscrizione alla newsletter del venerdì dal footer, senza account.
 *
 * Doppio opt-in: il server manda un link di conferma e finché non lo si
 * apre non arriva niente. La spunta del consenso parte vuota e serve per
 * iscriversi (art. 7 GDPR). Il server risponde sempre uguale, anche se
 * l'indirizzo è già iscritto, quindi il messaggio di successo è uno solo. */
export function NewsletterSignup() {
  const [email, setEmail] = useState("");
  const [consenso, setConsenso] = useState(false);
  const [website, setWebsite] = useState(""); // honeypot
  const [busy, setBusy] = useState(false);
  const [fatto, setFatto] = useState(false);
  const [errore, setErrore] = useState<string | null>(null);

  async function invia(e: React.FormEvent) {
    e.preventDefault();
    if (!consenso) {
      setErrore("Spunti la casella del consenso per iscriversi.");
      return;
    }
    setBusy(true);
    setErrore(null);
    try {
      const res = await fetch(`${PUBLIC_API_BASE}/api/newsletter/subscribe`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: email.trim(),
          consent: true,
          website: website.trim() || undefined,
        }),
      });
      if (res.status === 422) throw new Error("Controlli l'indirizzo email.");
      if (res.status === 429) throw new Error("Troppi tentativi: riprovi fra qualche minuto.");
      if (!res.ok) throw new Error("Non è andata: riprovi fra poco.");
      setFatto(true);
    } catch (err) {
      setErrore(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-6xl px-4 sm:px-6 pb-8">
      <div className="card p-5 sm:p-6 grid gap-4 sm:grid-cols-[1fr_1.3fr] sm:items-center">
        <div>
          <h4 className="display text-lg text-ink">📬 I nuovi arrivi ogni venerdì</h4>
          <p className="text-sm text-ink-soft mt-1">
            Una email a settimana con gli articoli appena pubblicati. Niente altro, e
            si disiscrive con un clic.
          </p>
        </div>
        {fatto ? (
          <p className="text-sm text-ink font-semibold">
            ✨ Ci siamo quasi: Le abbiamo scritto. Apra l&apos;email e confermi
            l&apos;iscrizione (se non la trova, guardi nello spam).
          </p>
        ) : (
          <form onSubmit={invia} className="space-y-2">
            <input
              type="text"
              name="hp_newsletter"
              tabIndex={-1}
              autoComplete="new-password"
              aria-hidden="true"
              style={{ display: "none" }}
              value={website}
              onChange={(e) => setWebsite(e.target.value)}
            />
            <div className="flex gap-2">
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="la-sua@email.it"
                aria-label="Email"
                maxLength={255}
                className="flex-1 min-w-0 rounded-2xl border border-ink/15 bg-white/85 px-3.5 py-2 text-sm text-ink outline-none focus:border-lilac-deep"
              />
              <button type="submit" disabled={busy} className="btn btn-primary text-sm whitespace-nowrap">
                {busy ? "Invio…" : "Iscrivimi"}
              </button>
            </div>
            <label className="flex items-start gap-2 text-xs text-ink-soft">
              <input
                type="checkbox"
                checked={consenso}
                onChange={(e) => setConsenso(e.target.checked)}
                className="mt-0.5"
              />
              <span>
                Acconsento a ricevere la newsletter dei nuovi arrivi di NerdNostalgia.{" "}
                <Link href="/privacy" className="underline hover:text-lilac-deep">
                  Informativa privacy
                </Link>
              </span>
            </label>
            {errore && <p className="text-pink-deep text-sm font-semibold">⚠ {errore}</p>}
          </form>
        )}
      </div>
    </div>
  );
}
