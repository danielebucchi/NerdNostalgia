"use client";

import { use, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { AdminShell } from "@/components/admin/AdminShell";
import { WantedForm } from "@/components/admin/WantedForm";
import { adminApi } from "@/lib/admin-api";
import type { WantedItem } from "@/lib/types";

interface PageProps {
  params: Promise<{ id: string }>;
}

export default function AdminWantedEditPage({ params }: PageProps) {
  const { id } = use(params);
  const router = useRouter();
  const [item, setItem] = useState<WantedItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const data = await adminApi.get<WantedItem>(`/api/wanted/${id}`);
        setItem(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
      } finally {
        setLoading(false);
      }
    })();
  }, [id]);

  async function handleDelete() {
    if (!confirm("Eliminare definitivamente questo wanted?")) return;
    setBusy(true);
    try {
      await adminApi.delete(`/api/wanted/${id}`);
      router.push("/admin/wanted");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setBusy(false);
    }
  }

  return (
    <AdminShell>
      <Link href="/admin/wanted" className="btn btn-ghost text-sm mb-6">
        ← Cerco/Compro
      </Link>

      {loading && <p className="text-ink-soft">Caricamento…</p>}
      {error && <p className="text-pink-deep mb-3">⚠ {error}</p>}

      {item && (
        <>
          <div className="flex items-start justify-between gap-4 mb-6">
            <div>
              <h1 className="display text-3xl text-ink">{item.title}</h1>
              <p className="text-ink-soft text-sm">
                #{item.id} · {item.status} · priorità {item.priority}
              </p>
            </div>
            <a
              href={`/cerco-compro/${item.id}`}
              target="_blank"
              rel="noreferrer"
              className="btn btn-ghost text-sm"
            >
              Vista pubblica ↗
            </a>
          </div>

          <div className="card p-5 mb-6 flex items-center justify-between gap-3">
            <div className="text-sm text-ink-soft">
              Creato il {new Date(item.created_at).toLocaleString("it-IT")}
              {item.fulfilled_at && (
                <> · trovato il {new Date(item.fulfilled_at).toLocaleString("it-IT")}</>
              )}
            </div>
            <button
              type="button"
              className="btn btn-ghost text-sm"
              onClick={handleDelete}
              disabled={busy}
            >
              🗑 Elimina
            </button>
          </div>

          <div className="card p-5">
            <h2 className="display text-lg text-ink mb-3">Dati wanted</h2>
            <WantedForm initial={item} onSaved={(saved) => setItem(saved)} />
          </div>
        </>
      )}
    </AdminShell>
  );
}
