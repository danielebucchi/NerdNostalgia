"use client";

import { useRef, useState } from "react";
import { CameraCapture, supportsInAppCamera } from "@/components/admin/CameraCapture";
import { adminApi, ApiError } from "@/lib/admin-api";
import { downloadUrl, saveBlob, shareImageUrl } from "@/lib/download";
import { compressImage } from "@/lib/image-compress";
import { uploadWithRetry } from "@/lib/upload-retry";

interface Props {
  /** Nome dell'endpoint di scope: "inventory" | "articles" */
  scope: "inventory" | "articles";
  /** ID dell'entita' (item o article). L'entita' DEVE gia' esistere. */
  entityId: number;
  /** URL immagini correnti. La cover e' l'index 0. */
  images: string[];
  /** Notifica il parent dopo add/remove/reorder. */
  onChange: (images: string[]) => void;
  /** Limite massimo (default 12, allineato al backend). */
  maxImages?: number;
  /** Se true, riduce spaziatura e mostra header piu' piccolo. */
  compact?: boolean;
}

// Deriva la thumb .thumb.webp per gli URL interni; se e' esterno o non e'
// .webp, ritorna l'URL originale.
function thumbUrlFor(url: string): string {
  if (url.endsWith(".webp") && !url.endsWith(".thumb.webp")) {
    return url.slice(0, -".webp".length) + ".thumb.webp";
  }
  return url;
}

