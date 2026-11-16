"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ExpansionCombobox } from "@/components/admin/ExpansionCombobox";
import { thumbUrlFor } from "@/lib/images";
import type { PersonalCard } from "@/lib/types";
import {
  type Analisi,
  type Candidato,
  GIOCHI,
  type Scan,
  type StatoScanner,
  aggiornaCarta,
  analizza,
  caricaRetro,
  caricaScan,
  cercaNellIndice,
  collezione,
  conferma,
  costruisciIndice,
  eliminaCarta,
  inFila,
  nomeDelFronte,
  pubblicaCardTrader,
  pubblicaEbay,
  pubblicaSito,
  ricerca,
  ritiraCardTrader,
  ritiraEbay,
  ritiraSito,
  salvaSessione,
  scanInAttesa,
  scaricaCsv,
  scarta,
  stato,
  urlVendutiEbay,
  valuta,
  vendutiAMano,
} from "@/lib/card-scanner";

/* Scanner carte.
 *
 * Dagli scan alla collezione: si caricano gli scan, il server legge
 * numero e sigla e confronta l'immagine col catalogo CardTrader, e propone
 * le carte possibili. La scelta la conferma una persona — una carta
 * sbagliata in catalogo la si scopre quando qualcuno l'ha comprata.
 *
 * Le carte confermate sono la collezione: valutate con CardTrader e con
 * le ultime vendite eBay, esportabili in CSV, pubblicabili da qui. */

const CONDIZIONI = ["Mint", "Near Mint", "Slightly Played", "Moderately Played", "Played", "Poor"];

const LINGUE = [
  { code: "", label: "Dallo scan" },
  { code: "it", label: "Italiano" },
  { code: "en", label: "Inglese" },
  { code: "jp", label: "Giapponese" },
  { code: "fr", label: "Francese" },
  { code: "de", label: "Tedesco" },
  { code: "es", label: "Spagnolo" },
];

const eur = (v: string | number | null | undefined) =>
  v == null || v === "" ? "—" : `€${Number(v).toFixed(2)}`;

const msg = (e: unknown) => (e instanceof Error ? e.message : String(e));

interface Impostazioni {
  gameId: number;
  expansionId: number | null;
  condizione: string; // "" = dalla stima sullo scan
  lingua: string;
  valutaSubito: boolean;
}

export default function ScannerCartePage() {
  const [st, setSt] = useState<StatoScanner | null>(null);
  const [imp, setImp] = useState<Impostazioni>({
    gameId: 5,
    expansionId: null,
    condizione: "",
    lingua: "",
    valutaSubito: true,
  });
  const [coda, setCoda] = useState<Scan[]>([]);
  const [carte, setCarte] = useState<PersonalCard[]>([]);
  const [errore, setErrore] = useState<string | null>(null);

  const ricaricaStato = useCallback(async () => {
    try {
      setSt(await stato());
    } catch (e) {
      setErrore(msg(e));
    }
  }, []);

  const ricaricaCarte = useCallback(async (search?: string) => {
    try {
      setCarte(await collezione(search));
    } catch (e) {
      setErrore(msg(e));
    }
  }, []);

  useEffect(() => {
    stato()
      .then((s) => {
        setSt(s);
        const g = s.session?.game_id ?? s.default_game_id;
        if (g) setImp((i) => ({ ...i, gameId: g }));
      })
      .catch((e) => setErrore(msg(e)));
    scanInAttesa().then(setCoda).catch((e) => setErrore(msg(e)));
    ricaricaCarte();
  }, [ricaricaCarte]);

  // Gioco ed espansione scelti qui valgono anche per la cartella osservata
  // (scripts/scanner_watch.py): si salvano a ogni cambio.
  const pronto = useRef(false);
  useEffect(() => {
    if (!st) return;
    if (!pronto.current) {
      pronto.current = true;
      return;
    }
    salvaSessione(imp.gameId, imp.expansionId).catch((e) => setErrore(msg(e)));
  }, [st, imp.gameId, imp.expansionId]);

  // Gli scan dalla cartella osservata arrivano senza passare da qui: si
  // chiede al server ogni pochi secondi. Si AGGIUNGONO solo i nuovi (e si
  // aggiorna chi ha ricevuto il retro), per non azzerare le scelte fatte
  // sulle righe gia' in coda.
  useEffect(() => {
    const t = window.setInterval(async () => {
      if (document.hidden) return;
      try {
        const dalServer = await scanInAttesa();
        setCoda((c) => {
          const perId = new Map(c.map((s) => [s.id, s]));
          let cambiata = false;
          const nuova = c.map((s) => {
            const srv = dalServer.find((x) => x.id === s.id);
            if (srv && srv.back_image_url !== s.back_image_url) {
              cambiata = true;
              return srv;
            }
            return s;
          });
          for (const srv of dalServer) {
            if (!perId.has(srv.id)) {
              nuova.push(srv);
              cambiata = true;
            }
          }
          return cambiata ? nuova : c;
        });
      } catch {
        /* rete momentaneamente giu': si riprova al giro dopo */
      }
    }, 4000);
    return () => window.clearInterval(t);
  }, []);

  // Mentre l'indice si costruisce, se ne segue l'avanzamento.
  const inCostruzione = st?.index.some((i) => i.build?.running);
  useEffect(() => {
    if (!inCostruzione) return;
    const t = window.setInterval(ricaricaStato, 3000);
    return () => window.clearInterval(t);
  }, [inCostruzione, ricaricaStato]);

  function confermata(scanId: number, carta: PersonalCard) {
    setCoda((c) => c.filter((s) => s.id !== scanId));
    setCarte((c) => [carta, ...c]);
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="display text-2xl sm:text-3xl text-ink">Scanner carte</h1>
        <p className="text-ink-soft text-sm mt-1 leading-snug">
          Carica gli scan: la carta si riconosce da numero e simbolo dell&apos;espansione. Confermi
          tu, e la carta entra nella collezione con il prezzo CardTrader e la media delle ultime
          vendite eBay.
        </p>
      </div>

      {errore && (
        <p className="text-pink-deep text-sm">
          ⚠ {errore}{" "}
          <button type="button" className="underline" onClick={() => setErrore(null)}>
            chiudi
          </button>
        </p>
      )}

      <Avvisi st={st} />

      <ImpostazioniScan st={st} imp={imp} setImp={setImp} onIndice={ricaricaStato} />

      <Caricamento
        imp={imp}
        coda={coda}
        onScan={(s) => setCoda((c) => (c.some((x) => x.id === s.id) ? c : [...c, s]))}
        onAggiornata={(s) => setCoda((c) => c.map((x) => (x.id === s.id ? s : x)))}
        disabilitato={!st?.ocr}
      />

      <CodaConferma
        coda={coda}
        imp={imp}
        onConfermata={confermata}
        onAggiornata={(s) => setCoda((c) => c.map((x) => (x.id === s.id ? s : x)))}
        onScartata={(id) => setCoda((c) => c.filter((s) => s.id !== id))}
      />

      <Collezione carte={carte} setCarte={setCarte} onCerca={ricaricaCarte} st={st} />
    </div>
  );
}

