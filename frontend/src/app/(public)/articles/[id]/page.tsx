import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { formatPrice, getArticle, getPublicSettings, listArticles } from "@/lib/api";
import type { Article } from "@/lib/types";
import { ArticleActions } from "@/components/ArticleActions";
import { ArticleCard } from "@/components/ArticleCard";
import { ArticleGallery } from "@/components/ArticleGallery";
import { BuyControls } from "@/components/BuyControls";
import { ShareButtons } from "@/components/ShareButtons";
import { StickyCtaBar } from "@/components/StickyCtaBar";
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

  // Correlati: stessa famiglia di categoria (parent se esiste, cosi' pesca
  // anche dalle sottocategorie sorelle), escluso l'articolo corrente. Se il
  // paniere e' magro si riempie con gli ultimi arrivi. Best-effort: la
  // pagina non deve fallire per un errore qui.
  let related: Article[] = [];
  try {
    const familyId = article.parent_category?.id ?? article.category?.id;
    if (familyId) {
      const r = await listArticles({ category_id: familyId, limit: 8 });
      related = r.items.filter((a) => a.id !== article.id);
    }
    if (related.length < 4) {
      const latest = await listArticles({ limit: 8 });
      for (const a of latest.items) {
        if (a.id !== article.id && !related.some((x) => x.id === a.id)) {
          related.push(a);
        }
      }
    }
    related = related.slice(0, 4);
  } catch {
    related = [];
  }

  // Riga finale della descrizione (es. "Spedizione veloce"): setting
  // runtime, vale per TUTTI gli articoli senza toccarne il testo.
  const settings = await getPublicSettings();
  const descriptionFooter = (settings.article_description_footer ?? "Spedizione veloce").trim();

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

      {/* Layout responsive:
          - Mobile (1col): titolo → immagine → descrizione → price → details → actions
          - Desktop (2col): immagine a sinistra; a destra titolo/price/descrizione/details/actions
          Implementato via grid + col-start/row-start espliciti, niente duplicazione DOM. */}
      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 md:gap-10">
        {/* Titolo + chips */}
        <div className="md:col-start-2 md:row-start-1">
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
        </div>

        {/* Gallery */}
        <div className="md:col-start-1 md:row-start-1 md:row-span-4">
          <ArticleGallery images={article.images ?? []} title={article.title} />
        </div>

        {/* Prezzo + bottoni di acquisto + dialog PayPal */}
        <div className="order-2 md:order-none md:col-start-2 md:row-start-2">
          <div className="display text-4xl text-pink-deep leading-none mb-4">
            {formatPrice(article)}
          </div>
          <BuyControls article={article} />
        </div>

        {/* Descrizione (+ riga finale da settings, es. "Spedizione veloce") */}
        {(article.description || descriptionFooter) && (
          <div className="order-1 md:order-none md:col-start-2 md:row-start-3">
            {article.description && (
              <p className="text-ink-soft text-lg whitespace-pre-line leading-relaxed">
                {article.description}
              </p>
            )}
            {descriptionFooter && (
              <p className="text-ink text-base font-semibold mt-3 inline-flex items-center gap-1.5">
                <span aria-hidden="true">🚚</span> {descriptionFooter}
              </p>
            )}
          </div>
        )}

        {/* Details + marketplaces + actions */}
        <div className="order-3 md:order-none md:col-start-2 md:row-start-4">
          <dl className="grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
            {article.brand && <Row label="Marca" value={article.brand} />}
            {article.model && <Row label="Modello" value={article.model} />}
            {article.sku && <Row label="SKU" value={article.sku} />}
            <Row label="Quantità" value={String(article.quantity)} />
            {article.weight_kg && <Row label="Peso" value={`${article.weight_kg} kg`} />}
            {article.dimensions_cm && <Row label="Dimensioni" value={article.dimensions_cm} />}
          </dl>

          <div className="mt-6 flex flex-wrap items-center gap-3">
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

      {/* Correlati: tiene l'utente nel catalogo */}
      {related.length > 0 && (
        <section className="mt-12 sm:mt-16" aria-label="Articoli correlati">
          <h2 className="display text-2xl sm:text-3xl text-ink mb-5">
            Potrebbero piacerti
          </h2>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-6">
            {related.map((a) => (
              <ArticleCard key={a.id} article={a} />
            ))}
          </div>
        </section>
      )}

      {/* Mobile: prezzo + CTA sempre a portata di pollice; il padding evita
          che la barra copra il fondo pagina */}
      <div className="sm:hidden h-20" aria-hidden="true" />
      <StickyCtaBar article={article} />
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
