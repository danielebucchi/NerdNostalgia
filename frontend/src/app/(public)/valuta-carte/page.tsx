"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { VendilaANoi } from "@/components/guida/VendilaANoi";
import { euro, searchGuide, type GuideCard } from "@/lib/price-guide";

/* "Valuta la tua carta": si scrive il nome (anche con il set o il numero),
 * si vede quanto vale e la si puo' proporre a noi. Cerca nella guida prezzi. */
export default function ValutaCartePage() {
  const [q, setQ] = useState("");
  const [risultati, setRisultati] = useState<GuideCard[] | null>(null);
  const [errore, setErrore] = useState<string | null>(null);
  const [cercando, setCercando] = useState(false);

  useEffect(() => {
    const testo = q.trim();
    if (testo.length < 2) {
      setRisultati(null);
      return;
    }
    const t = setTimeout(async () => {
      setCercando(true);
      setErrore(null);
      try {
        setRisultati(await searchGuide(testo));
      } catch (e) {
        setErrore(e instanceof Error ? e.message : String(e));
      } finally {
        setCercando(false);
      }
    }, 350);
    return () => clearTimeout(t);
  }, [q]);

  return (
    <section>
      <div className="hero-blob p-6 sm:p-10 md:p-12 mb-8 text-center">
        <span className="chip chip-mint mb-4 inline-flex">Valuta la tua carta</span>
        <h1 className="display text-3xl sm:text-4xl md:text-5xl text-ink leading-tight">
          Quanto vale la tua <span className="text-pink-deep">carta Pokémon</span>?
        </h1>
        <p className="text-ink-soft text-base sm:text-lg max-w-xl mx-auto mt-4">
          Scrivi il nome della carta, anche con il set o il numero (es. &quot;Charizard set base&quot;,
          &quot;Pikachu 58&quot;). Se ce l&apos;hai, possiamo comprarla noi.
        </p>
        <input
          type="search"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Nome della carta…"
          aria-label="Nome della carta"
          autoFocus
          className="mt-6 w-full max-w-lg rounded-2xl border border-ink/15 bg-white/90 px-5 py-3 text-lg text-ink outline-none focus:border-lilac-deep"
        />
      </div>

      {cercando && <p className="text-center text-ink-soft">Cerco…</p>}
      {errore && <p className="text-center text-pink-deep font-semibold">⚠ {errore}</p>}
      {risultati && risultati.length === 0 && !cercando && (
        <div className="card p-6 text-center">
          <p className="text-ink">Non la troviamo nella guida.</p>
          <p className="text-ink-soft text-sm mt-1">Provi con il nome in inglese o senza il set, oppure ce la descriva:</p>
          <div className="mt-4"><VendilaANoi carta={q.trim()} /></div>
        </div>
      )}

      {risultati && risultati.length > 0 && (
        <div className="space-y-3">
          {risultati.map((c) => (
            <div key={`${c.set_slug}/${c.slug}`} className="card p-3 sm:p-4 flex gap-4 items-center">
              <Link href={`/prezzi-carte-pokemon/${c.set_slug}/${c.slug}`} className="w-16 sm:w-20 shrink-0">
                {c.image ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={c.image} alt={c.name} loading="lazy" className="w-full rounded-lg" />
                ) : (
                  <div className="aspect-[63/88] rounded-lg bg-lilac/30" />
                )}
              </Link>
              <div className="flex-1 min-w-0">
                <Link href={`/prezzi-carte-pokemon/${c.set_slug}/${c.slug}`} className="display text-lg text-ink hover:underline">
                  {c.name} <span className="text-ink-soft">#{c.number}</span>
                </Link>
                <p className="text-sm text-ink-soft truncate">{c.set_name}</p>
                <p className="text-sm text-ink-soft">Valore di mercato da {euro(c.min_price)}</p>
                {c.buy_offer != null && (
                  <p className="font-bold text-pink-deep">💰 Ti diamo fino a {euro(c.buy_offer)}</p>
                )}
              </div>
              <div className="flex flex-col gap-2 items-end">
                {c.available && (
                  <Link href={`/articles/${c.available.id}`} className="chip chip-mint text-xs">Da noi {euro(c.available.price)}</Link>
                )}
                <VendilaANoi carta={`${c.name} #${c.number} – ${c.set_name}`} offerta={c.buy_offer}
                  className="btn btn-ghost text-xs sm:text-sm" />
              </div>
            </div>
          ))}
        </div>
      )}

      <p className="text-xs text-ink-soft mt-8 text-center">
        Prezzi: l&apos;offerta più bassa su CardTrader, aggiornata ogni settimana. &quot;Fino a&quot; è quanto
        diamo per una copia in ottime condizioni: la cifra esatta la confermiamo dopo aver visto le foto.{" "}
        <Link href="/prezzi-carte-pokemon" className="underline">Sfoglia tutti i set</Link>.
      </p>
    </section>
  );
}
