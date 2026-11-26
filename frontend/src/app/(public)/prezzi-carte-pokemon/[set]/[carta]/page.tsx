import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { CartaTile } from "@/components/guida/CartaTile";
import { VendilaANoi } from "@/components/guida/VendilaANoi";
import { absUrl } from "@/lib/seo";
import { anno, dataItaliana, euro, formatDataBreve, getGuideCard } from "@/lib/price-guide";

export const revalidate = 3600;

type Params = { params: Promise<{ set: string; carta: string }> };

export async function generateMetadata({ params }: Params): Promise<Metadata> {
  const p = await params;
  const c = await getGuideCard(p.set, p.carta);
  if (!c) return { title: "Carta non trovata" };
  const titolo = `${c.name} ${c.set.name} #${c.number}: prezzo e valore`;
  return {
    title: titolo,
    description: `Quanto vale ${c.name} (${c.set.name}, ${anno(c.set.release_date)}, n. ${c.number})? ` +
      `Da ${euro(c.min_price)} su CardTrader, aggiornato ogni settimana.` +
      (c.available ? ` Disponibile su NerdNostalgia a ${euro(c.available.price)}.` : ""),
    alternates: { canonical: `/prezzi-carte-pokemon/${c.set_slug}/${c.slug}` },
    openGraph: { title: titolo, url: `/prezzi-carte-pokemon/${c.set_slug}/${c.slug}`, images: c.image ? [c.image] : undefined },
  };
}

/* Una carta: quanto vale, se l'abbiamo, le altre versioni, e "vendila a noi". */
export default async function CartaPage({ params }: Params) {
  const p = await params;
  const c = await getGuideCard(p.set, p.carta);
  if (!c) notFound();

  const breadcrumb = {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: [
      { "@type": "ListItem", position: 1, name: "Prezzi carte Pokémon", item: absUrl("/prezzi-carte-pokemon") },
      { "@type": "ListItem", position: 2, name: c.set.name, item: absUrl(`/prezzi-carte-pokemon/${c.set_slug}`) },
      { "@type": "ListItem", position: 3, name: c.name, item: absUrl(`/prezzi-carte-pokemon/${c.set_slug}/${c.slug}`) },
    ],
  };

  return (
    <section>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(breadcrumb) }} />
      <Link href={`/prezzi-carte-pokemon/${c.set_slug}`} className="btn btn-ghost text-sm mb-6">← {c.set.name}</Link>

      <div className="grid gap-8 md:grid-cols-[minmax(0,360px)_1fr] items-start">
        <div className="card p-4">
          {c.image ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={c.image} alt={`${c.name} ${c.set.name}`} className="w-full rounded-xl" />
          ) : (
            <div className="aspect-[63/88] rounded-xl bg-lilac/30" />
          )}
        </div>
        <div>
          <h1 className="display text-3xl sm:text-4xl text-ink leading-tight">
            {c.name} <span className="text-ink-soft">#{c.number}</span>
          </h1>
          <p className="text-ink-soft mt-1">
            {c.set.name}
            {c.set.release_date ? ` · ${dataItaliana(c.set.release_date)}` : ""}
            {c.name_en !== c.name ? ` · in inglese ${c.name_en}` : ""}
          </p>

          <div className="card p-5 mt-6">
            <p className="text-sm text-ink-soft">Valore di mercato</p>
            <p className="display text-4xl text-pink-deep">da {euro(c.min_price)}</p>
            <p className="text-xs text-ink-soft mt-1">
              L&apos;offerta più bassa su CardTrader ({c.offers} in vendita), aggiornata il {formatDataBreve(c.updated_at)}.
              Il valore della tua copia dipende da condizioni, lingua ed edizione.
            </p>
          </div>

          {c.available ? (
            <div className="card p-5 mt-4 flex items-center gap-4">
              <div className="flex-1">
                <p className="display text-lg text-ink">Disponibile da noi</p>
                <p className="text-sm text-ink-soft">{c.available.title}</p>
              </div>
              <Link href={`/articles/${c.available.id}`} className="btn btn-primary">{euro(c.available.price)} →</Link>
            </div>
          ) : (
            <p className="text-sm text-ink-soft mt-4">
              Al momento non l&apos;abbiamo. <Link href="/" className="text-lilac-deep font-semibold hover:underline">Guarda il catalogo</Link>.
            </p>
          )}

          <div className="mt-6">
            <VendilaANoi carta={`${c.name} #${c.number} – ${c.set.name}`} />
          </div>
        </div>
      </div>

      {c.other_versions.length > 0 && (
        <div className="mt-12">
          <h2 className="display text-2xl text-ink mb-4">{c.name_en} in altri set</h2>
          <div className="grid gap-3 grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6">
            {c.other_versions.map((o) => <CartaTile key={`${o.set_slug}/${o.slug}`} carta={o} mostraSet />)}
          </div>
        </div>
      )}
      <p className="text-xs text-ink-soft mt-8">Immagine: TCGdex. Prezzi: CardTrader.</p>
    </section>
  );
}
