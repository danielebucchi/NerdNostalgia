"use client";

import Link from "next/link";
import { Suspense, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { PUBLIC_API_BASE } from "@/lib/api";

/* Conferma dell'iscrizione alla newsletter, dal link nell'email.
 *
 * Come /disiscriviti: la conferma parte all'apertura con una POST dal
 * browser, non con una GET, perché antispam e anteprime dei client di posta
 * aprono i link da soli e iscriverebbero chi non ha cliccato niente. */

type Stato =
  | { fase: "lavoro" }
  | { fase: "fatto"; email: string }
  | { fase: "errore"; messaggio: string };

function ConfermaContent() {
  const token = useSearchParams().get("t");
  const [stato, setStato] = useState<Stato>({ fase: "lavoro" });
  // StrictMode monta due volte in sviluppo: una conferma basta.
  const partito = useRef(false);

  useEffect(() => {
    if (partito.current) return;
    partito.current = true;
    if (!token) {
      setStato({ fase: "errore", messaggio: "Link incompleto: utilizzi quello nell'email." });
      return;
    }
    fetch(`${PUBLIC_API_BASE}/api/newsletter/confirm`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token }),
    })
      .then(async (res) => {
        const body = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(typeof body?.detail === "string" ? body.detail : `Errore ${res.status}`);
        setStato({ fase: "fatto", email: body.email });
      })
      .catch((err) =>
        setStato({ fase: "errore", messaggio: err instanceof Error ? err.message : String(err) }),
      );
  }, [token]);

  if (stato.fase === "lavoro") return <p className="text-ink-soft">Un attimo…</p>;

  if (stato.fase === "errore") {
    return (
      <>
        <h1 className="display text-2xl sm:text-3xl text-ink mb-3">Non ci sono riuscito</h1>
        <p className="text-ink-soft mb-6">{stato.messaggio}</p>
        <Link href="/" className="btn btn-primary">Torna al catalogo</Link>
      </>
    );
  }

  return (
    <>
      <div className="text-5xl mb-3">📬</div>
      <h1 className="display text-2xl sm:text-3xl text-ink mb-3">Iscrizione confermata!</h1>
      <p className="text-ink-soft mb-2">
        Da venerdì {stato.email} riceve i nuovi arrivi di NerdNostalgia, una volta a settimana.
      </p>
      <p className="text-ink-soft mb-6 text-sm">
        In fondo a ogni email c&apos;è il link per disiscriversi. Se li vuole vedere appena
        arrivano, c&apos;è anche il{" "}
        <a href="https://t.me/NerdNostalgia" target="_blank" rel="noopener noreferrer"
           className="text-lilac-deep font-semibold hover:underline">
          gruppo Telegram
        </a>.
      </p>
      <Link href="/" className="btn btn-primary">Vai al catalogo</Link>
    </>
  );
}

export default function ConfermaNewsletterPage() {
  return (
    <div className="max-w-xl mx-auto text-center py-10">
      <Suspense fallback={<p className="text-ink-soft">Un attimo…</p>}>
        <ConfermaContent />
      </Suspense>
    </div>
  );
}
