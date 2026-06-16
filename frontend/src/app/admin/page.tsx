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
      <h1 className="display text-3xl text-ink">Dashboard</h1>
      <p className="text-ink-soft mt-1">
        Riepilogo a colpo d&apos;occhio dello stato del negozio.
      </p>

      {error && (
        <div className="card p-4 mt-6 text-pink-deep">⚠ {error}</div>
      )}

      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 mt-8">
        <Stat label="Articoli pubblicati" value={stats?.articlesPublished} href="/admin/articles?status=PUBLISHED" tone="mint" />
        <Stat label="Bozze" value={stats?.articlesDraft} href="/admin/articles?status=DRAFT" tone="lilac" />
        <Stat label="Richieste nuove" value={stats?.inquiriesNew} hint={stats ? `su ${stats.inquiriesTotal}` : ""} href="/admin/inquiries?status=NEW" tone="pink" />
        <Stat label="Wanted attivi" value={stats?.wantedActive} href="/admin/wanted" tone="sky" />
      </div>

      <div className="mt-10 grid sm:grid-cols-2 gap-4">
        <Link href="/admin/articles/new" className="card card-clickable p-6">
          <h3 className="display text-lg text-ink">➕ Nuovo articolo</h3>
          <p className="text-ink-soft text-sm mt-1">
            Aggiungi un nuovo pezzo al catalogo (bozza o subito pubblicato).
          </p>
        </Link>
        <Link href="/admin/wanted/new" className="card card-clickable p-6">
          <h3 className="display text-lg text-ink">🔍 Nuovo wanted</h3>
          <p className="text-ink-soft text-sm mt-1">
            Pubblica una richiesta di acquisto nella sezione &laquo;Cerco/Compro&raquo;.
          </p>
        </Link>
      </div>
    </AdminShell>
  );
}

function Stat({
  label,
  value,
  hint,
  href,
  tone,
}: {
  label: string;
  value: number | undefined;
  hint?: string;
  href: string;
  tone: "pink" | "mint" | "sky" | "lilac";
}) {
  const ring: Record<string, string> = {
    pink: "border-pink-deep",
    mint: "border-mint-deep",
    sky: "border-sky-deep",
    lilac: "border-lilac-deep",
  };
  return (
    <Link href={href} className={`card card-clickable p-5 block ${ring[tone]}`}>
      <p className="text-xs uppercase tracking-wider text-ink-soft">{label}</p>
      <p className="display text-4xl text-ink mt-2">{value ?? "…"}</p>
      {hint && <p className="text-xs text-ink-soft mt-1">{hint}</p>}
    </Link>
  );
}
