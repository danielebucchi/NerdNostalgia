"use client";

import Link from "next/link";
import { Suspense, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { setConsentByToken, type ConsentState } from "@/lib/customer-auth";

/* Pagina di disiscrizione, raggiunta dal link in fondo alle email.
 *
 * Si disiscrive da sola all'apertura, senza un secondo clic di conferma: il
 * clic l'ha gia' fatto nell'email, e un consenso che per ritirarlo chiede
 * piu' fatica di quanta ne sia servita per darlo non e' valido (art. 7.3
 * GDPR).
 *
 * La chiamata e' una POST partita dal browser, non una GET: i filtri
 * antispam e le anteprime dei client di posta aprono i link in automatico
 * per controllarli, e con una GET che scrive avrebbero disiscritto gente
 * che non ha cliccato niente.
 *
 * E se il clic era per sbaglio, il bottone qui sotto rimette tutto com'era. */

type Stato =
  | { fase: "lavoro" }
  | { fase: "fatto"; dati: ConsentState }
  | { fase: "errore"; messaggio: string };

function DisiscrivitiContent() {
  const token = useSearchParams().get("t");
  const [stato, setStato] = useState<Stato>({ fase: "lavoro" });
  const [busy, setBusy] = useState(false);
  // StrictMode monta due volte in sviluppo: senza questa guardia la
  // disiscrizione partirebbe doppia.
  const partito = useRef(false);

  useEffect(() => {
    if (partito.current) return;
    partito.current = true;

    if (!token) {
      setStato({
        fase: "errore",
        messaggio: "Link incompleto: usa quello che trovi in fondo all'email.",
      });
      return;
    }
    setConsentByToken(token, false)
      .then((dati) => setStato({ fase: "fatto", dati }))
      .catch((err) =>
        setStato({
          fase: "errore",
          messaggio: err instanceof Error ? err.message : String(err),
        }),
      );
  }, [token]);

  async function cambia(consenso: boolean) {
    if (!token) return;
    setBusy(true);
    try {
      const dati = await setConsentByToken(token, consenso);
      setStato({ fase: "fatto", dati });
    } catch (err) {
      setStato({
        fase: "errore",
        messaggio: err instanceof Error ? err.message : String(err),
      });
    } finally {
      setBusy(false);
    }
  }

  if (stato.fase === "lavoro") {
    return <p className="text-ink-soft">Un attimo…</p>;
  }

  if (stato.fase === "errore") {
    return (
      <>
        <h1 className="display text-2xl sm:text-3xl text-ink mb-3">
          Non ci sono riuscito
        </h1>
        <p className="text-ink-soft mb-6">{stato.messaggio}</p>
        <p className="text-ink-soft text-sm mb-8">
          Scrivimi a{" "}
          <a
            href="mailto:nerdnostalgiaita@gmail.com"
            className="text-lilac-deep font-semibold hover:underline"
          >
            nerdnostalgiaita@gmail.com
          </a>{" "}
          e ti tolgo io dalla lista.
        </p>
        <Link href="/" className="btn btn-primary">
          Torna al negozio
        </Link>
      </>
    );
  }

  const { email, marketing_consent } = stato.dati;

  // Riscritto: il clic era per sbaglio e l'ha annullato.
  if (marketing_consent) {
    return (
      <>
        <h1 className="display text-2xl sm:text-3xl text-ink mb-3">
          Bentornato
        </h1>
        <p className="text-ink-soft mb-8">
          Continuerai a ricevere le novità su <strong>{email}</strong>. Il
          link in fondo a ogni email resta lì, se cambi idea.
        </p>
        <Link href="/" className="btn btn-primary">
          Torna al negozio
        </Link>
      </>
    );
  }

  return (
    <>
      <h1 className="display text-2xl sm:text-3xl text-ink mb-3">
        Fatto, non ti scrivo più
      </h1>
      <p className="text-ink-soft mb-6">
        Ho tolto <strong>{email}</strong> dalle email promozionali. Non devi
        fare altro.
      </p>
      <p className="text-ink-soft text-sm mb-8">
        Continuerai a ricevere solo le email legate ai tuoi ordini — conferma,
        spedizione, tracking — perché quelle servono a farti arrivare il
        pacco, non a venderti qualcosa.
      </p>

      <div className="flex flex-wrap gap-3">
        <Link href="/" className="btn btn-primary">
          Torna al negozio
        </Link>
        <button
          type="button"
          onClick={() => cambia(true)}
          disabled={busy}
          className="btn btn-ghost text-sm disabled:opacity-50"
        >
          {busy ? "Un attimo…" : "Era un errore, riscrivimi"}
        </button>
      </div>
    </>
  );
}

export default function DisiscrivitiPage() {
  return (
    <div className="max-w-xl mx-auto text-center sm:text-left py-6">
      <Suspense fallback={<p className="text-ink-soft">Un attimo…</p>}>
        <DisiscrivitiContent />
      </Suspense>
    </div>
  );
}
