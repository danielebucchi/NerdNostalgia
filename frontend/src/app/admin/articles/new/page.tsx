"use client";

import Link from "next/link";
import { AdminShell } from "@/components/admin/AdminShell";
import { ArticleForm } from "@/components/admin/ArticleForm";

export default function AdminArticleNewPage() {
  return (
    <AdminShell>
      <Link href="/admin/articles" className="btn btn-ghost text-sm mb-6">
        ← Articoli
      </Link>
      <h1 className="display text-3xl text-ink mb-6">Nuovo articolo</h1>
      <ArticleForm />
    </AdminShell>
  );
}
