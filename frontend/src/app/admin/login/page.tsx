"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/components/admin/AuthProvider";

export default function AdminLoginPage() {
  const { user, loading, login } = useAuth();
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!loading && user) {
      router.replace("/admin");
    }
  }, [loading, user, router]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(username.trim(), password);
      router.push("/admin");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login fallito");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4 sm:p-6">
      <div className="card w-full max-w-md p-6 sm:p-8">
        <Link href="/" className="display text-xl text-ink block mb-1">
          Nerd<span className="text-lilac-deep">.</span>Nostalgia
        </Link>
        <p className="text-[10px] text-ink-soft uppercase tracking-[0.16em] mb-6">
          Area admin
        </p>

        <h1 className="display text-2xl text-ink mb-2">Accedi</h1>
        <p className="text-ink-soft text-sm mb-6">
          Inserisci le tue credenziali per gestire catalogo, richieste e wishlist.
        </p>

        <form onSubmit={handleSubmit} className="space-y-3">
          <label className="block">
            <span className="text-xs font-bold uppercase tracking-wider text-ink-soft">
              Username
            </span>
            <input
              type="text"
              required
              autoFocus
              autoComplete="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="admin-input mt-1.5"
            />
          </label>
          <label className="block">
            <span className="text-xs font-bold uppercase tracking-wider text-ink-soft">
              Password
            </span>
            <input
              type="password"
              required
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="admin-input mt-1.5"
            />
          </label>

          {error && (
            <p className="text-pink-deep text-sm font-semibold">⚠ {error}</p>
          )}

          <button
            type="submit"
            className="btn btn-primary w-full justify-center mt-2"
            disabled={submitting}
          >
            {submitting ? "Accesso in corso…" : "Entra"}
          </button>
        </form>

        <p className="text-xs text-ink-soft mt-5 text-center">
          <Link href="/" className="underline hover:text-ink">
            ← Torna al sito
          </Link>
        </p>
      </div>

      <style>{`
        .admin-input {
          display: block;
          width: 100%;
          padding: 0.65rem 0.9rem;
          border: 1px solid rgba(61, 42, 92, 0.12);
          border-radius: 14px;
          background: rgba(255, 255, 255, 0.78);
          backdrop-filter: blur(8px);
          color: #3d2a5c;
          font-family: "Manrope", sans-serif;
          font-size: 0.95rem;
          outline: none;
          transition:
            box-shadow 150ms ease,
            border-color 150ms ease;
        }
        .admin-input:focus {
          border-color: var(--lilac-deep);
          box-shadow: 0 0 0 3px rgba(168, 144, 216, 0.25);
        }
      `}</style>
    </div>
  );
}
