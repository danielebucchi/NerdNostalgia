"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { adminApi } from "@/lib/admin-api";
import type { Article, ArticleCondition, ArticleStatus } from "@/lib/types";

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

  const isEdit = Boolean(initial);

  function set<K extends keyof FormState>(key: K, value: FormState[K]) {
    setState((s) => ({ ...s, [key]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
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

      const result = isEdit
        ? await adminApi.patch<Article>(`/api/articles/${initial!.id}`, payload)
        : await adminApi.post<Article>("/api/articles/", payload);

      if (onSaved) onSaved(result);
      else router.push(`/admin/articles/${result.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSubmitting(false);
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

      {error && <p className="text-pink-deep font-semibold">⚠ {error}</p>}

      <div className="flex gap-3 pt-3">
        <button type="submit" className="btn btn-primary" disabled={submitting}>
          {submitting ? "Salvataggio…" : isEdit ? "Salva modifiche" : "Crea articolo"}
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