export function ImageGalleryEditor({
  scope,
  entityId,
  images,
  onChange,
  maxImages = 12,
  compact = false,
}: Props) {
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [cameraOpen, setCameraOpen] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const base = `/api/${scope}/${entityId}`;
  const canAdd = images.length < maxImages && !busy;

  function reportError(err: unknown) {
    if (err instanceof ApiError) setError(err.message);
    else if (err instanceof Error) setError(err.message);
    else setError("Errore sconosciuto");
  }

  async function handleFiles(files: FileList | File[] | null) {
    if (!files || files.length === 0) return;
    setBusy(true);
    setError(null);
    try {
      const toUpload = Array.from(files).slice(0, maxImages - images.length);
      let latest = images;
      for (let i = 0; i < toUpload.length; i++) {
        // Comprime lato client: le foto da fotocamera superano il limite
        // 5MB del backend (e su iPhone escono in HEIC non accettato).
        setProgress(`Preparo ${i + 1} di ${toUpload.length}…`);
        const prepared = await compressImage(toUpload[i]);
        setProgress(`Carico ${i + 1} di ${toUpload.length}…`);
        const fd = new FormData();
        fd.append("file", prepared);
        const item = await uploadWithRetry<{ images: string[] }>(
          `${base}/upload-image`,
          fd,
        );
        latest = item.images ?? latest;
        onChange(latest);
      }
    } catch (err) {
      reportError(err);
    } finally {
      setBusy(false);
      setProgress(null);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  async function handleRemove(url: string) {
    if (!confirm("Rimuovere questa foto?")) return;
    setBusy(true);
    setError(null);
    try {
      const item = await adminApi.delete<{ images: string[] }>(
        `${base}/images?url=${encodeURIComponent(url)}`,
      );
      onChange(item.images ?? images.filter((u) => u !== url));
    } catch (err) {
      reportError(err);
    } finally {
      setBusy(false);
    }
  }

  async function handleReorder(next: string[]) {
    // Optimistic update: il parent vede subito il nuovo ordine.
    const previous = images;
    onChange(next);
    setBusy(true);
    setError(null);
    try {
      const item = await adminApi.put<{ images: string[] }>(
        `${base}/images`,
        { images: next },
      );
      onChange(item.images ?? next);
    } catch (err) {
      onChange(previous);
      reportError(err);
    } finally {
      setBusy(false);
    }
  }

  function move(index: number, delta: -1 | 1) {
    const target = index + delta;
    if (target < 0 || target >= images.length) return;
    const next = [...images];
    [next[index], next[target]] = [next[target], next[index]];
    handleReorder(next);
  }

  function setCover(index: number) {
    if (index === 0) return;
    const next = [...images];
    const [picked] = next.splice(index, 1);
    next.unshift(picked);
    handleReorder(next);
  }

  // Riporta le foto sul telefono (per Vinted/eBay: dopo l'upload gli
  // originali vivono solo sul server).
  async function downloadPhoto(url: string, index: number) {
    try {
      const name = `foto-${index + 1}.webp`;
      // Su mobile lo share sheet e' piu' utile del download (salva in
      // galleria / manda dritto a Vinted); fallback: download classico.
      const shared = await shareImageUrl(url, name);
      if (!shared) await downloadUrl(url, name);
    } catch (err) {
      reportError(err);
    }
  }

  async function downloadAllZip() {
    setBusy(true);
    setError(null);
    try {
      const blob = await adminApi.getBlob(`${base}/images.zip`);
      saveBlob(blob, `${scope}-${entityId}-foto.zip`);
    } catch (err) {
      reportError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className={compact ? "space-y-2" : "space-y-3"}>
      {!compact && (
        <div className="flex items-baseline justify-between">
          <h3 className="text-sm font-bold text-ink">Foto</h3>
          <span className="text-xs text-ink-soft">
            {images.length}/{maxImages}
          </span>
        </div>
      )}

      {images.length === 0 ? (
        <p className="text-xs text-ink-soft italic">
          Nessuna foto. Aggiungine almeno una per riconoscere subito l&apos;articolo.
        </p>
      ) : (
        <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 gap-2">
          {images.map((url, i) => (
            <div
              key={url}
              className="relative group aspect-square rounded-lg overflow-hidden bg-ink/5 ring-1 ring-ink/10"
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={thumbUrlFor(url)}
                alt={`Foto ${i + 1}`}
                loading="lazy"
                className="w-full h-full object-cover"
              />
              {i === 0 && (
                <span className="absolute top-1 left-1 bg-ink text-cream text-[10px] font-bold px-1.5 py-0.5 rounded">
                  COVER
                </span>
              )}
              {/* Su touch non c'e' hover: la barra azioni resta visibile */}
              <div className="absolute inset-x-0 bottom-0 bg-ink/70 opacity-100 sm:opacity-0 sm:group-hover:opacity-100 transition-opacity flex justify-between text-cream text-xs">
                <button
                  type="button"
                  disabled={busy || i === 0}
                  onClick={() => move(i, -1)}
                  className="px-1.5 py-0.5 disabled:opacity-30"
                  title="Sposta a sinistra"
                >
                  ←
                </button>
                <button
                  type="button"
                  disabled={busy || i === 0}
                  onClick={() => setCover(i)}
                  className="px-1.5 py-0.5 disabled:opacity-30"
                  title="Imposta come cover"
                >
                  ⭐
                </button>
                <button
                  type="button"
                  disabled={busy || i === images.length - 1}
                  onClick={() => move(i, 1)}
                  className="px-1.5 py-0.5 disabled:opacity-30"
                  title="Sposta a destra"
                >
                  →
                </button>
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => downloadPhoto(url, i)}
                  className="px-1.5 py-0.5 disabled:opacity-30"
                  title="Scarica / condividi la foto"
                >
                  ⬇
                </button>
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => handleRemove(url)}
                  className="px-1.5 py-0.5 text-pink-deep hover:text-pink-deep/70 disabled:opacity-30"
                  title="Rimuovi"
                >
                  ✕
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="flex items-center gap-2 pt-1 flex-wrap">
        <label
          className={`btn btn-ghost text-xs cursor-pointer ${
            !canAdd ? "opacity-50 cursor-not-allowed pointer-events-none" : ""
          }`}
        >
          📷 Aggiungi foto
          <input
            ref={inputRef}
            type="file"
            accept="image/*"
            multiple
            className="sr-only"
            onChange={(e) => handleFiles(e.target.files)}
            disabled={!canAdd}
          />
        </label>
        {/* Scatto: fotocamera IN-APP (getUserMedia) dove supportata — su
            Android l'app fotocamera esterna fa killare la PWA in background
            ("Memoria insufficiente") perdendo lo scatto. Fallback: input
            capture per i browser senza getUserMedia. */}
        {supportsInAppCamera() ? (
          <button
            type="button"
            onClick={() => setCameraOpen(true)}
            disabled={!canAdd}
            className="btn btn-ghost text-xs disabled:opacity-50"
          >
            📸 Scatta
          </button>
        ) : (
          <label
            className={`btn btn-ghost text-xs cursor-pointer ${
              !canAdd ? "opacity-50 cursor-not-allowed pointer-events-none" : ""
            }`}
          >
            📸 Scatta
            <input
              type="file"
              accept="image/*"
              capture="environment"
              className="sr-only"
              onChange={(e) => handleFiles(e.target.files)}
              disabled={!canAdd}
            />
          </label>
        )}
        {images.length > 0 && (
          <button
            type="button"
            onClick={downloadAllZip}
            disabled={busy}
            className="btn btn-ghost text-xs disabled:opacity-50"
            title="Scarica tutte le foto in uno zip"
          >
            ⬇ Tutte
          </button>
        )}
        {progress && <span className="text-xs text-ink-soft">{progress}</span>}
        {images.length >= maxImages && !progress && (
          <span className="text-xs text-ink-soft">Limite raggiunto</span>
        )}
      </div>

      {error && (
        <p className="text-xs text-pink-deep font-semibold">⚠ {error}</p>
      )}

      <CameraCapture
        open={cameraOpen}
        onClose={() => setCameraOpen(false)}
        onCapture={(file) => handleFiles([file])}
      />
    </div>
  );
}
