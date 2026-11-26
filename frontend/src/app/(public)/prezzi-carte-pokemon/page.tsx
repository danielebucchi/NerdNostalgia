import type { Metadata } from "next";
import Link from "next/link";
import { anno, getGuideSets, type GuideSet } from "@/lib/price-guide";

export const revalidate = 3600;

export const metadata: Metadata = {
  title: "Prezzi carte Pokémon: quanto valgono, set per set",
  description:
    "Quanto vale una carta Pokémon? Il prezzo di mercato di ogni carta di ogni set, dal Set Base a oggi, " +
    "aggiornato ogni settimana. E se ce l'hai, puoi venderla a noi.",
  alternates: { canonical: "/prezzi-carte-pokemon" },
};

/* L'indice della guida prezzi: i set raggruppati per serie, dal piu' recente. */
export default async function PrezziCartePokemonPage() {
  const sets = (await getGuideSets()) ?? [];
  const perSerie = new Map<string, GuideSet[]>();
  for (const s of sets) {
    const serie = s.serie || "Altri set";
    perSerie.set(serie, [...(perSerie.get(serie) ?? []), s]);
  }

  return (
    <section>
      <div className="hero-blob p-6 sm:p-10 md:p-12 mb-10 text-center">
        <span className="chip chip-pink mb-4 inline-flex">Guida prezzi</span>
        <h1 className="display text-3xl sm:text-4xl md:text-5xl text-ink leading-tight">
          Quanto valgono le tue <span className="text-pink-deep">carte Pokémon</span>?
        </h1>
        <p className="text-ink-soft text-base sm:text-lg max-w-2xl mx-auto mt-4">
          Il prezzo di mercato di ogni carta, set per set, aggiornato ogni settimana con le offerte
          di CardTrader. Cerca la tua carta o sfoglia i set.
        </p>
        <Link href="/valuta-carte" className="btn btn-primary mt-6 inline-flex">🔍 Valuta la tua carta</Link>
      </div>

      {sets.length === 0 && (
        <p className="text-center text-ink-soft">La guida si sta preparando: torni fra poco.</p>
      )}

      {[...perSerie.entries()].map(([serie, elenco]) => (
        <div key={serie} className="mb-10">
          <h2 className="display text-2xl text-ink mb-4">{serie}</h2>
          <div className="grid gap-3 grid-cols-2 sm:grid-cols-3 md:grid-cols-4">
            {elenco.map((s) => (
              <Link key={s.slug} href={`/prezzi-carte-pokemon/${s.slug}`}
                className="card p-4 flex flex-col items-center text-center hover:-translate-y-0.5 transition-transform">
                {s.logo && (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={s.logo} alt="" loading="lazy" className="h-14 object-contain mb-2" />
                )}
                <span className="display text-base text-ink leading-tight">{s.name}</span>
                <span className="text-xs text-ink-soft mt-1">
                  {anno(s.release_date)} · {s.cards_priced} carte
                </span>
              </Link>
            ))}
          </div>
        </div>
      ))}
    </section>
  );
}
