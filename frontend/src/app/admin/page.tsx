"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { AdminShell } from "@/components/admin/AdminShell";
import { adminApi } from "@/lib/admin-api";
import type {
  ArticleListResponse,
  DashboardTotals,
  InquiryStatus,
  WantedListResponse,
} from "@/lib/types";

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

const GROUP_LABELS: Record<string, string> = {
  carte: "Carte",
  videogiochi: "Videogiochi",
  nerdate: "Nerdate",
  altro: "Altro",
  vendite_varie: "Vendite varie",
  spese_carte: "Spese carte",
};

interface InquiryListLite {
  total: number;
  items: { id: number; status: InquiryStatus }[];
}

export default function AdminDashboardPage() {
  const [stats, setStats] = useState<{
    articlesPublished: number;
    articlesDraft: number;
    inquiriesNew: number;
    inquiriesTotal: number;
    wantedActive: number;
  } | null>(null);
  const [totals, setTotals] = useState<DashboardTotals | null>(null);
  const [year, setYear] = useState<number>(new Date().getFullYear());
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const [pub, draft, inqList, wantedList, totalsResp] = await Promise.all([
          adminApi.get<ArticleListResponse>("/api/articles/?status=PUBLISHED&limit=1"),
          adminApi.get<ArticleListResponse>("/api/articles/?status=DRAFT&limit=1"),
          adminApi.get<InquiryListLite>("/api/inquiries/?limit=100"),
          adminApi.get<WantedListResponse>("/api/wanted/?status=ACTIVE&limit=1"),
          adminApi.get<DashboardTotals>(`/api/dashboard/totals?year=${year}`),
        ]);
        setStats({
          articlesPublished: pub.total,
          articlesDraft: draft.total,
          inquiriesNew: inqList.items.filter((i) => i.status === "NEW").length,
          inquiriesTotal: inqList.total,
          wantedActive: wantedList.total,
        });
        setTotals(totalsResp);
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
      }
    })();
  }, [year]);

  return (
    <AdminShell>
      <h1 className="display text-2xl sm:text-3xl text-ink">Dashboard</h1>
      <p className="text-ink-soft mt-1 text-sm sm:text-base">
        Riepilogo a colpo d&apos;occhio dello stato del negozio.
      </p>

      {error && (
        <div className="card p-4 mt-6 text-pink-deep font-semibold">⚠ {error}</div>
      )}

      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 mt-8">
        <Stat
          label="Articoli pubblicati"
          value={stats?.articlesPublished}
          href="/admin/articles?status=PUBLISHED"
          tone="mint"
          icon="🎮"
        />
        <Stat
          label="Bozze"
          value={stats?.articlesDraft}
          href="/admin/articles?status=DRAFT"
          tone="lilac"
          icon="📝"
        />
        <Stat
          label="Richieste nuove"
          value={stats?.inquiriesNew}
          hint={stats ? `su ${stats.inquiriesTotal}` : ""}
          href="/admin/inquiries?status=NEW"
          tone="pink"
          icon="✉"
        />
        <Stat
          label="Wanted attivi"
          value={stats?.wantedActive}
          href="/admin/wanted"
          tone="sky"
          icon="🔍"
        />
      </div>

      {/* Bilancio anno — clone della sezione "Esterni" del foglio */}
      <div className="mt-10">
        <div className="flex items-end justify-between mb-3 gap-3 flex-wrap">
          <h2 className="display text-xl sm:text-2xl text-ink">
            📊 Bilancio {totals?.year ?? year}
          </h2>
          <select
            value={year}
            onChange={(e) => setYear(Number(e.target.value))}
            className="text-sm rounded-full bg-white/80 ring-1 ring-ink/10 px-3 py-1.5"
          >
            {[
              new Date().getFullYear(),
              new Date().getFullYear() - 1,
              new Date().getFullYear() - 2,
            ].map((y) => (
              <option key={y} value={y}>{y}</option>
            ))}
          </select>
        </div>

        {totals ? (
          <>
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
              <BigStat
                label="Ricavi totali"
                value={fmtMoney(totals.total_revenue)}
                color="bg-mint"
              />
              <BigStat
                label="Costi totali"
                value={fmtMoney(totals.total_cost)}
                color="bg-pink-soft"
              />
              <BigStat
                label="Profitto"
                value={fmtMoney(totals.total_profit)}
                color={Number(totals.total_profit) >= 0 ? "bg-mint" : "bg-pink"}
                accent
              />
              <BigStat
                label="Immobilizzato"
                value={fmtMoney(totals.total_immobilizzato)}
                color="bg-lilac-soft"
              />
            </div>

            <div className="grid sm:grid-cols-2 gap-4">
              <div className="card p-5">
                <h3 className="display text-base text-ink mb-3">Ricavi per gruppo</h3>
                <BreakdownTable data={totals.revenue_by_group} />
              </div>
              <div className="card p-5">
                <h3 className="display text-base text-ink mb-3">Profitto per gruppo</h3>
                <BreakdownTable data={totals.profit_by_group} highlightSign />
              </div>
            </div>

            <p className="text-xs text-ink-soft mt-3">
              {totals.articles_sold} articoli venduti · {totals.articles_available}{" "}
              disponibili · {totals.misc_sales_count} vendite varie ·{" "}
              {totals.card_purchases_count} spese carte
            </p>
          </>
        ) : (
          <p className="text-ink-soft">Caricamento totali…</p>
        )}
      </div>

      <div className="mt-8 sm:mt-10 grid sm:grid-cols-2 gap-4">
        <Link
          href="/admin/articles/new"
          className="card card-clickable p-5 sm:p-6 flex items-start gap-4"
        >
          <span className="text-3xl">➕</span>
          <div>
            <h3 className="display text-lg text-ink">Nuovo articolo</h3>
            <p className="text-ink-soft text-sm mt-1 leading-relaxed">
              Aggiungi un nuovo pezzo al catalogo (bozza o subito pubblicato).
            </p>
          </div>
        </Link>
        <Link
          href="/admin/wanted/new"
          className="card card-clickable p-5 sm:p-6 flex items-start gap-4"
        >
          <span className="text-3xl">🔍</span>
          <div>
            <h3 className="display text-lg text-ink">Nuovo wanted</h3>
            <p className="text-ink-soft text-sm mt-1 leading-relaxed">
              Pubblica una richiesta di acquisto nella sezione
              &laquo;Cerco/Compro&raquo;.
            </p>
          </div>
        </Link>
      </div>
    </AdminShell>
  );
}

