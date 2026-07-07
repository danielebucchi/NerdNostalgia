"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { AdminShell } from "@/components/admin/AdminShell";
import { ImageGalleryEditor } from "@/components/admin/ImageGalleryEditor";
import { adminApi } from "@/lib/admin-api";
import { useCategories } from "@/lib/useCategories";
import { usePlatforms } from "@/lib/usePlatforms";
import type {
  Category,
  InventoryItem,
  InventoryItemStatus,
  InventoryListResponse,
  Lot,
  LotStatus,
} from "@/lib/types";

const PEOPLE = ["", "C", "D"];

const ITEM_STATUSES: InventoryItemStatus[] = [
  "DRAFT", "LINKED", "LISTED", "RESERVED", "SOLD", "ARCHIVED",
];

const STATUS_LABEL: Record<InventoryItemStatus, string> = {
  DRAFT: "Bozza",
  LINKED: "Art. DRAFT",
  LISTED: "Pubblicato",
  RESERVED: "Riservato",
  SOLD: "Venduto",
  ARCHIVED: "Archiviato",
};

const STATUS_COLOR: Record<InventoryItemStatus, string> = {
  DRAFT: "bg-ink/10 text-ink",
  LINKED: "bg-lilac-soft text-lilac-deep",
  LISTED: "bg-mint text-mint-deep",
  RESERVED: "bg-pink-soft text-pink-deep",
  SOLD: "bg-mint-deep text-white",
  ARCHIVED: "bg-ink/20 text-ink-soft",
};

function fmtMoney(v: string | number | null | undefined): string {
  if (v == null || v === "") return "—";
  const n = typeof v === "number" ? v : Number(v);
  if (!Number.isFinite(n)) return "—";
  return new Intl.NumberFormat("it-IT", {
    style: "currency",
    currency: "EUR",
    maximumFractionDigits: 2,
  }).format(n);
}