/* ── Avvisi di configurazione ─────────────────────────────────── */

function Avvisi({ st }: { st: StatoScanner | null }) {
  if (!st) return null;
  const voci: string[] = [];
  if (!st.ocr) voci.push("Tesseract non è installato sul server: il riconoscimento non può partire.");
  if (!st.cardtrader) voci.push("CardTrader non configurato (CARDTRADER_JWT).");
  if (!st.ebay_sold)
    voci.push("eBay non configurato: i venduti si inseriscono a mano dalla collezione.");
  if (!st.ebay_publish) voci.push("eBay non collegato: «Carica su eBay» resta spento finché non completi il consenso.");
  if (!voci.length) return null;
  return (
    <ul className="card p-3 text-sm text-ink-soft space-y-1 border-l-4 border-pink-deep/50">
      {voci.map((v) => (
        <li key={v}>⚠ {v}</li>
      ))}
    </ul>
  );
}

/* ── Impostazioni della sessione di scansione ─────────────────── *
 * Restano fra uno scan e l'altro: in una scatola gioco, espansione,
 * condizione e lingua cambiano di rado. */

function ImpostazioniScan({
  st,
  imp,
  setImp,
  onIndice,
}: {
  st: StatoScanner | null;
  imp: Impostazioni;
  setImp: (f: (i: Impostazioni) => Impostazioni) => void;
  onIndice: () => void;
}) {
  const [espansione, setEspansione] = useState("");
  const [esitoIndice, setEsitoIndice] = useState<string | null>(null);
  const indice = st?.index.find((i) => i.game_id === imp.gameId);
  const build = indice?.build;

  async function avviaIndice(full: boolean) {
    setEsitoIndice(null);
    try {
      const r = await costruisciIndice(imp.gameId, full);
      if (!r.started) setEsitoIndice(r.detail ?? "Già in costruzione");
      onIndice();
    } catch (e) {
      setEsitoIndice(msg(e));
    }
  }

  const etichetta = "block text-xs font-bold uppercase tracking-wide text-ink-soft mb-1";
  return (
    <section className="card p-4 space-y-4">
      <div className="grid sm:grid-cols-4 gap-3">
        <label className="block">
          <span className={etichetta}>Gioco</span>
          <select
            className="input"
            value={imp.gameId}
            onChange={(e) => {
              setEspansione("");
              setImp((i) => ({ ...i, gameId: Number(e.target.value), expansionId: null }));
            }}
          >
            {GIOCHI.map((g) => (
              <option key={g.id} value={g.id}>
                {g.label}
              </option>
            ))}
          </select>
        </label>
        <label className="block sm:col-span-3">
          <span className={etichetta}>Espansione (facoltativa: se la scatola è di un set solo)</span>
          <div className="flex gap-2">
            <ExpansionCombobox
              key={imp.gameId}
              gameId={imp.gameId}
              value={espansione}
              onChange={(t) => {
                setEspansione(t);
                if (!t) setImp((i) => ({ ...i, expansionId: null }));
              }}
              onSelect={(e) => setImp((i) => ({ ...i, expansionId: e.id }))}
              placeholder="tutte — riconosce da numero, sigla e immagine"
              ariaLabel="Espansione fissa"
              className="flex-1"
            />
            {imp.expansionId && (
              <button
                type="button"
                className="btn btn-ghost text-xs"
                onClick={() => {
                  setEspansione("");
                  setImp((i) => ({ ...i, expansionId: null }));
                }}
              >
                Togli
              </button>
            )}
          </div>
        </label>
      </div>

      <div className="grid sm:grid-cols-4 gap-3">
        <label className="block">
          <span className={etichetta}>Condizione</span>
          <select
            className="input"
            value={imp.condizione}
            onChange={(e) => setImp((i) => ({ ...i, condizione: e.target.value }))}
          >
            <option value="">Stimata dallo scan</option>
            {CONDIZIONI.map((c) => (
              <option key={c}>{c}</option>
            ))}
          </select>
        </label>
        <label className="block">
          <span className={etichetta}>Lingua</span>
          <select
            className="input"
            value={imp.lingua}
            onChange={(e) => setImp((i) => ({ ...i, lingua: e.target.value }))}
          >
            {LINGUE.map((l) => (
              <option key={l.code} value={l.code}>
                {l.label}
              </option>
            ))}
          </select>
        </label>
        <label className="flex items-end gap-2 text-sm text-ink-soft pb-2 sm:col-span-2">
          <input
            type="checkbox"
            className="h-4 w-4 accent-lilac-deep"
            checked={imp.valutaSubito}
            onChange={(e) => setImp((i) => ({ ...i, valutaSubito: e.target.checked }))}
          />
          Valuta subito alla conferma (CardTrader + venduti eBay)
        </label>
      </div>

      <div className="text-sm text-ink-soft flex flex-wrap items-center gap-3 border-t border-ink/10 pt-3">
        <span>
          Indice carte:{" "}
          {indice?.blueprints ? (
            <strong className="text-ink">
              {indice.blueprints.toLocaleString("it-IT")} carte in {indice.expansions} espansioni
            </strong>
          ) : (
            <strong className="text-pink-deep">vuoto</strong>
          )}
        </span>
        {build?.running ? (
          <span>
            Costruzione… {build.done}/{build.total}
            {build.errors > 0 && ` · ${build.errors} errori`}
          </span>
        ) : (
          <>
            <button type="button" className="btn btn-ghost text-xs" onClick={() => avviaIndice(false)}>
              {indice?.blueprints ? "Aggiungi espansioni nuove" : "Costruisci indice"}
            </button>
            {!!indice?.blueprints && (
              <button type="button" className="btn btn-ghost text-xs" onClick={() => avviaIndice(true)}>
                Ricostruisci tutto
              </button>
            )}
          </>
        )}
        {esitoIndice && <span className="text-pink-deep">{esitoIndice}</span>}
        {!indice?.blueprints && !build?.running && (
          <span className="basis-full text-xs">
            Serve per riconoscere le carte senza sigla stampata (es. Pokémon vecchi): qualche
            minuto la prima volta. Le espansioni lette dalla sigla si aggiungono da sole.
          </span>
        )}
      </div>
    </section>
  );
}

