"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AdminShell } from "@/components/admin/AdminShell";
import { adminApi } from "@/lib/admin-api";
import { compressImage } from "@/lib/image-compress";
import { uploadWithRetry } from "@/lib/upload-retry";
import { useCategories } from "@/lib/useCategories";
import { usePlatforms } from "@/lib/usePlatforms";
import type { Category, Lot } from "@/lib/types";

const PEOPLE = ["", "C", "D"];

type PublishMode = "none" | "draft" | "live";

interface DraftItem {
  tempId: string;
  title: string;
  category_id: string;
  quantity: number;
  cost: string;
  list_price: string;
  card_collection: string;
  card_number: string;
  card_finish: string;
  /** Foto scattate/scelte prima del submit; upload dopo la creazione item. */
  photos: File[];
}

function newDraftItem(): DraftItem {
  return {
    tempId: Math.random().toString(36).slice(2),
    title: "",
    category_id: "",
    quantity: 1,
    cost: "",
    list_price: "",
    card_collection: "",
    card_number: "",
    card_finish: "",
    photos: [],
  };
}

export default function NewLotPage() {
  const router = useRouter();
  const { flat: categories } = useCategories();
  const { items: platformList } = usePlatforms();
  const platformNames = ["", ...platformList.map((p) => p.name)];

  const [step, setStep] = useState(1);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Step 1: anagrafica lotto
  const [meta, setMeta] = useState({
    title: "",
    purchase_date: new Date().toISOString().slice(0, 10),
    purchase_platform: "",
    bought_by: "",
    total_cost: "",
    notes: "",
  });

  // Step 2: items
  const [items, setItems] = useState<DraftItem[]>([newDraftItem()]);

  // Step 3: result of distribute + bulk-publish choices
  const [createdLot, setCreatedLot] = useState<Lot | null>(null);
  const [createdItemIds, setCreatedItemIds] = useState<number[]>([]);
  const [autoDistribute, setAutoDistribute] = useState(true);
  const [publishMode, setPublishMode] = useState<PublishMode>("none");
  const [progress, setProgress] = useState<string | null>(null);

  const totalQty = items.reduce((s, i) => s + Number(i.quantity || 0), 0);
  const unitCost = autoDistribute && meta.total_cost && totalQty > 0
    ? Number(meta.total_cost) / totalQty : null;

  function updateItem(tempId: string, patch: Partial<DraftItem>) {
    setItems(items.map((i) => i.tempId === tempId ? { ...i, ...patch } : i));
  }

  function removeItem(tempId: string) {
    setItems(items.filter((i) => i.tempId !== tempId));
  }

  function duplicateItem(tempId: string) {
    const src = items.find((i) => i.tempId === tempId);
    if (!src) return;
    // Foto NON copiate: sono del pezzo fisico, non del "tipo" articolo.
    setItems([...items, { ...src, tempId: newDraftItem().tempId, photos: [] }]);
  }

  async function handleCreate() {
    setBusy(true);
    setError(null);
    try {
      const lotPayload = {
        title: meta.title.trim() || null,
        purchase_date: meta.purchase_date || null,
        purchase_platform: meta.purchase_platform || null,
        bought_by: meta.bought_by || null,
        total_cost: meta.total_cost ? Number(meta.total_cost) : null,
        notes: meta.notes.trim() || null,
        status: "OPEN" as const,
      };
      const lot = await adminApi.post<Lot>("/api/lots/", lotPayload);

      const createdIds: number[] = [];
      const validItems = items.filter((it) => it.title.trim());
      for (let idx = 0; idx < validItems.length; idx++) {
        const it = validItems[idx];
        setProgress(`Creo item ${idx + 1} di ${validItems.length}…`);
        const itemPayload = {
          lot_id: lot.id,
          title: it.title.trim(),
          category_id: it.category_id ? Number(it.category_id) : null,
          quantity: Number(it.quantity || 1),
          cost: it.cost ? Number(it.cost) : null,
          list_price: it.list_price ? Number(it.list_price) : null,
          card_collection: it.card_collection.trim() || null,
          card_number: it.card_number.trim() || null,
          card_finish: it.card_finish.trim() || null,
        };
        const created = await adminApi.post<{ id: number }>("/api/inventory/", itemPayload);
        createdIds.push(created.id);

        // Upload foto (compresse client-side: reggono anche gli scatti
        // da fotocamera che superano i 5MB del backend)
        for (let p = 0; p < it.photos.length; p++) {
          setProgress(
            `Item ${idx + 1}/${validItems.length}: foto ${p + 1} di ${it.photos.length}…`,
          );
          const prepared = await compressImage(it.photos[p]);
          const fd = new FormData();
          fd.append("file", prepared);
          await uploadWithRetry(`/api/inventory/${created.id}/upload-image`, fd);
        }
      }

      // Auto-distribute (se richiesto e c'e' un total_cost)
      if (autoDistribute && meta.total_cost && Number(meta.total_cost) > 0 && createdIds.length > 0) {
        setProgress("Distribuisco il costo…");
        await adminApi.post(`/api/lots/${lot.id}/distribute-cost`, {
          total_cost: Number(meta.total_cost),
        });
      }

      // Creazione Article: bozze o direttamente online
      if (publishMode !== "none" && createdIds.length > 0) {
        setProgress(publishMode === "live" ? "Pubblico sul catalogo…" : "Creo le bozze…");
        await adminApi.post(`/api/lots/${lot.id}/bulk-publish`, {
          item_ids: createdIds,
          publish_now: publishMode === "live",
        });
      }

      setCreatedLot(lot);
      setCreatedItemIds(createdIds);
      setStep(4);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
      setProgress(null);
    }
  }

  const canNextStep1 = meta.title.trim() !== "" || meta.purchase_date !== "";
  const canNextStep2 = items.some((i) => i.title.trim() !== "");

  return (
    <AdminShell>
      <div className="mb-3">
        <Link href="/admin/lotti" className="text-xs text-ink-soft hover:text-ink">← Tutti i lotti</Link>
      </div>

      <div className="flex items-center justify-between mb-5">
        <h1 className="display text-3xl text-ink">📦 Nuovo lotto</h1>
        <Stepper step={step} />
      </div>

      {error && (
        <div className="card p-4 mb-4 text-pink-deep font-semibold">⚠ {error}</div>
      )}

      {step === 1 && (
        <Step1 meta={meta} setMeta={setMeta} platformNames={platformNames} />
      )}

      {step === 2 && (
        <Step2
          items={items}
          categories={categories}
          updateItem={updateItem}
          removeItem={removeItem}
          duplicateItem={duplicateItem}
          addItem={() => setItems([...items, newDraftItem()])}
        />
      )}

      {step === 3 && (
        <Step3
          meta={meta}
          items={items}
          totalQty={totalQty}
          unitCost={unitCost}
          autoDistribute={autoDistribute}
          setAutoDistribute={setAutoDistribute}
          publishMode={publishMode}
          setPublishMode={setPublishMode}
        />
      )}

      {step === 4 && createdLot && (
        <Step4 lot={createdLot} itemIds={createdItemIds} />
      )}

      {step !== 4 && (
        <div className="flex justify-between mt-5">
          {step > 1 ? (
            <button
              type="button"
              onClick={() => setStep(step - 1)}
              disabled={busy}
              className="btn btn-ghost text-sm"
            >
              ← Indietro
            </button>
          ) : <span />}
          {step < 3 && (
            <button
              type="button"
              onClick={() => setStep(step + 1)}
              disabled={busy || (step === 1 && !canNextStep1) || (step === 2 && !canNextStep2)}
              className="btn btn-primary text-sm"
            >
              Avanti →
            </button>
          )}
          {step === 3 && (
            <button
              type="button"
              onClick={handleCreate}
              disabled={busy}
              className="btn btn-primary text-sm"
            >
              {busy ? (progress ?? "Creo…") : "✨ Crea lotto + items"}
            </button>
          )}
        </div>
      )}

      <style>{styles}</style>
    </AdminShell>
  );
}

