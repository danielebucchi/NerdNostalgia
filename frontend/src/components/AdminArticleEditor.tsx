"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ArticleForm } from "@/components/admin/ArticleForm";
import { ImageGalleryEditor } from "@/components/admin/ImageGalleryEditor";
import { adminApi } from "@/lib/admin-api";
import { useIsAdmin } from "@/lib/auth-store";
import type { Article } from "@/lib/types";

/* Modifica al volo dalla pagina pubblica dell'articolo.
 *
 * Visibile solo con una sessione admin nel browser: l'admin che gira il
 * sito e vede un refuso, un prezzo da ritoccare o una foto storta lo
 * sistema li', senza cercare l'articolo nel pannello. Foto, stato e dati
 * stanno qui; i marketplace (Vinted, eBay, CardTrader) restano nel
 * pannello, a un link di distanza.
 *
 * L'articolo si ricarica dalle API admin all'apertura: la versione
 * pubblica non porta i campi interni (costo, note) che il form salva. */

const LIFECYCLE: { action: "publish" | "sell" | "archive"; label: string; status: string }[] = [
  { action: "publish", label: "Pubblica", status: "PUBLISHED" },
  { action: "sell", label: "Marca venduto", status: "SOLD" },
  { action: "archive", label: "Archivia", status: "ARCHIVED" },
];

export function AdminArticleEditor({ articleId }: { articleId: number }) {
  const isAdmin = useIsAdmin();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [article, setArticle] = useState<Article | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);
  // Qualcosa e' cambiato: alla chiusura la pagina si ridisegna dal server.
  const [dirty, setDirty] = useState(false);

  useEffect(() => {
    if (!open) return;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = "";
    };
  }, [open]);

  if (!isAdmin) return null;

  async function openEditor() {
    setOpen(true);
    setArticle(null);
    setError(null);
    setSaved(false);
    try {
      setArticle(await adminApi.get<Article>(`/api/articles/${articleId}`));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  function close() {
    setOpen(false);
    if (dirty) {
      setDirty(false);
      router.refresh();
    }
  }

  function updated(a: Article) {
    setArticle(a);
    setDirty(true);
  }

  async function lifecycle(action: "publish" | "sell" | "archive") {
    setBusy(true);
    setError(null);
    try {
      updated(await adminApi.post<Article>(`/api/articles/${articleId}/${action}`));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <button
        type="button"
        onClick={openEditor}
        className="fixed bottom-24 sm:bottom-6 left-4 z-40 btn btn-primary shadow-xl text-sm"
      >
        ✏️ Modifica articolo
      </button>

      {open && (
        // Niente chiusura cliccando fuori: un tocco sbagliato buttava le
        // modifiche non ancora salvate.
        <div className="fixed inset-0 z-50 flex items-start sm:items-center justify-center p-2 sm:p-4 bg-ink/40 backdrop-blur-sm">
          <div className="card w-full max-w-3xl p-4 sm:p-6 max-h-[95vh] overflow-y-auto">
            <div className="flex items-start justify-between gap-4 mb-4">
              <div>
                <h2 className="display text-2xl text-ink">Modifica articolo</h2>
                {article && (
                  <p className="text-sm text-ink-soft">
                    #{article.id} · {article.status}
                  </p>
                )}
              </div>
              <div className="flex items-center gap-2">
                <a
                  href={`/admin/articles/${articleId}`}
                  className="btn btn-ghost text-xs"
                  title="Marketplace, CardTrader ed eliminazione sono nel pannello"
                >
                  Pannello admin ↗
                </a>
                <button
                  type="button"
                  onClick={close}
                  className="w-9 h-9 rounded-full bg-ink text-white"
                  aria-label="Chiudi"
                >
                  ✕
                </button>
              </div>
            </div>

            {error && <p className="text-pink-deep font-semibold mb-4">⚠ {error}</p>}
            {!article && !error && <p className="text-ink-soft">Caricamento…</p>}

            {article && (
              <div className="space-y-6">
                <div className="flex gap-2 flex-wrap">
                  {LIFECYCLE.map(({ action, label, status }) => (
                    <button
                      key={action}
                      type="button"
                      className="btn btn-ghost text-sm"
                      onClick={() => lifecycle(action)}
                      disabled={busy || article.status === status}
                    >
                      {label}
                    </button>
                  ))}
                </div>

                <ImageGalleryEditor
                  scope="articles"
                  entityId={article.id}
                  images={article.images}
                  onChange={(images) => updated({ ...article, images })}
                  compact
                />

                {saved && <p className="text-sm font-semibold text-ink">✓ Modifiche salvate</p>}
                <ArticleForm
                  // Lo stato e' nel salvataggio del form: cambiato dai pulsanti
                  // sopra, il form riparte da li' (se no "Salva" lo riporterebbe
                  // indietro). Le foto no, e cambiarle non tocca i campi in corso.
                  key={article.status}
                  initial={article}
                  onSaved={(a) => {
                    updated(a);
                    setSaved(true);
                  }}
                  onCancel={close}
                />
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
}
