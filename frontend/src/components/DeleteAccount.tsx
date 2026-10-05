"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { PasswordInput } from "@/components/PasswordInput";
import { deleteAccount } from "@/lib/customer-auth";

/* Cancellazione dell'account.
 *
 * In fondo alla pagina e dietro due passaggi: non è una cosa che si fa
 * per sbaglio sfiorando lo schermo, e non si torna indietro.
 *
 * Cosa succede davvero sta scritto prima di premere, non dopo: gli ordini
 * restano, e non per nostra comodità — per le scritture contabili la
 * legge impone dieci anni. Scoprirlo a cose fatte sarebbe la scoperta
 * peggiore possibile. */
export function DeleteAccount() {
  const router = useRouter();
  const [aperto, setAperto] = useState(false);
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [errore, setErrore] = useState<string | null>(null);

  async function cancella(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErrore(null);
    try {
      await deleteAccount(password);
      router.push("/");
    } catch (err) {
      setErrore(err instanceof Error ? err.message : String(err));
      setBusy(false);
    }
  }

  return (
    <section className="mt-10 pt-6 border-t border-ink/10">
      <h2 className="display text-xl text-ink mb-2">Cancella il tuo profilo</h2>

      {!aperto ? (
        <>
          <p className="text-ink-soft text-sm leading-snug mb-3">
            Se non ti serve più, puoi eliminarlo quando vuoi.
          </p>
          <button
            type="button"
            onClick={() => setAperto(true)}
            className="btn btn-ghost text-sm text-pink-deep"
          >
            Voglio cancellare il profilo
          </button>
        </>
      ) : (
        <form onSubmit={cancella} className="card p-4 space-y-4">
          <div className="text-sm text-ink-soft leading-snug space-y-2">
            <p className="text-ink font-semibold">
              Questa cosa non si può annullare.
            </p>
            <p>Spariscono per sempre:</p>
            <ul className="list-disc pl-5 space-y-0.5">
              <li>il tuo profilo e l&apos;accesso al sito</li>
              <li>gli indirizzi di spedizione salvati</li>
              <li>l&apos;iscrizione alle email promozionali</li>
              <li>le recensioni che hai scritto</li>
            </ul>
            <p>
              <strong className="text-ink">Restano i dati dei tuoi ordini</strong>{" "}
              — non per nostra scelta: per le scritture contabili la legge
              impone di conservarli dieci anni. Non li vedrai più nel sito,
              perché il profilo non ci sarà più.
            </p>
            <p>
              Puoi sempre comprare di nuovo come ospite, o rifare un profilo
              con la stessa email.
            </p>
          </div>

          <label className="block">
            <span className="text-xs font-bold uppercase tracking-wider text-ink-soft">
              Scrivi la password per confermare
            </span>
            <PasswordInput
              required
              autoComplete="current-password"
              value={password}
              onChange={setPassword}
            />
          </label>

          {errore && <p className="text-pink-deep text-sm">⚠ {errore}</p>}

          <div className="flex flex-wrap gap-2">
            <button
              type="submit"
              disabled={busy}
              className="btn text-sm font-bold text-white bg-pink-deep hover:brightness-95 disabled:opacity-50"
            >
              {busy ? "Cancello…" : "Cancella definitivamente"}
            </button>
            <button
              type="button"
              onClick={() => {
                setAperto(false);
                setPassword("");
                setErrore(null);
              }}
              className="btn btn-ghost text-sm"
            >
              Lascia stare
            </button>
          </div>
        </form>
      )}
    </section>
  );
}
