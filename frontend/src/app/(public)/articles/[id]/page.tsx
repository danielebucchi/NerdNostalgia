import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { formatPrice, getArticle } from "@/lib/api";
import { ArticleActions } from "@/components/ArticleActions";
import { ArticleGallery } from "@/components/ArticleGallery";
import { MarketplaceLogo } from "@/components/MarketplaceLogo";
import { ShareButtons } from "@/components/ShareButtons";
import { WishlistButton } from "@/components/WishlistButton";
import { absUrl, clip, SITE_NAME } from "@/lib/seo";

interface PageProps {
  params: Promise<{ id: string }>;
}

const CONDITION_SCHEMA: Record<string, string> = {
  NEW: "https://schema.org/NewCondition",
  USED: "https://schema.org/UsedCondition",
  REFURBISHED: "https://schema.org/RefurbishedCondition",
  FOR_PARTS: "https://schema.org/DamagedCondition",
};

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { id } = await params;
  const article = await getArticle(id).catch(() => null);
  if (!article) {
    return { title: "Articolo non trovato" };
  }
  const cover = article.images?.[0];
  const desc = clip(article.description) || `${article.title} su ${SITE_NAME}.`;
  return {
    title: article.title,
    description: desc,
    alternates: { canonical: `/articles/${article.id}` },
    openGraph: {
      type: "website",
      title: article.title,
      description: desc,
      url: absUrl(`/articles/${article.id}`),
      images: cover ? [{ url: cover, alt: article.title }] : undefined,
    },
    twitter: {
      card: "summary_large_image",
      title: article.title,
      description: desc,
      images: cover ? [cover] : undefined,
    },
  };
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

  const productJsonLd = {
    "@context": "https://schema.org",
    "@type": "Product",
    name: article.title,
    description: article.description ?? article.title,
    image: article.images ?? [],
    sku: article.sku ?? `nn-${article.id}`,
    brand: article.brand
      ? { "@type": "Brand", name: article.brand }
      : undefined,
    category: article.category?.name ?? undefined,
    itemCondition: CONDITION_SCHEMA[article.condition] ?? CONDITION_SCHEMA.USED,
    offers: {
      "@type": "Offer",
      url: absUrl(`/articles/${article.id}`),
      priceCurrency: article.currency || "EUR",
      price: article.price,
      availability:
        article.status === "PUBLISHED" && article.quantity > 0
          ? "https://schema.org/InStock"
          : article.status === "SOLD"
            ? "https://schema.org/SoldOut"
            : "https://schema.org/OutOfStock",
      seller: { "@type": "Organization", name: SITE_NAME },
    },
  };

  return (
    <article>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(productJsonLd) }}
      />
      <Link href="/" className="btn btn-ghost text-sm mb-8">
        ← Catalogo
      </Link>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-10">
        {/* Gallery */}
        <div>
          <ArticleGallery images={article.images ?? []} title={article.title} />
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
              <span className="chip chip-lilac">
                {article.parent_category
                  ? `${article.parent_category.name} › ${article.category.name}`
                  : article.category.name}
              </span>
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

          {(article.vinted_status === "LISTED" && article.vinted_url) ||
          (article.ebay_status === "LISTED" && article.ebay_url) ? (
            <div className="mt-6 flex items-center gap-3">
              <span className="text-xs uppercase tracking-wider text-ink-soft">
                Anche su
              </span>
              {article.vinted_status === "LISTED" && article.vinted_url && (
                <a
                  href={article.vinted_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  aria-label="Apri il listing su Vinted"
                  className="inline-flex items-center bg-white/85 backdrop-blur rounded-full h-10 px-4 ring-1 ring-ink/10 shadow-soft hover:shadow-hover transition-shadow"
                >
                  <MarketplaceLogo marketplace="vinted" height={20} />
                </a>
              )}
              {article.ebay_status === "LISTED" && article.ebay_url && (
                <a
                  href={article.ebay_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  aria-label="Apri il listing su eBay"
                  className="inline-flex items-center bg-white/85 backdrop-blur rounded-full h-10 px-4 ring-1 ring-ink/10 shadow-soft hover:shadow-hover transition-shadow"
                >
                  <MarketplaceLogo marketplace="ebay" height={20} />
                </a>
              )}
            </div>
          ) : null}

          <div className="mt-8 flex flex-wrap items-center gap-3">
            <WishlistButton articleId={article.id} variant="full" />
            <ShareButtons
              url={absUrl(`/articles/${article.id}`)}
              title={article.title}
              text={`${article.title} su ${SITE_NAME}`}
            />
          </div>

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
