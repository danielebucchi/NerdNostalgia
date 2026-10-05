// API_BASE, non PUBLIC_API_BASE: questo è un componente server, e l'URL
// pubblico (localhost:7373) dal container del frontend punterebbe a se
// stesso invece che al backend.
import { API_BASE } from "@/lib/api";
import { ReviewsCarousel, type Review } from "@/components/ReviewsCarousel";

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
 * Cosa dicono i clienti: le ultime 10, in un carosello che gira.
 *
 * È un componente server e non guarda nessuna sessione — le recensioni
 * sono pubbliche e si vedono anche da sloggati. Il motivo per cui a
 * volte sembravano sparite era la cache: ora dura un minuto, così una
 * recensione appena approvata compare quasi subito.
 *
 * Resta nascosta solo se non ce n'è nessuna: una sezione "recensioni"
 * vuota su un negozio nuovo fa l'effetto opposto a quello che serve.
 */
export async function ReviewsSection() {
  let reviews: Review[] = [];
  let summary: Summary = { count: 0, average: null };

  try {
    const [r1, r2] = await Promise.all([
      fetch(`${API_BASE}/api/reviews/?limit=10`, { next: { revalidate: 60 } }),
      fetch(`${API_BASE}/api/reviews/summary`, { next: { revalidate: 60 } }),
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

      <ReviewsCarousel reviews={reviews} />

    </section>
  );
}
