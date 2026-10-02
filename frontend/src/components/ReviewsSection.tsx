// API_BASE, non PUBLIC_API_BASE: questo è un componente server, e l'URL
// pubblico (localhost:7373) dal container del frontend punterebbe a se
// stesso invece che al backend.
import { API_BASE } from "@/lib/api";

interface Review {
  id: number;
  author_name: string;
  rating: number;
  body: string | null;
  reply: string | null;
  created_at: string;
}

interface Summary {
  count: number;
  average: number | null;
}

function Stelle({ n }: { n: number }) {
  return (
    <span className="text-star-deep tracking-tight" aria-label={`${n} su 5`}>
      {"★".repeat(n)}
      <span className="text-ink/15">{"★".repeat(5 - n)}</span>
    </span>
  );
}

/**
 * Cosa dicono i clienti. Si vede solo se c'è qualcosa da mostrare: una
 * sezione "recensioni" vuota su un negozio nuovo fa l'effetto opposto a
 * quello che serve.
 */
export async function ReviewsSection() {
  let reviews: Review[] = [];
  let summary: Summary = { count: 0, average: null };

  try {
    const [r1, r2] = await Promise.all([
      fetch(`${API_BASE}/api/reviews/?limit=6`, { next: { revalidate: 300 } }),
      fetch(`${API_BASE}/api/reviews/summary`, { next: { revalidate: 300 } }),
    ]);
    if (r1.ok) reviews = await r1.json();
    if (r2.ok) summary = await r2.json();
  } catch {
    return null; // backend irraggiungibile: la home non deve rompersi
  }

  if (reviews.length === 0) return null;

  return (
    <section className="mb-10">
      <div className="flex flex-wrap items-baseline gap-3 mb-5">
        <h2 className="display text-2xl sm:text-3xl text-ink">
          Dicono di me
        </h2>
        {summary.average != null && (
          <p className="text-ink-soft text-sm">
            <Stelle n={Math.round(summary.average)} />{" "}
            <strong className="text-ink">{summary.average.toFixed(1)}</strong> su 5
            — {summary.count}{" "}
            {summary.count === 1 ? "recensione" : "recensioni"}
          </p>
        )}
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {reviews.map((r) => (
          <div key={r.id} className="card p-4 flex flex-col gap-2">
            <Stelle n={r.rating} />
            {r.body && (
              <p className="text-sm text-ink leading-relaxed flex-1">
                “{r.body}”
              </p>
            )}
            <p className="text-xs text-ink-soft">— {r.author_name}</p>
            {r.reply && (
              <p className="text-xs text-ink-soft bg-pink-soft/30 rounded-lg p-2 leading-snug">
                <strong className="text-ink">La mia risposta:</strong> {r.reply}
              </p>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}
