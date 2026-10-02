"use client";

import { useEffect, useState } from "react";
import { AddressAutocomplete } from "@/components/AddressAutocomplete";
import type { AddressSuggestion } from "@/lib/api";
import {
  type Address,
  type AddressInput,
  createAddress,
  deleteAddress,
  formatAddress,
  listAddresses,
  makeDefault,
  updateAddress,
} from "@/lib/addresses";

/* Rubrica indirizzi, nel profilo.
 *
 * Qui si aggiunge e si corregge con calma; al checkout si sceglie e basta.
 * Tenere la gestione fuori dal momento del pagamento è voluto: in mezzo a
 * un acquisto ogni passaggio in più costa un ordine. */

/** Deve restare allineato a MAX_INDIRIZZI in api/addresses.py: se
 *  divergono, il bottone promette un indirizzo che il server rifiuta. */
const MAX_INDIRIZZI = 5;

const VUOTO: AddressInput = {
  label: "",
  full_name: "",
  phone: "",
  street: "",
  city: "",
  postal_code: "",
  province: "",
  country: "Italia",
};

export function AddressBook() {
  const [lista, setLista] = useState<Address[] | null>(null);
  const [errore, setErrore] = useState<string | null>(null);
  // null = nessun modulo aperto; 0 = nuovo; >0 = sto modificando quell'id
  const [modifica, setModifica] = useState<number | null>(null);
  const [bozza, setBozza] = useState<AddressInput>(VUOTO);
  const [busy, setBusy] = useState(false);
  // Come al checkout: CAP, città e provincia arrivano dal suggerimento,
  // ma chi abita dove la mappa non arriva deve poterli scrivere.
  const [manuale, setManuale] = useState(false);

  useEffect(() => {
    listAddresses()
      .then(setLista)
      .catch((e) => {
        setLista([]);
        setErrore(e instanceof Error ? e.message : String(e));
      });
  }, []);

  function apriNuovo() {
    setBozza(VUOTO);
    setManuale(false);
    setModifica(0);
    setErrore(null);
  }

  function apriModifica(a: Address) {
    setBozza({
      label: a.label ?? "",
      full_name: a.full_name,
      phone: a.phone ?? "",
      street: a.street,
      city: a.city,
      postal_code: a.postal_code,
      province: a.province ?? "",
      country: a.country,
    });
    // I campi sono già coerenti fra loro: bloccarli renderebbe
    // impossibile correggere un CAP sbagliato.
    setManuale(true);
    setModifica(a.id);
    setErrore(null);
  }

  function suggerimento(sug: AddressSuggestion) {
    setBozza((b) => ({
      ...b,
      street: sug.street || b.street,
      postal_code: sug.postal_code || b.postal_code,
      city: sug.city || b.city,
      province: sug.province || b.province,
      country: sug.country || b.country,
    }));
  }

  async function salva(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErrore(null);
    try {
      const salvato =
        modifica && modifica > 0
          ? await updateAddress(modifica, bozza)
          : await createAddress(bozza);
      setLista((l) => {
        const resto = (l ?? []).filter((a) => a.id !== salvato.id);
        return ordina([...resto, salvato]);
      });
      setModifica(null);
    } catch (err) {
      setErrore(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function predefinito(id: number) {
    setBusy(true);
    try {
      await makeDefault(id);
      setLista((l) =>
        ordina((l ?? []).map((a) => ({ ...a, is_default: a.id === id }))),
      );
    } catch (err) {
      setErrore(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function cancella(id: number) {
    setBusy(true);
    try {
      await deleteAddress(id);
      // Ricarico invece di togliere la riga a mano: se spariva il
      // predefinito il server ne ha promosso un altro, e quale lo sa lui.
      setLista(await listAddresses());
    } catch (err) {
      setErrore(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  if (lista === null) return null;

  return (
    <section className="mt-10 pt-6 border-t border-ink/10">
      <div className="flex items-center justify-between gap-3 mb-3">
        <h2 className="display text-xl text-ink">Indirizzi di spedizione</h2>
        {modifica === null && lista.length < MAX_INDIRIZZI && (
          <button
            type="button"
            onClick={apriNuovo}
            className="btn btn-ghost text-sm"
          >
            + Aggiungi
          </button>
        )}
      </div>

      {errore && <p className="text-pink-deep text-sm mb-3">⚠ {errore}</p>}

      {lista.length >= MAX_INDIRIZZI && modifica === null && (
        <p className="text-ink-soft text-sm mb-3">
          Hai raggiunto il massimo di {MAX_INDIRIZZI} indirizzi. Per
          aggiungerne un altro, elimina prima uno di questi.
        </p>
      )}

      {lista.length === 0 && modifica === null && (
        <p className="text-ink-soft text-sm">
          Non hai ancora indirizzi salvati. Il primo si salva da solo al
          prossimo acquisto, oppure aggiungilo qui.
        </p>
      )}

      <div className="space-y-2">
        {lista.map((a) => (
          <div
            key={a.id}
            className="card p-3 flex flex-wrap items-start justify-between gap-3"
          >
            <div className="text-sm leading-snug min-w-0">
              <span className="font-semibold text-ink">
                {a.label || a.full_name}
              </span>
              {a.is_default && (
                <span className="ml-2 text-[10px] uppercase tracking-wide font-bold text-lilac-deep">
                  predefinito
                </span>
              )}
              <span className="block text-ink-soft">{formatAddress(a)}</span>
              {a.phone && (
                <span className="block text-ink-soft text-xs mt-0.5">
                  ☎ {a.phone}
                </span>
              )}
            </div>
            <div className="flex flex-wrap gap-2 flex-shrink-0">
              {!a.is_default && (
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => predefinito(a.id)}
                  className="btn btn-ghost text-xs disabled:opacity-50"
                >
                  Rendi predefinito
                </button>
              )}
              <button
                type="button"
                disabled={busy}
                onClick={() => apriModifica(a)}
                className="btn btn-ghost text-xs disabled:opacity-50"
              >
                Modifica
              </button>
              <button
                type="button"
                disabled={busy}
                onClick={() => cancella(a.id)}
                className="btn btn-ghost text-xs text-pink-deep disabled:opacity-50"
              >
                Elimina
              </button>
            </div>
          </div>
        ))}
      </div>

      {modifica !== null && (
        <form onSubmit={salva} className="card p-4 mt-3 space-y-3">
          <p className="display text-base text-ink">
            {modifica > 0 ? "Modifica indirizzo" : "Nuovo indirizzo"}
          </p>

          <div className="grid sm:grid-cols-2 gap-3">
            <Campo label="Nome e cognome del destinatario *">
              <input
                type="text"
                required
                value={bozza.full_name}
                onChange={(e) =>
                  setBozza({ ...bozza, full_name: e.target.value })
                }
                className="input"
              />
            </Campo>
            <Campo label="Telefono (consigliato)">
              <input
                type="tel"
                placeholder="es. 333 1234567"
                value={bozza.phone ?? ""}
                onChange={(e) => setBozza({ ...bozza, phone: e.target.value })}
                className="input"
              />
            </Campo>
          </div>

          <Campo label="Indirizzo (via e numero civico) *">
            <AddressAutocomplete
              required
              placeholder="es. Via Roma 12"
              value={bozza.street}
              onChange={(v) => setBozza({ ...bozza, street: v })}
              onSelect={suggerimento}
            />
          </Campo>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <Campo label="CAP *">
              <input
                type="text"
                required
                inputMode="numeric"
                readOnly={!manuale}
                value={bozza.postal_code}
                onChange={(e) =>
                  setBozza({ ...bozza, postal_code: e.target.value })
                }
                className={manuale ? "input" : "input input-locked"}
              />
            </Campo>
            <Campo label="Città *">
              <input
                type="text"
                required
                readOnly={!manuale}
                value={bozza.city}
                onChange={(e) => setBozza({ ...bozza, city: e.target.value })}
                className={manuale ? "input" : "input input-locked"}
              />
            </Campo>
            <Campo label="Provincia">
              <input
                type="text"
                readOnly={!manuale}
                value={bozza.province ?? ""}
                onChange={(e) =>
                  setBozza({ ...bozza, province: e.target.value })
                }
                className={manuale ? "input" : "input input-locked"}
              />
            </Campo>
          </div>

          {!manuale && (
            <p className="text-[11px] text-ink-soft leading-snug -mt-1">
              Questi tre campi si compilano scegliendo il suggerimento.{" "}
              <button
                type="button"
                onClick={() => setManuale(true)}
                className="underline decoration-dotted hover:text-pink-deep"
              >
                Il mio indirizzo non è nell&apos;elenco →
              </button>
            </p>
          )}

          <div className="grid sm:grid-cols-2 gap-3">
            <Campo label="Paese *">
              <input
                type="text"
                required
                value={bozza.country}
                onChange={(e) =>
                  setBozza({ ...bozza, country: e.target.value })
                }
                className="input"
              />
            </Campo>
            <Campo label="Etichetta (facoltativa)">
              <input
                type="text"
                maxLength={60}
                placeholder="es. Casa, Ufficio"
                value={bozza.label ?? ""}
                onChange={(e) => setBozza({ ...bozza, label: e.target.value })}
                className="input"
              />
            </Campo>
          </div>

          <div className="flex flex-wrap gap-2 pt-1">
            <button
              type="submit"
              disabled={busy}
              className="btn btn-primary text-sm disabled:opacity-50"
            >
              {busy ? "Salvo…" : "Salva"}
            </button>
            <button
              type="button"
              onClick={() => setModifica(null)}
              className="btn btn-ghost text-sm"
            >
              Annulla
            </button>
          </div>
        </form>
      )}
    </section>
  );
}

/** Predefinito in cima, poi i più recenti: lo stesso ordine del server. */
function ordina(l: Address[]): Address[] {
  return [...l].sort((a, b) => {
    if (a.is_default !== b.is_default) return a.is_default ? -1 : 1;
    return b.id - a.id;
  });
}

function Campo({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <label className="block">
      <span className="block text-xs font-bold tracking-wide uppercase text-ink-soft mb-1">
        {label}
      </span>
      {children}
    </label>
  );
}
