"use client";

import Link from "next/link";
import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { PasswordInput } from "@/components/PasswordInput";
import { resetPassword } from "@/lib/customer-auth";

function ReimpostaContent() {
  const router = useRouter();
  const token = useSearchParams().get("t");
  const [password, setPassword] = useState("");
  const [conferma, setConferma] = useState("");
  const [busy, setBusy] = useState(false);
  const [errore, setErrore] = useState<string | null>(null);
  const [fatto, setFatto] = useState(false);

  async function invia(e: React.FormEvent) {
    e.preventDefault();
    if (!token) {
      setErrore("Link incompleto: utilizzi quello ricevuto via email.");
      return;
    }
    // Controllato qui e non solo al submit del browser: due campi diversi
    // sono l'errore piu' facile da fare quando la password non si vede.
    if (password !== conferma) {
      setErrore("Le due password non coincidono.");
      return;
    }
    setBusy(true);
    setErrore(null);
    try {
      await resetPassword(token, password);
      setFatto(true);
      // Un attimo per leggere la conferma, poi al login.
      window.setTimeout(() => router.push("/accedi"), 2000);
    } catch (err) {
      setErrore(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  if (fatto) {
    return (
      <>
        <h1 className="display text-3xl text-ink mb-2">Password aggiornata</h1>
        <p className="text-ink-soft mb-6">
          Può ora accedere con la nuova password. Reindirizzamento in corso…
        </p>
        <Link href="/accedi" className="btn btn-primary">
          Vai ad accedere
        </Link>
      </>
    );
  }

  return (
    <>
      <h1 className="display text-3xl text-ink mb-2">Scegli una password</h1>
      <p className="text-ink-soft mb-6 leading-snug">
        Deve contenere almeno 8 caratteri. Può verificare quanto sta
        scrivendo con il pulsante 👁.
      </p>

      <form onSubmit={invia} className="card p-5 space-y-4">
        <label className="block">
          <span className="text-xs font-bold uppercase tracking-wider text-ink-soft">
            Nuova password
          </span>
          <PasswordInput
            required
            minLength={8}
            autoComplete="new-password"
            value={password}
            onChange={setPassword}
          />
        </label>

        <label className="block">
          <span className="text-xs font-bold uppercase tracking-wider text-ink-soft">
            Ripetila
          </span>
          <PasswordInput
            required
            minLength={8}
            autoComplete="new-password"
            value={conferma}
            onChange={setConferma}
          />
        </label>

        {errore && <p className="text-pink-deep text-sm">⚠ {errore}</p>}

        <button
          type="submit"
          disabled={busy}
          className="btn btn-primary w-full disabled:opacity-50"
        >
          {busy ? "Salvo…" : "Salva la nuova password"}
        </button>

        <p className="text-sm text-ink-soft text-center">
          Link scaduto?{" "}
          <Link href="/password-dimenticata" className="underline font-semibold">
            Chiedine un altro
          </Link>
        </p>
      </form>
    </>
  );
}

export default function ReimpostaPasswordPage() {
  return (
    <div className="max-w-md mx-auto py-6">
      <Suspense fallback={<p className="text-ink-soft">Un attimo…</p>}>
        <ReimpostaContent />
      </Suspense>
    </div>
  );
}
