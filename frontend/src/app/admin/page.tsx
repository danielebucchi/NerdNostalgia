"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { AdminShell } from "@/components/admin/AdminShell";
import { adminApi } from "@/lib/admin-api";
import type { ArticleListResponse, InquiryStatus, WantedListResponse } from "@/lib/types";

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
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const [pub, draft, inqList, wantedList] = await Promise.all([
          adminApi.get<ArticleListResponse>("/api/articles/?status=PUBLISHED&limit=1"),
          adminApi.get<ArticleListResponse>("/api/articles/?status=DRAFT&limit=1"),
          adminApi.get<InquiryListLite>("/api/inquiries/?limit=100"),
          adminApi.get<WantedListResponse>("/api/wanted/?status=ACTIVE&limit=1"),
        ]);
        setStats({
          articlesPublished: pub.total,
          articlesDraft: draft.total,
          inquiriesNew: inqList.items.filter((i) => i.status === "NEW").length,
          inquiriesTotal: inqList.total,
          wantedActive: wantedList.total,
        });
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
      }
    })();
  }, []);

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
