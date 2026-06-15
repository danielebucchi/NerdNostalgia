"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { adminApi } from "@/lib/admin-api";
import { Sortable } from "@/components/admin/Sortable";
import type { Article, ArticleCondition, ArticleStatus } from "@/lib/types";

interface PendingFile {
  id: string;
  file: File;
}

let pendingCounter = 0;
function makePending(file: File): PendingFile {
  pendingCounter += 1;
  return { id: `pf-${Date.now()}-${pendingCounter}`, file };
}

interface Props {
  initial?: Article;
  onSaved?: (saved: Article) => void;
}

interface FormState {
  title: string;
  description: string;
  price: string;
  currency: string;
  category: string;
  condition: ArticleCondition;
  status: ArticleStatus;
  quantity: string;
  sku: string;
  brand: string;
  model: string;
  weight_kg: string;
  dimensions_cm: string;
}

const empty: FormState = {
  title: "",
  description: "",
  price: "",
  currency: "EUR",
  category: "",
  condition: "USED",
  status: "DRAFT",
  quantity: "1",
  sku: "",
  brand: "",
  model: "",
  weight_kg: "",
  dimensions_cm: "",
};

function toForm(article: Article): FormState {
  return {
    title: article.title,
    description: article.description ?? "",
    price: String(article.price ?? ""),
    currency: article.currency ?? "EUR",
    category: article.category ?? "",
    condition: article.condition,
    status: article.status,
    quantity: String(article.quantity ?? 1),
    sku: article.sku ?? "",
    brand: article.brand ?? "",
    model: article.model ?? "",
    weight_kg: article.weight_kg ?? "",
    dimensions_cm: article.dimensions_cm ?? "",
  };
}

