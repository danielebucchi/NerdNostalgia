import type { Metadata } from "next";
import Link from "next/link";
import { getPublicSettings, listArticles } from "@/lib/api";
import { CatalogSection } from "@/components/CatalogSection";
import { ReviewsSection } from "@/components/ReviewsSection";
import { LogoImage } from "@/components/LogoImage";

export const metadata: Metadata = {
  alternates: { canonical: "/" },
};

export default async function HomePage() {
  let articles: Awaited<ReturnType<typeof listArticles>>["items"] = [];
  let error: string | null = null;

  try {
    // Carichiamo il catalogo per i filtri client-side (limit 100 = cap backend).
    // Per scalare oltre serviranno paginazione + facet count API lato server.
    const data = await listArticles({ status: "PUBLISHED", limit: 100 });
    articles = data.items;
  } catch (err) {
    error = err instanceof Error ? err.message : "Errore sconosciuto";
  }

  // Promozione "spedizione gratuita su tutto": l'annuncio in home deve dire
  // la stessa cosa che il carrello poi applica.
  let freeShippingAll = false;
  try {
    const settings = await getPublicSettings();
    freeShippingAll =
      (settings.free_shipping_all || "").trim().toLowerCase() === "true";
  } catch {
    /* settings irraggiungibili: resta l'annuncio con la soglia */
  }

  return (
    <>
      {/* Hero — compatto su desktop cosi' il catalogo si intravede subito
          sotto la fold senza dover scrollare */}
      <section className="hero-blob p-6 sm:p-8 md:p-8 mb-8 sm:mb-10 relative overflow-hidden">
        {/* Logo mobile (sopra il testo) */}
        <div className="md:hidden flex justify-center mb-5">
          <LogoImage
            size={160}
            className="w-32 h-32 rounded-full ring-1 ring-lilac-deep/20 shadow-glow object-cover bg-white"
            alt="NerdNostalgia logo"
          />
        </div>
        <div className="grid gap-6 md:grid-cols-[1.7fr_1fr] items-center">
          <div className="text-center md:text-left">
            <span className="chip chip-pink mb-3 inline-flex">
              ★ nuovi arrivi ogni settimana
            </span>
            <h1 className="display text-3xl sm:text-4xl text-ink leading-[1.1] mb-3">
              Le tue <span className="text-pink-deep">nerderie</span>,
              <br className="hidden sm:inline" />{" "}
              casa dolce casa.
            </h1>
            <p className="text-ink-soft text-base max-w-md mx-auto md:mx-0 leading-relaxed">
              Videogiochi vintage, carte Pokémon, Funko e gadget retro selezionati
              con cura. Spedizione veloce in tutta Italia.
            </p>
            <p className="mt-3 inline-flex items-center gap-2 rounded-full bg-mint-deep/15 ring-1 ring-mint-deep/40 px-4 py-2 text-sm font-semibold text-ink">
              <span aria-hidden="true" className="text-base">🚚</span>
              <span>
                Spedizione <span className="text-mint-deep">gratuita</span>{" "}
                {freeShippingAll ? "su tutto il catalogo" : "per ordini da 250 €"}
              </span>
            </p>
            <div className="mt-5 flex flex-wrap gap-3 justify-center md:justify-start">
              <Link href="#catalogo" className="btn btn-primary">
                Sfoglia il catalogo →
              </Link>
            </div>
          </div>
          <div className="hidden md:flex items-center justify-center relative">
            <LogoImage
              size={160}
              className="w-40 h-40 rounded-full ring-1 ring-lilac-deep/20 shadow-glow object-cover bg-white"
              alt="NerdNostalgia logo"
            />
          </div>
        </div>
      </section>

      {/* Catalog (con filtri client-side) */}
      {/* Prima del catalogo: chi arriva vuole sapere di chi si fida prima di
          scegliere, non dopo aver scorso tutte le schede. */}
      <ReviewsSection />

      <section id="catalogo">
        <div className="mb-6">
          <h2 className="display text-2xl sm:text-3xl text-ink">Catalogo</h2>
        </div>

        {error ? (
          <div className="card p-6 text-center">
            <p className="display text-lg text-pink-deep mb-1">
              Backend non raggiungibile
            </p>
            <p className="text-sm text-ink-soft">
              {error}. Assicurati che il backend giri su{" "}
              <code className="text-ink">localhost:7373</code>.
            </p>
          </div>
        ) : (
          <CatalogSection initialArticles={articles} />
        )}
      </section>
    </>
  );
}
