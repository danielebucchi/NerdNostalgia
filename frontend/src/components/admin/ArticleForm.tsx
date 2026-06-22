"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { adminApi } from "@/lib/admin-api";
import { CategoryPicker } from "@/components/admin/CategoryPicker";
import { Sortable } from "@/components/admin/Sortable";
import { calcMarkup } from "@/components/admin/MarketplaceSyncBox";
import { useCategories } from "@/lib/useCategories";
import { getMarkupsFromFees, useMarketplaceFees } from "@/lib/useMarketplaceFees";
import type {
  Article,
  ArticleCondition,
  ArticleStatus,
  MarketplaceStatus,
} from "@/lib/types";

type MarketplaceKey = "vinted" | "ebay";

interface MarketplaceSeed {
  enabled: boolean;
  status: MarketplaceStatus;
  url: string;
  price: string;
}

const MARKETPLACE_META: Record<
  MarketplaceKey,
  {
    label: string;
    emoji: string;
    urlPlaceholder: string;
    newListingUrl: string;
  }
> = {
  vinted: {
    label: "Vinted",
    emoji: "🛍",
    urlPlaceholder: "https://www.vinted.it/items/123456789-…",
    newListingUrl: "https://www.vinted.it/items/new",
  },
  ebay: {
    label: "eBay",
    emoji: "🏷",
    urlPlaceholder: "https://www.ebay.it/itm/123456789",
    newListingUrl: "https://www.ebay.it/sl/sell",
  },
};

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
  shipping_price: string;
  currency: string;
  category_id: number | null;
  condition: ArticleCondition;
  status: ArticleStatus;
  quantity: string;
  sku: string;
  brand: string;
  model: string;
  weight_kg: string;
  dimensions_cm: string;
  // Inventario
  lotto: string;
  purchase_date: string;
  cost: string;
  purchase_platform: string;
  bought_by: string;
  sold_by: string;
  fee_amount: string;
  shipping_cost: string;
  quantity_sold: string;
  card_collection: string;
  card_number: string;
  card_finish: string;
}

const empty: FormState = {
  title: "",
  description: "",
  price: "",
  shipping_price: "",
  currency: "EUR",
  category_id: null,
  condition: "USED",
  status: "DRAFT",
  quantity: "1",
  sku: "",
  brand: "",
  model: "",
  weight_kg: "",
  dimensions_cm: "",
  lotto: "",
  purchase_date: "",
  cost: "",
  purchase_platform: "",
  bought_by: "",
  sold_by: "",
  fee_amount: "",
  shipping_cost: "",
  quantity_sold: "0",
  card_collection: "",
  card_number: "",
  card_finish: "",
};

function toForm(article: Article): FormState {
  return {
    title: article.title,
    description: article.description ?? "",
    price: String(article.price ?? ""),
    shipping_price: article.shipping_price ?? "",
    currency: article.currency ?? "EUR",
    category_id: article.category_id ?? null,
    condition: article.condition,
    status: article.status,
    quantity: String(article.quantity ?? 1),
    sku: article.sku ?? "",
    brand: article.brand ?? "",
    model: article.model ?? "",
    weight_kg: article.weight_kg ?? "",
    dimensions_cm: article.dimensions_cm ?? "",
    lotto: article.lotto ?? "",
    purchase_date: article.purchase_date ?? "",
    cost: article.cost ?? "",
    purchase_platform: article.purchase_platform ?? "",
    bought_by: article.bought_by ?? "",
    sold_by: article.sold_by ?? "",
    fee_amount: article.fee_amount ?? "",
    shipping_cost: article.shipping_cost ?? "",
    quantity_sold: String(article.quantity_sold ?? 0),
    card_collection: article.card_collection ?? "",
    card_number: article.card_number ?? "",
    card_finish: article.card_finish ?? "",
  };
}

