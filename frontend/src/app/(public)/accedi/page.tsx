"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { loginCustomer } from "@/lib/customer-auth";

export default function AccediPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await loginCustomer(email.trim(), password);
      router.push("/profilo");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setBusy(false);
    }
  }

  return (
    <article className="max-w-md mx-auto">
      <h1 className="display text-3xl text-ink mb-2">Accedi</h1>
      <p className="text-ink-soft text-sm mb-6">
        Per vedere i tuoi ordini e seguire le spedizioni.
      </p>

      <form onSubmit={handleSubmit} className="card p-6 space-y-4">
        {error && <p className="text-pink-deep text-sm">⚠ {error}</p>}

        <label className="block">
          <span className="text-xs font-bold uppercase tracking-wider text-ink-soft">
            Email
          </span>
          <input
            type="email"
            required
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
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

        <button
          type="submit"
          disabled={busy}
          className="btn btn-primary w-full text-base font-bold px-6 py-3"
        >
          {busy ? "Accedo…" : "Accedi"}
        </button>

        <p className="text-xs text-ink-soft text-center">
          Non hai un profilo?{" "}
          <Link href="/registrati" className="underline font-semibold">
            Crealo adesso
          </Link>
        </p>
      </form>
    </article>
  );
}
