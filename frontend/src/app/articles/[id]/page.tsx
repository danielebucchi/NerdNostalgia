import Link from "next/link";
import { notFound } from "next/navigation";
import { formatPrice, getArticle } from "@/lib/api";

interface PageProps {
  params: Promise<{ id: string }>;
}

const CONDITION_LABEL: Record<string, string> = {
  NEW: "NUOVO",
  USED: "USATO",
  REFURBISHED: "REVISIONATO",
  FOR_PARTS: "PER PEZZI",
};

const STATUS_LABEL: Record<string, string> = {
  PUBLISHED: "DISPONIBILE",
  SOLD: "VENDUTO",
  DRAFT: "BOZZA",
  ARCHIVED: "ARCHIVIATO",
};

export default async function ArticleDetailPage({ params }: PageProps) {
  const { id } = await params;
  const article = await getArticle(id);

  if (!article) {
    notFound();
  }

  const cover = article.images?.[0];
  const gallery = article.images?.slice(1) ?? [];

  return (
    <article>
      <Link href="/" className="pixel-btn ghost inline-block mb-8">
        ← CATALOGO
      </Link>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-10">
        <div>
          <div className="card aspect-square w-full flex items-center justify-center p-2">
            {cover ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={cover}
                alt={article.title}
                className="pixel-img max-h-full max-w-full object-contain"
              />
            ) : (
              <span className="font-pixel text-retro-neon text-sm">NO PHOTO</span>
            )}
          </div>

          {gallery.length > 0 && (
            <div className="mt-4 grid grid-cols-4 gap-3">
              {gallery.map((img) => (
                <div key={img} className="aspect-square card p-1">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={img} alt="" className="pixel-img w-full h-full object-contain" />
                </div>
              ))}
            </div>
          )}
        </div>

        <div>
          <div className="flex gap-2 flex-wrap mb-4">
            <span className="badge text-retro-neon">
              {CONDITION_LABEL[article.condition] ?? article.condition}
            </span>
            <span className="badge text-retro-sun">
              {STATUS_LABEL[article.status] ?? article.status}
            </span>
            {article.category && (
              <span className="badge text-retro-green">{article.category.toUpperCase()}</span>
            )}
          </div>

          <h1 className="font-pixel text-retro-sun glow text-lg sm:text-xl leading-snug">
            {article.title}
          </h1>

          <div className="mt-6 font-pixel text-retro-accent glow text-2xl">
            {formatPrice(article)}
          </div>

          {article.description && (
            <p className="mt-6 font-retro text-xl text-[#f1e6ff] whitespace-pre-line leading-relaxed">
              {article.description}
            </p>
          )}

          <dl className="mt-8 grid grid-cols-2 gap-3 text-sm font-retro text-retro-neon">
            {article.brand && (
              <Row label="MARCA" value={article.brand} />
            )}
            {article.model && (
              <Row label="MODELLO" value={article.model} />
            )}
            {article.sku && <Row label="SKU" value={article.sku} />}
            <Row label="QUANTITA" value={String(article.quantity)} />
            {article.weight_kg && <Row label="PESO" value={`${article.weight_kg} kg`} />}
            {article.dimensions_cm && (
              <Row label="DIMENSIONI" value={article.dimensions_cm} />
            )}
          </dl>

          <div className="mt-10 flex flex-wrap gap-3">
            <button className="pixel-btn" type="button" disabled>
              AGGIUNGI AL CARRELLO
            </button>
            <button className="pixel-btn ghost" type="button" disabled>
              CHIEDI INFO
            </button>
          </div>
          <p className="mt-3 text-retro-sun font-retro text-base">
            (Carrello e form contatti arrivano nelle prossime fasi.)
          </p>
        </div>
      </div>
    </article>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="font-pixel text-[10px] text-retro-accent">{label}</dt>
      <dd className="text-lg text-retro-sun">{value}</dd>
    </div>
  );
}
