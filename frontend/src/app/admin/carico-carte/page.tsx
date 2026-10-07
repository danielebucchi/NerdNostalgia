"use client";

import { useEffect, useRef, useState } from "react";
import { ExpansionCombobox } from "@/components/admin/ExpansionCombobox";
import {
  type Blueprint,
  type EsitoRiga,
  type RigaCarico,
  type RigaCsv,
  cercaBlueprint,
  leggiCsv,
  pubblica,
} from "@/lib/bulk-cards";

/* Carico rapido delle carte.
 *
 * Non è la scheda articolo: qui non ci sono foto, descrizioni né
 * categorie. Serve a svuotare una scatola, e ogni campo in più è tempo
 * moltiplicato per il numero di carte.
 *
 * Le carte nascono in bozza — restano in inventario ma fuori dal
 * catalogo — e vanno in vendita su CardTrader al secondo prezzo più
 * basso fra le inserzioni con la stessa condizione e lingua. */

const CONDIZIONI = [
  "Mint",
  "Near Mint",
  "Slightly Played",
  "Moderately Played",
  "Played",
  "Poor",
];

const LINGUE = [
  { code: "it", label: "Italiano" },
  { code: "en", label: "Inglese" },
  { code: "ja", label: "Giapponese" },
  { code: "fr", label: "Francese" },
  { code: "de", label: "Tedesco" },
  { code: "es", label: "Spagnolo" },
];

