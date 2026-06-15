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
  const [dragIdx, setDragIdx] = useState<number | null>(null);
  const [overIdx, setOverIdx] = useState<number | null>(null);

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

  async function handleSetCover(url: string) {
    if (!article || article.images[0] === url) return;
    const reordered = [url, ...article.images.filter((u) => u !== url)];
    await persistImages(reordered);
  }

  async function handleMoveImage(index: number, delta: -1 | 1) {
    if (!article) return;
    const target = index + delta;
    if (target < 0 || target >= article.images.length) return;
    const next = [...article.images];
    [next[index], next[target]] = [next[target], next[index]];
    await persistImages(next);
  }

  async function persistImages(next: string[]) {
    setBusy(true);
    try {
      const a = await adminApi.patch<Article>(`/api/articles/${id}`, { images: next });
      setArticle(a);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  function handleDragStart(e: React.DragEvent<HTMLDivElement>, index: number) {
    setDragIdx(index);
    e.dataTransfer.effectAllowed = "move";
    e.dataTransfer.setData("text/plain", String(index));
  }

  function handleDragOver(e: React.DragEvent<HTMLDivElement>, index: number) {
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
    if (overIdx !== index) setOverIdx(index);
  }

  function handleDragLeave() {
    setOverIdx(null);
  }

  async function handleDrop(e: React.DragEvent<HTMLDivElement>, target: number) {
    e.preventDefault();
    const from = dragIdx ?? Number(e.dataTransfer.getData("text/plain"));
    setDragIdx(null);
    setOverIdx(null);
    if (!article || Number.isNaN(from) || from === target) return;
    const next = [...article.images];
    const [moved] = next.splice(from, 1);
    next.splice(target, 0, moved);
    await persistImages(next);
  }

  function handleDragEnd() {
    setDragIdx(null);
    setOverIdx(null);
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
            <div className="flex items-baseline justify-between mb-3">
              <h2 className="display text-lg text-ink">Immagini</h2>
              {article.images.length > 1 && (
                <p className="text-xs text-ink-soft">
                  Trascina per riordinare · ⭐ per copertina · ← → per spostare
                </p>
              )}
            </div>
            {article.images.length === 0 ? (
              <p className="text-ink-soft text-sm">Nessuna immagine caricata.</p>
            ) : (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
                {article.images.map((url, idx) => {
                  const isCover = idx === 0;
                  const isLast = idx === article.images.length - 1;
                  const isDragging = dragIdx === idx;
                  const isOver = overIdx === idx && dragIdx !== null && dragIdx !== idx;
                  return (
                    <div key={url} className="flex flex-col gap-1">
                      <div
                        draggable={!busy}
                        onDragStart={(e) => handleDragStart(e, idx)}
                        onDragOver={(e) => handleDragOver(e, idx)}
                        onDragLeave={handleDragLeave}
                        onDrop={(e) => handleDrop(e, idx)}
                        onDragEnd={handleDragEnd}
                        className={
                          "relative aspect-square rounded-xl overflow-hidden border-2 bg-cream cursor-grab active:cursor-grabbing transition-all " +
                          (isCover ? "border-pink-deep shadow-hover " : "border-ink/15 ") +
                          (isDragging ? "opacity-40 scale-95 " : "") +
                          (isOver ? "ring-4 ring-pink-deep ring-offset-2 ring-offset-white " : "")
                        }
                      >
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img src={url} alt="" className="w-full h-full object-cover" />

                        {isCover && (
                          <span className="absolute top-1 left-1 chip chip-pink text-[10px] py-0.5">
                            ⭐ Copertina
                          </span>
                        )}

                        {!isCover && (
                          <button
                            type="button"
                            onClick={() => handleSetCover(url)}
                            className="absolute top-1 left-1 w-7 h-7 rounded-full bg-pink text-ink text-xs flex items-center justify-center border-2 border-ink"
                            disabled={busy}
                            aria-label="Imposta come copertina"
                            title="Imposta come copertina"
                          >
                            ⭐
                          </button>
                        )}

                        <button
                          type="button"
                          onClick={() => handleRemoveImage(url)}
                          className="absolute top-1 right-1 w-7 h-7 rounded-full bg-ink text-white text-xs flex items-center justify-center"
                          disabled={busy}
                          aria-label="Rimuovi"
                        >
                          ✕
                        </button>

                        <span className="absolute bottom-1 right-1 text-[10px] text-white bg-ink/70 rounded px-1.5 py-0.5">
                          {idx + 1}
                        </span>
                      </div>
                      <div className="flex gap-1">
                        <button
                          type="button"
                          onClick={() => handleMoveImage(idx, -1)}
                          disabled={busy || isCover}
                          className="flex-1 h-7 rounded-lg border-2 border-ink bg-white text-ink text-sm font-bold disabled:opacity-30 disabled:cursor-not-allowed"
                          aria-label="Sposta a sinistra"
                          title="Sposta a sinistra"
                        >
                          ←
                        </button>
                        <button
                          type="button"
                          onClick={() => handleMoveImage(idx, 1)}
                          disabled={busy || isLast}
                          className="flex-1 h-7 rounded-lg border-2 border-ink bg-white text-ink text-sm font-bold disabled:opacity-30 disabled:cursor-not-allowed"
                          aria-label="Sposta a destra"
                          title="Sposta a destra"
                        >
                          →
                        </button>
                      </div>
                    </div>
                  );
                })}
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
