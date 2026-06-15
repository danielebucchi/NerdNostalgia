import { listArticles } from "@/lib/api";
import { ArticleCard } from "@/components/ArticleCard";

export default async function HomePage() {
  let articles = [];
  let error: string | null = null;

  try {
    const data = await listArticles({ status: "PUBLISHED", limit: 24 });
    articles = data.items;
  } catch (err) {
    error = err instanceof Error ? err.message : "Errore sconosciuto";
  }

  return (
    <section>
      <div className="mb-10 text-center">
        <h2 className="font-pixel text-retro-sun text-xl sm:text-2xl glow">
          ★ CATALOGO ★
        </h2>
        <p className="font-retro text-retro-neon text-lg mt-3 max-w-xl mx-auto">
          Tutto quello che ho in inventario, dai retrogame alle carte Pokemon.
          Scrivimi se ti interessa qualcosa o se vuoi vendermi le tue nerderie.
        </p>
      </div>

      {error && (
        <div className="card p-6 text-center font-retro text-xl text-retro-accent">
          ⚠ Impossibile contattare il backend (<span className="font-pixel text-xs">{error}</span>).
          <br />
          Assicurati che il backend giri su <code>localhost:7373</code>.
        </div>
      )}

      {!error && articles.length === 0 && (
        <div className="card p-10 text-center">
          <p className="font-pixel text-retro-neon text-sm mb-4">INVENTARIO VUOTO</p>
          <p className="font-retro text-retro-sun text-lg">
            Nessun articolo ancora pubblicato.
            <br />
            Usa l&apos;API per crearne uno o popola via Swagger su{" "}
            <a
              className="text-retro-accent underline"
              href="http://localhost:7373/docs"
              target="_blank"
              rel="noreferrer"
            >
              /docs
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
  );
}
