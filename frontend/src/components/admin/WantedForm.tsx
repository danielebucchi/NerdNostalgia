"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { adminApi } from "@/lib/admin-api";
import type { ArticleCondition, WantedItem, WantedStatus } from "@/lib/types";

interface Props {
  initial?: WantedItem;
  onSaved?: (saved: WantedItem) => void;
}

interface FormState {
  title: string;
  description: string;
  category: string;
  brand: string;
  model: string;
  preferred_condition: "" | ArticleCondition;
  max_price: string;
  currency: string;
  notes: string;
  priority: string;
  status: WantedStatus;
}

const empty: FormState = {
  title: "",
  description: "",
  category: "",
  brand: "",
  model: "",
  preferred_condition: "",
  max_price: "",
  currency: "EUR",
  notes: "",
  priority: "10",
  status: "ACTIVE",
};

function toForm(item: WantedItem): FormState {
  return {
    title: item.title,
    description: item.description ?? "",
    category: item.category ?? "",
    brand: item.brand ?? "",
    model: item.model ?? "",
    preferred_condition: item.preferred_condition ?? "",
    max_price: item.max_price ?? "",
    currency: item.currency ?? "EUR",
    notes: item.notes ?? "",
    priority: String(item.priority ?? 0),
    status: item.status,
  };
}

export function WantedForm({ initial, onSaved }: Props) {
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
        category: state.category.trim() || null,
        brand: state.brand.trim() || null,
        model: state.model.trim() || null,
        preferred_condition: state.preferred_condition || null,
        max_price: state.max_price.trim() ? Number(state.max_price) : null,
        currency: state.currency.trim().toUpperCase(),
        notes: state.notes.trim() || null,
        priority: Number(state.priority),
        status: state.status,
      };

      const result = isEdit
        ? await adminApi.patch<WantedItem>(`/api/wanted/${initial!.id}`, payload)
        : await adminApi.post<WantedItem>("/api/wanted/", payload);

      if (onSaved) onSaved(result);
      else router.push(`/admin/wanted/${result.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <Field label="Titolo *">
        <input
          type="text"
          required
          value={state.title}
          onChange={(e) => set("title", e.target.value)}
          placeholder="Cerco Game Boy Advance SP"
          className="input"
        />
      </Field>

      <Field label="Descrizione">
        <textarea
          rows={4}
          value={state.description}
          onChange={(e) => set("description", e.target.value)}
          className="input"
        />
      </Field>

      <div className="grid gap-3 sm:grid-cols-3">
        <Field label="Categoria">
          <input
            type="text"
            value={state.category}
            onChange={(e) => set("category", e.target.value)}
            className="input"
          />
        </Field>
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
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        <Field label="Condizione preferita">
          <select
            value={state.preferred_condition}
            onChange={(e) => set("preferred_condition", e.target.value as FormState["preferred_condition"])}
            className="input"
          >
            <option value="">— qualsiasi —</option>
            <option value="NEW">NEW</option>
            <option value="USED">USED</option>
            <option value="REFURBISHED">REFURBISHED</option>
            <option value="FOR_PARTS">FOR_PARTS</option>
          </select>
        </Field>
        <Field label="Offerta max (EUR)">
          <input
            type="number"
            step="0.01"
            min="0"
            value={state.max_price}
            onChange={(e) => set("max_price", e.target.value)}
            placeholder="da concordare"
            className="input"
          />
        </Field>
        <Field label="Priorità (0-100)">
          <input
            type="number"
            min="0"
            max="100"
            value={state.priority}
            onChange={(e) => set("priority", e.target.value)}
            className="input"
          />
        </Field>
      </div>

      <Field label="Note">
        <textarea
          rows={3}
          value={state.notes}
          onChange={(e) => set("notes", e.target.value)}
          className="input"
        />
      </Field>

      <Field label="Stato">
        <select
          value={state.status}
          onChange={(e) => set("status", e.target.value as WantedStatus)}
          className="input"
        >
          <option value="ACTIVE">ACTIVE</option>
          <option value="FULFILLED">FULFILLED</option>
          <option value="CLOSED">CLOSED</option>
        </select>
      </Field>

      {error && <p className="text-pink-deep font-semibold">⚠ {error}</p>}

      <div className="flex gap-3 pt-2">
        <button type="submit" className="btn btn-primary" disabled={submitting}>
          {submitting ? "Salvataggio…" : isEdit ? "Salva modifiche" : "Crea wanted"}
        </button>
        <button
          type="button"
          className="btn btn-ghost"
          onClick={() => router.push("/admin/wanted")}
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
        }
        .input:focus {
          box-shadow: 0 0 0 3px rgba(248, 168, 200, 0.45);
          border-color: #e879a8;
        }
      `}</style>
    </form>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="text-xs font-bold uppercase tracking-wider text-ink-soft">{label}</span>
      <div className="mt-1">{children}</div>
    </label>
  );
}
