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
    <div className="min-h-screen flex items-center justify-center p-6">
      <div className="card w-full max-w-md p-8">
        <Link href="/" className="display text-xl text-ink block mb-1">
          Nerd<span className="text-pink-deep">.</span>Nostalgia
        </Link>
        <p className="text-xs text-ink-soft uppercase tracking-wider mb-6">Area admin</p>

        <h1 className="display text-2xl text-ink mb-2">Accedi</h1>
        <p className="text-ink-soft text-sm mb-6">
          Inserisci le tue credenziali admin per gestire catalogo, richieste e wishlist.
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
              className="input mt-1"
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
              className="input mt-1"
            />
          </label>

          {error && <p className="text-pink-deep text-sm font-semibold">⚠ {error}</p>}

          <button type="submit" className="btn btn-primary w-full justify-center" disabled={submitting}>
            {submitting ? "Accesso in corso…" : "Entra"}
          </button>
        </form>

        <p className="text-xs text-ink-soft mt-4 text-center">
          <Link href="/" className="underline">← Torna al sito</Link>
        </p>
      </div>

      <style>{`
        .input {
          display: block;
          width: 100%;
          padding: 0.6rem 0.85rem;
          border: 2px solid #3d2a5c;
          border-radius: 12px;
          background: #fffaf3;
          color: #3d2a5c;
          font-family: "Manrope", sans-serif;
          font-size: 0.95rem;
          outline: none;
          transition: box-shadow 120ms ease, border-color 120ms ease;
        }
        .input:focus {
          box-shadow: 0 0 0 3px rgba(248, 168, 200, 0.45);
          border-color: #e879a8;
        }
      `}</style>
    </div>
  );
}
