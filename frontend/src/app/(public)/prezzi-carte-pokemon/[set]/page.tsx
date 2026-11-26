import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { CartaTile } from "@/components/guida/CartaTile";
import { absUrl } from "@/lib/seo";
import { anno, dataItaliana, euro, getGuideSet } from "@/lib/price-guide";

export const revalidate = 3600;

type Params = { params: Promise<{ set: string }> };

export async function generateMetadata({ params }: Params): Promise<Metadata> {
  const s = await getGuideSet((await params).set);
  if (!s) return { title: "Set non trovato" };
  const titolo = `Prezzi carte ${s.name} (${anno(s.release_date)}): quanto valgono`;
  return {
    title: titolo,
    description: `Il valore di mercato di tutte le ${s.cards_priced} carte Pokémon del set ${s.name}, ` +
      `aggiornato ogni settimana. Scopri quanto vale la tua carta.`,
    alternates: { canonical: `/prezzi-carte-pokemon/${s.slug}` },
    openGraph: { title: titolo, url: `/prezzi-carte-pokemon/${s.slug}`, images: s.logo ? [s.logo] : undefined },
  };
}

/* Un set: tutte le carte con il prezzo, le piu' care in evidenza. */
export default async function SetPage({ params }: Params) {
  const s = await getGuideSet((await params).set);
  if (!s) notFound();
  const conPrezzo = s.cards.filter((c) => c.min_price != null);
  const top = [...conPrezzo].sort((a, b) => (b.min_price ?? 0) - (a.min_price ?? 0)).slice(0, 4);
  const disponibili = s.cards.filter((c) => c.available).length;

  const breadcrumb = {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: [
      { "@type": "ListItem", position: 1, name: "Prezzi carte Pokémon", item: absUrl("/prezzi-carte-pokemon") },
      { "@type": "ListItem", position: 2, name: s.name, item: absUrl(`/prezzi-carte-pokemon/${s.slug}`) },
    ],
  };

  return (
    <section>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(breadcrumb) }} />
      <Link href="/prezzi-carte-pokemon" className="btn btn-ghost text-sm mb-6">← Tutti i set</Link>
      <div className="card p-6 sm:p-8 mb-8 flex flex-col sm:flex-row gap-6 items-center">
        {s.logo && (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={s.logo} alt={s.name} className="h-20 object-contain" />
        )}
        <div className="flex-1 text-center sm:text-left">
          <h1 className="display text-3xl sm:text-4xl text-ink leading-tight">Prezzi carte {s.name}</h1>
          <p className="text-ink-soft mt-2">
            {s.release_date && <>Uscito il {dataItaliana(s.release_date)}</>}
            {s.card_count ? ` · ${s.card_count} carte` : ""}
            {s.serie ? ` · serie ${s.serie}` : ""}
          </p>
          {top.length > 0 && (
            <p className="text-sm text-ink mt-3">
              Le più ricercate: {top.map((c) => `${c.name} (${euro(c.min_price)})`).join(", ")}.
            </p>
          )}
          {disponibili > 0 && (
            <p className="text-sm text-ink mt-1">
              <span className="chip chip-mint text-xs">{disponibili} disponibil{disponibili === 1 ? "e" : "i"} da noi</span>
            </p>
          )}
        </div>
      </div>

      <div className="grid gap-3 grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
        {s.cards.map((c) => <CartaTile key={c.slug} carta={c} />)}
      </div>

      <p className="text-xs text-ink-soft mt-8">
        Prezzi: l&apos;offerta più bassa su CardTrader per una copia Near Mint (italiana se c&apos;è, se no inglese),
        aggiornata ogni settimana. Nella pagina di ogni carta i prezzi per tutte le condizioni. Immagini: TCGdex.
      </p>
    </section>
  );
}