export default function CaricoCartePage() {
  const [modo, setModo] = useState<"ricerca" | "csv">("ricerca");
  const [posizione, setPosizione] = useState(2);
  const [coda, setCoda] = useState<RigaCarico[]>([]);
  const [esiti, setEsiti] = useState<EsitoRiga[]>([]);
  const [fatte, setFatte] = useState(0);
  const [busy, setBusy] = useState(false);
  const [errore, setErrore] = useState<string | null>(null);

  async function invia() {
    if (!coda.length) return;
    setBusy(true);
    setErrore(null);
    setEsiti([]);
    setFatte(0);
    try {
      const finali = await pubblica(coda, posizione, (n, parziali) => {
        setFatte(n);
        setEsiti(parziali);
      });
      // Resta in coda solo ciò che non è andato: così si riprova senza
      // ricaricare tutto da capo.
      const falliti = new Set(finali.filter((e) => !e.ok).map((e) => e.index));
      setCoda((c) => c.filter((_, i) => falliti.has(i)));
    } catch (err) {
      setErrore(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  const riusciti = esiti.filter((e) => e.ok).length;
  const falliti = esiti.filter((e) => !e.ok);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="display text-2xl sm:text-3xl text-ink">Carico rapido carte</h1>
        <p className="text-ink-soft text-sm mt-1 leading-snug">
          Senza foto e senza scheda. Le carte restano in bozza — fuori dal
          catalogo del sito — e vanno in vendita su CardTrader al prezzo di
          mercato.
        </p>
      </div>

      <div className="flex gap-2">
        {(["ricerca", "csv"] as const).map((m) => (
          <button
            key={m}
            type="button"
            onClick={() => setModo(m)}
            className={
              "btn text-sm " + (modo === m ? "btn-primary" : "btn-ghost")
            }
          >
            {m === "ricerca" ? "🔎 Ricerca rapida" : "📄 Da CSV"}
          </button>
        ))}
      </div>

      {modo === "ricerca" ? (
        <RicercaRapida onAggiungi={(r) => setCoda((c) => [...c, r])} />
      ) : (
        <DaCsv onAggiungi={(righe) => setCoda((c) => [...c, ...righe])} />
      )}

      <section className="card p-4">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
          <h2 className="display text-lg text-ink">
            Da caricare{coda.length > 0 && ` (${coda.length})`}
          </h2>
          <label className="text-sm text-ink-soft flex items-center gap-2">
            Prezzo:
            <select
              value={posizione}
              onChange={(e) => setPosizione(Number(e.target.value))}
              className="input py-1 text-sm"
            >
              {[1, 2, 3, 4, 5].map((n) => (
                <option key={n} value={n}>
                  {n}° più basso
                </option>
              ))}
            </select>
          </label>
        </div>

        {coda.length === 0 ? (
          <p className="text-ink-soft text-sm">
            Nessuna carta in coda. Cercala qui sopra o carica un CSV.
          </p>
        ) : (
          <>
            <ul className="divide-y divide-ink/10 mb-4 max-h-80 overflow-y-auto">
              {coda.map((r, i) => (
                <li key={i} className="py-2 flex items-center justify-between gap-3 text-sm">
                  <span className="min-w-0">
                    <strong className="text-ink">{r.name || `#${r.blueprint_id}`}</strong>
                    {r.number && <span className="text-ink-soft"> · n. {r.number}</span>}
                    <span className="block text-ink-soft text-xs">
                      {r.condition}
                      {r.language && ` · ${r.language}`}
                      {r.reverse && " · reverse"}
                      {r.first_edition && " · 1ª ed."}
                      {r.quantity > 1 && ` · ×${r.quantity}`}
                    </span>
                  </span>
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => setCoda((c) => c.filter((_, j) => j !== i))}
                    className="btn btn-ghost text-xs text-pink-deep disabled:opacity-50"
                  >
                    Togli
                  </button>
                </li>
              ))}
            </ul>

            <div className="flex flex-wrap items-center gap-3">
              <button
                type="button"
                onClick={invia}
                disabled={busy}
                className="btn btn-primary text-sm disabled:opacity-50"
              >
                {busy
                  ? `Carico… ${fatte}/${coda.length}`
                  : `Carica ${coda.length} cart${coda.length === 1 ? "a" : "e"} su CardTrader`}
              </button>
              <button
                type="button"
                disabled={busy}
                onClick={() => setCoda([])}
                className="btn btn-ghost text-sm disabled:opacity-50"
              >
                Svuota la coda
              </button>
            </div>
          </>
        )}

        {errore && <p className="text-pink-deep text-sm mt-3">⚠ {errore}</p>}

        {esiti.length > 0 && (
          <div className="mt-4 text-sm">
            <p className="text-ink">
              <strong>{riusciti}</strong> in vendita
              {falliti.length > 0 && (
                <span className="text-pink-deep">
                  {" "}· {falliti.length} non caricate
                </span>
              )}
            </p>
            {falliti.length > 0 && (
              <ul className="mt-2 space-y-1 text-xs text-ink-soft">
                {falliti.map((e) => (
                  <li key={e.index}>
                    riga {e.index + 1}: {e.error}
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </section>
    </div>
  );
}

/* ── Ricerca rapida ───────────────────────────────────────────────
 *
 * L'espansione si sceglie una volta sola e resta: chi svuota una scatola
 * sta quasi sempre dentro lo stesso set, e rimetterla a ogni carta
 * sarebbe il grosso del lavoro. */
function RicercaRapida({ onAggiungi }: { onAggiungi: (r: RigaCarico) => void }) {
  const [espansione, setEspansione] = useState("");
  const [expId, setExpId] = useState<number | null>(null);
  const [cerca, setCerca] = useState("");
  const [risultati, setRisultati] = useState<Blueprint[]>([]);
  const [caricando, setCaricando] = useState(false);

  // Impostazioni che restano fra una carta e l'altra: in una scatola la
  // condizione e la lingua cambiano di rado.
  const [condizione, setCondizione] = useState("Near Mint");
  const [lingua, setLingua] = useState("it");
  const [reverse, setReverse] = useState(false);
  const [primaEd, setPrimaEd] = useState(false);
  const [quantita, setQuantita] = useState(1);

  const campoCerca = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!expId || cerca.trim().length < 2) {
      setRisultati([]);
      return;
    }
    let vivo = true;
    setCaricando(true);
    // Mezzo secondo di pausa: senza, ogni lettera sarebbe una chiamata.
    const t = window.setTimeout(() => {
      cercaBlueprint(expId, cerca)
        .then((r) => vivo && setRisultati(r.slice(0, 25)))
        .catch(() => vivo && setRisultati([]))
        .finally(() => vivo && setCaricando(false));
    }, 400);
    return () => {
      vivo = false;
      window.clearTimeout(t);
    };
  }, [expId, cerca]);

  function aggiungi(b: Blueprint) {
    onAggiungi({
      blueprint_id: b.id,
      name: b.name ?? null,
      number: b.collector_number ?? null,
      collection: espansione || null,
      quantity: quantita,
      condition: condizione,
      language: lingua || null,
      reverse,
      first_edition: primaEd,
    });
    // Pulisco e rimetto il fuoco: la carta dopo si digita subito, senza
    // toccare il mouse.
    setCerca("");
    setRisultati([]);
    campoCerca.current?.focus();
  }

  return (
    <section className="card p-4 space-y-4">
      <label className="block">
        <span className="block text-xs font-bold uppercase tracking-wide text-ink-soft mb-1">
          Espansione
        </span>
        <ExpansionCombobox
          value={espansione}
          onChange={setEspansione}
          onSelect={(e) => setExpId(e.id)}
          placeholder="es. Darkness Ablaze"
          ariaLabel="Espansione CardTrader"
        />
      </label>

      <div className="grid sm:grid-cols-4 gap-3">
        <label className="block">
          <span className="block text-xs font-bold uppercase tracking-wide text-ink-soft mb-1">
            Condizione
          </span>
          <select
            value={condizione}
            onChange={(e) => setCondizione(e.target.value)}
            className="input"
          >
            {CONDIZIONI.map((c) => (
              <option key={c}>{c}</option>
            ))}
          </select>
        </label>
        <label className="block">
          <span className="block text-xs font-bold uppercase tracking-wide text-ink-soft mb-1">
            Lingua
          </span>
          <select
            value={lingua}
            onChange={(e) => setLingua(e.target.value)}
            className="input"
          >
            {LINGUE.map((l) => (
              <option key={l.code} value={l.code}>
                {l.label}
              </option>
            ))}
          </select>
        </label>
        <label className="block">
          <span className="block text-xs font-bold uppercase tracking-wide text-ink-soft mb-1">
            Quantità
          </span>
          <input
            type="number"
            min={1}
            value={quantita}
            onChange={(e) => setQuantita(Math.max(1, Number(e.target.value)))}
            className="input"
          />
        </label>
        <div className="flex flex-col justify-end gap-1 pb-1">
          <label className="flex items-center gap-2 text-sm text-ink-soft">
            <input
              type="checkbox"
              checked={reverse}
              onChange={(e) => setReverse(e.target.checked)}
              className="h-4 w-4 accent-lilac-deep"
            />
            Reverse
          </label>
          <label className="flex items-center gap-2 text-sm text-ink-soft">
            <input
              type="checkbox"
              checked={primaEd}
              onChange={(e) => setPrimaEd(e.target.checked)}
              className="h-4 w-4 accent-lilac-deep"
            />
            1ª edizione
          </label>
        </div>
      </div>

      <label className="block">
        <span className="block text-xs font-bold uppercase tracking-wide text-ink-soft mb-1">
          Carta
        </span>
        <input
          ref={campoCerca}
          type="text"
          value={cerca}
          disabled={!expId}
          onChange={(e) => setCerca(e.target.value)}
          onKeyDown={(e) => {
            // Invio sul primo risultato: così si va avanti senza mouse.
            if (e.key === "Enter" && risultati.length > 0) {
              e.preventDefault();
              aggiungi(risultati[0]);
            }
          }}
          placeholder={expId ? "nome o numero, poi Invio" : "scegli prima l'espansione"}
          className="input"
        />
      </label>

      {caricando && <p className="text-ink-soft text-sm">Cerco…</p>}

      {risultati.length > 0 && (
        <ul className="divide-y divide-ink/10 max-h-72 overflow-y-auto">
          {risultati.map((b) => (
            <li key={b.id}>
              <button
                type="button"
                onClick={() => aggiungi(b)}
                className="w-full text-left py-2 px-1 hover:bg-lilac-soft rounded transition-colors"
              >
                <span className="text-ink">{b.name}</span>
                {b.collector_number && (
                  <span className="text-ink-soft text-sm"> · n. {b.collector_number}</span>
                )}
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

/* ── Da CSV ───────────────────────────────────────────────────────
 *
 * I nomi vanno risolti in carte vere, e la risoluzione la conferma una
 * persona: un nome che somiglia non è un nome che coincide, e una carta
 * sbagliata messa in vendita la si scopre quando qualcuno l'ha comprata. */
function DaCsv({ onAggiungi }: { onAggiungi: (righe: RigaCarico[]) => void }) {
  const [testo, setTesto] = useState("");
  const [espansione, setEspansione] = useState("");
  const [expId, setExpId] = useState<number | null>(null);
  const [righe, setRighe] = useState<RigaCsv[] | null>(null);
  const [scelte, setScelte] = useState<Record<number, number>>({});
  const [busy, setBusy] = useState(false);
  const [errore, setErrore] = useState<string | null>(null);

  async function leggi() {
    setBusy(true);
    setErrore(null);
    try {
      const r = await leggiCsv({ csv_text: testo, expansion_id: expId });
      setRighe(r);
      // Preselezione del primo candidato: quasi sempre è quello giusto,
      // e chi controlla deve poter solo correggere le eccezioni.
      const pre: Record<number, number> = {};
      r.forEach((x) => {
        if (x.candidates[0]) pre[x.index] = x.candidates[0].id;
      });
      setScelte(pre);
    } catch (err) {
      setErrore(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  function accoda() {
    if (!righe) return;
    const pronte: RigaCarico[] = [];
    righe.forEach((r) => {
      const id = scelte[r.index];
      if (!id) return;
      const b = r.candidates.find((c) => c.id === id);
      pronte.push({
        blueprint_id: id,
        name: b?.name ?? r.name ?? null,
        number: b?.collector_number ?? r.number ?? null,
        collection: r.collection || espansione || null,
        quantity: r.quantity,
        condition: r.condition,
        language: r.language ?? null,
        reverse: r.reverse,
        first_edition: r.first_edition,
      });
    });
    onAggiungi(pronte);
    setRighe(null);
    setTesto("");
  }

  const risolte = righe?.filter((r) => scelte[r.index]).length ?? 0;

  return (
    <section className="card p-4 space-y-4">
      <label className="block">
        <span className="block text-xs font-bold uppercase tracking-wide text-ink-soft mb-1">
          Espansione (se sono tutte dello stesso set)
        </span>
        <ExpansionCombobox
          value={espansione}
          onChange={setEspansione}
          onSelect={(e) => setExpId(e.id)}
          placeholder="facoltativa, ma rende il riconoscimento esatto"
          ariaLabel="Espansione CardTrader"
        />
      </label>

      <label className="block">
        <span className="block text-xs font-bold uppercase tracking-wide text-ink-soft mb-1">
          CSV
        </span>
        <input
          type="file"
          accept=".csv,text/csv,text/plain"
          onChange={async (e) => {
            const f = e.target.files?.[0];
            if (f) setTesto(await f.text());
          }}
          className="block text-sm text-ink-soft mb-2"
        />
        <textarea
          rows={6}
          value={testo}
          onChange={(e) => setTesto(e.target.value)}
          placeholder={"nome;numero;quantita;condizione;lingua\nCharizard VMAX;20;3;Near Mint;it"}
          className="input font-mono text-xs"
        />
        <span className="block text-[11px] text-ink-soft mt-1 leading-snug">
          Intestazioni riconosciute: nome/carta, numero, espansione, quantità,
          condizione, lingua, reverse, prima_edizione. Vanno bene anche in
          inglese e col punto e virgola.
        </span>
      </label>

      <button
        type="button"
        onClick={leggi}
        disabled={busy || !testo.trim()}
        className="btn btn-primary text-sm disabled:opacity-50"
      >
        {busy ? "Leggo…" : "Leggi il file"}
      </button>

      {errore && <p className="text-pink-deep text-sm">⚠ {errore}</p>}

      {righe && (
        <div className="space-y-3">
          <p className="text-sm text-ink">
            {risolte} su {righe.length} riconosciute.
            {risolte < righe.length && " Le altre restano fuori finché non scegli la carta."}
          </p>
          <ul className="divide-y divide-ink/10 max-h-96 overflow-y-auto">
            {righe.map((r) => (
              <li key={r.index} className="py-2 text-sm">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="text-ink">
                    {r.name || "(senza nome)"}
                    {r.number && <span className="text-ink-soft"> · n. {r.number}</span>}
                    {r.quantity > 1 && <span className="text-ink-soft"> · ×{r.quantity}</span>}
                  </span>
                  {r.candidates.length > 0 ? (
                    <select
                      value={scelte[r.index] ?? ""}
                      onChange={(e) =>
                        setScelte((s) => ({ ...s, [r.index]: Number(e.target.value) }))
                      }
                      className="input py-1 text-xs max-w-xs"
                    >
                      <option value="">— non caricare —</option>
                      {r.candidates.map((c) => (
                        <option key={c.id} value={c.id}>
                          {c.name} {c.collector_number ? `· n. ${c.collector_number}` : ""}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <span className="text-pink-deep text-xs">
                      {r.error || "nessuna corrispondenza"}
                    </span>
                  )}
                </div>
              </li>
            ))}
          </ul>
          <button
            type="button"
            onClick={accoda}
            disabled={risolte === 0}
            className="btn btn-primary text-sm disabled:opacity-50"
          >
            Metti in coda {risolte} cart{risolte === 1 ? "a" : "e"}
          </button>
        </div>
      )}
    </section>
  );
}
