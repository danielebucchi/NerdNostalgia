"use client";

import { use, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { AdminShell } from "@/components/admin/AdminShell";
import { adminApi } from "@/lib/admin-api";
import type { Inquiry, InquiryStatus } from "@/lib/types";

interface PageProps {
  params: Promise<{ id: string }>;
}

const STATUS_OPTIONS: InquiryStatus[] = ["NEW", "READ", "REPLIED", "CLOSED"];

export default function AdminInquiryDetailPage({ params }: PageProps) {
  const { id } = use(params);
  const router = useRouter();
  const [inquiry, setInquiry] = useState<Inquiry | null>(null);
  const [notes, setNotes] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const data = await adminApi.get<Inquiry>(`/api/inquiries/${id}`);
        setInquiry(data);
        setNotes(data.admin_notes ?? "");
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
      } finally {
        setLoading(false);
      }
    })();
  }, [id]);

  async function changeStatus(status: InquiryStatus) {
    setBusy(true);
    try {
      const updated = await adminApi.patch<Inquiry>(`/api/inquiries/${id}`, { status });
      setInquiry(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function saveNotes() {
    setBusy(true);
    try {
      const updated = await adminApi.patch<Inquiry>(`/api/inquiries/${id}`, {
        admin_notes: notes,
      });
      setInquiry(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete() {
    if (!confirm("Eliminare la richiesta?")) return;
    setBusy(true);
    try {
      await adminApi.delete(`/api/inquiries/${id}`);
      router.push("/admin/inquiries");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setBusy(false);
    }
  }

  return (
    <AdminShell>
      <Link href="/admin/inquiries" className="btn btn-ghost text-sm mb-6">
        ← Richieste
      </Link>

      {loading && <p className="text-ink-soft">Caricamento…</p>}
      {error && <p className="text-pink-deep mb-3">⚠ {error}</p>}

      {inquiry && (
        <>
          <div className="card p-6 mb-6">
            <div className="flex items-start justify-between gap-3 mb-3">
              <div>
                <h1 className="display text-2xl text-ink">
                  {inquiry.subject ?? "Senza oggetto"}
                </h1>
                <p className="text-xs text-ink-soft">
                  #{inquiry.id} · {new Date(inquiry.created_at).toLocaleString("it-IT")}
                </p>
              </div>
              <span className="chip chip-pink">{inquiry.status}</span>
            </div>

            <div className="grid sm:grid-cols-2 gap-3 text-sm mb-4">
              <div>
                <p className="text-xs uppercase tracking-wider text-ink-soft">Da</p>
                <p className="text-ink font-semibold">{inquiry.name}</p>
                <p className="text-pink-deep">
                  <a href={`mailto:${inquiry.email}`} className="underline">{inquiry.email}</a>
                </p>
                {inquiry.phone && (
                  <p className="text-ink-soft">
                    <a href={`tel:${inquiry.phone}`}>{inquiry.phone}</a>
                  </p>
                )}
              </div>
              {inquiry.article_id && (
                <div>
                  <p className="text-xs uppercase tracking-wider text-ink-soft">Articolo collegato</p>
                  <Link
                    href={`/admin/articles/${inquiry.article_id}`}
                    className="text-pink-deep underline font-semibold"
                  >
                    #{inquiry.article_id} →
                  </Link>
                </div>
              )}
            </div>

            <div className="border-t-2 border-dashed border-ink/15 pt-4">
              <p className="text-xs uppercase tracking-wider text-ink-soft mb-1">Messaggio</p>
              <p className="text-ink whitespace-pre-line leading-relaxed">{inquiry.message}</p>
            </div>
          </div>

          <div className="card p-5 mb-6">
            <h2 className="display text-lg text-ink mb-3">Cambia stato</h2>
            <div className="flex gap-2 flex-wrap">
              {STATUS_OPTIONS.map((s) => (
                <button
                  key={s}
                  type="button"
                  className={`btn text-sm ${inquiry.status === s ? "btn-primary" : "btn-ghost"}`}
                  disabled={busy || inquiry.status === s}
                  onClick={() => changeStatus(s)}
                >
                  {s}
                </button>
              ))}
              <button
                type="button"
                className="btn btn-ghost text-sm ml-auto"
                onClick={handleDelete}
                disabled={busy}
              >
                🗑 Elimina
              </button>
            </div>
            {inquiry.replied_at && (
              <p className="text-xs text-ink-soft mt-3">
                Risposto il {new Date(inquiry.replied_at).toLocaleString("it-IT")}
              </p>
            )}
          </div>

          <div className="card p-5">
            <h2 className="display text-lg text-ink mb-3">Note interne</h2>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={5}
              placeholder="Es: risposto via email, in attesa di conferma…"
              className="input w-full"
            />
            <button
              type="button"
              className="btn btn-primary text-sm mt-3"
              onClick={saveNotes}
              disabled={busy || notes === (inquiry.admin_notes ?? "")}
            >
              Salva note
            </button>
          </div>

          <style>{`
            .input {
              padding: 0.6rem 0.85rem;
              border: 1px solid rgba(61, 42, 92, 0.12);
              border-radius: 12px;
              background: #fffaf3;
              color: #3d2a5c;
              font-family: "Manrope", sans-serif;
              font-size: 0.95rem;
              outline: none;
              resize: vertical;
            }
            .input:focus {
              box-shadow: 0 0 0 3px rgba(248, 168, 200, 0.45);
              border-color: #e879a8;
            }
          `}</style>
        </>
      )}
    </AdminShell>
  );
}