export function ArticleForm({ initial, onSaved }: Props) {
  const router = useRouter();
  const [state, setState] = useState<FormState>(initial ? toForm(initial) : empty);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pendingFiles, setPendingFiles] = useState<PendingFile[]>([]);
  const [uploadProgress, setUploadProgress] = useState<string | null>(null);
  const [vinted, setVinted] = useState<MarketplaceSeed>({
    enabled: false,
    status: "LISTED",
    url: "",
    price: "",
  });
  const [ebay, setEbay] = useState<MarketplaceSeed>({
    enabled: false,
    status: "LISTED",
    url: "",
    price: "",
  });

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
        shipping_price: state.shipping_price.trim() ? Number(state.shipping_price) : null,
        currency: state.currency.trim().toUpperCase(),
        category_id: state.category_id,
        condition: state.condition,
        quantity: Number(state.quantity),
        sku: state.sku.trim() || null,
        brand: state.brand.trim() || null,
        model: state.model.trim() || null,
        weight_kg: state.weight_kg.trim() ? Number(state.weight_kg) : null,
        dimensions_cm: state.dimensions_cm.trim() || null,
        // Inventario
        lotto: state.lotto.trim() || null,
        purchase_date: state.purchase_date || null,
        cost: state.cost.trim() ? Number(state.cost) : null,
        purchase_platform: state.purchase_platform.trim() || null,
        bought_by: state.bought_by.trim() || null,
        sold_by: state.sold_by.trim() || null,
        fee_amount: state.fee_amount.trim() ? Number(state.fee_amount) : null,
        shipping_cost: state.shipping_cost.trim() ? Number(state.shipping_cost) : null,
        quantity_sold: state.quantity_sold.trim() ? Number(state.quantity_sold) : 0,
        card_collection: state.card_collection.trim() || null,
        card_number: state.card_number.trim() || null,
        card_finish: state.card_finish.trim() || null,
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
      }

      // Sync iniziale Vinted / eBay (solo in create)
      if (!isEdit) {
        if (vinted.enabled) {
          setUploadProgress("Sincronizzo Vinted…");
          result = await adminApi.patch<Article>(
            `/api/articles/${result.id}/vinted`,
            {
              vinted_status: vinted.status,
              vinted_url: vinted.url.trim() || null,
              vinted_price: vinted.price.trim() ? Number(vinted.price) : null,
            },
          );
        }
        if (ebay.enabled) {
          setUploadProgress("Sincronizzo eBay…");
          result = await adminApi.patch<Article>(
            `/api/articles/${result.id}/ebay`,
            {
              ebay_status: ebay.status,
              ebay_url: ebay.url.trim() || null,
              ebay_price: ebay.price.trim() ? Number(ebay.price) : null,
            },
          );
        }
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

      <Row>
        <Field
          label="Spedizione richiesta al cliente"
          full
          hint="Sommata al prezzo nel link PayPal. Lascia vuoto per 'da concordare'."
        >
          <input
            type="number"
            step="0.01"
            min="0"
            placeholder="es. 5.00"
            value={state.shipping_price}
            onChange={(e) => set("shipping_price", e.target.value)}
            className="input"
          />
        </Field>
      </Row>

      <Row>
        <div className="col-span-full">
          <CategoryPicker
            value={state.category_id}
            onChange={(next) => set("category_id", next)}
          />
        </div>
      </Row>

      <Row cols={2}>
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

      <div className="border border-dashed border-ink/20 rounded-big p-4 bg-white/40 space-y-3">
        <div>
          <h3 className="display text-base text-ink">📊 Inventario (foglio Cate)</h3>
          <p className="text-xs text-ink-soft">
            Costo acquisto, fee, spedizione → vengono usati per calcolare il
            profitto reale nella pagina <code>/admin/inventario</code> e nei totali della dashboard.
          </p>
        </div>

        <Row cols={3}>
          <Field label="Lotto">
            <input
              type="text"
              value={state.lotto}
              onChange={(e) => set("lotto", e.target.value)}
              placeholder="es. L01"
              className="input"
            />
          </Field>
          <Field label="Data acquisto">
            <input
              type="date"
              value={state.purchase_date}
              onChange={(e) => set("purchase_date", e.target.value)}
              className="input"
            />
          </Field>
          <Field label="Costo (€)">
            <input
              type="number"
              step="0.01"
              min="0"
              value={state.cost}
              onChange={(e) => set("cost", e.target.value)}
              className="input"
            />
          </Field>
        </Row>

        <Row cols={3}>
          <Field label="Piattaforma acquisto">
            <select
              value={state.purchase_platform}
              onChange={(e) => set("purchase_platform", e.target.value)}
              className="input"
            >
              <option value="">—</option>
              {["Vinted", "mercato", "Subito", "eBay", "Wallapop", "Regalo", "Altro"].map((p) => (
                <option key={p} value={p}>{p}</option>
              ))}
            </select>
          </Field>
          <Field label="Chi compra">
            <select
              value={state.bought_by}
              onChange={(e) => set("bought_by", e.target.value)}
              className="input"
            >
              <option value="">—</option>
              <option value="C">C</option>
              <option value="D">D</option>
            </select>
          </Field>
          <Field label="Chi vende">
            <select
              value={state.sold_by}
              onChange={(e) => set("sold_by", e.target.value)}
              className="input"
            >
              <option value="">—</option>
              <option value="C">C</option>
              <option value="D">D</option>
            </select>
          </Field>
        </Row>

        <Row cols={3}>
          <Field label="Fee marketplace (€)">
            <input
              type="number"
              step="0.01"
              min="0"
              value={state.fee_amount}
              onChange={(e) => set("fee_amount", e.target.value)}
              className="input"
            />
          </Field>
          <Field label="Costo spedizione (€)">
            <input
              type="number"
              step="0.01"
              min="0"
              value={state.shipping_cost}
              onChange={(e) => set("shipping_cost", e.target.value)}
              className="input"
            />
          </Field>
          <Field label="Quantità venduta">
            <input
              type="number"
              min="0"
              value={state.quantity_sold}
              onChange={(e) => set("quantity_sold", e.target.value)}
              className="input"
            />
          </Field>
        </Row>

        <div className="pt-2 border-t border-ink/10">
          <h4 className="text-xs font-bold uppercase tracking-wider text-ink-soft mb-2">
            Solo per carte (Pokemon, Magic, ecc)
          </h4>
          <Row cols={3}>
            <Field label="Collezione">
              <input
                type="text"
                value={state.card_collection}
                onChange={(e) => set("card_collection", e.target.value)}
                placeholder="es. Base Set"
                className="input"
              />
            </Field>
            <Field label="Numero">
              <input
                type="text"
                value={state.card_number}
                onChange={(e) => set("card_number", e.target.value)}
                placeholder="4/102"
                className="input"
              />
            </Field>
            <Field label="Finitura">
              <select
                value={state.card_finish}
                onChange={(e) => set("card_finish", e.target.value)}
                className="input"
              >
                <option value="">—</option>
                <option value="normal">normal</option>
                <option value="holo">holo</option>
                <option value="reverse">reverse</option>
                <option value="full art">full art</option>
                <option value="textured">textured</option>
                <option value="rainbow">rainbow</option>
              </select>
            </Field>
          </Row>
        </div>
      </div>

      {!isEdit && (
        <div className="border border-dashed border-ink/20 rounded-big p-4 bg-white/40">
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
                          "relative aspect-square rounded-2xl overflow-hidden bg-white/60 cursor-grab active:cursor-grabbing transition-all " +
                          (isCover ? "ring-2 ring-pink-deep shadow-soft " : "ring-1 ring-ink/10 ") +
                          (isDragging ? "ring-4 ring-lilac-deep/50 " : "")
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
                            className="absolute top-1 left-1 w-7 h-7 rounded-full bg-white/95 backdrop-blur text-ink text-xs flex items-center justify-center ring-1 ring-ink/15 shadow-soft hover:bg-pink-soft transition-colors"
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
                          className="flex-1 h-7 rounded-full ring-1 ring-ink/15 bg-white/80 text-ink text-sm font-bold hover:ring-ink/30 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
                          aria-label="Sposta a sinistra"
                          title="Sposta a sinistra"
                        >
                          ←
                        </button>
                        <button
                          type="button"
                          onClick={() => movePendingFile(p.id, 1)}
                          disabled={isLast}
                          className="flex-1 h-7 rounded-full ring-1 ring-ink/15 bg-white/80 text-ink text-sm font-bold hover:ring-ink/30 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
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

      {!isEdit && (
        <div className="border border-dashed border-ink/20 rounded-big p-4 bg-white/40">
          <h3 className="display text-base text-ink mb-1">
            Sincronizza subito su marketplace
          </h3>
          <p className="text-xs text-ink-soft mb-4">
            Spunta solo se hai già pubblicato (o stai per pubblicare) l&apos;annuncio
            altrove. Cliccando <strong>Apri ↗</strong> da mobile si apre direttamente
            l&apos;app Vinted / eBay (se installata).
          </p>

          <div className="grid sm:grid-cols-2 gap-4">
            <MarketplacePicker
              marketplace="vinted"
              state={vinted}
              onChange={setVinted}
              basePrice={state.price}
              categoryId={state.category_id}
            />
            <MarketplacePicker
              marketplace="ebay"
              state={ebay}
              onChange={setEbay}
              basePrice={state.price}
              categoryId={state.category_id}
            />
          </div>
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
              : buildCreateLabel(pendingFiles.length, vinted.enabled, ebay.enabled)}
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
  hint,
  children,
}: {
  label: string;
  full?: boolean;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <label className={`block ${full ? "col-span-full" : ""}`}>
      <span className="text-xs font-bold uppercase tracking-wider text-ink-soft">{label}</span>
      <div className="mt-1">{children}</div>
      {hint && (
        <span className="text-[11px] text-ink-soft mt-1 block leading-snug">{hint}</span>
      )}
    </label>
  );
}

function buildCreateLabel(
  fileCount: number,
  vintedOn: boolean,
  ebayOn: boolean,
): string {
  const extras: string[] = [];
  if (fileCount > 0) extras.push(`+${fileCount} foto`);
  if (vintedOn) extras.push("Vinted");
  if (ebayOn) extras.push("eBay");
  return extras.length > 0
    ? `Crea articolo (${extras.join(" · ")})`
    : "Crea articolo";
}

function MarketplacePicker({
  marketplace,
  state,
  onChange,
  basePrice,
  categoryId,
}: {
  marketplace: MarketplaceKey;
  state: MarketplaceSeed;
  onChange: (next: MarketplaceSeed) => void;
  basePrice: string;
  categoryId: number | null;
}) {
  const meta = MARKETPLACE_META[marketplace];
  const hasBase = basePrice.trim() !== "" && Number(basePrice) > 0;
  const { fees } = useMarketplaceFees();
  const { byId } = useCategories();
  const parentId = categoryId != null ? byId[categoryId]?.parent_id ?? null : null;
  const markups = getMarkupsFromFees(fees, marketplace, categoryId, parentId);

  return (
    <div
      className={
        "rounded-2xl p-3 transition-all " +
        (state.enabled
          ? "ring-2 ring-pink-deep bg-pink-soft/40 shadow-soft"
          : "ring-1 ring-ink/10 bg-white/70 hover:ring-ink/20")
      }
    >
      <div className="flex items-start justify-between gap-2">
        <label className="flex items-start gap-2 cursor-pointer flex-1">
          <input
            type="checkbox"
            checked={state.enabled}
            onChange={(e) => onChange({ ...state, enabled: e.target.checked })}
            className="mt-1 accent-pink-deep w-4 h-4"
          />
          <span className="flex-1">
            <span className="display text-base text-ink block">
              {meta.emoji} Anche su {meta.label}
            </span>
            <span className="text-xs text-ink-soft">
              Spunta se vuoi tracciare il listing su {meta.label}.
            </span>
          </span>
        </label>
        <a
          href={meta.newListingUrl}
          target="_blank"
          rel="noopener noreferrer"
          onClick={(e) => e.stopPropagation()}
          className="text-xs font-bold text-pink-deep underline whitespace-nowrap flex-shrink-0 mt-1"
          title={`Apri ${meta.label} (app se installata su mobile)`}
        >
          Apri ↗
        </a>
      </div>

      {state.enabled && (
        <div className="mt-3 space-y-2">
          <label className="block">
            <span className="text-xs font-bold uppercase tracking-wider text-ink-soft">
              Stato
            </span>
            <select
              value={state.status}
              onChange={(e) =>
                onChange({ ...state, status: e.target.value as MarketplaceStatus })
              }
              className="input mt-1"
            >
              <option value="NOT_LISTED">Da listare</option>
              <option value="LISTED">Online (ho già pubblicato)</option>
            </select>
          </label>
          <label className="block">
            <span className="text-xs font-bold uppercase tracking-wider text-ink-soft">
              Prezzo su {meta.label} (opzionale)
            </span>
            <input
              type="number"
              step="0.01"
              min="0"
              value={state.price}
              onChange={(e) => onChange({ ...state, price: e.target.value })}
              placeholder="vuoto = usa prezzo catalogo"
              className="input mt-1"
            />
            {hasBase && (
              <div className="flex flex-wrap gap-1.5 mt-2">
                <span className="text-[10px] uppercase tracking-wider text-ink-soft self-center mr-1">
                  Da catalogo:
                </span>
                {markups.map((m) => (
                  <button
                    key={m}
                    type="button"
                    onClick={() =>
                      onChange({ ...state, price: calcMarkup(basePrice, m) })
                    }
                    className="text-[11px] font-bold px-2.5 py-1 rounded-full ring-1 ring-ink/15 bg-white/80 backdrop-blur hover:ring-lilac-deep hover:bg-lilac-soft transition-all"
                    title={`${basePrice} + ${m}% = ${calcMarkup(basePrice, m)}`}
                  >
                    {m === 0 ? "uguale" : `+${m}%`}
                  </button>
                ))}
                {state.price && (
                  <button
                    type="button"
                    onClick={() => onChange({ ...state, price: "" })}
                    className="text-[11px] font-bold px-2.5 py-1 rounded-full ring-1 ring-ink/10 text-ink-soft bg-white/60 hover:ring-ink/30 hover:text-ink transition-all"
                  >
                    ✕ vuota
                  </button>
                )}
              </div>
            )}
          </label>
          <label className="block">
            <span className="text-xs font-bold uppercase tracking-wider text-ink-soft">
              URL listing (opzionale)
            </span>
            <input
              type="url"
              value={state.url}
              onChange={(e) => onChange({ ...state, url: e.target.value })}
              placeholder={meta.urlPlaceholder}
              className="input mt-1"
            />
          </label>
        </div>
      )}
    </div>
  );
}
