"use client";

import { use, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { AdminShell } from "@/components/admin/AdminShell";
import { ArticleForm } from "@/components/admin/ArticleForm";
import { adminApi } from "@/lib/admin-api";
import type { Article } from "@/lib/types";

interface PageProps {
  params: Promise<{ id: string }>;
}

export default function AdminArticleEditPage({ params }: PageProps) {
  const { id } = use(params);
  const router = useRouter();
  const [article, setArticle] = useState<Article | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [uploading, setUploading] = useState(false);

  async function reload() {
    setLoading(true);
    try {
      const a = await adminApi.get<Article>(`/api/articles/${id}`);
      setArticle(a);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  async function doAction(action: "publish" | "sell" | "archive") {
    setBusy(true);
    try {
      const a = await adminApi.post<Article>(`/api/articles/${id}/${action}`);
      setArticle(a);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete() {
    if (!confirm("Eliminare definitivamente l'articolo e le sue immagini?")) return;
    setBusy(true);
    try {
      await adminApi.delete(`/api/articles/${id}`);
      router.push("/admin/articles");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setBusy(false);
    }
  }

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const a = await adminApi.postForm<Article>(`/api/articles/${id}/upload-image`, fd);
      setArticle(a);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  }

  async function handleRemoveImage(url: string) {
    if (!confirm("Rimuovere questa immagine?")) return;
    setBusy(true);
    try {
      const a = await adminApi.delete<Article>(
        `/api/articles/${id}/images?url=${encodeURIComponent(url)}`,
      );
      setArticle(a);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <AdminShell>
      <Link href="/admin/articles" className="btn btn-ghost text-sm mb-6">
        ← Articoli
      </Link>

      {loading && <p className="text-ink-soft">Caricamento…</p>}
      {error && <p className="text-pink-deep mb-4">⚠ {error}</p>}

      {article && (
        <>
          <div className="flex items-start justify-between gap-4 mb-6">
            <div>
              <h1 className="display text-3xl text-ink">{article.title}</h1>
              <p className="text-ink-soft text-sm">#{article.id} · {article.status}</p>
            </div>
            <a href={`/articles/${article.id}`} target="_blank" rel="noreferrer" className="btn btn-ghost text-sm">
              Vista pubblica ↗
            </a>
          </div>

          {/* Lifecycle */}
          <div className="card p-5 mb-6">
            <h2 className="display text-lg text-ink mb-3">Lifecycle</h2>
            <div className="flex gap-2 flex-wrap">
              <button
                type="button"
                className="btn btn-primary text-sm"
                onClick={() => doAction("publish")}
                disabled={busy || article.status === "PUBLISHED"}
              >
                Pubblica
              </button>
              <button
                type="button"
                className="btn btn-ghost text-sm"
                onClick={() => doAction("sell")}
                disabled={busy || article.status === "SOLD"}
              >
                Marca venduto
              </button>
              <button
                type="button"
                className="btn btn-ghost text-sm"
                onClick={() => doAction("archive")}
                disabled={busy || article.status === "ARCHIVED"}
              >
                Archivia
              </button>
              <button
                type="button"
                className="btn btn-ghost text-sm ml-auto"
                onClick={handleDelete}
                disabled={busy}
              >
                🗑 Elimina
              </button>
            </div>
          </div>

          {/* Images */}
          <div className="card p-5 mb-6">
            <h2 className="display text-lg text-ink mb-3">Immagini</h2>
            {article.images.length === 0 ? (
              <p className="text-ink-soft text-sm">Nessuna immagine caricata.</p>
            ) : (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
                {article.images.map((url) => (
                  <div key={url} className="relative aspect-square rounded-xl overflow-hidden border-2 border-ink/15 bg-cream">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img src={url} alt="" className="w-full h-full object-cover" />
                    <button
                      type="button"
                      onClick={() => handleRemoveImage(url)}
                      className="absolute top-1 right-1 w-7 h-7 rounded-full bg-ink text-white text-xs flex items-center justify-center"
                      disabled={busy}
                      aria-label="Rimuovi"
                    >
                      ✕
                    </button>
                  </div>
                ))}
              </div>
            )}
            <label className="btn btn-ghost text-sm inline-flex cursor-pointer">
              {uploading ? "Caricamento…" : "📷 Carica immagine"}
              <input type="file" accept="image/*" hidden onChange={handleUpload} disabled={uploading} />
            </label>
            <p className="text-xs text-ink-soft mt-2">
              Formati: JPEG / PNG / WebP / GIF. Dimensione max 5 MB.
            </p>
          </div>

          {/* Edit form */}
          <div className="card p-5">
            <h2 className="display text-lg text-ink mb-3">Dati articolo</h2>
            <ArticleForm initial={article} onSaved={(saved) => setArticle(saved)} />
          </div>
        </>
      )}
    </AdminShell>
  );
}
