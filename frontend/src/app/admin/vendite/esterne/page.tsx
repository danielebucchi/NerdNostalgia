"use client";

import { useState } from "react";
import { AdminShell } from "@/components/admin/AdminShell";
import { VenditeNav } from "@/components/admin/VenditeNav";
import { SalesTable } from "@/components/admin/vendite/SalesTable";
import { usePlatforms } from "@/lib/usePlatforms";

function todayYear() { return new Date().getFullYear(); }

export default function VenditeEsternePage() {
  const { items: platformList } = usePlatforms();
  const platformNames = ["", ...platformList.map((p) => p.name)];
  const [year, setYear] = useState<string>(String(todayYear()));

  return (
    <AdminShell>
      <VenditeNav active="esterne" />

      <div className="flex items-center justify-between mb-4 gap-3 flex-wrap">
        <p className="text-ink-soft text-sm">
          Vendite NON legate al catalogo del sito (mercato, privati, ecc.).
          Contribuiscono al bilancio dashboard come <em>vendite varie</em>.
        </p>
        <select value={year} onChange={(e) => setYear(e.target.value)} className="input" style={{ maxWidth: 160 }}>
          <option value="">Tutti gli anni</option>
          {[todayYear(), todayYear() - 1, todayYear() - 2, todayYear() - 3].map((y) => (
            <option key={y} value={y}>Anno {y}</option>
          ))}
        </select>
      </div>

      <SalesTable kind="external" year={year} platformNames={platformNames} />

      <style>{styles}</style>
    </AdminShell>
  );
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
