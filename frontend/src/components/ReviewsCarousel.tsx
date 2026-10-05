"use client";

import { useEffect, useState } from "react";

export interface Review {
  id: number;
  author_name: string;
  rating: number;
  body: string | null;
  reply: string | null;
  created_at: string;
}

const PAUSA_MS = 5000;

function Stelle({ n }: { n: number }) {
  return (
    <span className="text-star-deep tracking-tight" aria-label={`${n} su 5`}>
      {"★".repeat(n)}
      <span className="text-ink/15">{"★".repeat(5 - n)}</span>
    </span>
  );
}

/* Carosello delle recensioni.
 *
 * Una pista che trasla, non un contenitore che scorre. Il primo tentativo
 * usava scroll-snap e leggeva la posizione dagli eventi di scroll per
 * tenere aggiornati i puntini: quella lettura rimetteva mano allo stato,
 * lo stato rifaceva scorrere, e lo scorrimento morbido emetteva altri
 * eventi — un anello che bloccava la scheda del browser.
 *
 * Qui lo stato e' uno solo e comanda lui: `indice` decide la traslazione,
 * e niente lo riscrive di rimando. Una scheda per volta, perche' una
 * testimonianza si legge, non si sfoglia.
 */
export function ReviewsCarousel({ reviews }: { reviews: Review[] }) {
  const [indice, setIndice] = useState(0);
  const [fermo, setFermo] = useState(false);

  // Con una sola recensione non c'e' niente da far girare.
  const gira = reviews.length > 1;

  useEffect(() => {
    if (!gira || fermo) return;
    // Chi ha chiesto meno animazioni al sistema non deve vedere niente
    // muoversi da solo.
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    const t = window.setInterval(
      () => setIndice((i) => (i + 1) % reviews.length),
      PAUSA_MS,
    );
    return () => window.clearInterval(t);
  }, [gira, fermo, reviews.length]);

  return (
    <div
      onMouseEnter={() => setFermo(true)}
      onMouseLeave={() => setFermo(false)}
      onFocusCapture={() => setFermo(true)}
      onBlurCapture={() => setFermo(false)}
    >
      <div className="overflow-hidden">
        <div
          className="flex transition-transform duration-500 ease-out"
          style={{ transform: `translateX(-${indice * 100}%)` }}
        >
          {reviews.map((r, i) => (
            <div
              key={r.id}
              className="w-full shrink-0 px-1"
              // Fuori schermo non si legge e non si tabula.
              aria-hidden={i !== indice}
            >
              <div className="card p-5 sm:p-6 max-w-2xl mx-auto flex flex-col gap-3">
                <Stelle n={r.rating} />
                {r.body && (
                  <p className="text-ink leading-relaxed">
                    &ldquo;{r.body}&rdquo;
                  </p>
                )}
                <p className="text-sm text-ink-soft">— {r.author_name}</p>
                {r.reply && (
                  <p className="text-sm text-ink-soft bg-pink-soft/30 rounded-lg p-3 leading-snug">
                    <strong className="text-ink">La mia risposta:</strong>{" "}
                    {r.reply}
                  </p>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {gira && (
        <div className="flex justify-center gap-2 mt-4">
          {reviews.map((r, i) => (
            <button
              key={r.id}
              type="button"
              onClick={() => setIndice(i)}
              aria-label={`Vai alla recensione ${i + 1} di ${reviews.length}`}
              aria-current={i === indice}
              className={
                "h-2 rounded-full transition-all " +
                (i === indice
                  ? "w-5 bg-lilac-deep"
                  : "w-2 bg-ink/20 hover:bg-ink/35")
              }
            />
          ))}
        </div>
      )}
    </div>
  );
}
