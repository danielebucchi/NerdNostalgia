"use client";

import Link from "next/link";
import { AdminShell } from "@/components/admin/AdminShell";
import { WantedForm } from "@/components/admin/WantedForm";

export default function AdminWantedNewPage() {
  return (
    <AdminShell>
      <Link href="/admin/wanted" className="btn btn-ghost text-sm mb-6">
        ← Cerco/Compro
      </Link>
      <h1 className="display text-3xl text-ink mb-6">Nuovo wanted</h1>
      <WantedForm />
    </AdminShell>
  );
}
