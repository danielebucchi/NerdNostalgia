"use client";

/**
 * Fotocamera IN-APP via getUserMedia: su Android l'input capture apre
 * l'app fotocamera di sistema e il SO spesso killa la PWA in background
 * ("Memoria insufficiente"), perdendo lo scatto. Restando dentro la pagina
 * il problema sparisce, e in piu' si scatta in raffica senza rientrare.
 *
 * Chi chiama deve fare feature-detect (supportsInAppCamera) e tenere
 * l'input capture come fallback per browser senza getUserMedia.
 */
import { useCallback, useEffect, useRef, useState } from "react";

export function supportsInAppCamera(): boolean {
  return (
    typeof navigator !== "undefined" &&
    !!navigator.mediaDevices?.getUserMedia &&
    typeof window !== "undefined" &&
    window.isSecureContext // getUserMedia richiede HTTPS (o localhost)
  );
}

interface Props {
  open: boolean;
  onClose: () => void;
  /** Chiamata a ogni scatto (si puo' scattare in raffica). */
  onCapture: (file: File) => void;
}

export function CameraCapture({ open, onClose, onCapture }: Props) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [shots, setShots] = useState(0);
  const [flash, setFlash] = useState(false);

  const stop = useCallback(() => {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
  }, []);

  useEffect(() => {
    if (!open) return;
    setError(null);
    setShots(0);
    let cancelled = false;
    navigator.mediaDevices
      .getUserMedia({
        video: {
          facingMode: "environment",
          width: { ideal: 1920 },
          height: { ideal: 1920 },
        },
        audio: false,
      })
      .then((stream) => {
        if (cancelled) {
          stream.getTracks().forEach((t) => t.stop());
          return;
        }
        streamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
        }
      })
      .catch((err: unknown) => {
        setError(
          err instanceof DOMException && err.name === "NotAllowedError"
            ? "Permesso fotocamera negato. Abilitalo dalle impostazioni del sito."
            : "Fotocamera non disponibile su questo dispositivo.",
        );
      });
    return () => {
      cancelled = true;
      stop();
    };
  }, [open, stop]);

  if (!open) return null;

  function shoot() {
    const video = videoRef.current;
    if (!video || video.videoWidth === 0) return;
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext("2d")?.drawImage(video, 0, 0);
    canvas.toBlob(
      (blob) => {
        if (!blob) return;
        onCapture(
          new File([blob], `scatto-${Date.now()}.jpg`, { type: "image/jpeg" }),
        );
        setShots((n) => n + 1);
        // feedback flash
        setFlash(true);
        setTimeout(() => setFlash(false), 120);
      },
      "image/jpeg",
      0.9,
    );
  }

  function handleDone() {
    stop();
    onClose();
  }

  return (
    <div className="fixed inset-0 z-[70] bg-black flex flex-col">
      {/* Anteprima */}
      <div className="relative flex-1 min-h-0">
        {error ? (
          <div className="absolute inset-0 flex items-center justify-center p-8">
            <p className="text-white text-center text-sm">{error}</p>
          </div>
        ) : (
          // eslint-disable-next-line jsx-a11y/media-has-caption
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            className="absolute inset-0 w-full h-full object-contain"
          />
        )}
        {flash && <div className="absolute inset-0 bg-white/80" aria-hidden="true" />}
        {shots > 0 && (
          <span className="absolute top-4 left-4 bg-mint-deep text-white text-sm font-bold px-3 py-1 rounded-full">
            {shots} scatt{shots === 1 ? "o" : "i"} ✓
          </span>
        )}
        <button
          type="button"
          onClick={handleDone}
          className="absolute top-4 right-4 w-10 h-10 rounded-full bg-white/20 backdrop-blur text-white text-xl flex items-center justify-center"
          aria-label="Chiudi fotocamera"
        >
          ✕
        </button>
      </div>

      {/* Controlli */}
      <div
        className="flex items-center justify-center gap-8 py-5 bg-black"
        style={{ paddingBottom: "calc(1.25rem + env(safe-area-inset-bottom))" }}
      >
        <button
          type="button"
          onClick={shoot}
          disabled={!!error}
          className="w-18 h-18 rounded-full border-4 border-white p-1 disabled:opacity-40"
          aria-label="Scatta foto"
          style={{ width: 72, height: 72 }}
        >
          <span className="block w-full h-full rounded-full bg-white active:bg-white/70 transition-colors" />
        </button>
        <button
          type="button"
          onClick={handleDone}
          className="absolute right-6 text-white font-bold text-sm bg-white/15 backdrop-blur px-4 py-2 rounded-full"
        >
          {shots > 0 ? "✓ Fatto" : "Annulla"}
        </button>
      </div>
    </div>
  );
}
