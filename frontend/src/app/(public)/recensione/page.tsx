"use client";

import Link from "next/link";
import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { PUBLIC_API_BASE } from "@/lib/api";

interface CanReview {
  order_id: number;
  buyer_name: string;
  already_reviewed: boolean;
}

function Stelle({
  value,
  onChange,
}: {
  value: number;
  onChange: (v: number) => void;
}) {
  return (
    <div className="flex gap-1" role="radiogroup" aria-label="Voto">
      {[1, 2, 3, 4, 5].map((n) => (
        <button
          key={n}
          type="button"
          role="radio"
          aria-checked={value === n}
          aria-label={`${n} ${n === 1 ? "stella" : "stelle"}`}
          onClick={() => onChange(n)}
          className={
            "text-3xl leading-none transition-transform hover:scale-110 " +
            (n <= value ? "text-star-deep" : "text-ink/20")
          }
        >
          ★
        </button>
      ))}
    </div>
  );
}

function RecensioneContent() {
  const params = useSearchParams();
  const orderId = params.get("order");
  const token = params.get("t");

  const [info, setInfo] = useState<CanReview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [rating, setRating] = useState(0);
  const [body, setBody] = useState("");
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);

  useEffect(() => {
    if (!orderId || !token) {
      setError("Link non valido: utilizzi quello ricevuto via email.");
      return;
    }
    fetch(
      `${PUBLIC_API_BASE}/api/reviews/can-review?order_id=${encodeURIComponent(orderId)}&token=${encodeURIComponent(token)}`,
      { cache: "no-store" },
    )
      .then(async (r) => {
        if (!r.ok) {
          const b = await r.json().catch(() => ({}));
          throw new Error(b.detail || "Link non valido o scaduto.");
        }
        return r.json();
      })
      .then(setInfo)
      .catch((err) => setError(err.message));
  }, [orderId, token]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (rating === 0) {
      setError("Scegli quante stelle dare.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const res = await fetch(`${PUBLIC_API_BASE}/api/reviews/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          order_id: Number(orderId),
          token,
          rating,
          body: body.trim() || undefined,
        }),
      });
      if (!res.ok) {
        const b = await res.json().catch(() => ({}));
        throw new Error(b.detail || `Errore ${res.status}`);
      }
      setDone(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  if (done || info?.already_reviewed) {
    return (
      <div className="max-w-xl mx-auto text-center py-12">
        <div className="text-5xl mb-4">⭐</div>
        <h1 className="display text-3xl text-ink mb-3">
          {done ? "Grazie!" : "Recensione già inviata per questo ordine"}
        </h1>
        <p className="text-ink-soft leading-relaxed mb-8">
          {done
            ? "Sarà verificata e pubblicata a breve. La ringraziamo del tempo dedicato."
            : "È prevista una sola recensione per ordine: la Sua è già stata registrata."}
        </p>
        <Link href="/" className="btn btn-primary">
          Torna al negozio
        </Link>
      </div>
    );
  }

  if (error && !info) {
    return (
      <div className="max-w-xl mx-auto text-center py-12">
        <p className="text-pink-deep mb-6">⚠ {error}</p>
        <Link href="/" className="btn btn-ghost">
          Torna al negozio
        </Link>
      </div>
    );
  }

  if (!info) return <p className="text-ink-soft">Caricamento…</p>;

  return (
    <article className="max-w-xl mx-auto">
      <h1 className="display text-3xl text-ink mb-2">Com&apos;è andata?</h1>
      <p className="text-ink-soft text-sm mb-6 leading-relaxed">
        Ordine #{info.order_id}. Sono sufficienti poche righe — e se preferisce non
        scrivere, anche solo le stelle vanno benissimo.
      </p>

      <form onSubmit={handleSubmit} className="card p-6 space-y-5">
        {error && <p className="text-pink-deep text-sm">⚠ {error}</p>}

        <div>
          <span className="text-xs font-bold uppercase tracking-wider text-ink-soft block mb-2">
            Il mio voto *
          </span>
          <Stelle value={rating} onChange={setRating} />
        </div>

        <label className="block">
          <span className="text-xs font-bold uppercase tracking-wider text-ink-soft">
            Desidera aggiungere qualcosa? (facoltativo)
          </span>
          <textarea
            rows={4}
            maxLength={2000}
            placeholder="Imballo, tempi, corrispondenza con la descrizione…"
            value={body}
            onChange={(e) => setBody(e.target.value)}
            className="input mt-1"
          />
        </label>

        <button
          type="submit"
          disabled={busy}
          className="btn btn-primary w-full text-base font-bold px-6 py-3"
        >
          {busy ? "Invio…" : "Invia la recensione"}
        </button>

        <p className="text-[11px] text-ink-soft text-center leading-snug">
          Sarà pubblicata sul sito con il Suo nome, previa verifica.
        </p>
      </form>
    </article>
  );
}

export default function RecensionePage() {
  return (
    <Suspense fallback={<p className="text-ink-soft">Caricamento…</p>}>
      <RecensioneContent />
    </Suspense>
  );
}