function BigStat({
  label,
  value,
  color,
  accent,
}: {
  label: string;
  value: string;
  color: string;
  accent?: boolean;
}) {
  return (
    <div className="card p-4 relative overflow-hidden">
      <div
        className={`absolute -top-6 -right-6 w-24 h-24 rounded-full ${color} blur-2xl opacity-60`}
        aria-hidden="true"
      />
      <p className="text-[10px] uppercase tracking-wider text-ink-soft relative">{label}</p>
      <p
        className={
          "display mt-1 leading-none tabular-nums relative " +
          (accent ? "text-3xl text-pink-deep" : "text-2xl text-ink")
        }
      >
        {value}
      </p>
    </div>
  );
}

function BreakdownTable({
  data,
  highlightSign,
}: {
  data: Record<string, string>;
  highlightSign?: boolean;
}) {
  const entries = Object.entries(data).filter(([_, v]) => Number(v) !== 0);
  if (entries.length === 0) {
    return <p className="text-sm text-ink-soft">Nessun dato per questo anno.</p>;
  }
  // Ordina per valore assoluto desc
  entries.sort(([, a], [, b]) => Math.abs(Number(b)) - Math.abs(Number(a)));

  return (
    <table className="w-full text-sm">
      <tbody>
        {entries.map(([slug, val]) => {
          const n = Number(val);
          const color = highlightSign
            ? n > 0
              ? "text-mint-deep"
              : n < 0
                ? "text-pink-deep"
                : "text-ink"
            : "text-ink";
          return (
            <tr key={slug} className="border-b border-ink/8 last:border-0">
              <td className="py-2 text-ink-soft capitalize">
                {GROUP_LABELS[slug] ?? slug.replace(/_/g, " ")}
              </td>
              <td className={`py-2 text-right tabular-nums font-semibold ${color}`}>
                {fmtMoney(val)}
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

const TONE_BG: Record<string, string> = {
  pink: "from-pink/30 to-pink-soft",
  mint: "from-mint/30 to-mint-soft",
  sky: "from-sky/30 to-sky-soft",
  lilac: "from-lilac/30 to-lilac-soft",
};

function Stat({
  label,
  value,
  hint,
  href,
  tone,
  icon,
}: {
  label: string;
  value: number | undefined;
  hint?: string;
  href: string;
  tone: "pink" | "mint" | "sky" | "lilac";
  icon: string;
}) {
  return (
    <Link
      href={href}
      className="card card-clickable p-5 block relative overflow-hidden"
    >
      <div
        className={`absolute -top-6 -right-6 w-24 h-24 rounded-full bg-gradient-to-br ${TONE_BG[tone]} blur-xl pointer-events-none`}
        aria-hidden="true"
      />
      <div className="relative">
        <div className="flex items-center justify-between mb-2">
          <p className="text-xs uppercase tracking-wider text-ink-soft">
            {label}
          </p>
          <span className="text-lg opacity-60">{icon}</span>
        </div>
        <p className="display text-4xl text-ink leading-none">
          {value ?? "…"}
        </p>
        {hint && <p className="text-xs text-ink-soft mt-2">{hint}</p>}
      </div>
    </Link>
  );
}
