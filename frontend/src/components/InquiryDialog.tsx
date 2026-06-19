"use client";

import { useEffect, useState } from "react";
import { submitInquiry } from "@/lib/api";

interface InquiryDialogProps {
  open: boolean;
  onClose: () => void;
  articleId?: number;
  articleTitle?: string;
  /** Override del subject autogenerato (es. "Ce l'ho: <titolo>") */
  customSubject?: string;
  /** Titolo del dialog (default: "Chiedi info" se articleTitle, sennò "Contattami") */
  dialogTitle?: string;
  /** Sottotitolo opzionale sotto al titolo */
  subtitle?: React.ReactNode;
  /** Placeholder textarea */
  messagePlaceholder?: string;
}

export function InquiryDialog({
  open,
  onClose,
  articleId,
  articleTitle,
  customSubject,
  dialogTitle,
  subtitle,
  messagePlaceholder,
}: InquiryDialogProps) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [message, setMessage] = useState("");
  const [website, setWebsite] = useState(""); // honeypot — utenti veri non vedono il campo
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      setError(null);
      setDone(false);
    }
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const onEsc = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", onEsc);
    return () => {
      document.body.style.overflow = "";
      window.removeEventListener("keydown", onEsc);
    };
  }, [open, onClose]);

  if (!open) return null;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const subject =
        customSubject ?? (articleTitle ? `Info su: ${articleTitle}` : undefined);
      await submitInquiry({
        article_id: articleId ?? null,
        name: name.trim(),
        email: email.trim(),
        phone: phone.trim() || undefined,
        subject,
        message: message.trim(),
        website: website.trim() || undefined,
      });
      setDone(true);
      setName("");
      setEmail("");
      setPhone("");
      setMessage("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Errore sconosciuto");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-ink/40 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="card w-full max-w-lg p-6 sm:p-8 max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-4 mb-4">
          <div>
            <h2 className="display text-2xl text-ink">
              {dialogTitle ?? (articleTitle ? "Chiedi info" : "Contattami")}
            </h2>
            {(subtitle || articleTitle) && (
              <p className="text-sm text-ink-soft mt-1">
                {subtitle ?? <>su <strong>{articleTitle}</strong></>}
              </p>
            )}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="w-8 h-8 rounded-full border-2 border-ink flex items-center justify-center text-ink hover:bg-pink"
            aria-label="Chiudi"
          >
            ✕
          </button>
        </div>

        {done ? (
          <div className="text-center py-6">
            <div className="text-5xl mb-3">✨</div>
            <p className="display text-xl text-ink mb-2">Richiesta inviata!</p>
            <p className="text-ink-soft">Ti rispondo appena possibile. Grazie!</p>
            <button type="button" onClick={onClose} className="btn btn-primary mt-6">
              Chiudi
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-3">
            {/* Honeypot: nascosto visivamente E ai tab. Solo i bot lo vedono. */}
            <div
              aria-hidden="true"
              style={{ position: "absolute", left: "-10000px", top: "auto", width: 1, height: 1, overflow: "hidden" }}
            >
              <label>
                Sito web (lascia vuoto)
                <input
                  type="text"
                  tabIndex={-1}
                  autoComplete="off"
                  value={website}
                  onChange={(e) => setWebsite(e.target.value)}
                />
              </label>
            </div>

            <Field label="Nome" required>
              <input
                type="text"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="input"
                maxLength={255}
              />
            </Field>

            <div className="grid sm:grid-cols-2 gap-3">
              <Field label="Email" required>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="input"
                  maxLength={255}
                />
              </Field>
              <Field label="Telefono">
                <input
                  type="tel"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  className="input"
                  maxLength={50}
                />
              </Field>
            </div>

            <Field label="Messaggio" required>
              <textarea
                required
                rows={5}
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                className="input resize-none"
                minLength={5}
                maxLength={4000}
                placeholder={
                  messagePlaceholder ??
                  (articleTitle
                    ? "Sono interessato/a a questo articolo, vorrei sapere se..."
                    : "Scrivimi cosa cerchi o cosa hai da propormi...")
                }
              />
            </Field>

            {error && (
              <p className="text-pink-deep text-sm font-semibold">⚠ {error}</p>
            )}

            <div className="flex flex-wrap gap-3 pt-2">
              <button type="submit" className="btn btn-primary" disabled={submitting}>
                {submitting ? "Invio…" : "Invia richiesta"}
              </button>
              <button type="button" onClick={onClose} className="btn btn-ghost" disabled={submitting}>
                Annulla
              </button>
            </div>
            <p className="text-xs text-ink-soft pt-1">
              I tuoi dati vengono usati solo per risponderti.
            </p>
          </form>
        )}
      </div>

      <style>{`
        .input {
          display: block;
          width: 100%;
          padding: 0.55rem 0.8rem;
          border: 1px solid rgba(61, 42, 92, 0.12);
          border-radius: 12px;
          background: #fffaf3;
          color: #3d2a5c;
          font-family: "Manrope", sans-serif;
          font-size: 0.95rem;
          outline: none;
          transition: box-shadow 120ms ease, border-color 120ms ease;
        }
        .input:focus {
          box-shadow: 0 0 0 3px rgba(248, 168, 200, 0.45);
          border-color: #e879a8;
        }
      `}</style>
    </div>
  );
}

function Field({
  label,
  required,
  children,
}: {
  label: string;
  required?: boolean;
  children: React.ReactNode;
}) {
  return (
    <label className="block">
      <span className="text-xs font-bold uppercase tracking-wider text-ink-soft">
        {label}
        {required && <span className="text-pink-deep">*</span>}
      </span>
      <div className="mt-1">{children}</div>
    </label>
  );
}