export function ArticleForm({ initial, onSaved }: Props) {
  const router = useRouter();
  const [state, setState] = useState<FormState>(initial ? toForm(initial) : empty);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pendingFiles, setPendingFiles] = useState<PendingFile[]>([]);
  const [uploadProgress, setUploadProgress] = useState<string | null>(null);

  const isEdit = Boolean(initial);

  function set<K extends keyof FormState>(key: K, value: FormState[K]) {
    setState((s) => ({ ...s, [key]: value }));
  }

  function addPendingFiles(files: FileList | null) {
    if (!files || files.length === 0) return;
    setPendingFiles((curr) => [...curr, ...Array.from(files).map(makePending)]);
  }

  function removePendingFile(id: string) {
    setPendingFiles((curr) => curr.filter((p) => p.id !== id));
  }

  function setPendingCover(id: string) {
    setPendingFiles((curr) => {
      const idx = curr.findIndex((p) => p.id === id);
      if (idx <= 0) return curr;
      const next = [...curr];
      const [item] = next.splice(idx, 1);
      next.unshift(item);
      return next;
    });
  }

  function movePendingFile(id: string, delta: -1 | 1) {
    setPendingFiles((curr) => {
      const idx = curr.findIndex((p) => p.id === id);
      const target = idx + delta;
      if (idx < 0 || target < 0 || target >= curr.length) return curr;
      const next = [...curr];
      [next[idx], next[target]] = [next[target], next[idx]];
      return next;
    });
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    setUploadProgress(null);
    try {
      const payload: Record<string, unknown> = {
        title: state.title.trim(),
        description: state.description.trim() || null,
        price: Number(state.price),
        currency: state.currency.trim().toUpperCase(),
        category: state.category.trim() || null,
        condition: state.condition,
        quantity: Number(state.quantity),
        sku: state.sku.trim() || null,
        brand: state.brand.trim() || null,
        model: state.model.trim() || null,
        weight_kg: state.weight_kg.trim() ? Number(state.weight_kg) : null,
        dimensions_cm: state.dimensions_cm.trim() || null,
      };
      if (!isEdit) {
        payload.user_id = 1; // admin id
        payload.status = state.status;
      } else {
        payload.status = state.status;
      }

      let result = isEdit
        ? await adminApi.patch<Article>(`/api/articles/${initial!.id}`, payload)
        : await adminApi.post<Article>("/api/articles/", payload);

      // Upload sequenziale di eventuali file selezionati (solo in create)
      if (!isEdit && pendingFiles.length > 0) {
        for (let i = 0; i < pendingFiles.length; i++) {
          const pending = pendingFiles[i];
          setUploadProgress(`Carico immagine ${i + 1} di ${pendingFiles.length}…`);
          const fd = new FormData();
          fd.append("file", pending.file);
          result = await adminApi.postForm<Article>(
            `/api/articles/${result.id}/upload-image`,
            fd,
          );
        }
        setPendingFiles([]);
        setUploadProgress(null);
      }

      if (onSaved) onSaved(result);
      else router.push(`/admin/articles/${result.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSubmitting(false);
      setUploadProgress(null);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <Row>
        <Field label="Titolo *" full>
          <input
            type="text"
            required
            value={state.title}
            onChange={(e) => set("title", e.target.value)}
            className="input"
          />
        </Field>
      </Row>

      <Row>
        <Field label="Descrizione" full>
          <textarea
            rows={4}
            value={state.description}
            onChange={(e) => set("description", e.target.value)}
            className="input"
          />
        </Field>
      </Row>

      <Row cols={3}>
        <Field label="Prezzo *">
          <input
            type="number"
            step="0.01"
            min="0"
            required
            value={state.price}
            onChange={(e) => set("price", e.target.value)}
            className="input"
          />
        </Field>
        <Field label="Valuta">
          <input
            type="text"
            maxLength={3}
            value={state.currency}
            onChange={(e) => set("currency", e.target.value)}
            className="input uppercase"
          />
        </Field>
        <Field label="Quantità">
          <input
            type="number"
            min="0"
            value={state.quantity}
            onChange={(e) => set("quantity", e.target.value)}
            className="input"
          />
        </Field>
      </Row>

      <Row cols={3}>
        <Field label="Categoria">
          <input
            type="text"
            value={state.category}
            onChange={(e) => set("category", e.target.value)}
            placeholder="videogames"
            className="input"
          />
        </Field>
        <Field label="Condizione">
          <select
            value={state.condition}
            onChange={(e) => set("condition", e.target.value as ArticleCondition)}
            className="input"
          >
            <option value="NEW">NEW</option>
            <option value="USED">USED</option>
            <option value="REFURBISHED">REFURBISHED</option>
            <option value="FOR_PARTS">FOR_PARTS</option>
          </select>
        </Field>
        <Field label="Stato">
          <select
            value={state.status}
            onChange={(e) => set("status", e.target.value as ArticleStatus)}
            className="input"
          >
            <option value="DRAFT">DRAFT</option>
            <option value="PUBLISHED">PUBLISHED</option>
            <option value="SOLD">SOLD</option>
            <option value="ARCHIVED">ARCHIVED</option>
          </select>
        </Field>
      </Row>

      <Row cols={3}>
        <Field label="Marca">
          <input
            type="text"
            value={state.brand}
            onChange={(e) => set("brand", e.target.value)}
            className="input"
          />
        </Field>
        <Field label="Modello">
          <input
            type="text"
            value={state.model}
            onChange={(e) => set("model", e.target.value)}
            className="input"
          />
        </Field>
        <Field label="SKU">
          <input
            type="text"
            value={state.sku}
            onChange={(e) => set("sku", e.target.value)}
            className="input"
          />
        </Field>
      </Row>

      <Row cols={2}>
        <Field label="Peso (kg)">
          <input
            type="number"
            step="0.01"
            min="0"
            value={state.weight_kg}
            onChange={(e) => set("weight_kg", e.target.value)}
            className="input"
          />
        </Field>
        <Field label="Dimensioni (cm)">
          <input
            type="text"
            placeholder="20x15x5"
            value={state.dimensions_cm}
            onChange={(e) => set("dimensions_cm", e.target.value)}
            className="input"
          />
        </Field>
      </Row>

      {!isEdit && (
        <div className="border-2 border-dashed border-ink/25 rounded-big p-4">
          <div className="flex items-center justify-between gap-3 mb-3">
            <div>
              <h3 className="display text-base text-ink">Immagini iniziali</h3>
              <p className="text-xs text-ink-soft">
                Verranno caricate subito dopo la creazione dell&apos;articolo.
                JPEG / PNG / WebP / GIF · max 5 MB per file.
              </p>
            </div>
            <label className="btn btn-ghost text-sm cursor-pointer flex-shrink-0">
              📷 Aggiungi
              <input
                type="file"
                accept="image/*"
                multiple
                hidden
                onChange={(e) => {
                  addPendingFiles(e.target.files);
                  e.target.value = "";
                }}
              />
            </label>
          </div>

          {pendingFiles.length === 0 ? (
            <p className="text-sm text-ink-soft">Nessun file selezionato.</p>
          ) : (
            <>
              {pendingFiles.length > 1 && (
                <p className="text-xs text-ink-soft mb-2">
                  Trascina per riordinare · ⭐ per copertina · ← → per spostare
                </p>
              )}
              <Sortable
                items={pendingFiles}
                getKey={(p) => p.id}
                onReorder={setPendingFiles}
                className="grid grid-cols-2 sm:grid-cols-4 gap-3"
                renderItem={(p, idx, { listeners, attributes, isDragging }) => {
                  const isCover = idx === 0;
                  const isLast = idx === pendingFiles.length - 1;
                  return (
                    <div className="flex flex-col gap-1">
                      <div
                        {...attributes}
                        {...listeners}
                        className={
                          "relative aspect-square rounded-xl overflow-hidden border-2 bg-cream cursor-grab active:cursor-grabbing " +
                          (isCover ? "border-pink-deep " : "border-ink/15 ") +
                          (isDragging ? "ring-4 ring-pink-deep ring-offset-2 ring-offset-white " : "")
                        }
                      >
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img
                          src={URL.createObjectURL(p.file)}
                          alt={p.file.name}
                          className="w-full h-full object-cover pointer-events-none"
                        />

                        {isCover && (
                          <span className="absolute top-1 left-1 chip chip-pink text-[10px] py-0.5 pointer-events-none">
                            ⭐ Copertina
                          </span>
                        )}

                        {!isCover && (
                          <button
                            type="button"
                            onPointerDown={(e) => e.stopPropagation()}
                            onClick={() => setPendingCover(p.id)}
                            className="absolute top-1 left-1 w-7 h-7 rounded-full bg-pink text-ink text-xs flex items-center justify-center border-2 border-ink"
                            aria-label="Imposta come copertina"
                            title="Imposta come copertina"
                          >
                            ⭐
                          </button>
                        )}

                        <button
                          type="button"
                          onPointerDown={(e) => e.stopPropagation()}
                          onClick={() => removePendingFile(p.id)}
                          className="absolute top-1 right-1 w-7 h-7 rounded-full bg-ink text-white text-xs flex items-center justify-center"
                          aria-label="Rimuovi"
                        >
                          ✕
                        </button>

                        <span className="absolute bottom-1 left-1 right-1 text-[10px] text-white bg-ink/70 rounded px-1 py-0.5 truncate text-center pointer-events-none">
                          {idx + 1} · {p.file.name}
                        </span>
                      </div>
                      <div className="flex gap-1">
                        <button
                          type="button"
                          onClick={() => movePendingFile(p.id, -1)}
                          disabled={isCover}
                          className="flex-1 h-7 rounded-lg border-2 border-ink bg-white text-ink text-sm font-bold disabled:opacity-30 disabled:cursor-not-allowed"
                          aria-label="Sposta a sinistra"
                          title="Sposta a sinistra"
                        >
                          ←
                        </button>
                        <button
                          type="button"
                          onClick={() => movePendingFile(p.id, 1)}
                          disabled={isLast}
                          className="flex-1 h-7 rounded-lg border-2 border-ink bg-white text-ink text-sm font-bold disabled:opacity-30 disabled:cursor-not-allowed"
                          aria-label="Sposta a destra"
                          title="Sposta a destra"
                        >
                          →
                        </button>
                      </div>
                    </div>
                  );
                }}
              />
            </>
          )}
        </div>
      )}

      {error && <p className="text-pink-deep font-semibold">⚠ {error}</p>}
      {uploadProgress && <p className="text-ink-soft text-sm">{uploadProgress}</p>}

      <div className="flex gap-3 pt-3">
        <button type="submit" className="btn btn-primary" disabled={submitting}>
          {submitting
            ? uploadProgress ?? "Salvataggio…"
            : isEdit
              ? "Salva modifiche"
              : pendingFiles.length > 0
                ? `Crea articolo (+${pendingFiles.length} ${pendingFiles.length === 1 ? "foto" : "foto"})`
                : "Crea articolo"}
        </button>
        <button
          type="button"
          className="btn btn-ghost"
          onClick={() => router.push("/admin/articles")}
        >
          Annulla
        </button>
      </div>

      <style>{`
        .input {
          display: block;
          width: 100%;
          padding: 0.55rem 0.8rem;
          border: 2px solid #3d2a5c;
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
    </form>
  );
}

function Row({ cols = 1, children }: { cols?: number; children: React.ReactNode }) {
  const grid =
    cols === 3 ? "sm:grid-cols-3" : cols === 2 ? "sm:grid-cols-2" : "";
  return <div className={`grid gap-3 ${grid}`}>{children}</div>;
}

function Field({
  label,
  full,
  children,
}: {
  label: string;
  full?: boolean;
  children: React.ReactNode;
}) {
  return (
    <label className={`block ${full ? "col-span-full" : ""}`}>
      <span className="text-xs font-bold uppercase tracking-wider text-ink-soft">{label}</span>
      <div className="mt-1">{children}</div>
    </label>
  );
}