function Stepper({ step }: { step: number }) {
  const steps = ["Lotto", "Item", "Riepilogo", "Fatto"];
  return (
    <div className="flex items-center gap-2 text-xs">
      {steps.map((label, i) => {
        const n = i + 1;
        const active = step === n;
        const done = step > n;
        return (
          <div key={label} className="flex items-center gap-2">
            <span className={`w-7 h-7 rounded-full flex items-center justify-center font-bold ${
              active ? "bg-pink text-white"
              : done ? "bg-mint text-mint-deep"
              : "bg-ink/10 text-ink-soft"
            }`}>
              {done ? "✓" : n}
            </span>
            <span className={`hidden sm:inline ${active ? "font-semibold text-ink" : "text-ink-soft"}`}>{label}</span>
            {n < steps.length && <span className="text-ink-soft/40">→</span>}
          </div>
        );
      })}
    </div>
  );
}

function Step1({ meta, setMeta, platformNames }: { meta: any; setMeta: (m: any) => void; platformNames: string[] }) {
  return (
    <div className="card p-5 grid sm:grid-cols-2 gap-4">
      <h2 className="display text-lg text-ink col-span-full">1. Anagrafica lotto</h2>
      <Field label="Nome lotto (opzionale)">
        <input
          value={meta.title}
          onChange={(e) => setMeta({ ...meta, title: e.target.value })}
          placeholder="es. Bundle Pokémon Vinted aprile"
          className="input"
          autoFocus
        />
      </Field>
      <Field label="Data acquisto">
        <input
          type="date"
          value={meta.purchase_date}
          onChange={(e) => setMeta({ ...meta, purchase_date: e.target.value })}
          className="input"
        />
      </Field>
      <Field label="Piattaforma acquisto">
        <select
          value={meta.purchase_platform}
          onChange={(e) => setMeta({ ...meta, purchase_platform: e.target.value })}
          className="input"
        >
          {platformNames.map((p) => <option key={p || "_"} value={p}>{p || "—"}</option>)}
        </select>
      </Field>
      <Field label="Chi compra">
        <select
          value={meta.bought_by}
          onChange={(e) => setMeta({ ...meta, bought_by: e.target.value })}
          className="input"
        >
          {PEOPLE.map((p) => <option key={p || "_"} value={p}>{p || "—"}</option>)}
        </select>
      </Field>
      <Field label="Costo totale lotto €">
        <input
          type="number" step="0.01"
          value={meta.total_cost}
          onChange={(e) => setMeta({ ...meta, total_cost: e.target.value })}
          placeholder="0.00"
          className="input"
        />
      </Field>
      <Field label="Note (opzionale)">
        <input
          value={meta.notes}
          onChange={(e) => setMeta({ ...meta, notes: e.target.value })}
          className="input"
        />
      </Field>
    </div>
  );
}

