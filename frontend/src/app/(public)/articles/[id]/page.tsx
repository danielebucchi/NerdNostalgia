import Link from "next/link";
import { notFound } from "next/navigation";
import { formatPrice, getArticle } from "@/lib/api";
import { ArticleActions } from "@/components/ArticleActions";

interface PageProps {
  params: Promise<{ id: string }>;
}

const CONDITION_LABEL: Record<string, string> = {
  NEW: "Nuovo",
  USED: "Usato",
  REFURBISHED: "Revisionato",
  FOR_PARTS: "Per pezzi",
};

const STATUS_LABEL: Record<string, string> = {
  PUBLISHED: "Disponibile",
  SOLD: "Venduto",
  DRAFT: "Bozza",
  ARCHIVED: "Archiviato",
};

const STATUS_CHIP: Record<string, string> = {
  PUBLISHED: "chip-mint",
  SOLD: "chip-pink",
  DRAFT: "chip-lilac",
  ARCHIVED: "chip-sky",
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
      <Link href="/" className="btn btn-ghost text-sm mb-8">
        ← Catalogo
      </Link>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-10">
        {/* Gallery */}
        <div>
          <div className="card aspect-square w-full flex items-center justify-center p-4 overflow-hidden">
            {cover ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={cover}
                alt={article.title}
                className="max-w-full max-h-full object-contain"
              />
            ) : (
              <span className="display text-ink-soft text-xl">No photo</span>
            )}
          </div>

          {gallery.length > 0 && (
            <div className="mt-4 grid grid-cols-4 gap-3">
              {gallery.map((img) => (
                <div key={img} className="aspect-square card p-1 overflow-hidden">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={img} alt="" className="w-full h-full object-cover rounded-lg" />
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Info */}
        <div>
          <div className="flex flex-wrap gap-2 mb-4">
            <span className={`chip ${STATUS_CHIP[article.status] ?? "chip-mint"}`}>
              {STATUS_LABEL[article.status] ?? article.status}
            </span>
            <span className="chip chip-sky">
              {CONDITION_LABEL[article.condition] ?? article.condition}
            </span>
            {article.category && (
              <span className="chip chip-lilac">{article.category.replace(/-/g, " ")}</span>
            )}
          </div>

          <h1 className="display text-3xl sm:text-4xl text-ink leading-tight">
            {article.title}
          </h1>

          <div className="mt-6 display text-4xl text-pink-deep">
            {formatPrice(article)}
          </div>

          {article.description && (
            <p className="mt-6 text-ink-soft text-lg whitespace-pre-line leading-relaxed">
              {article.description}
            </p>
          )}

          <dl className="mt-8 grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
            {article.brand && <Row label="Marca" value={article.brand} />}
            {article.model && <Row label="Modello" value={article.model} />}
            {article.sku && <Row label="SKU" value={article.sku} />}
            <Row label="Quantità" value={String(article.quantity)} />
            {article.weight_kg && <Row label="Peso" value={`${article.weight_kg} kg`} />}
            {article.dimensions_cm && <Row label="Dimensioni" value={article.dimensions_cm} />}
          </dl>

          <div className="mt-10">
            <ArticleActions
              articleId={article.id}
              articleTitle={article.title}
              sold={article.status === "SOLD"}
            />
          </div>
        </div>
      </div>
    </article>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="border-b border-dashed border-ink/15 pb-2">
      <dt className="text-xs uppercase tracking-wider text-ink-soft">{label}</dt>
      <dd className="text-base text-ink font-semibold">{value}</dd>
    </div>
  );
}
