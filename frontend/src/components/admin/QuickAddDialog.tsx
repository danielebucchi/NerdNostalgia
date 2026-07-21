"use client";

/**
 * "Scatta e cataloga": inserimento rapido da telefono.
 * Foto (camera in-app/galleria) + titolo + listino + lotto → crea l'item,
 * carica le foto e opzionalmente pubblica subito.
 *
 * Robustezza rete/processo:
 * - upload con retry esponenziale (uploadWithRetry) e stato PER FOTO
 * - se l'invio fallisce a meta', l'item gia' creato viene ricordato
 *   (draftItemId) e "Riprova" riparte dalle foto mancanti — niente doppioni
 * - la bozza (titolo/prezzi/lotto) vive in sessionStorage: sopravvive anche
 *   se Android killa la PWA mentre sei in giro
 */
import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { CameraCapture, supportsInAppCamera } from "@/components/admin/CameraCapture";
import { useSoldPriceHint } from "@/components/admin/useSoldPriceHint";
import { adminApi } from "@/lib/admin-api";
import { compressImage } from "@/lib/image-compress";
import { uploadWithRetry } from "@/lib/upload-retry";
import { findTopLevel, useCategories } from "@/lib/useCategories";
import type { Lot, LotListResponse } from "@/lib/types";

const DRAFT_KEY = "nn:quickadd-draft:v1";
// Slug top-level "carte": abilita i campi collezione/numero per l'auto-match
// del blueprint CardTrader (stessa logica di is_card_article lato backend).
const CARD_TOP_SLUGS = new Set(["carte", "cards"]);

interface Draft {
  title: string;
  description: string;
  listPrice: string;
  cost: string;
  categoryId: string;
  lotId: string;
  publishNow: boolean;
  draftItemId: number | null;
  cardCollection: string;
  cardNumber: string;
}

type PhotoStatus = "pending" | "done" | "error";

interface Props {
  open: boolean;
  onClose: () => void;
}

