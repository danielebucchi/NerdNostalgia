"use client";

import { useEffect, useState } from "react";
import { PUBLIC_API_BASE } from "@/lib/api";
import type { Category } from "@/lib/types";

/**
 * Campanella "Avvisami dei nuovi arrivi" nell'header: apre un dialog che
 * iscrive l'email agli avvisi per una categoria top-level (o tutte) via
 * POST /api/alerts/. Le categorie vengono fetchate lazy alla prima apertura.
 */
export function AlertBell({ variant = "desktop" }: { variant?: "desktop" | "mobile" }) {
  const [open, setOpen] = useState(false);
  const [categories, setCategories] = useState<Category[]>([]);
  const [email, setEmail] = useState("");
  const [categoryId, setCategoryId] = useState<string>("");
  const [website, setWebsite] = useState(""); // honeypot
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Categorie top-level, fetchate solo quando serve (prima apertura)
  useEffect(() => {
    if (!open || categories.length > 0) return;
    fetch(`${PUBLIC_API_BASE}/api/categories/`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d: { items: Category[] } | null) => {
        if (d) {
          setCategories(
            d.items
              .filter((c) => c.parent_id == null)
              .sort((a, b) => a.name.localeCompare(b.name, "it")),
          );
        }
      })
      .catch(() => {});
  }, [open, categories.length]);

  useEffect(() => {
    if (open) {
      setDone(false);
      setError(null);
    }
  }, [open]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const res = await fetch(`${PUBLIC_API_BASE}/api/alerts/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: email.trim(),
          category_id: categoryId ? Number(categoryId) : null,
          website: website.trim() || undefined,
        }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(
          typeof body?.detail === "string" ? body.detail : `Errore ${res.status}`,
        );
      }
      setDone(true);
      setEmail("");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      {variant === "mobile" ? (
        <button
          type="button"
          onClick={() => setOpen(true)}
          className="btn btn-ghost text-xs px-2.5 py-1.5"
          aria-label="Avvisami dei nuovi arrivi"
          title="Avvisami dei nuovi arrivi"
        >
          🔔
        </button>
      ) : (
        <button
          type="button"
          onClick={() => setOpen(true)}
          className="btn btn-ghost text-sm inline-flex items-center gap-1.5"
          title="Ricevi una mail quando arrivano nuovi articoli"
        >
          <span aria-hidden="true">🔔</span>
          <span>Avvisami</span>
        </button>
      )}

      {open && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-ink/40 backdrop-blur-sm"
          onClick={() => setOpen(false)}
        >
          <div
            className="card w-full max-w-md p-6"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-start justify-between gap-3 mb-3">
              <h3 className="display text-xl text-ink">🔔 Avvisami dei nuovi arrivi</h3>
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="w-8 h-8 rounded-full border-2 border-ink flex items-center justify-center text-ink hover:bg-pink shrink-0"
                aria-label="Chiudi"
              >
                ✕
              </button>
            </div>

            {done ? (
              <div className="text-center py-4">
                <div className="text-4xl mb-2">✨</div>
                <p className="display text-lg text-ink mb-1">Iscrizione fatta!</p>
                <p className="text-sm text-ink-soft">
                  Ti scrivo appena arriva qualcosa di nuovo. Puoi disiscriverti
                  dal link in fondo a ogni email.
                </p>
                <button
                  type="button"
                  onClick={() => setOpen(false)}
                  className="btn btn-primary mt-4 text-sm"
                >
                  Chiudi
                </button>
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="space-y-3">
                <p className="text-sm text-ink-soft">
                  Lascia la tua email: quando pubblico un nuovo articolo ti
                  arriva un avviso. Niente spam, solo nuovi arrivi.
                </p>
                {/* Honeypot nascosto */}
                <input
                  type="text"
                  name="hp_bell"
                  tabIndex={-1}
                  autoComplete="new-password"
                  aria-hidden="true"
                  style={{ display: "none" }}
                  value={website}
                  onChange={(e) => setWebsite(e.target.value)}
                />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="la-tua@email.it"
                  className="bell-input"
                  maxLength={255}
                />
                <select
                  value={categoryId}
                  onChange={(e) => setCategoryId(e.target.value)}
                  className="bell-input"
                  aria-label="Categoria di interesse"
                >
                  <option value="">Tutte le novità</option>
                  {categories.map((c) => (
                    <option key={c.id} value={c.id}>Solo {c.name}</option>
                  ))}
                </select>
                {error && (
                  <p className="text-pink-deep text-sm font-semibold">⚠ {error}</p>
                )}
                <button
                  type="submit"
                  disabled={busy}
                  className="btn btn-primary w-full text-sm"
                >
                  {busy ? "Invio…" : "Iscrivimi"}
                </button>
                <p className="text-[11px] text-ink-soft">
                  Usata solo per gli avvisi. Disiscrizione con un click.
                </p>
              </form>
            )}

            <style>{`
              .bell-input {
                display: block;
                width: 100%;
                padding: 0.55rem 0.85rem;
                border-radius: 14px;
                border: 1px solid rgba(61, 42, 92, 0.12);
                background: rgba(255, 255, 255, 0.85);
                color: #3d2a5c;
                font-family: "Manrope", sans-serif;
                font-size: 0.92rem;
                outline: none;
              }
              .bell-input:focus {
                border-color: var(--lilac-deep);
                box-shadow: 0 0 0 3px rgba(168, 144, 216, 0.25);
              }
            `}</style>
          </div>
        </div>
      )}
    </>
  );
}
