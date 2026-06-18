"use client";

import { useEffect, useState } from "react";
import { AdminShell } from "@/components/admin/AdminShell";
import { adminApi } from "@/lib/admin-api";
import type { MiscSale, MiscSaleListResponse } from "@/lib/types";

const PLATFORMS = ["Vinted", "Wallapop", "Subito", "mercato", "eBay", "Altro"];
const SELLERS = ["C", "D"];

function fmtMoney(v: string | number | null | undefined): string {
  if (v == null || v === "") return "—";
  const n = typeof v === "number" ? v : Number(v);
  if (!Number.isFinite(n)) return "—";
  return new Intl.NumberFormat("it-IT", {
    style: "currency",
    currency: "EUR",
  }).format(n);
}

export default function AdminVenditePage() {
  const [items, setItems] = useState<MiscSale[]>([]);
  const [totalAmount, setTotalAmount] = useState("0");
  const [totalPaid, setTotalPaid] = useState("0");
  const [totalUnpaid, setTotalUnpaid] = useState("0");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [year, setYear] = useState<string>(String(new Date().getFullYear()));
  const [sellerFilter, setSellerFilter] = useState<string>("");

  // Form nuovo
  const [date, setDate] = useState("");
  const [item, setItem] = useState("");
  const [amount, setAmount] = useState("");
  const [seller, setSeller] = useState("C");
  const [platform, setPlatform] = useState("Vinted");
  const [paidByBuyer, setPaidByBuyer] = useState(false);

  async function reload() {
    setLoading(true);
    setError(null);
    try {
      const qs = new URLSearchParams();
      if (year) qs.set("year", year);
      if (sellerFilter) qs.set("seller", sellerFilter);
      const data = await adminApi.get<MiscSaleListResponse>(
        `/api/misc-sales/?${qs}`,
      );
      setItems(data.items);
      setTotalAmount(data.total_amount);
      setTotalPaid(data.total_paid);
      setTotalUnpaid(data.total_unpaid);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [year, sellerFilter]);

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await adminApi.post("/api/misc-sales/", {
        sale_date: date || null,
        item: item.trim(),
        amount: Number(amount),
        seller,
        platform,
        paid_by_buyer: paidByBuyer,
      });
      setDate("");
      setItem("");
      setAmount("");
      setPaidByBuyer(false);
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleSave(id: number, payload: Record<string, unknown>) {
    setBusy(true);
    try {
      await adminApi.patch(`/api/misc-sales/${id}`, payload);
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete(id: number) {
    if (!confirm("Eliminare questa vendita?")) return;
    setBusy(true);
    try {
      await adminApi.delete(`/api/misc-sales/${id}`);
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <AdminShell>
      <h1 className="display text-3xl text-ink mb-1">💰 Vendite</h1>
      <p className="text-ink-soft mb-6 text-sm">
        Vendite generiche su Vinted/Wallapop/mercato per cose senza scheda nel catalogo
        (vestiti, libri, oggetti vari). Clone del foglio "Vendite".
      </p>

      {error && (
        <div className="card p-4 mb-4 text-pink-deep font-semibold">⚠ {error}</div>
      )}

      <div className="flex items-end gap-3 mb-4 flex-wrap">
        <label className="block">
          <span className="text-xs font-bold uppercase tracking-wider text-ink-soft">
            Anno
          </span>
          <select
            value={year}
            onChange={(e) => setYear(e.target.value)}
            className="input mt-1"
          >
            <option value="">Tutti</option>
            {[
              new Date().getFullYear(),
              new Date().getFullYear() - 1,
              new Date().getFullYear() - 2,
            ].map((y) => (
              <option key={y} value={y}>{y}</option>
            ))}
          </select>
        </label>
        <label className="block">
          <span className="text-xs font-bold uppercase tracking-wider text-ink-soft">
            Venditore
          </span>
          <select
            value={sellerFilter}
            onChange={(e) => setSellerFilter(e.target.value)}
            className="input mt-1"
          >
            <option value="">Tutti</option>
            {SELLERS.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </label>
        <div className="grid grid-cols-3 gap-2 flex-1">
          <Totale label="Tot venduto" value={fmtMoney(totalAmount)} color="bg-mint" />
          <Totale label="Pagate" value={fmtMoney(totalPaid)} color="bg-sky" />
          <Totale label="Non pagate" value={fmtMoney(totalUnpaid)} color="bg-pink-soft" />
        </div>
      </div>

      <form onSubmit={handleAdd} className="card p-4 mb-6">
        <h2 className="display text-base text-ink mb-3">+ Aggiungi vendita</h2>
        <div className="grid sm:grid-cols-6 gap-3">
          <label className="block">
            <span className="text-xs font-bold uppercase tracking-wider text-ink-soft">
              Data
            </span>
            <input
              type="date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
              className="input mt-1"
            />
          </label>
          <label className="block sm:col-span-2">
            <span className="text-xs font-bold uppercase tracking-wider text-ink-soft">
              Oggetto *
            </span>
            <input
              type="text"
              required
              value={item}
              onChange={(e) => setItem(e.target.value)}
              placeholder="giacchetto k-way"
              className="input mt-1"
            />
          </label>
          <label className="block">
            <span className="text-xs font-bold uppercase tracking-wider text-ink-soft">
              Importo *
            </span>
            <input
              type="number"
              step="0.01"
              min="0"
              required
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              className="input mt-1"
            />
          </label>
          <label className="block">
            <span className="text-xs font-bold uppercase tracking-wider text-ink-soft">
              Venditore
            </span>
            <select
              value={seller}
              onChange={(e) => setSeller(e.target.value)}
              className="input mt-1"
            >
              {SELLERS.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </label>
          <label className="block">
            <span className="text-xs font-bold uppercase tracking-wider text-ink-soft">
              Piattaforma
            </span>
            <select
              value={platform}
              onChange={(e) => setPlatform(e.target.value)}
              className="input mt-1"
            >
              {PLATFORMS.map((p) => (
                <option key={p} value={p}>{p}</option>
              ))}
            </select>
          </label>
        </div>
        <div className="flex items-center justify-between mt-3 gap-3 flex-wrap">
          <label className="inline-flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={paidByBuyer}
              onChange={(e) => setPaidByBuyer(e.target.checked)}
              className="w-4 h-4 accent-pink-deep"
            />
            <span>Pagato dal compratore (già incassato)</span>
          </label>
          <button
            type="submit"
            className="btn btn-primary text-sm"
            disabled={busy}
          >
            {busy ? "..." : "Aggiungi vendita"}
          </button>
        </div>
      </form>

      {loading && <p className="text-ink-soft">Caricamento…</p>}

      {!loading && items.length === 0 && (
        <div className="card p-10 text-center">
          <p className="text-ink-soft">Nessuna vendita con i filtri correnti.</p>
        </div>
      )}

      {!loading && items.length > 0 && (
        <div className="card overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="bg-white/60 backdrop-blur border-b border-ink/10 text-ink-soft text-[11px] uppercase tracking-wider">
              <tr>
                <th className="text-left py-2 px-3">Data</th>
                <th className="text-left py-2 px-3">Oggetto</th>
                <th className="text-right py-2 px-3">Importo</th>
                <th className="text-left py-2 px-3 hidden sm:table-cell">Vend.</th>
                <th className="text-left py-2 px-3 hidden sm:table-cell">Piattaforma</th>
                <th className="text-center py-2 px-3">Pagato</th>
                <th className="py-2 px-3"></th>
              </tr>
            </thead>
            <tbody>
              {items.map((s) => (
                <SaleRow
                  key={s.id}
                  item={s}
                  busy={busy}
                  onSave={(p) => handleSave(s.id, p)}
                  onDelete={() => handleDelete(s.id)}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}

      <style>{`
        .input {
          display: block;
          width: 100%;
          padding: 0.5rem 0.7rem;
          border: 1px solid rgba(61, 42, 92, 0.12);
          border-radius: 12px;
          background: #fffaf3;
          color: #3d2a5c;
          font-family: "Manrope", sans-serif;
          font-size: 0.9rem;
          outline: none;
        }
        .input:focus {
          box-shadow: 0 0 0 3px rgba(248, 168, 200, 0.45);
          border-color: #e879a8;
        }
      `}</style>
    </AdminShell>
  );
}

function Totale({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div className="card p-3 relative overflow-hidden">
      <div className={`absolute -top-4 -right-4 w-16 h-16 rounded-full ${color} blur-2xl opacity-50`} />
      <span className="text-[10px] uppercase tracking-wider text-ink-soft relative block">{label}</span>
      <span className="display text-lg text-ink mt-0.5 block tabular-nums relative">{value}</span>
    </div>
  );
}

function SaleRow({
  item,
  busy,
  onSave,
  onDelete,
}: {
  item: MiscSale;
  busy: boolean;
  onSave: (p: Record<string, unknown>) => void;
  onDelete: () => void;
}) {
  const [date, setDate] = useState(item.sale_date ?? "");
  const [name, setName] = useState(item.item);
  const [amount, setAmount] = useState(item.amount);
  const [seller, setSeller] = useState(item.seller ?? "");
  const [platform, setPlatform] = useState(item.platform ?? "");
  const [paid, setPaid] = useState(item.paid_by_buyer);

  const dirty =
    (date || null) !== (item.sale_date || null) ||
    name !== item.item ||
    amount !== item.amount ||
    (seller || null) !== (item.seller || null) ||
    (platform || null) !== (item.platform || null) ||
    paid !== item.paid_by_buyer;

  function save() {
    onSave({
      sale_date: date || null,
      item: name.trim(),
      amount: Number(amount),
      seller: seller || null,
      platform: platform || null,
      paid_by_buyer: paid,
    });
  }

  return (
    <tr className="border-b border-ink/5 hover:bg-pink-soft/30">
      <td className="py-2 px-3">
        <input
          type="date"
          value={date}
          onChange={(e) => setDate(e.target.value)}
          className="input"
        />
      </td>
      <td className="py-2 px-3">
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="input"
        />
      </td>
      <td className="py-2 px-3 text-right">
        <input
          type="number"
          step="0.01"
          min="0"
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
          className="input text-right tabular-nums"
        />
      </td>
      <td className="py-2 px-3 hidden sm:table-cell">
        <select
          value={seller}
          onChange={(e) => setSeller(e.target.value)}
          className="input"
        >
          <option value="">—</option>
          {SELLERS.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
      </td>
      <td className="py-2 px-3 hidden sm:table-cell">
        <select
          value={platform}
          onChange={(e) => setPlatform(e.target.value)}
          className="input"
        >
          <option value="">—</option>
          {PLATFORMS.map((p) => (
            <option key={p} value={p}>{p}</option>
          ))}
        </select>
      </td>
      <td className="py-2 px-3 text-center">
        <input
          type="checkbox"
          checked={paid}
          onChange={(e) => setPaid(e.target.checked)}
          className="w-4 h-4 accent-pink-deep"
        />
      </td>
      <td className="py-2 px-3 whitespace-nowrap">
        <div className="flex gap-1">
          {dirty && (
            <button
              type="button"
              className="btn btn-primary text-xs px-3 py-1"
              onClick={save}
              disabled={busy}
            >
              Salva
            </button>
          )}
          <button
            type="button"
            className="btn btn-ghost text-xs px-3 py-1"
            onClick={onDelete}
            disabled={busy}
          >
            🗑
          </button>
        </div>
      </td>
    </tr>
  );
}