/* ── Caricamento scan ─────────────────────────────────────────── */

/* I retro si riconoscono dal nome ("carta12_retro.jpg" va con
 * "carta12.jpg") e si caricano dopo i fronti, attaccati al loro scan. */
function Caricamento({
  imp,
  coda,
  onScan,
  onAggiornata,
  disabilitato,
}: {
  imp: Impostazioni;
  coda: Scan[];
  onScan: (s: Scan) => void;
  onAggiornata: (s: Scan) => void;
  disabilitato: boolean;
}) {
  const [busy, setBusy] = useState(false);
  const [fatti, setFatti] = useState(0);
  const [totale, setTotale] = useState(0);
  const [errori, setErrori] = useState<{ item: File; error: string }[]>([]);
  const [sopra, setSopra] = useState(false);
  const input = useRef<HTMLInputElement>(null);

  async function carica(files: File[]) {
    const immagini = files.filter((f) => f.type.startsWith("image/"));
    if (!immagini.length || busy) return;
    const fronti = immagini.filter((f) => nomeDelFronte(f.name) === null);
    const retri = immagini.filter((f) => nomeDelFronte(f.name) !== null);
    const base = (nome: string) => nome.replace(/\.[^.]+$/, "");
    // Fronti gia' in coda (caricati prima) + quelli di questo giro
    const perNome = new Map<string, number>();
    coda.forEach((s) => s.original_filename && perNome.set(base(s.original_filename), s.id));

    setBusy(true);
    setFatti(0);
    setTotale(immagini.length);
    setErrori([]);
    const r1 = await inFila(
      fronti,
      async (f) => {
        const s = await caricaScan(f, imp.gameId, imp.expansionId);
        perNome.set(base(f.name), s.id);
        onScan(s);
        return s;
      },
      (n, e) => {
        setFatti(n);
        setErrori(e);
      },
    );
    await inFila(
      retri,
      async (f) => {
        const id = perNome.get(nomeDelFronte(f.name)!);
        if (!id) throw new Error("nessun fronte con questo nome");
        const s = await caricaRetro(id, f);
        onAggiornata(s);
        return s;
      },
      (n, e) => {
        setFatti(fronti.length + n);
        setErrori([...r1.errori, ...e]);
      },
    );
    setBusy(false);
    if (input.current) input.current.value = "";
  }

  return (
    <section
      className={
        "card p-6 text-center border-2 border-dashed transition-colors " +
        (sopra ? "border-lilac-deep bg-lilac/10" : "border-ink/15")
      }
      onDragOver={(e) => {
        e.preventDefault();
        setSopra(true);
      }}
      onDragLeave={() => setSopra(false)}
      onDrop={(e) => {
        e.preventDefault();
        setSopra(false);
        carica(Array.from(e.dataTransfer.files));
      }}
    >
      <p className="text-ink">
        Trascina qui gli scan, oppure{" "}
        <button
          type="button"
          className="underline text-lilac-deep disabled:opacity-50"
          disabled={busy || disabilitato}
          onClick={() => input.current?.click()}
        >
          scegli i file
        </button>
      </p>
      <p className="text-xs text-ink-soft mt-1">
        Una carta per file, JPEG o PNG (il TIFF lo apre solo Safari), 300–600 dpi. Il retro è
        facoltativo ma migliora la stima della condizione: chiamalo come il fronte con
        «_retro» in fondo (carta12.jpg → carta12_retro.jpg). Per farli arrivare da soli appena
        scansionati usa la cartella osservata (scripts/scanner_watch.py).
      </p>
      <input
        ref={input}
        type="file"
        accept="image/*"
        multiple
        hidden
        onChange={(e) => carica(Array.from(e.target.files ?? []))}
      />
      {busy && (
        <p className="text-sm text-ink mt-3">
          Leggo {fatti}/{totale}…
        </p>
      )}
      {!busy && totale > 0 && (
        <p className="text-sm text-ink-soft mt-3">
          {totale - errori.length} scan letti
          {errori.length > 0 && <span className="text-pink-deep"> · {errori.length} non caricati</span>}
        </p>
      )}
      {errori.length > 0 && (
        <ul className="mt-2 text-xs text-pink-deep text-left max-w-xl mx-auto">
          {errori.map((e) => (
            <li key={e.item.name}>
              {e.item.name}: {e.error}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

/* ── Coda da confermare ───────────────────────────────────────── */

function CodaConferma({
  coda,
  imp,
  onConfermata,
  onAggiornata,
  onScartata,
}: {
  coda: Scan[];
  imp: Impostazioni;
  onConfermata: (scanId: number, c: PersonalCard) => void;
  onAggiornata: (s: Scan) => void;
  onScartata: (id: number) => void;
}) {
  const [busy, setBusy] = useState(false);
  const [avanzamento, setAvanzamento] = useState<string | null>(null);
  const sicure = coda.filter((s) => s.confidence === "alta" && s.candidates.length && !s.note);

  async function confermaSicure() {
    setBusy(true);
    const { errori } = await inFila(
      sicure,
      async (s) => {
        const c = await conferma(s.id, datiConferma(s, s.candidates[0], imp));
        onConfermata(s.id, c);
      },
      (n) => setAvanzamento(`Confermo ${n}/${sicure.length}…`),
    );
    setAvanzamento(errori.length ? `${errori.length} non confermate: ${errori[0].error}` : null);
    setBusy(false);
  }

  return (
    <section className="card p-4">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
        <h2 className="display text-lg text-ink">
          Da confermare{coda.length > 0 && ` (${coda.length})`}
        </h2>
        {sicure.length > 0 && (
          <button
            type="button"
            className="btn btn-primary text-sm disabled:opacity-50"
            disabled={busy}
            onClick={confermaSicure}
          >
            Conferma le {sicure.length} sicure
          </button>
        )}
      </div>
      {avanzamento && <p className="text-sm text-ink-soft mb-2">{avanzamento}</p>}
      {coda.length === 0 ? (
        <p className="text-ink-soft text-sm">Nessuno scan in attesa.</p>
      ) : (
        <ul className="space-y-4">
          {coda.map((s) => (
            <RigaScan
              key={s.id}
              scan={s}
              imp={imp}
              onConfermata={onConfermata}
              onAggiornata={onAggiornata}
              onScartata={onScartata}
            />
          ))}
        </ul>
      )}
    </section>
  );
}

/* Senza scelte esplicite reverse, prima edizione e condizione li decide
 * il server dall'analisi dello scan (solo quando la misura è sicura). */
function datiConferma(s: Scan, c: Candidato, imp: Impostazioni) {
  return {
    blueprint_id: c.blueprint_id,
    condition: imp.condizione || null,
    language: imp.lingua || s.ocr.language || null,
    quantity: 1,
    price_now: imp.valutaSubito,
  };
}

/** Valori iniziali dei controlli della riga, dall'analisi della carta. */
function dallAnalisi(a: Analisi | undefined, imp: Impostazioni) {
  return {
    condizione: imp.condizione || a?.condition?.value || "Near Mint",
    reverse: a?.reverse?.value === true,
    primaEd: a?.first_edition?.value === true,
  };
}

function Indizio({ etichetta, m, attivo }: { etichetta: string; m?: { value: boolean | null; score?: number }; attivo: boolean }) {
  if (!attivo || !m) return null;
  const testo = m.value === true ? "sì" : m.value === false ? "no" : "incerto";
  const colore = m.value === true ? "bg-mint-soft" : m.value === null ? "bg-star" : "bg-ink/5";
  return (
    <span className={"px-2 py-0.5 rounded text-xs " + colore} title={m.score != null ? `misura ${m.score}` : undefined}>
      {etichetta}: {testo}
    </span>
  );
}

const COLORE_CONFIDENZA = {
  alta: "bg-mint-soft text-ink",
  media: "bg-star text-ink",
  bassa: "bg-pink-soft text-pink-deep",
};

function RigaScan({
  scan,
  imp,
  onConfermata,
  onAggiornata,
  onScartata,
}: {
  scan: Scan;
  imp: Impostazioni;
  onConfermata: (scanId: number, c: PersonalCard) => void;
  onAggiornata: (s: Scan) => void;
  onScartata: (id: number) => void;
}) {
  const [scelto, setScelto] = useState<Candidato | null>(scan.candidates[0] ?? null);
  const [extra, setExtra] = useState<Candidato[]>([]);
  const [numero, setNumero] = useState(scan.ocr.number ?? "");
  const [nome, setNome] = useState("");
  const [collezione, setCollezione] = useState("");
  const [collezioneId, setCollezioneId] = useState<number | null>(scan.expansion_id ?? null);
  const [qty, setQty] = useState(1);
  const iniziali = dallAnalisi(scan.features, imp);
  const [condizione, setCondizione] = useState(iniziali.condizione);
  const [reverse, setReverse] = useState(iniziali.reverse);
  const [primaEd, setPrimaEd] = useState(iniziali.primaEd);
  const [busy, setBusy] = useState(false);
  const [errore, setErrore] = useState<string | null>(null);
  const retro = useRef<HTMLInputElement>(null);

  useEffect(() => setScelto(scan.candidates[0] ?? null), [scan.candidates]);

  // L'analisi è fatta sulla carta in testa: scegliendone un'altra la si
  // rifà (reverse e timbro si misurano rispetto alla SUA immagine).
  const analisiValida = scan.features?.blueprint_id === scelto?.blueprint_id;
  useEffect(() => {
    if (!scelto || scan.features?.blueprint_id === scelto.blueprint_id) return;
    let vivo = true;
    analizza(scan.id, scelto.blueprint_id)
      .then((s) => vivo && onAggiornata(s))
      .catch(() => undefined);
    return () => {
      vivo = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scelto?.blueprint_id]);

  // Quando arriva l'analisi giusta, i controlli ripartono da lì.
  useEffect(() => {
    if (!analisiValida) return;
    const v = dallAnalisi(scan.features, imp);
    setCondizione(v.condizione);
    setReverse(v.reverse);
    setPrimaEd(v.primaEd);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [analisiValida, scan.features]);

  async function aggiungiRetro(f: File | undefined) {
    if (!f) return;
    setBusy(true);
    setErrore(null);
    try {
      onAggiornata(await caricaRetro(scan.id, f));
    } catch (e) {
      setErrore(msg(e));
    } finally {
      setBusy(false);
    }
  }

  /* Ricerca a mano con i dati che si vedono sulla carta: collezione,
   * numero, nome — anche solo uno. Si rifà il riconoscimento con questi
   * (il confronto d'immagine ordina i risultati) e, se c'è un nome, si
   * aggiungono le carte dell'indice che lo contengono: la carta giusta
   * deve comparire anche se l'immagine la mette in fondo. */
  async function cerca() {
    setBusy(true);
    setErrore(null);
    try {
      const aggiornato = await ricerca(scan.id, {
        // 0 = togli l'espansione fissata (campo svuotato)
        expansion_id: collezioneId ?? (collezione.trim() ? undefined : 0),
        number: numero.trim() || null,
        name: nome.trim() || null,
      });
      onAggiornata(aggiornato);
      setExtra(
        nome.trim().length >= 2
          ? await cercaNellIndice(scan.game_id ?? imp.gameId, nome.trim(), collezioneId)
          : [],
      );
      if (!aggiornato.candidates.length && nome.trim().length < 2) {
        setErrore("Nessuna carta con questi dati: prova ad aggiungere il nome");
      }
    } catch (e) {
      setErrore(msg(e));
    } finally {
      setBusy(false);
    }
  }

  async function confermaScelto() {
    if (!scelto) return;
    setBusy(true);
    setErrore(null);
    try {
      const c = await conferma(scan.id, {
        ...datiConferma(scan, scelto, imp),
        condition: condizione,
        quantity: qty,
        reverse,
        first_edition: primaEd,
      });
      onConfermata(scan.id, c);
    } catch (e) {
      setErrore(msg(e));
      setBusy(false);
    }
  }

  async function scartaScan() {
    setBusy(true);
    try {
      await scarta(scan.id);
      onScartata(scan.id);
    } catch (e) {
      setErrore(msg(e));
      setBusy(false);
    }
  }

  const candidati = [...scan.candidates, ...extra.filter((x) => !scan.candidates.some((c) => c.blueprint_id === x.blueprint_id))];
  const letto = [
    scan.ocr.printed_code && `n. ${scan.ocr.printed_code}`,
    scan.ocr.set_code && `sigla ${scan.ocr.set_code}`,
    scan.ocr.language && scan.ocr.language.toUpperCase(),
  ].filter(Boolean);

  return (
    <li className="border border-ink/10 rounded-lg p-3 flex flex-col md:flex-row gap-4">
      <div className="shrink-0 w-32">
        <a href={scan.image_url} target="_blank" rel="noreferrer">
          <img src={thumbUrlFor(scan.image_url)} alt="scan" className="w-32 rounded shadow" />
        </a>
        <p className="text-[11px] text-ink-soft mt-1 break-all">{scan.original_filename}</p>
        {scan.back_image_url ? (
          <a href={scan.back_image_url} target="_blank" rel="noreferrer" className="block mt-2">
            <img src={thumbUrlFor(scan.back_image_url)} alt="retro" className="w-16 rounded shadow" />
          </a>
        ) : (
          <button type="button" className="text-[11px] underline text-lilac-deep mt-1" disabled={busy}
            onClick={() => retro.current?.click()}>
            + retro
          </button>
        )}
        <input ref={retro} type="file" accept="image/*" hidden onChange={(e) => aggiungiRetro(e.target.files?.[0])} />
      </div>

      <div className="flex-1 min-w-0 space-y-3">
        <div className="flex flex-wrap items-center gap-2 text-sm">
          {scan.confidence && (
            <span className={"px-2 py-0.5 rounded text-xs font-bold " + COLORE_CONFIDENZA[scan.confidence]}>
              {scan.confidence}
            </span>
          )}
          <span className="text-ink-soft">
            Letto: {letto.length ? letto.join(" · ") : "niente di utile"}
          </span>
          {scan.error && <span className="text-pink-deep">· {scan.error}</span>}
        </div>

        {scan.note && <p className="text-xs text-pink-deep">⚠ {scan.note}</p>}

        {analisiValida && (
          <div className="flex flex-wrap items-center gap-2 text-ink-soft">
            <Indizio etichetta="Reverse/foil" m={scan.features.reverse} attivo={!!scan.features.supports?.reverse} />
            <Indizio etichetta="1ª edizione" m={scan.features.first_edition} attivo={!!scan.features.supports?.first_edition} />
            {scan.features.condition && (
              <span className="px-2 py-0.5 rounded text-xs bg-ink/5"
                title={scan.features.condition.reason}>
                Stima: {scan.features.condition.value ?? "non misurabile"}
                {scan.features.condition.centering?.lr != null &&
                  ` · centratura ${scan.features.condition.centering.lr}/${100 - scan.features.condition.centering.lr}`}
                {scan.features.condition.wear_front != null &&
                  ` · bordi ${(scan.features.condition.wear_front * 100).toFixed(1)}%`}
                {scan.features.condition.wear_back != null &&
                  ` · retro ${(scan.features.condition.wear_back * 100).toFixed(1)}%`}
              </span>
            )}
            {!scan.back_image_url && <span className="text-[11px]">senza retro la condizione è indicativa</span>}
          </div>
        )}

        {candidati.length > 0 && (
          <div className="flex gap-2 overflow-x-auto pb-1">
            {candidati.map((c) => (
              <button
                key={c.blueprint_id}
                type="button"
                onClick={() => setScelto(c)}
                className={
                  "shrink-0 w-28 text-left rounded p-1 border-2 transition-colors " +
                  (scelto?.blueprint_id === c.blueprint_id ? "border-lilac-deep bg-lilac/10" : "border-transparent hover:border-ink/20")
                }
              >
                {c.image_url && <img src={c.image_url} alt="" className="w-full rounded" loading="lazy" />}
                <span className="block text-xs font-bold text-ink leading-tight mt-1">{c.name}</span>
                <span className="block text-[11px] text-ink-soft leading-tight">
                  {c.expansion_name} · {c.number}
                  {c.version ? ` · ${c.version}` : ""}
                </span>
                {c.variant_of_top && <span className="block text-[10px] font-bold text-pink-deep">altra versione</span>}
              </button>
            ))}
          </div>
        )}

        <div className="text-sm">
          <span className="block text-xs text-ink-soft mb-1">
            Non è tra queste? Scrivi quello che leggi sulla carta (basta anche un campo solo):
          </span>
          <div
            className="grid gap-2 sm:grid-cols-[minmax(0,2fr)_minmax(0,1fr)_minmax(0,2fr)_auto] items-start"
            onKeyDown={(e) => {
              // Invio da qualunque campo fa partire la ricerca, ma non
              // mentre si sceglie dalla tendina delle collezioni.
              if (e.key === "Enter" && !(e.target as HTMLElement).closest("[data-tendina]")) cerca();
            }}
          >
            <div data-tendina>
              <ExpansionCombobox
                gameId={scan.game_id ?? imp.gameId}
                value={collezione}
                onChange={(t) => {
                  setCollezione(t);
                  if (!t.trim()) setCollezioneId(null);
                }}
                onSelect={(e) => setCollezioneId(e.id)}
                placeholder={scan.expansion_id ? "collezione fissata" : "collezione — cerca per nome o sigla"}
                ariaLabel="Collezione"
                className="input py-1 text-sm w-full"
              />
            </div>
            <input
              className="input py-1 text-sm w-full"
              value={numero}
              onChange={(e) => setNumero(e.target.value)}
              placeholder="numero (es. 47/127)"
              aria-label="Numero"
            />
            <input
              className="input py-1 text-sm w-full"
              value={nome}
              onChange={(e) => setNome(e.target.value)}
              placeholder="nome carta"
              aria-label="Nome carta"
            />
            <button type="button" className="btn btn-primary text-sm disabled:opacity-50" disabled={busy} onClick={cerca}>
              {busy ? "…" : "🔎 Cerca"}
            </button>
          </div>
          {collezione.trim() && !collezioneId && (
            <span className="block text-[11px] text-pink-deep mt-1">Scegli la collezione dalla tendina</span>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-3 text-sm">
          <select className="input py-1 text-sm w-auto" value={condizione}
            onChange={(e) => setCondizione(e.target.value)} aria-label="Condizione">
            {CONDIZIONI.map((c) => (
              <option key={c}>{c}</option>
            ))}
          </select>
          <label className="flex items-center gap-1 text-ink-soft">
            Qtà
            <input
              type="number"
              min={1}
              className="input py-1 w-16"
              value={qty}
              onChange={(e) => setQty(Math.max(1, Number(e.target.value)))}
            />
          </label>
          {(!analisiValida || scan.features.supports?.reverse) && (
            <label className="flex items-center gap-1 text-ink-soft">
              <input type="checkbox" className="accent-lilac-deep" checked={reverse} onChange={(e) => setReverse(e.target.checked)} />
              Reverse/foil
            </label>
          )}
          {(!analisiValida || scan.features.supports?.first_edition) && (
            <label className="flex items-center gap-1 text-ink-soft">
              <input type="checkbox" className="accent-lilac-deep" checked={primaEd} onChange={(e) => setPrimaEd(e.target.checked)} />
              1ª ed.
            </label>
          )}
          <button
            type="button"
            className="btn btn-primary text-sm disabled:opacity-50"
            disabled={busy || !scelto}
            onClick={confermaScelto}
          >
            {scelto ? `Conferma: ${scelto.name}` : "Scegli una carta"}
          </button>
          <button type="button" className="btn btn-ghost text-xs text-pink-deep" disabled={busy} onClick={scartaScan}>
            Scarta
          </button>
        </div>
        {errore && <p className="text-pink-deep text-xs">⚠ {errore}</p>}
      </div>
    </li>
  );
}

/* ── Collezione ───────────────────────────────────────────────── */

function Collezione({
  carte,
  setCarte,
  onCerca,
  st,
}: {
  carte: PersonalCard[];
  setCarte: (f: (c: PersonalCard[]) => PersonalCard[]) => void;
  onCerca: (q?: string) => void;
  st: StatoScanner | null;
}) {
  const [selezione, setSelezione] = useState<Set<number>>(new Set());
  const [cerca, setCerca] = useState("");
  const [busy, setBusy] = useState(false);
  const [avanzamento, setAvanzamento] = useState<string | null>(null);
  const [esito, setEsito] = useState<string | null>(null);

  useEffect(() => {
    const t = window.setTimeout(() => onCerca(cerca), 350);
    return () => window.clearTimeout(t);
  }, [cerca, onCerca]);

  const sostituisci = (c: PersonalCard) => setCarte((cs) => cs.map((x) => (x.id === c.id ? c : x)));
  const scelte = carte.filter((c) => selezione.has(c.id));

  async function inBlocco(etichetta: string, fn: (c: PersonalCard) => Promise<unknown>) {
    if (!scelte.length) return;
    setBusy(true);
    setEsito(null);
    const { errori } = await inFila(scelte, fn, (n) => setAvanzamento(`${etichetta} ${n}/${scelte.length}…`));
    setAvanzamento(null);
    setEsito(
      errori.length
        ? `${scelte.length - errori.length} ok · ${errori.length} non riuscite — ${errori
            .slice(0, 3)
            .map((e) => `${e.item.name}: ${e.error}`)
            .join(" | ")}`
        : `${scelte.length} fatte`,
    );
    setBusy(false);
    onCerca(cerca);
  }

  const valoreTotale = carte
    .filter((c) => c.status === "IN_STOCK")
    .reduce((t, c) => t + Number(c.list_price ?? c.estimated_value ?? 0) * (c.quantity || 1), 0);

  return (
    <section className="card p-4">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
        <h2 className="display text-lg text-ink">
          Collezione ({carte.length})
          <span className="text-sm text-ink-soft font-normal"> · valore in magazzino {eur(valoreTotale)}</span>
        </h2>
        <div className="flex flex-wrap gap-2">
          <input
            className="input py-1 text-sm w-48"
            placeholder="cerca nome, set, numero"
            value={cerca}
            onChange={(e) => setCerca(e.target.value)}
          />
          <button type="button" className="btn btn-ghost text-sm" onClick={() => scaricaCsv().catch((e) => setEsito(msg(e)))}>
            📄 Esporta CSV
          </button>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2 mb-3 text-sm">
        <span className="text-ink-soft">{selezione.size} selezionate:</span>
        <button type="button" className="btn btn-ghost text-xs" disabled={busy || !selezione.size}
          onClick={() => inBlocco("Valuto", async (c) => sostituisci((await valuta(c.id)).card))}>
          💶 Valuta
        </button>
        <button type="button" className="btn btn-primary text-xs disabled:opacity-50" disabled={busy || !selezione.size}
          onClick={() => inBlocco("Sito", (c) => pubblicaSito(c.id))}>
          Carica sul sito
        </button>
        <button type="button" className="btn btn-primary text-xs disabled:opacity-50" disabled={busy || !selezione.size || !st?.cardtrader}
          onClick={() => inBlocco("CardTrader", (c) => pubblicaCardTrader(c.id))}>
          Carica su CardTrader
        </button>
        <button type="button" className="btn btn-primary text-xs disabled:opacity-50" disabled={busy || !selezione.size || !st?.ebay_publish}
          title={st?.ebay_publish ? undefined : "eBay non collegato"}
          onClick={() => inBlocco("eBay", (c) => pubblicaEbay(c.id))}>
          Carica su eBay
        </button>
        <button type="button" className="btn btn-ghost text-xs text-pink-deep disabled:opacity-50" disabled={busy || !selezione.size}
          onClick={() => {
            if (!window.confirm(`Eliminare ${selezione.size} cart${selezione.size === 1 ? "a" : "e"} dalla collezione? Spariscono anche gli scan.`)) return;
            inBlocco("Elimino", async (c) => {
              await eliminaCarta(c.id);
              setSelezione((s) => {
                const n = new Set(s);
                n.delete(c.id);
                return n;
              });
            });
          }}>
          🗑 Elimina
        </button>
        {avanzamento && <span className="text-ink">{avanzamento}</span>}
      </div>
      {esito && <p className="text-xs text-ink-soft mb-3">{esito}</p>}

      {carte.length === 0 ? (
        <p className="text-ink-soft text-sm">Nessuna carta: conferma qualche scan.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs uppercase tracking-wide text-ink-soft border-b border-ink/10">
                <th className="py-2 pr-2">
                  <input
                    type="checkbox"
                    className="accent-lilac-deep"
                    checked={selezione.size === carte.length && carte.length > 0}
                    onChange={(e) => setSelezione(e.target.checked ? new Set(carte.map((c) => c.id)) : new Set())}
                  />
                </th>
                <th className="py-2 pr-2"></th>
                <th className="py-2 pr-2">Carta</th>
                <th className="py-2 pr-2 text-right">CardTrader</th>
                <th className="py-2 pr-2 text-right">Venduti eBay</th>
                <th className="py-2 pr-2 text-right">Suggerito</th>
                <th className="py-2 pr-2 text-right">Prezzo</th>
                <th className="py-2">In vendita</th>
              </tr>
            </thead>
            <tbody>
              {carte.map((c) => (
                <RigaCarta
                  key={c.id}
                  carta={c}
                  scelta={selezione.has(c.id)}
                  onScelta={(v) =>
                    setSelezione((s) => {
                      const n = new Set(s);
                      if (v) n.add(c.id);
                      else n.delete(c.id);
                      return n;
                    })
                  }
                  onCambiata={sostituisci}
                  onRicarica={() => onCerca(cerca)}
                  st={st}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function RigaCarta({
  carta: c,
  scelta,
  onScelta,
  onCambiata,
  onRicarica,
  st,
}: {
  carta: PersonalCard;
  scelta: boolean;
  onScelta: (v: boolean) => void;
  onCambiata: (c: PersonalCard) => void;
  onRicarica: () => void;
  st: StatoScanner | null;
}) {
  const [prezzo, setPrezzo] = useState(c.list_price ?? "");
  const [busy, setBusy] = useState(false);
  const [nota, setNota] = useState<string | null>(null);
  const [aMano, setAMano] = useState(false);
  const [prezziEbay, setPrezziEbay] = useState("");

  useEffect(() => setPrezzo(c.list_price ?? ""), [c.list_price]);

  async function azione(fn: () => Promise<unknown>, ok?: string) {
    setBusy(true);
    setNota(null);
    try {
      await fn();
      if (ok) setNota(ok);
    } catch (e) {
      setNota(`⚠ ${msg(e)}`);
    } finally {
      setBusy(false);
    }
  }

  async function salvaPrezzo() {
    const v = String(prezzo).replace(",", ".").trim();
    if (v === (c.list_price ?? "")) return;
    await azione(async () => onCambiata(await aggiornaCarta(c.id, { list_price: v || null })));
  }

  async function apriVenduti() {
    const { url } = await urlVendutiEbay(c.id);
    window.open(url, "_blank", "noopener");
    setAMano(true);
  }

  const scan = c.images?.[0];
  return (
    <tr className="border-b border-ink/5 align-top">
      <td className="py-2 pr-2">
        <input type="checkbox" className="accent-lilac-deep" checked={scelta} onChange={(e) => onScelta(e.target.checked)} />
      </td>
      <td className="py-2 pr-2 w-12">
        {scan && (
          <a href={scan} target="_blank" rel="noreferrer">
            <img src={thumbUrlFor(scan)} alt="" className="w-10 rounded" loading="lazy" />
          </a>
        )}
      </td>
      <td className="py-2 pr-2 min-w-[12rem]">
        <strong className="text-ink">{c.name}</strong>
        <span className="block text-xs text-ink-soft">
          {c.collection} · {c.printed_code || c.card_number}
        </span>
        <span className="block text-xs text-ink-soft">
          {(c.language || "").toUpperCase()} · {c.condition}
          {c.reverse && " · reverse"}
          {c.first_edition && " · 1ª ed."}
          {c.quantity > 1 && ` · ×${c.quantity}`}
          {c.status !== "IN_STOCK" && ` · ${c.status}`}
        </span>
        {nota && <span className="block text-xs text-pink-deep">{nota}</span>}
      </td>
      <td className="py-2 pr-2 text-right whitespace-nowrap">
        {eur(c.cardtrader_price)}
        {c.cardtrader_offers != null && <span className="block text-[11px] text-ink-soft">{c.cardtrader_offers} in vendita</span>}
      </td>
      <td className="py-2 pr-2 text-right whitespace-nowrap">
        {eur(c.ebay_sold_avg)}
        <span className="block text-[11px] text-ink-soft">
          {c.ebay_sold_count ? `media di ${c.ebay_sold_count}` : "nessuno"}
          {c.ebay_sold_source === "manuale" && " · a mano"}
        </span>
        <button type="button" className="text-[11px] underline text-lilac-deep" onClick={() => apriVenduti().catch((e) => setNota(msg(e)))}>
          venduti ↗
        </button>
        {aMano && (
          <div className="mt-1 flex gap-1 justify-end">
            <input
              className="input py-0.5 text-xs w-32"
              placeholder="12,50 9,90 15…"
              value={prezziEbay}
              onChange={(e) => setPrezziEbay(e.target.value)}
              aria-label="Prezzi venduti eBay"
            />
            <button
              type="button"
              className="btn btn-ghost text-[11px] px-2"
              disabled={busy}
              onClick={() =>
                azione(async () => {
                  onCambiata((await vendutiAMano(c.id, prezziEbay)).card);
                  setAMano(false);
                  setPrezziEbay("");
                })
              }
            >
              OK
            </button>
          </div>
        )}
      </td>
      <td className="py-2 pr-2 text-right whitespace-nowrap">
        <strong className="text-ink">{eur(c.estimated_value)}</strong>
        <button
          type="button"
          className="block ml-auto text-[11px] underline text-lilac-deep disabled:opacity-50"
          disabled={busy}
          onClick={() =>
            azione(async () => {
              const v = await valuta(c.id);
              onCambiata(v.card);
              const avvisi = Object.values(v.warnings);
              if (avvisi.length) setNota(avvisi.join(" · "));
            })
          }
        >
          {busy ? "…" : "rivaluta"}
        </button>
      </td>
      <td className="py-2 pr-2 text-right">
        <input
          className="input py-1 text-sm w-20 text-right"
          value={prezzo}
          onChange={(e) => setPrezzo(e.target.value)}
          onBlur={salvaPrezzo}
          onKeyDown={(e) => e.key === "Enter" && (e.target as HTMLInputElement).blur()}
          aria-label="Prezzo di vendita"
        />
      </td>
      <td className="py-2 whitespace-nowrap space-y-1">
        <div>
          {c.site_status === "PUBLISHED" ? (
            <span className="text-xs text-ink-soft">
              ✅ Sito ·{" "}
              <a href={`/articles/${c.article_id}`} target="_blank" rel="noreferrer" className="underline">vedi</a>
              {" · "}
              <button type="button" className="underline" disabled={busy}
                onClick={() => azione(async () => { await ritiraSito(c.id); onRicarica(); }, "tolta dal sito")}>
                ritira
              </button>
            </span>
          ) : c.site_status === "SOLD" ? (
            <span className="text-xs text-ink-soft">💰 venduta sul sito</span>
          ) : (
            <button type="button" className="btn btn-ghost text-xs" disabled={busy || c.status === "SOLD"}
              title="In vetrina sul sito, con le foto dello scan"
              onClick={() => azione(async () => { await pubblicaSito(c.id); onRicarica(); }, "in vetrina sul sito")}>
              Sito
            </button>
          )}
        </div>
        <div>
          {c.cardtrader_product_id ? (
            <button type="button" className="text-xs underline text-ink-soft" disabled={busy}
              onClick={() => azione(async () => { await ritiraCardTrader(c.id); onRicarica(); }, "tolta da CardTrader")}>
              ✅ CardTrader · ritira
            </button>
          ) : (
            <button type="button" className="btn btn-ghost text-xs" disabled={busy || !st?.cardtrader}
              onClick={() => azione(async () => { await pubblicaCardTrader(c.id); onRicarica(); }, "in vendita su CardTrader")}>
              CardTrader
            </button>
          )}
        </div>
        <div>
          {c.ebay_listing_id ? (
            <button type="button" className="text-xs underline text-ink-soft" disabled={busy}
              onClick={() => azione(async () => { await ritiraEbay(c.id); onRicarica(); }, "tolta da eBay")}>
              ✅ eBay · ritira
            </button>
          ) : (
            <button type="button" className="btn btn-ghost text-xs" disabled={busy || !st?.ebay_publish}
              onClick={() => azione(async () => { await pubblicaEbay(c.id); onRicarica(); }, "in vendita su eBay")}>
              eBay
            </button>
          )}
        </div>
        <div>
          <button type="button" className="text-xs underline text-pink-deep disabled:opacity-50" disabled={busy}
            title={c.cardtrader_product_id || c.ebay_listing_id || c.site_status === "PUBLISHED" ? "Prima ritirala dalla vendita" : undefined}
            onClick={() => {
              if (!window.confirm(`Eliminare «${c.name}» dalla collezione? Sparisce anche lo scan.`)) return;
              azione(async () => { await eliminaCarta(c.id); onRicarica(); });
            }}>
            🗑 elimina
          </button>
        </div>
      </td>
    </tr>
  );
}