export function QuickAddDialog({ open, onClose }: Props) {
  const { flat: categories, byId: categoriesById } = useCategories();
  const [lots, setLots] = useState<Lot[]>([]);
  const [lotId, setLotId] = useState<string>("");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [listPrice, setListPrice] = useState("");
  const [cost, setCost] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [cardCollection, setCardCollection] = useState("");
  const [cardNumber, setCardNumber] = useState("");
  const [photos, setPhotos] = useState<File[]>([]);
  const [photoStatus, setPhotoStatus] = useState<PhotoStatus[]>([]);
  const [publishNow, setPublishNow] = useState(false);
  const [cameraOpen, setCameraOpen] = useState(false);
  // Item gia' creato da un tentativo precedente fallito: si riprende da qui
  const [draftItemId, setDraftItemId] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState<{ itemId: number; lotId: number } | null>(null);

  const priceHint = useSoldPriceHint(title);

  // È una carta? (categoria il cui top-level è "carte") → mostra i campi
  // collezione/numero che alimentano l'auto-push CardTrader alla pubblicazione.
  const isCard = useMemo(() => {
    if (!categoryId) return false;
    const top = findTopLevel(categoriesById, Number(categoryId));
    return !!top && CARD_TOP_SLUGS.has((top.slug || "").toLowerCase());
  }, [categoryId, categoriesById]);

  // Anteprime foto (object URL, revocate al cleanup)
  const previews = useMemo(() => photos.map((f) => URL.createObjectURL(f)), [photos]);
  useEffect(() => () => previews.forEach((u) => URL.revokeObjectURL(u)), [previews]);

  // Ripristino bozza (una volta, all'apertura)
  useEffect(() => {
    if (!open) return;
    setDone(null);
    setError(null);
    try {
      const raw = window.sessionStorage.getItem(DRAFT_KEY);
      if (raw) {
        const d: Draft = JSON.parse(raw);
        if (d.title) setTitle(d.title);
        if (d.description) setDescription(d.description);
        if (d.listPrice) setListPrice(d.listPrice);
        if (d.cost) setCost(d.cost);
        if (d.categoryId) setCategoryId(d.categoryId);
        if (d.lotId) setLotId(d.lotId);
        if (d.publishNow) setPublishNow(d.publishNow);
        if (d.draftItemId) setDraftItemId(d.draftItemId);
        if (d.cardCollection) setCardCollection(d.cardCollection);
        if (d.cardNumber) setCardNumber(d.cardNumber);
      }
    } catch {
      // bozza corrotta: ignora
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  // Persistenza bozza a ogni modifica (foto escluse: i File non si
  // serializzano — al kill del processo si riscattano, il resto resta)
  useEffect(() => {
    if (!open) return;
    const draft: Draft = {
      title, description, listPrice, cost, categoryId, lotId, publishNow, draftItemId,
      cardCollection, cardNumber,
    };
    try {
      if (title.trim() || draftItemId) {
        window.sessionStorage.setItem(DRAFT_KEY, JSON.stringify(draft));
      }
    } catch {
      // storage pieno/negato: pazienza
    }
  }, [open, title, description, listPrice, cost, categoryId, lotId, publishNow, draftItemId, cardCollection, cardNumber]);

  function clearDraft() {
    try {
      window.sessionStorage.removeItem(DRAFT_KEY);
    } catch {
      // ignore
    }
    setDraftItemId(null);
  }

  // Lotti OPEN alla prima apertura; preseleziona il piu' recente
  useEffect(() => {
    if (!open) return;
    adminApi
      .get<LotListResponse>("/api/lots/?status=OPEN")
      .then((d) => {
        setLots(d.items);
        if (d.items.length > 0) {
          setLotId((curr) => curr || String(d.items[0].id));
        }
      })
      .catch(() => {});
  }, [open]);

  // Esc + scroll lock
  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape" && !busy) onClose();
    }
    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = "";
      window.removeEventListener("keydown", onKey);
    };
  }, [open, busy, onClose]);

  if (!open) return null;

  function addPhotos(files: FileList | File[] | null) {
    if (!files) return;
    const arr = Array.from(files);
    setPhotos((curr) => [...curr, ...arr]);
    setPhotoStatus((curr) => [...curr, ...arr.map(() => "pending" as PhotoStatus)]);
  }

  function removePhoto(index: number) {
    setPhotos((c) => c.filter((_, j) => j !== index));
    setPhotoStatus((c) => c.filter((_, j) => j !== index));
  }

  async function createQuickLot() {
    const name = `Quick ${new Date().toISOString().slice(0, 10)}`;
    try {
      const lot = await adminApi.post<Lot>("/api/lots/", {
        title: name,
        purchase_date: new Date().toISOString().slice(0, 10),
      });
      setLots((curr) => [lot, ...curr]);
      setLotId(String(lot.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!lotId) {
      setError("Scegli un lotto (o creane uno rapido).");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      // 1) Item: crea SOLO se non esiste gia' da un tentativo precedente
      let itemId = draftItemId;
      if (!itemId) {
        setProgress("Creo l'item…");
        const item = await adminApi.post<{ id: number }>("/api/inventory/", {
          lot_id: Number(lotId),
          title: title.trim(),
          description: description.trim() || null,
          quantity: 1,
          cost: cost.trim() ? Number(cost) : null,
          list_price: listPrice.trim() ? Number(listPrice) : null,
          category_id: categoryId ? Number(categoryId) : null,
          // Solo per le carte: alimentano l'auto-match del blueprint CardTrader
          card_collection: isCard && cardCollection.trim() ? cardCollection.trim() : null,
          card_number: isCard && cardNumber.trim() ? cardNumber.trim() : null,
        });
        itemId = item.id;
        setDraftItemId(itemId);
      }

      // 2) Foto: salta quelle gia' caricate, retry su rete instabile
      for (let i = 0; i < photos.length; i++) {
        if (photoStatus[i] === "done") continue;
        setProgress(`Foto ${i + 1} di ${photos.length}…`);
        try {
          const prepared = await compressImage(photos[i]);
          const fd = new FormData();
          fd.append("file", prepared);
          await uploadWithRetry(`/api/inventory/${itemId}/upload-image`, fd);
          setPhotoStatus((c) => c.map((s, j) => (j === i ? "done" : s)));
        } catch (err) {
          setPhotoStatus((c) => c.map((s, j) => (j === i ? "error" : s)));
          throw new Error(
            `Foto ${i + 1} non caricata (${err instanceof Error ? err.message : "rete?"}). ` +
              `L'item #${itemId} è salvo: premi Riprova per completare.`,
          );
        }
      }

      // 3) Pubblicazione opzionale
      if (publishNow && listPrice.trim()) {
        setProgress("Pubblico sul catalogo…");
        await adminApi.post(`/api/inventory/${itemId}/publish`, { publish_now: true });
      }

      setDone({ itemId, lotId: Number(lotId) });
      clearDraft();
      // reset per il prossimo giro (tenendo il lotto selezionato)
      setTitle("");
      setDescription("");
      setListPrice("");
      setCost("");
      setCardCollection("");
      setCardNumber("");
      setPhotos([]);
      setPhotoStatus([]);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
      setProgress(null);
    }
  }

  const statusIcon: Record<PhotoStatus, string> = {
    pending: "",
    done: "✓",
    error: "⚠",
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-start sm:items-center justify-center p-4 bg-ink/50 backdrop-blur-sm overflow-y-auto"
      onClick={busy ? undefined : onClose}
    >
      <div
        className="card w-full max-w-lg p-5 sm:p-6 my-6"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-3 mb-4">
          <h2 className="display text-xl text-ink">📸 Scatta e cataloga</h2>
          <button
            type="button"
            onClick={onClose}
            disabled={busy}
            className="w-8 h-8 rounded-full border-2 border-ink flex items-center justify-center text-ink hover:bg-pink shrink-0 disabled:opacity-40"
            aria-label="Chiudi"
          >
            ✕
          </button>
        </div>

        {done ? (
          <div className="text-center py-4">
            <div className="text-4xl mb-2">✨</div>
            <p className="display text-lg text-ink mb-1">Catalogato!</p>
            <p className="text-sm text-ink-soft mb-4">
              Item #{done.itemId} salvato nel lotto.
            </p>
            <div className="flex flex-wrap gap-2 justify-center">
              <button
                type="button"
                onClick={() => setDone(null)}
                className="btn btn-primary text-sm"
              >
                📸 Aggiungi un altro
              </button>
              <Link href={`/admin/lotti/${done.lotId}`} className="btn btn-ghost text-sm">
                Apri il lotto
              </Link>
            </div>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-3">
            {draftItemId && (
              <p className="text-xs rounded-lg bg-lilac-soft/50 text-lilac-deep px-3 py-2">
                ↻ Ripresa: item <strong>#{draftItemId}</strong> già creato — mancano
                solo le foto/pubblicazione.
              </p>
            )}

            {/* Foto: prima cosa, e' il gesto principale del flusso */}
            <div>
              <div className="flex gap-2 flex-wrap items-center">
                {/* Camera in-app dove possibile: l'app fotocamera esterna
                    fa killare la PWA su Android (perdendo lo scatto) */}
                {supportsInAppCamera() ? (
                  <button
                    type="button"
                    onClick={() => setCameraOpen(true)}
                    disabled={busy}
                    className="btn btn-primary text-sm"
                  >
                    📸 Scatta
                  </button>
                ) : (
                  <label className="btn btn-primary text-sm cursor-pointer">
                    📸 Scatta
                    <input
                      type="file" accept="image/*" capture="environment"
                      className="sr-only"
                      onChange={(e) => { addPhotos(e.target.files); e.target.value = ""; }}
                      disabled={busy}
                    />
                  </label>
                )}
                <label className="btn btn-ghost text-sm cursor-pointer">
                  📷 Galleria
                  <input
                    type="file" accept="image/*" multiple
                    className="sr-only"
                    onChange={(e) => { addPhotos(e.target.files); e.target.value = ""; }}
                    disabled={busy}
                  />
                </label>
              </div>
              {photos.length > 0 && (
                <div className="flex gap-2 mt-2 flex-wrap">
                  {previews.map((src, i) => (
                    <div
                      key={i}
                      className={`relative w-16 h-16 rounded-lg overflow-hidden ring-2 ${
                        photoStatus[i] === "done"
                          ? "ring-mint-deep"
                          : photoStatus[i] === "error"
                            ? "ring-red-500"
                            : "ring-ink/10"
                      }`}
                    >
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img src={src} alt="" className="w-full h-full object-cover" />
                      {photoStatus[i] !== "pending" && (
                        <span
                          className={`absolute bottom-0 left-0 text-[10px] font-bold px-1 rounded-tr ${
                            photoStatus[i] === "done"
                              ? "bg-mint-deep text-white"
                              : "bg-red-500 text-white"
                          }`}
                        >
                          {statusIcon[photoStatus[i]]}
                        </span>
                      )}
                      {photoStatus[i] !== "done" && (
                        <button
                          type="button"
                          onClick={() => removePhoto(i)}
                          className="absolute top-0 right-0 w-5 h-5 bg-ink/70 text-white text-xs rounded-bl-lg"
                          aria-label="Rimuovi foto"
                        >
                          ✕
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            <input
              type="text"
              required
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Cosa hai in mano? *"
              className="qa-input"
              maxLength={500}
            />

            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Descrizione (condizioni, difetti, cosa include…) — finisce sull'articolo quando pubblichi"
              className="qa-input resize-none"
              rows={3}
              maxLength={4000}
            />

            <div>
              <div className="grid grid-cols-2 gap-3">
                <input
                  type="number" step="0.01" min="0" inputMode="decimal"
                  value={listPrice}
                  onChange={(e) => setListPrice(e.target.value)}
                  placeholder="Listino €"
                  className="qa-input"
                />
                <input
                  type="number" step="0.01" min="0" inputMode="decimal"
                  value={cost}
                  onChange={(e) => setCost(e.target.value)}
                  placeholder="Costo €"
                  className="qa-input"
                />
              </div>
              {priceHint && (
                <p className="text-[11px] text-ink-soft mt-1">{priceHint}</p>
              )}
            </div>

            <div className="grid grid-cols-2 gap-3">
              <select
                value={categoryId}
                onChange={(e) => setCategoryId(e.target.value)}
                className="qa-input"
                aria-label="Categoria"
              >
                <option value="">— categoria —</option>
                {categories
                  .filter((c) => c.parent_id == null)
                  .map((top) => (
                    <optgroup key={top.id} label={top.name}>
                      <option value={top.id}>{top.name}</option>
                      {categories
                        .filter((c) => c.parent_id === top.id)
                        .map((sub) => (
                          <option key={sub.id} value={sub.id}>↳ {sub.name}</option>
                        ))}
                    </optgroup>
                  ))}
              </select>
              <div className="flex gap-1.5">
                <select
                  value={lotId}
                  onChange={(e) => setLotId(e.target.value)}
                  className="qa-input flex-1 min-w-0"
                  aria-label="Lotto di destinazione"
                >
                  <option value="">— lotto * —</option>
                  {lots.map((l) => (
                    <option key={l.id} value={l.id}>
                      {l.code} {l.title ? `· ${l.title}` : ""}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  onClick={createQuickLot}
                  disabled={busy}
                  className="btn btn-ghost text-xs px-2 flex-shrink-0"
                  title="Crea un lotto rapido per oggi"
                >
                  ＋
                </button>
              </div>
            </div>

            {isCard && (
              <div className="grid grid-cols-2 gap-3">
                <input
                  type="text"
                  value={cardCollection}
                  onChange={(e) => setCardCollection(e.target.value)}
                  placeholder="Espansione/collezione"
                  className="qa-input"
                  maxLength={100}
                  aria-label="Collezione carta"
                />
                <input
                  type="text"
                  value={cardNumber}
                  onChange={(e) => setCardNumber(e.target.value)}
                  placeholder="N° carta (es. 4/102)"
                  className="qa-input"
                  maxLength={50}
                  aria-label="Numero carta"
                />
                <p className="col-span-2 text-[11px] text-ink-soft -mt-1">
                  🃏 Collezione + numero servono per pubblicarla in automatico su
                  CardTrader (prezzo = 4° più basso). Facoltativi.
                </p>
              </div>
            )}

            <label className="flex items-center gap-2 cursor-pointer text-sm">
              <input
                type="checkbox"
                checked={publishNow}
                onChange={(e) => setPublishNow(e.target.checked)}
                disabled={!listPrice.trim()}
              />
              <span className={listPrice.trim() ? "" : "opacity-50"}>
                🚀 Pubblica subito sul catalogo
                {!listPrice.trim() && " (serve il listino)"}
              </span>
            </label>

            {error && (
              <p className="text-pink-deep text-sm font-semibold">⚠ {error}</p>
            )}

            <button
              type="submit"
              disabled={busy || !title.trim() || !lotId}
              className="btn btn-primary w-full text-sm"
            >
              {busy
                ? (progress ?? "Salvo…")
                : draftItemId
                  ? "↻ Riprova (completa item)"
                  : "✨ Cataloga"}
            </button>
          </form>
        )}

        <CameraCapture
          open={cameraOpen}
          onClose={() => setCameraOpen(false)}
          onCapture={(file) => addPhotos([file])}
        />

        <style>{`
          .qa-input {
            display: block;
            width: 100%;
            padding: 0.6rem 0.8rem;
            border: 1px solid rgba(61, 42, 92, 0.12);
            border-radius: 12px;
            background: #fffaf3;
            color: #3d2a5c;
            font-family: "Manrope", sans-serif;
            font-size: 16px;
            outline: none;
          }
          .qa-input:focus {
            box-shadow: 0 0 0 3px rgba(248, 168, 200, 0.45);
            border-color: #e879a8;
          }
        `}</style>
      </div>
    </div>
  );
}
