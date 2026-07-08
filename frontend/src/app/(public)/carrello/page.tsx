"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { PurchaseDialog } from "@/components/PurchaseDialog";
import { formatPrice, getArticle } from "@/lib/api";
import { aggregateShipping, cartSubtotal, useCart } from "@/lib/cart";
import { useSettings } from "@/lib/settings-context";
import type { Article } from "@/lib/types";

export default function CartPage() {
  const { paymentsEnabled } = useSettings();
  // Feature flag: se i pagamenti sono off, /carrello mostra solo un avviso.
  if (!paymentsEnabled) {
    return (
      <article>
        <Link href="/" className="btn btn-ghost text-sm mb-6">
          ← Catalogo
        </Link>
        <div className="card p-8 text-center max-w-xl mx-auto">
          <h1 className="display text-2xl text-ink mb-3">
            🛒 Carrello non disponibile
          </h1>
          <p className="text-ink-soft mb-6">
            Gli acquisti dal sito sono temporaneamente disabilitati. Per il
            momento contattami direttamente per qualsiasi articolo.
          </p>
          <Link href="/contatti" className="btn btn-primary text-sm inline-flex">
            Scrivimi
          </Link>
        </div>
      </article>
    );
  }
  return <CartContent />;
}

function CartContent() {
  const { items, remove, clear, hydrated } = useCart();
  const { paypalMe, handExchangeCapPrefixes, handExchangeCities } = useSettings();
  const paypalConfigured = paypalMe.length > 0;
  const capZonesLabel = handExchangeCapPrefixes.map((p) => `${p}xxx`).join(" / ");
  const [articles, setArticles] = useState<Article[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);

  useEffect(() => {
    if (!hydrated) return;
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const fetched = await Promise.all(
          items.map((it) =>
            getArticle(it.article_id).catch(() => null),
          ),
        );
        if (cancelled) return;
        const valid = fetched.filter((a): a is Article => !!a);

        // Auto-cleanup: rimuovi dal carrello i 404 (articoli cancellati o
        // diventati non PUBLISHED) - manteniamo l'UI sincronizzata
        const validIds = new Set(valid.map((a) => a.id));
        items
          .filter((it) => !validIds.has(it.article_id))
          .forEach((it) => remove(it.article_id));

        setArticles(valid.filter((a) => a.status === "PUBLISHED"));
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : String(err));
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hydrated, items.length]);

  const subtotal = cartSubtotal(articles);
  const shippingTotal = aggregateShipping(articles);
  const grandTotal = subtotal + shippingTotal;
  const currency = articles[0]?.currency || "EUR";

  return (
    <article>
      <Link href="/" className="btn btn-ghost text-sm mb-6">
        ← Catalogo
      </Link>

      <h1 className="display text-3xl sm:text-4xl text-ink mb-6">
        🛒 Il tuo carrello
      </h1>

      {!hydrated || loading ? (
        <p className="text-ink-soft">Caricamento…</p>
      ) : error ? (
        <p className="text-pink-deep">⚠ {error}</p>
      ) : articles.length === 0 ? (
        <div className="card p-8 text-center">
          <p className="text-ink-soft mb-4">
            Il carrello è vuoto. Aggiungi articoli dal catalogo per acquistarli
            insieme con spedizione unica.
          </p>
          <Link href="/" className="btn btn-primary text-sm inline-flex">
            Sfoglia il catalogo
          </Link>
        </div>
      ) : (
        <div className="grid lg:grid-cols-3 gap-6">
          {/* Lista articoli */}
          <div className="lg:col-span-2 space-y-3">
            {articles.map((a) => {
              const cover = a.images?.[0];
              return (
                <div
                  key={a.id}
                  className="card p-4 flex items-center gap-4"
                >
                  <Link
                    href={`/articles/${a.id}`}
                    className="flex-shrink-0 w-20 h-20 sm:w-24 sm:h-24 rounded-xl overflow-hidden bg-ink/5"
                  >
                    {cover ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img
                        src={cover}
                        alt={a.title}
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-ink-soft text-2xl">
                        🎮
                      </div>
                    )}
                  </Link>
                  <div className="flex-1 min-w-0">
                    <Link
                      href={`/articles/${a.id}`}
                      className="text-ink font-semibold hover:text-pink-deep transition-colors line-clamp-2"
                    >
                      {a.title}
                    </Link>
                    <p className="text-ink-soft text-sm mt-1">
                      {formatPrice(a)}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => remove(a.id)}
                    aria-label="Rimuovi dal carrello"
                    className="flex-shrink-0 w-9 h-9 rounded-full bg-ink/10 hover:bg-pink-deep hover:text-white text-ink flex items-center justify-center font-bold transition-colors"
                  >
                    ✕
                  </button>
                </div>
              );
            })}

            <button
              type="button"
              onClick={clear}
              className="btn btn-ghost text-sm mt-4"
            >
              Svuota carrello
            </button>
          </div>

          {/* Riepilogo + CTA */}
          <aside>
            <div className="card p-5 sticky top-4">
              <h2 className="display text-xl text-ink mb-4">Riepilogo</h2>
              <dl className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <dt className="text-ink-soft">
                    Subtotale ({articles.length}{" "}
                    {articles.length === 1 ? "articolo" : "articoli"})
                  </dt>
                  <dd className="tabular-nums">€ {subtotal.toFixed(2)}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-ink-soft">
                    Spedizione{" "}
                    <span
                      title="Spedizione aggregata: prendiamo il valore più alto tra gli articoli (il pacco unico ottimizza i costi)."
                      className="text-[10px] underline decoration-dotted cursor-help"
                    >
                      come si calcola?
                    </span>
                  </dt>
                  <dd className="tabular-nums">€ {shippingTotal.toFixed(2)}</dd>
                </div>
                <div className="flex justify-between font-bold text-lg text-pink-deep pt-2 border-t border-ink/10">
                  <dt>Totale</dt>
                  <dd className="tabular-nums">
                    € {grandTotal.toFixed(2)} {currency}
                  </dd>
                </div>
              </dl>

              {paypalConfigured ? (
                <button
                  type="button"
                  onClick={() => setDialogOpen(true)}
                  className="btn btn-paypal w-full mt-5 text-base font-bold px-6 py-3.5 inline-flex items-center justify-center gap-2"
                >
                  <span>Procedi al pagamento</span>
                  <span aria-hidden="true">→</span>
                </button>
              ) : (
                <p className="text-xs text-ink-soft mt-5 text-center">
                  PayPal non configurato. Scrivimi per concordare il pagamento.
                </p>
              )}

              <p className="text-xs text-ink-soft mt-3 leading-snug">
                Conferma indirizzo + dati, ti scrivo per finalizzare la
                spedizione. Pagamento via PayPal.
              </p>
              {articles.length > 0 && (
                <div className="text-[11px] rounded-lg bg-mint-deep/12 text-mint-deep px-3 py-2 mt-3 leading-snug ring-1 ring-mint-deep/30">
                  🤝 <strong>Consegna a mano gratuita</strong> a {handExchangeCities}
                  {" "}(CAP {capZonesLabel}). Scegli l&apos;opzione al checkout per
                  azzerare la spedizione.
                </div>
              )}
              {paypalConfigured && articles.length > 0 && (
                <p className="text-[11px] text-[#003087] bg-[#ffc439]/20 rounded-lg px-3 py-2 mt-2 leading-snug">
                  💡 Su PayPal seleziona{" "}
                  <strong>&quot;A un amico o familiare&quot;</strong> per evitare le
                  commissioni.
                </p>
              )}
            </div>
          </aside>
        </div>
      )}

      <PurchaseDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        articles={articles}
        shippingTotal={shippingTotal}
        onSuccess={() => clear()}
      />
    </article>
  );
}
