import type { Metadata } from "next";
import Link from "next/link";
import { listArticles } from "@/lib/api";
import { ArticleCard } from "@/components/ArticleCard";
import { LogoImage } from "@/components/LogoImage";

export const metadata: Metadata = {
  alternates: { canonical: "/" },
};

const CATEGORIES = [
  { slug: "videogames", label: "Videogiochi", emoji: "🎮", chip: "chip-sky" },
  { slug: "pokemon-cards", label: "Carte Pokémon", emoji: "⚡", chip: "chip-pink" },
  { slug: "funko-pop", label: "Funko Pop", emoji: "🧸", chip: "chip-lilac" },
];

export default async function HomePage() {
  let articles: Awaited<ReturnType<typeof listArticles>>["items"] = [];
  let error: string | null = null;

  try {
    const data = await listArticles({ status: "PUBLISHED", limit: 24 });
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

      {/* Categories */}
      <section className="mb-12">
        <h2 className="display text-2xl text-ink mb-4">Categorie</h2>
        <div className="grid gap-4 sm:grid-cols-3">
          {CATEGORIES.map((cat) => (
            <Link
              key={cat.slug}
              href={`/?category=${cat.slug}`}
              className="card card-clickable p-6 flex items-center gap-4"
            >
              <span className="text-4xl">{cat.emoji}</span>
              <div className="flex-1">
                <span className={`chip ${cat.chip}`}>{cat.label}</span>
                <p className="text-sm text-ink-soft mt-2">Sfoglia →</p>
              </div>
            </Link>
          ))}
        </div>
      </section>

      {/* Catalog */}
      <section id="catalogo">
        <div className="flex items-end justify-between mb-6">
          <div>
            <h2 className="display text-2xl text-ink">Catalogo</h2>
            <p className="text-ink-soft">Tutto quello che ho in inventario in questo momento.</p>
          </div>
          {!error && articles.length > 0 && (
            <span className="chip chip-mint">{articles.length} articoli</span>
          )}
        </div>

        {error && (
          <div className="card p-6 text-center">
            <p className="display text-lg text-pink-deep mb-1">Backend non raggiungibile</p>
            <p className="text-sm text-ink-soft">
              {error}. Assicurati che il backend giri su{" "}
              <code className="text-ink">localhost:7373</code>.
            </p>
          </div>
        )}

        {!error && articles.length === 0 && (
          <div className="card p-10 text-center">
            <p className="display text-xl text-ink mb-2">Inventario vuoto</p>
            <p className="text-ink-soft">
              Nessun articolo ancora pubblicato. Aggiungine via{" "}
              <a
                className="text-pink-deep underline font-semibold"
                href="http://localhost:7373/docs"
                target="_blank"
                rel="noreferrer"
              >
                Swagger
              </a>
              .
            </p>
          </div>
        )}

        {articles.length > 0 && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {articles.map((article) => (
              <ArticleCard key={article.id} article={article} />
            ))}
          </div>
        )}
      </section>
    </>
  );
}
