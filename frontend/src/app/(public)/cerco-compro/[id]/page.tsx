import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { formatMaxPrice, getWantedItem } from "@/lib/api";
import { WantedActions } from "@/components/WantedActions";
import { absUrl, clip, SITE_NAME } from "@/lib/seo";

interface PageProps {
  params: Promise<{ id: string }>;
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { id } = await params;
  const item = await getWantedItem(id).catch(() => null);
  if (!item) {
    return { title: "Richiesta non trovata" };
  }
  const desc =
    clip(item.description) || `Sto cercando ${item.title}. Te lo propongo su ${SITE_NAME}?`;
  return {
    title: `Cerco: ${item.title}`,
    description: desc,
    alternates: { canonical: `/cerco-compro/${item.id}` },
    openGraph: {
      title: `Cerco: ${item.title}`,
      description: desc,
      url: absUrl(`/cerco-compro/${item.id}`),
    },
    twitter: {
      card: "summary",
      title: `Cerco: ${item.title}`,
      description: desc,
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
  ACTIVE: "Sto cercando",
  FULFILLED: "Trovato",
  CLOSED: "Chiusa",
};

const STATUS_CHIP: Record<string, string> = {
  ACTIVE: "chip-mint",
  FULFILLED: "chip-pink",
  CLOSED: "chip-sky",
};

export default async function WantedDetailPage({ params }: PageProps) {
  const { id } = await params;
  const item = await getWantedItem(id);

  if (!item) {
    notFound();
  }

  const maxPrice = formatMaxPrice(item);

  return (
    <article>
      <Link href="/cerco-compro" className="btn btn-ghost text-sm mb-8">
        ← Cerco/Compro
      </Link>

      <div className="grid grid-cols-1 md:grid-cols-[2fr_1fr] gap-10">
        <div>
          <div className="flex flex-wrap gap-2 mb-4">
            <span className={`chip ${STATUS_CHIP[item.status] ?? "chip-mint"}`}>
              {STATUS_LABEL[item.status] ?? item.status}
            </span>
            {item.priority >= 50 && (
              <span className="chip chip-star">🔥 con urgenza</span>
            )}
            {item.category && (
              <span className="chip chip-lilac">{item.category.replace(/-/g, " ")}</span>
            )}
            {item.preferred_condition && (
              <span className="chip chip-sky">
                Condizione: {CONDITION_LABEL[item.preferred_condition] ?? item.preferred_condition}
              </span>
            )}
          </div>

          <h1 className="display text-3xl sm:text-4xl text-ink leading-tight">
            {item.title}
          </h1>

          {item.description && (
            <p className="mt-6 text-ink-soft text-lg whitespace-pre-line leading-relaxed">
              {item.description}
            </p>
          )}

          {item.notes && (
            <div className="mt-6 card p-4 bg-lilac-soft border-lilac-deep">
              <h3 className="display text-base text-ink mb-1">Note</h3>
              <p className="text-ink-soft whitespace-pre-line">{item.notes}</p>
            </div>
          )}

          <dl className="mt-8 grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
            {item.brand && <Row label="Marca preferita" value={item.brand} />}
            {item.model && <Row label="Modello" value={item.model} />}
            {item.preferred_condition && (
              <Row
                label="Condizione preferita"
                value={CONDITION_LABEL[item.preferred_condition] ?? item.preferred_condition}
              />
            )}
            {item.category && <Row label="Categoria" value={item.category.replace(/-/g, " ")} />}
          </dl>
        </div>

        <aside>
          <div className="card p-6 sticky top-28">
            <div className="text-center mb-4">
              <span className="text-xs uppercase tracking-wider text-ink-soft">Offerta</span>
              <div className="display text-3xl text-pink-deep mt-1">
                {maxPrice ?? "Da concordare"}
              </div>
              {maxPrice && (
                <p className="text-xs text-ink-soft mt-1">cifra indicativa, trattabile</p>
              )}
            </div>

            <WantedActions
              wantedId={item.id}
              title={item.title}
              fulfilled={item.status !== "ACTIVE"}
            />
          </div>
        </aside>
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