export default function AdminLotDetailPage() {
  const params = useParams();
  const router = useRouter();
  const lotId = Number(params.id);

  const { flat: categories } = useCategories();
  const { items: platformList } = usePlatforms();
  const platformNames = useMemo(() => ["", ...platformList.map((p) => p.name)], [platformList]);
  const [lot, setLot] = useState<Lot | null>(null);
  const [items, setItems] = useState<InventoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [photosOpen, setPhotosOpen] = useState<number | null>(null);

  async function reload() {
    setLoading(true);
    setError(null);
    try {
      const [lotData, inv] = await Promise.all([
        adminApi.get<Lot>(`/api/lots/${lotId}`),
        adminApi.get<InventoryListResponse>(`/api/inventory/?lot_id=${lotId}`),
      ]);
      setLot(lotData);
      setItems(inv.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (Number.isFinite(lotId)) reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lotId]);

  async function saveLotMeta(patch: Partial<Lot>) {
    if (!lot) return;
    setBusy(true);
    try {
      await adminApi.patch(`/api/lots/${lotId}`, patch);
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleDistribute(totalCost: number) {
    setBusy(true);
    setError(null);
    try {
      const resp = await adminApi.post<{
        items_updated: number; total_pieces: number; unit_cost: string;
      }>(`/api/lots/${lotId}/distribute-cost`, { total_cost: totalCost });
      await reload();
      alert(
        `Distribuito ${totalCost.toFixed(2)} €:\n` +
        `${resp.items_updated} item · ${resp.total_pieces} pezzi\n` +
        `Costo unitario: ${Number(resp.unit_cost).toFixed(2)} €`,
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleAddItem(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      const form = e.target as HTMLFormElement;
      const fd = new FormData(form);
      const payload = {
        lot_id: lotId,
        title: String(fd.get("title") || "").trim(),
        cost: fd.get("cost") ? Number(fd.get("cost")) : null,
        category_id: fd.get("category_id") ? Number(fd.get("category_id")) : null,
        quantity: Number(fd.get("quantity") || 1),
        card_collection: String(fd.get("card_collection") || "") || null,
        card_number: String(fd.get("card_number") || "") || null,
      };
      if (!payload.title) throw new Error("Titolo obbligatorio");
      await adminApi.post("/api/inventory/", payload);
      form.reset();
      (form.elements.namedItem("title") as HTMLInputElement)?.focus();
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleSaveItem(id: number, patch: Partial<InventoryItem>) {
    setBusy(true);
    try {
      await adminApi.patch(`/api/inventory/${id}`, patch);
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleDeleteItem(id: number) {
    if (!confirm("Eliminare questo item?")) return;
    setBusy(true);
    try {
      await adminApi.delete(`/api/inventory/${id}`);
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleBulkPublish() {
    const ids = Array.from(selected);
    if (ids.length === 0) return;
    if (!confirm(`Creare ${ids.length} bozze Article DRAFT?`)) return;
    setBusy(true);
    try {
      const resp = await adminApi.post<{ created: number; skipped: number }>(
        `/api/lots/${lotId}/bulk-publish`,
        { item_ids: ids },
      );
      alert(`Create: ${resp.created}\nSaltate (già pubblicate): ${resp.skipped}`);
      setSelected(new Set());
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleDeleteLot() {
    if (!lot) return;
    if (items.length > 0) {
      alert("Lotto non vuoto: archivialo invece di eliminarlo.");
      return;
    }
    if (!confirm(`Eliminare il lotto ${lot.code}?`)) return;
    setBusy(true);
    try {
      await adminApi.delete(`/api/lots/${lotId}`);
      router.push("/admin/lotti");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setBusy(false);
    }
  }

  if (loading && !lot) {
    return <AdminShell><p className="text-ink-soft">Caricamento…</p></AdminShell>;
  }

  if (!lot) {
    return (
      <AdminShell>
        <p className="text-pink-deep">Lotto non trovato.</p>
        <Link href="/admin/lotti" className="btn btn-ghost text-sm mt-3">← Torna alla lista</Link>
      </AdminShell>
    );
  }

  return (
    <AdminShell>
      <div className="mb-3">
        <Link href="/admin/lotti" className="text-xs text-ink-soft hover:text-ink">← Tutti i lotti</Link>
      </div>

      <div className="flex items-start justify-between mb-4 gap-3 flex-wrap">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="font-mono text-sm px-2 py-0.5 rounded-full bg-lilac-soft text-lilac-deep">
              {lot.code}
            </span>
            <span className={`text-[10px] px-2 py-0.5 rounded-full uppercase tracking-wider ${
              lot.status === "OPEN" ? "bg-mint text-mint-deep"
              : lot.status === "CLOSED" ? "bg-ink/10 text-ink"
              : "bg-ink/20 text-ink-soft"
            }`}>
              {lot.status}
            </span>
          </div>
          <h1 className="display text-3xl text-ink">{lot.title || "(senza nome)"}</h1>
        </div>
        <button
          type="button"
          onClick={handleDeleteLot}
          disabled={busy || items.length > 0}
          className="btn btn-ghost text-xs"
          title={items.length > 0 ? "Lotto non vuoto" : "Elimina lotto"}
        >
          🗑 Elimina lotto
        </button>
      </div>

      {error && (
        <div className="card p-4 mb-4 text-pink-deep font-semibold">⚠ {error}</div>
      )}

      <LotMetaEditor lot={lot} busy={busy} platformNames={platformNames} onSave={saveLotMeta} />

      <div className="grid grid-cols-2 lg:grid-cols-5 gap-2 mb-4">
        <TotalCard label="Item" value={String(lot.items_count)} color="bg-pink-soft" />
        <TotalCard label="Costo totale" value={fmtMoney(lot.cost_sum)} color="bg-pink-soft" />
        <TotalCard label="Ricavi" value={fmtMoney(lot.revenue_sum)} color="bg-mint" />
        <TotalCard
          label="Profitto"
          value={fmtMoney(lot.profit_sum)}
          color={Number(lot.profit_sum || 0) >= 0 ? "bg-mint" : "bg-pink"}
          accent
        />
        <TotalCard label="Immob." value={fmtMoney(lot.immobilizzato)} color="bg-lilac-soft" />
      </div>

      <DistributeBox busy={busy} onDistribute={handleDistribute} suggested={lot.total_cost} />

      <form onSubmit={handleAddItem} className="card p-4 mb-4">
        <h2 className="display text-base text-ink mb-3">+ Aggiungi item al lotto</h2>
        <div className="grid sm:grid-cols-6 gap-2">
          <input name="title" placeholder="Oggetto *" required className="input col-span-2" />
          <select name="category_id" className="input col-span-2">
            <option value="">— categoria —</option>
            {renderCategoryOptions(categories)}
          </select>
          <input name="cost" type="number" step="0.01" placeholder="Costo unit. €" className="input" />
          <input name="quantity" type="number" min="1" defaultValue="1" placeholder="Qty" className="input" />
        </div>
        <div className="grid sm:grid-cols-6 gap-2 mt-2">
          <input name="card_collection" placeholder="Collezione (carte)" className="input col-span-2" />
          <input name="card_number" placeholder="N° carta" className="input" />
          <button type="submit" disabled={busy} className="btn btn-primary text-sm col-span-3">
            {busy ? "..." : "Aggiungi"}
          </button>
        </div>
      </form>

      {selected.size > 0 && (
        <div className="card p-3 mb-3 bg-lilac-soft/40 flex items-center justify-between flex-wrap gap-2">
          <span className="text-sm font-semibold text-lilac-deep">
            {selected.size} item selezionati
          </span>
          <div className="flex gap-2">
            <button onClick={handleBulkPublish} disabled={busy} className="btn btn-primary text-xs">
              📝 Crea bozze Article ({selected.size})
            </button>
            <button onClick={() => setSelected(new Set())} className="btn btn-ghost text-xs">
              Deseleziona
            </button>
          </div>
        </div>
      )}

      {items.length === 0 ? (
        <div className="card p-10 text-center">
          <p className="text-ink-soft">Nessun item nel lotto. Aggiungine uno qui sopra.</p>
        </div>
      ) : (
        <div className="card overflow-x-auto">
          <table className="min-w-full text-xs">
            <thead className="bg-white/60 backdrop-blur border-b border-ink/10 text-ink-soft uppercase tracking-wider">
              <tr>
                <Th>
                  <input
                    type="checkbox"
                    checked={selected.size === items.length && items.length > 0}
                    onChange={(e) => {
                      setSelected(e.target.checked ? new Set(items.map((i) => i.id)) : new Set());
                    }}
                  />
                </Th>
                <Th>Stato</Th>
                <Th>Foto</Th>
                <Th>Oggetto</Th>
                <Th>Cat.</Th>
                <Th className="text-right">Costo</Th>
                <Th>Data vend.</Th>
                <Th className="text-right">Ricavo</Th>
                <Th className="text-right">Fee</Th>
                <Th className="text-right">Sped.</Th>
                <Th>Pf. vend.</Th>
                <Th>Chi</Th>
                <Th className="text-right">Netto</Th>
                <Th className="text-right">Profitto</Th>
                <Th>Article</Th>
                <Th></Th>
              </tr>
            </thead>
            <tbody>
              {items.map((it) => (
                <Row
                  key={it.id}
                  item={it}
                  categories={categories}
                  platformNames={platformNames}
                  busy={busy}
                  selected={selected.has(it.id)}
                  onToggle={() => {
                    const next = new Set(selected);
                    if (next.has(it.id)) next.delete(it.id);
                    else next.add(it.id);
                    setSelected(next);
                  }}
                  onSave={(patch) => handleSaveItem(it.id, patch)}
                  onDelete={() => handleDeleteItem(it.id)}
                  onOpenPhotos={() => setPhotosOpen(it.id)}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}

      <p className="text-xs text-ink-soft mt-3">
        Seleziona uno o più item e usa <strong>📝 Crea bozze Article</strong> per
        pubblicarli sul sito in stato DRAFT. Poi completi foto e descrizione in{" "}
        <code>/admin/articles</code>.
      </p>

      {photosOpen !== null && (() => {
        const target = items.find((i) => i.id === photosOpen);
        if (!target) return null;
        return (
          <PhotosDialog
            item={target}
            onClose={() => setPhotosOpen(null)}
            onImagesChange={(imgs) => {
              // Aggiorna in-place la riga senza ricaricare l'intera tabella:
              // reload() sarebbe uno spreco per una modifica cosi' localizzata.
              setItems((curr) =>
                curr.map((i) => (i.id === target.id ? { ...i, images: imgs } : i)),
              );
            }}
          />
        );
      })()}

      <style>{styles}</style>
    </AdminShell>
  );
}

function PhotosDialog({
  item,
  onClose,
  onImagesChange,
}: {
  item: InventoryItem;
  onClose: () => void;
  onImagesChange: (images: string[]) => void;
}) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-ink/50 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="card w-full max-w-3xl p-5 sm:p-6 max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-3 mb-4">
          <div className="min-w-0">
            <h2 className="display text-xl text-ink truncate">Foto — {item.title}</h2>
            <p className="text-xs text-ink-soft mt-0.5">
              Le foto vengono copiate sull&apos;articolo pubblico quando pubblichi il lotto.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="w-8 h-8 rounded-full border-2 border-ink flex items-center justify-center text-ink hover:bg-pink shrink-0"
            aria-label="Chiudi"
          >
            ✕
          </button>
        </div>
        <ImageGalleryEditor
          scope="inventory"
          entityId={item.id}
          images={item.images ?? []}
          onChange={onImagesChange}
        />
      </div>
    </div>
  );
}

function LotMetaEditor({
  lot,
  busy,
  platformNames,
  onSave,
}: {
  lot: Lot;
  busy: boolean;
  platformNames: string[];
  onSave: (patch: Partial<Lot>) => Promise<void> | void;
}) {
  const [title, setTitle] = useState(lot.title ?? "");
  const [purchaseDate, setPurchaseDate] = useState(lot.purchase_date ?? "");
  const [purchasePlatform, setPurchasePlatform] = useState(lot.purchase_platform ?? "");
  const [boughtBy, setBoughtBy] = useState(lot.bought_by ?? "");
  const [notes, setNotes] = useState(lot.notes ?? "");
  const [status, setStatus] = useState<LotStatus>(lot.status);

  function maybe(key: keyof Lot, value: unknown, original: unknown) {
    if (value === original) return;
    if (typeof value === "string" && value === "" && (original === null || original === "")) return;
    onSave({ [key]: (value === "" ? null : value) as never });
  }

  return (
    <div className="card p-4 mb-4 grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
      <Field label="Nome">
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          onBlur={() => maybe("title", title, lot.title)}
          disabled={busy}
          className="input"
        />
      </Field>
      <Field label="Data acquisto">
        <input
          type="date"
          value={purchaseDate}
          onChange={(e) => setPurchaseDate(e.target.value)}
          onBlur={() => maybe("purchase_date", purchaseDate, lot.purchase_date)}
          disabled={busy}
          className="input"
        />
      </Field>
      <Field label="Stato lotto">
        <select
          value={status}
          onChange={(e) => {
            const v = e.target.value as LotStatus;
            setStatus(v);
            if (v !== lot.status) onSave({ status: v });
          }}
          disabled={busy}
          className="input"
        >
          <option value="OPEN">Aperto</option>
          <option value="CLOSED">Chiuso</option>
          <option value="ARCHIVED">Archiviato</option>
        </select>
      </Field>
      <Field label="Piattaforma acquisto">
        <select
          value={purchasePlatform}
          onChange={(e) => {
            const v = e.target.value;
            setPurchasePlatform(v);
            if (v !== (lot.purchase_platform ?? "")) onSave({ purchase_platform: (v || null) as never });
          }}
          disabled={busy}
          className="input"
        >
          {platformNames.map((p) => <option key={p || "_"} value={p}>{p || "—"}</option>)}
        </select>
      </Field>
      <Field label="Chi compra">
        <select
          value={boughtBy}
          onChange={(e) => {
            const v = e.target.value;
            setBoughtBy(v);
            if (v !== (lot.bought_by ?? "")) onSave({ bought_by: (v || null) as never });
          }}
          disabled={busy}
          className="input"
        >
          {PEOPLE.map((p) => <option key={p || "_"} value={p}>{p || "—"}</option>)}
        </select>
      </Field>
      <Field label="Note">
        <input
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          onBlur={() => maybe("notes", notes, lot.notes)}
          disabled={busy}
          className="input"
        />
      </Field>
    </div>
  );
}

function DistributeBox({
  busy,
  suggested,
  onDistribute,
}: {
  busy: boolean;
  suggested: string | null;
  onDistribute: (totalCost: number) => Promise<void> | void;
}) {
  const [total, setTotal] = useState(suggested ?? "");
  const valid = total.trim() !== "" && Number(total) >= 0;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!valid) return;
    if (!confirm(`Distribuire ${Number(total).toFixed(2)} € su tutti gli item del lotto?`)) return;
    await onDistribute(Number(total));
  }

  return (
    <form onSubmit={handleSubmit} className="card p-3 mb-4 bg-lilac-soft/30 flex flex-wrap items-center gap-2">
      <span className="text-xs text-ink-soft">
        💰 <strong>Distribuisci costo</strong> sul lotto (diviso per quantità totale):
      </span>
      <input
        type="number" step="0.01" min="0"
        value={total}
        onChange={(e) => setTotal(e.target.value)}
        placeholder="Costo totale €"
        className="input"
        style={{ maxWidth: 180 }}
      />
      <button type="submit" disabled={busy || !valid} className="btn btn-primary text-sm">
        Distribuisci
      </button>
    </form>
  );
}

function Row({
  item, categories, platformNames, busy, selected, onToggle, onSave, onDelete, onOpenPhotos,
}: {
  item: InventoryItem;
  categories: Category[];
  platformNames: string[];
  busy: boolean;
  selected: boolean;
  onToggle: () => void;
  onSave: (patch: Partial<InventoryItem>) => void;
  onDelete: () => void;
  onOpenPhotos: () => void;
}) {
  const [title, setTitle] = useState(item.title);
  const [cost, setCost] = useState(item.cost ?? "");
  const [soldDate, setSoldDate] = useState(item.sold_date ?? "");
  const [salePrice, setSalePrice] = useState(item.sale_price ?? "");
  const [fee, setFee] = useState(item.fee_amount ?? "");
  const [shipping, setShipping] = useState(item.shipping_cost ?? "");
  const [soldPlatform, setSoldPlatform] = useState(item.sold_platform ?? "");
  const [soldBy, setSoldBy] = useState(item.sold_by ?? "");
  const [categoryId, setCategoryId] = useState<string>(
    item.category_id != null ? String(item.category_id) : "",
  );

  function maybeSave(key: keyof InventoryItem, current: unknown, original: unknown) {
    if (current === original) return;
    if (typeof current === "string" && current === "" && (original === null || original === "")) return;
    onSave({ [key]: (current === "" ? null : current) as never });
  }

  return (
    <tr className="border-b border-ink/5 hover:bg-pink-soft/20">
      <Td>
        <input type="checkbox" checked={selected} onChange={onToggle} />
      </Td>
      <Td>
        <select
          value={item.status}
          onChange={(e) => {
            const v = e.target.value as InventoryItemStatus;
            if (v !== item.status) {
              adminApi
                .patch(`/api/inventory/${item.id}/status`, { status: v })
                .then(() => onSave({}));
            }
          }}
          className={`cell-input text-[10px] font-semibold rounded-full px-2 ${STATUS_COLOR[item.status]}`}
        >
          {ITEM_STATUSES.map((s) => (
            <option key={s} value={s}>{STATUS_LABEL[s]}</option>
          ))}
        </select>
      </Td>
      <Td>
        <PhotoCell
          images={item.images ?? []}
          onOpen={onOpenPhotos}
        />
      </Td>
      <Td>
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          onBlur={() => maybeSave("title", title, item.title)}
          className="cell-input font-semibold text-ink min-w-[180px]"
        />
      </Td>
      <Td>
        <select
          value={categoryId}
          onChange={(e) => {
            const v = e.target.value;
            setCategoryId(v);
            const next = v === "" ? null : Number(v);
            if (next !== item.category_id) onSave({ category_id: next as never });
          }}
          className="cell-input text-[11px] max-w-[120px]"
        >
          <option value="">—</option>
          {renderCategoryOptions(categories)}
        </select>
      </Td>
      <Td className="text-right">
        <input
          type="number" step="0.01"
          value={cost ?? ""}
          onChange={(e) => setCost(e.target.value)}
          onBlur={() => maybeSave("cost", cost, item.cost)}
          className="cell-input text-right tabular-nums w-20"
        />
      </Td>
      <Td>
        <input
          type="date"
          value={soldDate}
          onChange={(e) => setSoldDate(e.target.value)}
          onBlur={() => maybeSave("sold_date", soldDate, item.sold_date)}
          className="cell-input text-[11px] w-28"
        />
      </Td>
      <Td className="text-right">
        <input
          type="number" step="0.01"
          value={salePrice ?? ""}
          onChange={(e) => setSalePrice(e.target.value)}
          onBlur={() => maybeSave("sale_price", salePrice, item.sale_price)}
          className="cell-input text-right tabular-nums w-20"
        />
      </Td>
      <Td className="text-right">
        <input
          type="number" step="0.01"
          value={fee ?? ""}
          onChange={(e) => setFee(e.target.value)}
          onBlur={() => maybeSave("fee_amount", fee, item.fee_amount)}
          className="cell-input text-right tabular-nums w-16"
        />
      </Td>
      <Td className="text-right">
        <input
          type="number" step="0.01"
          value={shipping ?? ""}
          onChange={(e) => setShipping(e.target.value)}
          onBlur={() => maybeSave("shipping_cost", shipping, item.shipping_cost)}
          className="cell-input text-right tabular-nums w-16"
        />
      </Td>
      <Td>
        <select
          value={soldPlatform}
          onChange={(e) => {
            const v = e.target.value;
            setSoldPlatform(v);
            if (v !== (item.sold_platform ?? "")) onSave({ sold_platform: (v || null) as never });
          }}
          className="cell-input text-[11px] w-24"
        >
          {platformNames.map((p) => <option key={p || "_"} value={p}>{p || "—"}</option>)}
        </select>
      </Td>
      <Td>
        <select
          value={soldBy}
          onChange={(e) => {
            const v = e.target.value;
            setSoldBy(v);
            if (v !== (item.sold_by ?? "")) onSave({ sold_by: (v || null) as never });
          }}
          className="cell-input text-[11px] w-12"
        >
          {PEOPLE.map((p) => <option key={p || "_"} value={p}>{p || "—"}</option>)}
        </select>
      </Td>
      <Td className="text-right tabular-nums text-ink-soft">{fmtMoney(item.net_revenue)}</Td>
      <Td className="text-right tabular-nums">
        <span className={
          Number(item.profit ?? 0) > 0
            ? "text-mint-deep font-bold"
            : Number(item.profit ?? 0) < 0
              ? "text-pink-deep font-bold"
              : "text-ink-soft"
        }>
          {item.sold_date ? fmtMoney(item.profit) : "—"}
        </span>
      </Td>
      <Td>
        {item.article_id ? (
          <Link
            href={`/admin/articles/${item.article_id}`}
            className="chip chip-mint text-[10px]"
            title={`Article #${item.article_id}`}
          >
            #{item.article_id} ↗
          </Link>
        ) : (
          <span className="text-ink-soft/60 text-[10px]">—</span>
        )}
      </Td>
      <Td>
        <button
          type="button"
          onClick={onDelete}
          disabled={busy}
          className="btn btn-ghost text-[10px] px-2 py-1"
          title="Elimina"
        >
          🗑
        </button>
      </Td>
    </tr>
  );
}

function Th({ children, className = "" }: { children?: React.ReactNode; className?: string }) {
  return <th className={`text-left py-2 px-2 font-semibold whitespace-nowrap ${className}`}>{children}</th>;
}

function Td({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <td className={`py-1 px-1 align-middle ${className}`}>{children}</td>;
}

function PhotoCell({ images, onOpen }: { images: string[]; onOpen: () => void }) {
  const cover = images[0];
  const thumb = cover && cover.endsWith(".webp") && !cover.endsWith(".thumb.webp")
    ? cover.slice(0, -".webp".length) + ".thumb.webp"
    : cover;
  return (
    <button
      type="button"
      onClick={onOpen}
      title={images.length > 0 ? `${images.length} foto — gestisci` : "Aggiungi foto"}
      className="relative w-10 h-10 rounded-md overflow-hidden bg-ink/5 ring-1 ring-ink/10 hover:ring-pink-deep flex items-center justify-center"
    >
      {cover ? (
        <>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={thumb} alt="" loading="lazy" className="w-full h-full object-cover" />
          {images.length > 1 && (
            <span className="absolute bottom-0 right-0 bg-ink/80 text-cream text-[9px] font-bold px-1 rounded-tl">
              {images.length}
            </span>
          )}
        </>
      ) : (
        <span className="text-lg text-ink-soft/50">＋</span>
      )}
    </button>
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

function TotalCard({ label, value, color, accent }: { label: string; value: string; color: string; accent?: boolean }) {
  return (
    <div className="card p-3 relative overflow-hidden">
      <div className={`absolute -top-4 -right-4 w-16 h-16 rounded-full ${color} blur-2xl opacity-60`} />
      <span className="text-[10px] uppercase tracking-wider text-ink-soft relative block">{label}</span>
      <span className={`display mt-0.5 block tabular-nums relative ${accent ? "text-xl text-pink-deep" : "text-lg text-ink"}`}>
        {value}
      </span>
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
  .cell-input {
    background: transparent;
    border: none;
    outline: none;
    padding: 0.25rem 0.4rem;
    width: 100%;
    font: inherit;
    color: inherit;
    border-radius: 4px;
  }
  .cell-input:focus {
    background: #fffaf3;
    box-shadow: 0 0 0 2px rgba(168, 144, 216, 0.35);
  }
`;