function Step2({
  items, categories, updateItem, removeItem, duplicateItem, addItem,
}: {
  items: DraftItem[];
  categories: Category[];
  updateItem: (id: string, patch: Partial<DraftItem>) => void;
  removeItem: (id: string) => void;
  duplicateItem: (id: string) => void;
  addItem: () => void;
}) {
  return (
    <div className="card p-5">
      <div className="flex items-center justify-between mb-3">
        <h2 className="display text-lg text-ink">2. Aggiungi item</h2>
        <button type="button" onClick={addItem} className="btn btn-ghost text-xs">+ Riga</button>
      </div>
      <p className="text-xs text-ink-soft mb-3">
        Solo le righe con un titolo verranno create. Lascia <em>costo</em> vuoto se vuoi
        farlo distribuire automaticamente dal costo totale del lotto allo step 3.
      </p>
      <div className="space-y-2">
        {items.map((it) => (
          <div key={it.tempId} className="grid sm:grid-cols-[2fr_2fr_1fr_1fr_1fr_1fr_1fr_auto] gap-2 items-center border-b border-ink/5 pb-2 sm:border-0 sm:pb-0">
            <input
              value={it.title}
              onChange={(e) => updateItem(it.tempId, { title: e.target.value })}
              placeholder="Oggetto *"
              className="input"
            />
            <select
              value={it.category_id}
              onChange={(e) => updateItem(it.tempId, { category_id: e.target.value })}
              className="input"
            >
              <option value="">— categoria —</option>
              {renderCategoryOptions(categories)}
            </select>
            <input
              type="number" min="1"
              value={it.quantity}
              onChange={(e) => updateItem(it.tempId, { quantity: Number(e.target.value) || 1 })}
              placeholder="Qty"
              className="input"
            />
            <input
              type="number" step="0.01"
              value={it.cost}
              onChange={(e) => updateItem(it.tempId, { cost: e.target.value })}
              placeholder="Costo €"
              className="input"
            />
            <input
              type="number" step="0.01"
              value={it.list_price}
              onChange={(e) => updateItem(it.tempId, { list_price: e.target.value })}
              placeholder="Listino €"
              title="Prezzo di listino sul catalogo"
              className="input"
            />
            <input
              value={it.card_collection}
              onChange={(e) => updateItem(it.tempId, { card_collection: e.target.value })}
              placeholder="Collezione"
              className="input"
            />
            <input
              value={it.card_number}
              onChange={(e) => updateItem(it.tempId, { card_number: e.target.value })}
              placeholder="N°"
              className="input"
            />
            <div className="flex gap-1 items-center flex-wrap">
              {/* Foto: galleria multipla + scatto diretto da fotocamera.
                  Upload dopo la creazione (serve l'id), compresse client-side. */}
              <label className="btn btn-ghost text-xs cursor-pointer relative" title="Aggiungi foto dalla galleria">
                📷
                <input
                  type="file"
                  accept="image/*"
                  multiple
                  className="sr-only"
                  onChange={(e) => {
                    const files = Array.from(e.target.files ?? []);
                    if (files.length) {
                      updateItem(it.tempId, { photos: [...it.photos, ...files] });
                    }
                    e.target.value = "";
                  }}
                />
              </label>
              <label className="btn btn-ghost text-xs cursor-pointer" title="Scatta una foto">
                📸
                <input
                  type="file"
                  accept="image/*"
                  capture="environment"
                  className="sr-only"
                  onChange={(e) => {
                    const files = Array.from(e.target.files ?? []);
                    if (files.length) {
                      updateItem(it.tempId, { photos: [...it.photos, ...files] });
                    }
                    e.target.value = "";
                  }}
                />
              </label>
              {it.photos.length > 0 && (
                <button
                  type="button"
                  onClick={() => updateItem(it.tempId, { photos: [] })}
                  className="text-[10px] font-bold px-1.5 py-0.5 rounded-full bg-mint text-mint-deep"
                  title={`${it.photos.length} foto pronte — click per svuotare`}
                >
                  {it.photos.length}📸✕
                </button>
              )}
              <button
                type="button"
                onClick={() => duplicateItem(it.tempId)}
                className="btn btn-ghost text-xs"
                title="Duplica riga (senza foto)"
              >⎘</button>
              <button
                type="button"
                onClick={() => removeItem(it.tempId)}
                disabled={items.length === 1}
                className="btn btn-ghost text-xs"
                title="Rimuovi"
              >✕</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function Step3({
  meta, items, totalQty, unitCost, autoDistribute, setAutoDistribute, publishMode, setPublishMode,
}: {
  meta: any;
  items: DraftItem[];
  totalQty: number;
  unitCost: number | null;
  autoDistribute: boolean;
  setAutoDistribute: (v: boolean) => void;
  publishMode: PublishMode;
  setPublishMode: (v: PublishMode) => void;
}) {
  const validItems = items.filter((i) => i.title.trim() !== "");
  const totalPhotos = validItems.reduce((s, i) => s + i.photos.length, 0);

  return (
    <div className="card p-5 space-y-4">
      <h2 className="display text-lg text-ink">3. Riepilogo</h2>

      <div className="grid sm:grid-cols-2 gap-3 text-sm">
        <KV label="Nome">{meta.title || "(senza nome)"}</KV>
        <KV label="Data">{meta.purchase_date || "—"}</KV>
        <KV label="Piattaforma">{meta.purchase_platform || "—"}</KV>
        <KV label="Chi compra">{meta.bought_by || "—"}</KV>
        <KV label="Item totali">{validItems.length}</KV>
        <KV label="Pezzi totali">{totalQty}</KV>
        <KV label="Foto pronte">{totalPhotos > 0 ? `${totalPhotos} 📸` : "—"}</KV>
        <KV label="Costo totale lotto">{meta.total_cost ? `${Number(meta.total_cost).toFixed(2)} €` : "—"}</KV>
        {unitCost != null && (
          <KV label="Costo unitario stimato">{unitCost.toFixed(2)} €/pezzo</KV>
        )}
      </div>

      <div className="border-t border-ink/10 pt-3 space-y-2">
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={autoDistribute}
            onChange={(e) => setAutoDistribute(e.target.checked)}
            disabled={!meta.total_cost || Number(meta.total_cost) <= 0}
          />
          <span className="text-sm">
            💰 Distribuisci automaticamente il costo totale ({meta.total_cost ? `${meta.total_cost} €` : "—"})
            su tutti gli item (sovrascrive eventuali costi unitari).
          </span>
        </label>
        <div className="space-y-1.5">
          <p className="text-xs font-bold uppercase tracking-wider text-ink-soft">
            Pubblicazione sul sito
          </p>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="radio"
              name="publish-mode"
              checked={publishMode === "none"}
              onChange={() => setPublishMode("none")}
            />
            <span className="text-sm">Non creare Article (solo inventario interno)</span>
          </label>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="radio"
              name="publish-mode"
              checked={publishMode === "draft"}
              onChange={() => setPublishMode("draft")}
            />
            <span className="text-sm">
              📝 Crea bozze Article (DRAFT) — rifinisci in <code>/admin/articles</code> prima
              di andare online
            </span>
          </label>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="radio"
              name="publish-mode"
              checked={publishMode === "live"}
              onChange={() => setPublishMode("live")}
            />
            <span className="text-sm">
              🚀 Pubblica <strong>subito online</strong> — usa foto e prezzo di listino
              inseriti qui (gli iscritti agli avvisi ricevono l&apos;email)
            </span>
          </label>
        </div>
      </div>
    </div>
  );
}

function Step4({ lot, itemIds }: { lot: Lot; itemIds: number[] }) {
  return (
    <div className="card p-6 text-center">
      <p className="display text-2xl text-mint-deep mb-2">✨ Lotto creato!</p>
      <p className="text-ink-soft text-sm mb-4">
        Codice: <strong className="font-mono">{lot.code}</strong> · {itemIds.length} item creati
      </p>
      <div className="flex gap-2 justify-center flex-wrap">
        <Link href={`/admin/lotti/${lot.id}`} className="btn btn-primary text-sm">
          Apri lotto {lot.code}
        </Link>
        <Link href="/admin/lotti/new" className="btn btn-ghost text-sm">
          + Altro lotto
        </Link>
        <Link href="/admin/lotti" className="btn btn-ghost text-sm">
          Torna alla lista
        </Link>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="text-[10px] uppercase tracking-wider text-ink-soft block mb-0.5">{label}</span>
      {children}
    </label>
  );
}

function KV({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-wider text-ink-soft">{label}</div>
      <div className="font-semibold text-ink">{children}</div>
    </div>
  );
}

function renderCategoryOptions(flat: Category[]) {
  const tops = flat.filter((c) => c.parent_id == null);
  return tops.flatMap((top) => [
    <option key={top.id} value={top.id}>{top.name}</option>,
    ...flat
      .filter((c) => c.parent_id === top.id)
      .map((sub) => (
        <option key={sub.id} value={sub.id}>{"  ↳ " + sub.name}</option>
      )),
  ]);
}

const styles = `
  .input {
    display: block;
    width: 100%;
    padding: 0.4rem 0.6rem;
    border: 1px solid rgba(61, 42, 92, 0.12);
    border-radius: 10px;
    background: #fffaf3;
    color: #3d2a5c;
    font-family: "Manrope", sans-serif;
    font-size: 0.85rem;
    outline: none;
  }
  .input:focus {
    box-shadow: 0 0 0 2px rgba(248, 168, 200, 0.45);
    border-color: #e879a8;
  }
`;
