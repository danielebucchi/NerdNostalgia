import type { Metadata } from "next";
import Link from "next/link";
import { listArticles } from "@/lib/api";
import { CatalogSection } from "@/components/CatalogSection";
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

  return (
    <>
      {/* Hero */}
      <section className="hero-blob p-6 sm:p-10 md:p-12 mb-10 sm:mb-12 relative overflow-hidden">
        {/* Logo mobile (sopra il testo) */}
        <div className="md:hidden flex justify-center mb-5">
          <LogoImage
            size={160}
            className="w-32 h-32 rounded-full ring-1 ring-lilac-deep/20 shadow-glow object-cover bg-white"
            alt="NerdNostalgia logo"
          />
        </div>
        <div className="grid gap-8 md:grid-cols-[1.4fr_1fr] items-center">
          <div className="text-center md:text-left">
            <span className="chip chip-pink mb-4 inline-flex">
              ★ nuovi arrivi ogni settimana
            </span>
            <h1 className="display text-3xl sm:text-4xl md:text-5xl text-ink leading-[1.1] mb-4">
              Le tue <span className="text-pink-deep">nerderie</span>,
              <br className="hidden sm:inline" />{" "}
              casa dolce casa.
            </h1>
            <p className="text-ink-soft text-base sm:text-lg max-w-md mx-auto md:mx-0 leading-relaxed">
              Videogiochi vintage, carte Pokémon, Funko e gadget retro selezionati
              con cura. Spedizione veloce in tutta Italia.
            </p>
            <div className="mt-6 flex flex-wrap gap-3 justify-center md:justify-start">
              <Link href="#catalogo" className="btn btn-primary">
                Sfoglia il catalogo →
              </Link>
              <Link href="/cerco-compro" className="btn btn-ghost">
                Vendi le tue cose
              </Link>
            </div>
          </div>
          <div className="hidden md:flex items-center justify-center relative">
            <LogoImage
              size={256}
              className="w-64 h-64 rounded-full ring-1 ring-lilac-deep/20 shadow-glow object-cover bg-white"
              alt="NerdNostalgia logo"
            />
          </div>
        </div>
      </section>

      {/* Catalog (con filtri client-side) */}
      <section id="catalogo">
        <div className="mb-6">
          <h2 className="display text-2xl sm:text-3xl text-ink">Catalogo</h2>
          <p className="text-ink-soft">
            Tutto quello che ho in inventario in questo momento.
          </p>
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
