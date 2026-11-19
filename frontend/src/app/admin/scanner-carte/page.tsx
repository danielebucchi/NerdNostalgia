"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { AdminShell } from "@/components/admin/AdminShell";
import { CameraCapture, supportsInAppCamera } from "@/components/admin/CameraCapture";
import { ExpansionCombobox } from "@/components/admin/ExpansionCombobox";
import { thumbUrlFor } from "@/lib/images";
import type { PersonalCard } from "@/lib/types";
import {
  type Analisi,
  type Candidato,
  type Canali,
  type Misura,
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
  pubblicaOvunque,
  controllaVendite,
  gruppiEbay,
  pubblicaGruppoEbay,
  type GruppoEbay,
  pubblicaSito,
  ricerca,
  ritiraCardTrader,
  ritiraEbay,
  ritiraSito,
  salvaSessione,
  scanInAttesa,
  scaricaCsv,
  scaricaKitWindows,
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
    <AdminShell>
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
    </AdminShell>
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
  // Su telefono le impostazioni stanno chiuse: si scelgono una volta per
  // scatola, e aperte spingerebbero la coda fuori dallo schermo.
  const [aperte, setAperte] = useState(false);
  const riassunto = [
    GIOCHI.find((g) => g.id === imp.gameId)?.label,
    espansione || "tutte le espansioni",
    imp.condizione || "condizione stimata",
    LINGUE.find((l) => l.code === imp.lingua)?.label.toLowerCase(),
  ].filter(Boolean).join(" · ");
  return (
    <section className="card p-4 space-y-4">
      <button type="button" className="md:hidden w-full flex items-center justify-between gap-2 text-left"
        onClick={() => setAperte((v) => !v)} aria-expanded={aperte}>
        <span className="min-w-0">
          <span className="block text-xs font-bold uppercase tracking-wide text-ink-soft">Impostazioni scansione</span>
          <span className="block text-sm text-ink truncate">{riassunto}</span>
        </span>
        <span className="text-ink-soft text-lg">{aperte ? "▴" : "▾"}</span>
      </button>
      <div className={(aperte ? "" : "hidden ") + "md:block space-y-4"}>
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
          <div className="flex gap-2 [&>div]:flex-1">
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
              className="input"
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
        {st?.learning && <Apprendimento l={st.learning} />}
        <span className="basis-full text-xs flex flex-wrap items-center gap-2 border-t border-ink/10 pt-3">
          💻 Scanner collegato a un PC Windows? Lo script carica da solo, una volta al giorno, le carte
          nuove della sua cartella.
          <button type="button" className="btn btn-ghost text-xs"
            onClick={() => scaricaKitWindows().catch((e) => setEsitoIndice(msg(e)))}>
            Scarica per Windows
          </button>
          <span className="text-ink-soft">Estrai lo ZIP e fai doppio clic su Installa.cmd.</span>
        </span>
        {!indice?.blueprints && !build?.running && (
          <span className="basis-full text-xs">
            Serve per riconoscere le carte senza sigla stampata (es. Pokémon vecchi): qualche
            minuto la prima volta. Le espansioni lette dalla sigla si aggiungono da sole.
          </span>
        )}
      </div>
      </div>
    </section>
  );
}

/* Cosa ha imparato lo scanner dalle tue conferme. */
function Apprendimento({ l }: { l: NonNullable<StatoScanner["learning"]> }) {
  const tarate = [
    ...l.calibrated.reverse.map((g) => `reverse (${g})`),
    l.calibrated.first_edition && "prima edizione",
    l.calibrated.condition && "condizione",
  ].filter(Boolean);
  const esempiUsura = l.examples.usura ?? 0;
  return (
    <span className="basis-full text-xs">
      Imparato finora: <strong className="text-ink">{l.references}</strong> carte memorizzate dai tuoi scan ·{" "}
      <strong className="text-ink">{l.corrections}</strong> correzioni dell&apos;OCR · soglie{" "}
      {tarate.length ? (
        <>tarate sui tuoi scan per {tarate.join(", ")}</>
      ) : (
        <>ancora di partenza (servono almeno 5 esempi per tipo; condizione: {esempiUsura} finora)</>
      )}
    </span>
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
  const [inCorso, setInCorso] = useState(false);
  const [fatti, setFatti] = useState(0);
  const [totale, setTotale] = useState(0);
  const [errori, setErrori] = useState<{ nome: string; error: string }[]>([]);
  const [sopra, setSopra] = useState(false);
  const [camera, setCamera] = useState(false);
  const input = useRef<HTMLInputElement>(null);
  const scatto = useRef<HTMLInputElement>(null);

  // Una fila sola per tutto quello che arriva (file scelti, trascinati,
  // scatti in raffica): si continua a scattare mentre si leggono i
  // precedenti, e i retro aspettano il loro fronte.
  const fila = useRef<File[]>([]);
  const lavora = useRef(false);
  const perNome = useRef(new Map<string, number>());
  const impRef = useRef(imp);
  impRef.current = imp;
  const base = (nome: string) => nome.replace(/\.[^.]+$/, "");

  useEffect(() => {
    coda.forEach((s) => s.original_filename && perNome.current.set(base(s.original_filename), s.id));
  }, [coda]);

  async function svuotaFila() {
    if (lavora.current) return;
    lavora.current = true;
    setInCorso(true);
    while (fila.current.length) {
      // Prima i fronti: un retro ha bisogno del suo fronte gia' caricato.
      const i = fila.current.findIndex((f) => nomeDelFronte(f.name) === null);
      const f = fila.current.splice(i >= 0 ? i : 0, 1)[0];
      try {
        const fronte = nomeDelFronte(f.name);
        if (fronte === null) {
          const s = await caricaScan(f, impRef.current.gameId, impRef.current.expansionId);
          perNome.current.set(base(f.name), s.id);
          onScan(s);
        } else {
          const id = perNome.current.get(fronte);
          if (!id) throw new Error("nessun fronte con questo nome");
          onAggiornata(await caricaRetro(id, f));
        }
      } catch (e) {
        setErrori((x) => [...x, { nome: f.name, error: msg(e) }]);
      }
      setFatti((n) => n + 1);
    }
    lavora.current = false;
    setInCorso(false);
  }

  function aggiungi(files: File[]) {
    const immagini = files.filter((f) => f.type.startsWith("image/"));
    if (!immagini.length) return;
    if (!lavora.current) {
      setFatti(0);
      setTotale(0);
      setErrori([]);
    }
    fila.current.push(...immagini);
    setTotale((t) => t + immagini.length);
    svuotaFila();
  }

  // Il pulsante tondo in basso a destra (telefono) apre la fotocamera.
  useEffect(() => {
    const apri = () => apriFotocamera();
    window.addEventListener("nn:admin-fab", apri);
    return () => window.removeEventListener("nn:admin-fab", apri);
  });

  function apriFotocamera() {
    if (disabilitato) return;
    // Fotocamera dentro la pagina se il browser la offre (si scatta in
    // raffica e su Android la pagina non viene chiusa); altrimenti
    // quella del telefono, uno scatto alla volta.
    if (supportsInAppCamera()) setCamera(true);
    else scatto.current?.click();
  }

  const pulsante = "btn text-base py-3 disabled:opacity-50 flex-1 sm:flex-none";
  return (
    <section
      className={
        "card p-4 sm:p-6 text-center sm:border-2 sm:border-dashed transition-colors " +
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
        aggiungi(Array.from(e.dataTransfer.files));
      }}
    >
      <div className="flex gap-2 justify-center">
        <button type="button" className={pulsante + " btn-primary"} disabled={disabilitato} onClick={apriFotocamera}>
          📷 Fotografa
        </button>
        <button type="button" className={pulsante + " btn-ghost"} disabled={disabilitato} onClick={() => input.current?.click()}>
          🖼 <span className="sm:hidden">Galleria</span><span className="hidden sm:inline">Scegli i file</span>
        </button>
      </div>
      <p className="hidden sm:block text-ink-soft text-sm mt-3">…oppure trascina qui gli scan.</p>
      <p className="text-xs text-ink-soft mt-3 text-left sm:text-center">
        Una carta per foto o per file, inquadrata dritta e intera, senza riflessi. Dallo scanner:
        JPEG o PNG a 300–600 dpi; il retro (facoltativo, migliora la stima della condizione) si
        chiama come il fronte con «_retro» in fondo. Per farli arrivare da soli usa la cartella
        osservata (scripts/scanner_watch.py).
      </p>
      <input ref={input} type="file" accept="image/*" multiple hidden
        onChange={(e) => {
          aggiungi(Array.from(e.target.files ?? []));
          e.target.value = "";
        }} />
      <input ref={scatto} type="file" accept="image/*" capture="environment" hidden
        onChange={(e) => {
          aggiungi(Array.from(e.target.files ?? []));
          e.target.value = "";
        }} />
      <CameraCapture open={camera} onClose={() => setCamera(false)} onCapture={(f) => aggiungi([f])} />
      {inCorso && (
        <p className="text-sm text-ink mt-3">
          Leggo {fatti + 1}/{totale}…
        </p>
      )}
      {!inCorso && totale > 0 && (
        <p className="text-sm text-ink-soft mt-3">
          {totale - errori.length} lett{totale - errori.length === 1 ? "o" : "i"}
          {errori.length > 0 && <span className="text-pink-deep"> · {errori.length} non caricati</span>}
        </p>
      )}
      {errori.length > 0 && (
        <ul className="mt-2 text-xs text-pink-deep text-left max-w-xl mx-auto">
          {errori.map((e, i) => (
            <li key={i}>
              {e.nome}: {e.error}
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

function Indizio({ etichetta, m, attivo }: { etichetta: string; m?: Misura; attivo: boolean }) {
  if (!attivo || !m) return null;
  const testo = m.value === true ? "sì" : m.value === false ? "no" : "incerto";
  const colore = m.value === true ? "bg-mint-soft" : m.value === null ? "bg-star" : "bg-ink/5";
  return (
    <span className={"px-2 py-0.5 rounded text-xs " + colore} title={m.score != null ? `misura ${m.score}` : undefined}>
      {etichetta}: {testo}
      {m.calibrated && <span className="opacity-60"> · tarata</span>}
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
      <div className="shrink-0 md:w-32 flex md:block gap-3 items-start">
        <a href={scan.image_url} target="_blank" rel="noreferrer" className="block w-28 md:w-32 shrink-0">
          <img src={thumbUrlFor(scan.image_url)} alt="scan" className="w-full rounded shadow" />
        </a>
        {/* Telefono: la carta scelta accanto allo scan, per confrontarle
            senza scorrere la fila dei candidati. */}
        {scelto?.image_url && (
          <figure className="md:hidden w-28 shrink-0">
            <img src={scelto.image_url} alt="" className="w-full rounded shadow" />
            <figcaption className="text-[10px] text-ink-soft mt-0.5 leading-tight">scelta: {scelto.expansion_name}</figcaption>
          </figure>
        )}
        <div className="min-w-0 md:contents">
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
          <div className="flex gap-2 overflow-x-auto pb-1 snap-x -mx-3 px-3 md:mx-0 md:px-0">
            {candidati.map((c) => (
              <button
                key={c.blueprint_id}
                type="button"
                onClick={() => setScelto(c)}
                className={
                  "shrink-0 snap-start w-28 text-left rounded p-1 border-2 transition-colors " +
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
                {c.seen_before != null && (
                  <span className="block text-[10px] font-bold text-ink" title={`somiglianza ${c.seen_before}`}>
                    ✓ già vista nei tuoi scan
                  </span>
                )}
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
              className="input py-1 !w-16"
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
            className="btn btn-primary text-sm disabled:opacity-50 w-full sm:w-auto py-3 sm:py-2 truncate"
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

/* Dove e' in vendita una carta: sito, CardTrader, eBay. */
function canali(c: PersonalCard): string[] {
  return [
    c.site_status === "PUBLISHED" && "Sito",
    c.cardtrader_product_id && "CardTrader",
    c.ebay_listing_id && (c.ebay_group_key ? "eBay (varianti)" : "eBay"),
  ].filter(Boolean) as string[];
}

const sulSito = (c: PersonalCard) => c.site_status === "PUBLISHED";
const suCardTrader = (c: PersonalCard) => !!c.cardtrader_product_id;
const suEbay = (c: PersonalCard) => !!c.ebay_listing_id;

/* Filtro per canale: dove e' gia' caricata una carta, e su eBay come (da
 * sola o come voce di un'inserzione con varianti). Le voci "non su" servono
 * a trovare cosa manca da caricare. */
type FiltroCanale =
  | "tutti" | "sito" | "cardtrader" | "ebay" | "ebay_singola" | "ebay_varianti"
  | "nessuno" | "no_sito" | "no_cardtrader" | "no_ebay";

const FILTRI_CANALE: { id: FiltroCanale; label: string; filtro: (c: PersonalCard) => boolean }[] = [
  { id: "tutti", label: "Tutti i canali", filtro: () => true },
  { id: "sito", label: "Sul sito", filtro: sulSito },
  { id: "cardtrader", label: "Su CardTrader", filtro: suCardTrader },
  { id: "ebay", label: "Su eBay", filtro: suEbay },
  { id: "ebay_singola", label: "eBay: inserzione singola", filtro: (c) => suEbay(c) && !c.ebay_group_key },
  { id: "ebay_varianti", label: "eBay: con varianti", filtro: (c) => suEbay(c) && !!c.ebay_group_key },
  { id: "nessuno", label: "Su nessun canale", filtro: (c) => !sulSito(c) && !suCardTrader(c) && !suEbay(c) },
  { id: "no_sito", label: "Non sul sito", filtro: (c) => !sulSito(c) },
  { id: "no_cardtrader", label: "Non su CardTrader", filtro: (c) => !suCardTrader(c) },
  { id: "no_ebay", label: "Non su eBay", filtro: (c) => !suEbay(c) },
];

type Vista = "da_caricare" | "in_vendita" | "vendute" | "tutte";

const NOMI_CANALI: Record<keyof Canali, string> = { site: "Sito", cardtrader: "CardTrader", ebay: "eBay" };

type Ordine = "recenti" | "numero";

/** Per espansione e poi per numero stampato, contando i numeri come numeri:
 *  "9/191" prima di "10/191", come stanno nel raccoglitore. */
function perNumero(a: PersonalCard, b: PersonalCard): number {
  const set = (a.collection || "").localeCompare(b.collection || "", "it");
  if (set) return set;
  const num = (c: PersonalCard) => c.printed_code || c.card_number || "";
  return num(a).localeCompare(num(b), "it", { numeric: true }) || a.id - b.id;
}

const VISTE: { id: Vista; label: string; filtro: (c: PersonalCard) => boolean }[] = [
  { id: "da_caricare", label: "Da mettere in vendita",
    filtro: (c) => c.status !== "SOLD" && c.status !== "ARCHIVED" && canali(c).length === 0 },
  { id: "in_vendita", label: "In vendita", filtro: (c) => c.status !== "SOLD" && canali(c).length > 0 },
  { id: "vendute", label: "Vendute", filtro: (c) => c.status === "SOLD" },
  { id: "tutte", label: "Tutte", filtro: () => true },
];

function Collezione({
  carte: tutte,
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
  // La vista resta quella dell'ultima volta: di solito si torna per
  // mettere in vendita le carte appena confermate.
  const [vista, setVistaStato] = useState<Vista>("da_caricare");
  useEffect(() => {
    const v = window.localStorage.getItem("nn_scanner_vista") as Vista | null;
    if (v && VISTE.some((x) => x.id === v)) setVistaStato(v);
  }, []);
  function setVista(v: Vista) {
    setVistaStato(v);
    // Cambiando vista si azzera la selezione: le azioni in blocco non
    // devono toccare carte che non si vedono.
    setSelezione(new Set());
    window.localStorage.setItem("nn_scanner_vista", v);
  }
  // Anche l'ordine resta quello scelto l'ultima volta.
  const [ordine, setOrdineStato] = useState<Ordine>("recenti");
  useEffect(() => {
    if (window.localStorage.getItem("nn_scanner_ordine") === "numero") setOrdineStato("numero");
  }, []);
  function setOrdine(o: Ordine) {
    setOrdineStato(o);
    window.localStorage.setItem("nn_scanner_ordine", o);
  }
  const [canale, setCanaleStato] = useState<FiltroCanale>("tutti");
  useEffect(() => {
    const v = window.localStorage.getItem("nn_scanner_canale") as FiltroCanale | null;
    if (v && FILTRI_CANALE.some((f) => f.id === v)) setCanaleStato(v);
  }, []);
  function setCanale(c: FiltroCanale) {
    setCanaleStato(c);
    setSelezione(new Set()); // come per le viste: niente azioni su carte nascoste
    window.localStorage.setItem("nn_scanner_canale", c);
  }
  const nellaVista = tutte.filter(VISTE.find((x) => x.id === vista)!.filtro);
  const filtrate = nellaVista.filter(FILTRI_CANALE.find((f) => f.id === canale)!.filtro);
  // Quante voci ha ogni inserzione con varianti: lo mostra la riga.
  const vociGruppo: Record<string, number> = {};
  for (const c of tutte) if (c.ebay_group_key && c.ebay_listing_id) vociGruppo[c.ebay_group_key] = (vociGruppo[c.ebay_group_key] || 0) + 1;
  // "recenti": l'ordine del server.
  const carte = ordine === "numero" ? [...filtrate].sort(perNumero) : filtrate;
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

  // Metti in vendita su piu' canali insieme. La scelta dei canali resta
  // quella dell'ultima volta.
  const [pannello, setPannello] = useState(false);
  const [canaliScelti, setCanaliScelti] = useState<Canali>({ site: true, cardtrader: true, ebay: true });
  useEffect(() => {
    try {
      const v = JSON.parse(window.localStorage.getItem("nn_scanner_canali") || "null");
      if (v) setCanaliScelti(v);
    } catch {
      /* scelta salvata illeggibile: si tengono i default */
    }
  }, []);
  function scegliCanale(k: keyof Canali, v: boolean) {
    setCanaliScelti((c) => {
      const n = { ...c, [k]: v };
      window.localStorage.setItem("nn_scanner_canali", JSON.stringify(n));
      return n;
    });
  }
  const disponibili: Canali = { site: true, cardtrader: !!st?.cardtrader, ebay: !!st?.ebay_publish };
  const canaliAttivi = (Object.keys(canaliScelti) as (keyof Canali)[]).filter((k) => canaliScelti[k] && disponibili[k]);

  // eBay: un'inserzione per carta, o tutte insieme in un'inserzione con
  // varianti (il compratore sceglie la carta da un menu). Nuova, o
  // aggiungendo le carte a una gia' pubblicata.
  const [ebayVarianti, setEbayVarianti] = useState(false);
  const [titoloGruppo, setTitoloGruppo] = useState("");
  const [gruppoScelto, setGruppoScelto] = useState("");
  const [gruppi, setGruppi] = useState<GruppoEbay[]>([]);
  useEffect(() => {
    if (pannello && ebayVarianti) gruppiEbay().then(setGruppi).catch(() => setGruppi([]));
  }, [pannello, ebayVarianti]);
  // Titolo proposto all'apertura del pannello: col gioco delle carte scelte,
  // se sono tutte dello stesso.
  useEffect(() => {
    if (!pannello) return;
    const giochi = new Set(scelte.map((c) => c.game_id));
    const gioco = giochi.size === 1 ? GIOCHI.find((g) => g.id === scelte[0]?.game_id)?.label : undefined;
    setTitoloGruppo(gioco ? `Carte ${gioco} singole - scegli la tua carta` : "Carte singole - scegli la tua carta");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pannello]);
  const conVarianti = ebayVarianti && canaliAttivi.includes("ebay");

  async function mettiInVendita() {
    // Con le varianti eBay non va carta per carta: una chiamata sola alla fine.
    const perCarta = canaliAttivi.filter((k) => !(k === "ebay" && conVarianti));
    const richiesta: Canali = { site: false, cardtrader: false, ebay: false };
    perCarta.forEach((k) => (richiesta[k] = true));
    const conta: Record<string, { ok: number; ko: string[] }> = {};
    perCarta.forEach((k) => (conta[k] = { ok: 0, ko: [] }));
    setBusy(true);
    setEsito(null);
    const righe: string[] = [];
    if (perCarta.length) {
      const { errori } = await inFila(
        scelte,
        async (c) => {
          const esiti = await pubblicaOvunque(c.id, richiesta);
          for (const [k, e] of Object.entries(esiti)) {
            if (!e) continue;
            if (e.ok) conta[k].ok++;
            else conta[k].ko.push(`${c.name}: ${e.detail ?? "errore"}`);
          }
        },
        (n) => setAvanzamento(`In vendita ${n}/${scelte.length}…`),
      );
      for (const k of perCarta) {
        const r = conta[k];
        const tot = scelte.length - errori.length;
        righe.push(`${NOMI_CANALI[k]}: ${r.ok}/${tot}` + (r.ko.length ? ` — ${r.ko.slice(0, 2).join(" | ")}` : ""));
      }
      if (errori.length) righe.push(`Non riuscite del tutto: ${errori.map((e) => `${e.item.name}: ${e.error}`).slice(0, 2).join(" | ")}`);
    }
    if (conVarianti) {
      setAvanzamento("eBay: preparo l'inserzione con varianti…");
      try {
        const g = await pubblicaGruppoEbay(scelte.map((c) => c.id), titoloGruppo.trim(), gruppoScelto || undefined);
        righe.push(`eBay: inserzione con ${g.count} carte` + (g.url ? ` — ${g.url}` : ""));
      } catch (err) {
        righe.push(`eBay (varianti): ${err instanceof Error ? err.message : String(err)}`);
      }
    }
    setAvanzamento(null);
    setEsito(righe.join("\n"));
    setBusy(false);
    setPannello(false);
    setSelezione(new Set());
    onCerca(cerca);
  }

  const mobile = useMobile();
  const propsRiga = (c: PersonalCard) => ({
    carta: c,
    scelta: selezione.has(c.id),
    onScelta: (v: boolean) =>
      setSelezione((s) => {
        const n = new Set(s);
        if (v) n.add(c.id);
        else n.delete(c.id);
        return n;
      }),
    onCambiata: sostituisci,
    onRicarica: () => onCerca(cerca),
    st,
    vociGruppo: c.ebay_group_key ? vociGruppo[c.ebay_group_key] : undefined,
  });

  const valoreTotale = tutte
    .filter((c) => c.status === "IN_STOCK")
    .reduce((t, c) => t + Number(c.list_price ?? c.estimated_value ?? 0) * (c.quantity || 1), 0);

  return (
    <section className="card p-4">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
        <h2 className="display text-lg text-ink">
          Collezione ({tutte.length})
          <span className="text-sm text-ink-soft font-normal"> · valore in magazzino {eur(valoreTotale)}</span>
        </h2>
        <div className="flex flex-wrap gap-2 w-full sm:w-auto">
          <input
            className="input py-1 text-sm !w-full sm:!w-48"
            placeholder="cerca nome, set, numero"
            value={cerca}
            onChange={(e) => setCerca(e.target.value)}
          />
          <button type="button" className="btn btn-ghost text-sm" onClick={() => scaricaCsv().catch((e) => setEsito(msg(e)))}>
            📄 Esporta CSV
          </button>
          <button type="button" className="btn btn-ghost text-sm" disabled={busy}
            title="Cerca vendite su CardTrader ed eBay e ritira le carte vendute dagli altri canali (lo fa anche da solo ogni 15 minuti)"
            onClick={async () => {
              setBusy(true);
              try {
                const r = await controllaVendite();
                const righe = r.vendute.map((v) =>
                  `${v.nome}: venduta su ${v.piattaforma}${v.da_ritirare_a_mano.length ? ` (ritira a mano da ${v.da_ritirare_a_mano.join(", ")})` : ""}`);
                Object.entries(r.errori).forEach(([k, e]) => righe.push(`${k} non risponde: ${e}`));
                setEsito(righe.length ? righe.join("\n") : "Nessuna vendita nuova su CardTrader o eBay");
                if (r.vendute.length) onCerca(cerca);
              } catch (e) {
                setEsito(msg(e));
              } finally {
                setBusy(false);
              }
            }}>
            🔄 Controlla vendite
          </button>
        </div>
      </div>

      <div className="flex gap-1 mb-3 overflow-x-auto -mx-4 px-4 md:mx-0 md:px-0 whitespace-nowrap" role="tablist">
        {VISTE.map((v) => {
          const n = tutte.filter(v.filtro).length;
          const attiva = v.id === vista;
          return (
            <button key={v.id} type="button" role="tab" aria-selected={attiva}
              onClick={() => setVista(v.id)}
              className={"px-3 py-2 rounded-full text-sm font-semibold transition-colors " +
                (attiva ? "bg-lilac-deep text-white" : "bg-ink/5 text-ink-soft hover:bg-ink/10")}>
              {v.label} <span className={attiva ? "opacity-80" : "opacity-60"}>{n}</span>
            </button>
          );
        })}
        <select className={"input text-sm !w-auto ml-auto py-1.5 " + (canale !== "tutti" ? "ring-2 ring-lilac-deep" : "")}
          value={canale} aria-label="Canale" onChange={(e) => setCanale(e.target.value as FiltroCanale)}>
          {FILTRI_CANALE.map((f) => (
            <option key={f.id} value={f.id}>
              {f.label} ({nellaVista.filter(f.filtro).length})
            </option>
          ))}
        </select>
        <select className="input text-sm !w-auto py-1.5" value={ordine} aria-label="Ordine"
          onChange={(e) => setOrdine(e.target.value as Ordine)}>
          <option value="recenti">Più recenti</option>
          <option value="numero">Per numero</option>
        </select>
      </div>

      {/* Su telefono la barra resta in vista sotto l'intestazione mentre si
          scorre la lista, e i pulsanti scorrono di lato invece di andare a capo. */}
      <div className={
        "flex items-center gap-2 mb-3 text-sm " +
        (selezione.size > 0
          ? "sticky top-14 md:static z-20 -mx-4 px-4 py-2 md:m-0 md:p-0 bg-white/95 md:bg-transparent backdrop-blur overflow-x-auto md:flex-wrap md:overflow-visible whitespace-nowrap"
          : "flex-wrap")
      }>
        <span className="text-ink-soft md:hidden">
          {selezione.size ? `${selezione.size} selezionate:` : "Seleziona le carte per valutarle o caricarle in blocco"}
        </span>
        <span className="text-ink-soft hidden md:inline">{selezione.size} selezionate:</span>
        <div className={(selezione.size ? "flex" : "hidden md:flex") + " items-center gap-2 md:flex-wrap"}>
        <button type="button" className="btn btn-ghost text-xs" disabled={busy || !selezione.size}
          onClick={() => inBlocco("Valuto", async (c) => sostituisci((await valuta(c.id)).card))}>
          💶 Valuta
        </button>
        <button type="button" className="btn btn-primary text-xs disabled:opacity-50" disabled={busy || !selezione.size}
          onClick={() => setPannello((v) => !v)} aria-expanded={pannello}>
          🛒 Metti in vendita…
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
        </div>
        {avanzamento && <span className="text-ink">{avanzamento}</span>}
      </div>
      {pannello && selezione.size > 0 && (
        <div className="mb-3 p-3 rounded-xl border border-lilac-deep/40 bg-lilac/10 text-sm">
          <p className="font-semibold text-ink mb-2">
            Metti in vendita {selezione.size} cart{selezione.size === 1 ? "a" : "e"} su:
          </p>
          <div className="flex flex-wrap gap-x-5 gap-y-2">
            {([
              ["site", "Sito", true, null],
              ["cardtrader", "CardTrader", !!st?.cardtrader, "non configurato"],
              ["ebay", "eBay", !!st?.ebay_publish, "non collegato"],
            ] as const).map(([k, label, disponibile, motivo]) => (
              <label key={k} className={"flex items-center gap-2 " + (disponibile ? "text-ink" : "text-ink-soft")}>
                <input type="checkbox" className="h-5 w-5 accent-lilac-deep" disabled={!disponibile}
                  checked={disponibile && canaliScelti[k]}
                  onChange={(e) => scegliCanale(k, e.target.checked)} />
                {label}
                {!disponibile && <span className="text-xs">({motivo})</span>}
              </label>
            ))}
          </div>
          {disponibili.ebay && canaliScelti.ebay && (
            <div className="mt-3 pl-3 border-l-2 border-lilac-deep/40 space-y-2">
              <div className="flex flex-wrap gap-x-5 gap-y-1">
                <label className="flex items-center gap-2 text-ink">
                  <input type="radio" name="ebay-modo" className="h-4 w-4 accent-lilac-deep"
                    checked={!ebayVarianti} onChange={() => setEbayVarianti(false)} />
                  eBay: un&apos;inserzione per carta
                </label>
                <label className="flex items-center gap-2 text-ink">
                  <input type="radio" name="ebay-modo" className="h-4 w-4 accent-lilac-deep"
                    checked={ebayVarianti} onChange={() => setEbayVarianti(true)} />
                  eBay: un&apos;unica inserzione con varianti
                </label>
              </div>
              {ebayVarianti && (
                <div className="flex flex-wrap items-center gap-2">
                  <select className="input text-sm max-w-xs" value={gruppoScelto}
                    onChange={(e) => setGruppoScelto(e.target.value)}>
                    <option value="">Nuova inserzione</option>
                    {gruppi.map((g) => (
                      <option key={g.group_key} value={g.group_key}>
                        Aggiungi a {g.listing_id ?? g.group_key} ({g.count} carte)
                      </option>
                    ))}
                  </select>
                  {!gruppoScelto && (
                    <input className="input text-sm flex-1 min-w-48" maxLength={80} value={titoloGruppo}
                      onChange={(e) => setTitoloGruppo(e.target.value)} placeholder="Titolo dell'inserzione" />
                  )}
                  <p className="text-xs text-ink-soft w-full">
                    Una pagina eBay con il menu &quot;Carta&quot;: ogni carta con il suo prezzo e la sua foto.
                    Le carte già su eBay da sole vanno tolte prima. Su eBay sotto 1 € si va a 1 € (il minimo di eBay).
                  </p>
                </div>
              )}
            </div>
          )}
          <p className="text-xs text-ink-soft mt-2">
            Ogni piattaforma al suo prezzo (colonna Prezzi). Dove non l&apos;hai scritto: CardTrader come il sito;
            eBay quanto serve a coprire la commissione di <a href="/admin/markups" className="underline">Commissioni</a>
            (11% se non c&apos;è), mai sotto 1 €. Se una carta è già in vendita su un canale, l&apos;inserzione si
            aggiorna (anche il prezzo) invece di duplicarsi.
          </p>
          <div className="flex gap-2 mt-3">
            <button type="button" className="btn btn-primary text-sm disabled:opacity-50"
              disabled={busy || !canaliAttivi.length} onClick={mettiInVendita}>
              {busy ? "…" : `Vai: ${canaliAttivi.map((k) => NOMI_CANALI[k]).join(" + ") || "scegli un canale"}`}
            </button>
            <button type="button" className="btn btn-ghost text-sm" onClick={() => setPannello(false)}>Annulla</button>
          </div>
        </div>
      )}
      {esito && <p className="text-xs text-ink-soft mb-3 whitespace-pre-line">{esito}</p>}

      {carte.length === 0 ? (
        <p className="text-ink-soft text-sm">
          {tutte.length === 0
            ? "Nessuna carta: conferma qualche scan."
            : vista === "da_caricare"
              ? "Tutte le carte sono gia' in vendita da qualche parte. 🎉"
              : vista === "in_vendita"
                ? "Nessuna carta in vendita: mettile in vendita da «Da mettere in vendita»."
                : "Nessuna carta qui."}
        </p>
      ) : mobile ? (
        <>
          <label className="flex items-center gap-2 text-sm text-ink-soft mb-2">
            <input
              type="checkbox"
              className="h-5 w-5 accent-lilac-deep"
              checked={selezione.size === carte.length && carte.length > 0}
              onChange={(e) => setSelezione(e.target.checked ? new Set(carte.map((c) => c.id)) : new Set())}
            />
            Seleziona tutte
          </label>
          <ul className="space-y-3">
            {carte.map((c) => (
              <RigaCarta key={c.id} layout="scheda" {...propsRiga(c)} />
            ))}
          </ul>
        </>
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
                <th className="py-2 pr-2 text-right">Prezzi</th>
                <th className="py-2">In vendita</th>
              </tr>
            </thead>
            <tbody>
              {carte.map((c) => (
                <RigaCarta key={c.id} layout="riga" {...propsRiga(c)} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

/** Prezzo di una piattaforma: salva all'uscita dal campo (o Invio) solo se
 *  e' cambiato. Vuoto mostra in grigio quello che si userebbe. */
function CampoPrezzo({ etichetta, valore, auto, onSalva }: {
  etichetta: string;
  valore?: string | null;
  auto?: string | number | null;
  onSalva: (v: string) => void;
}) {
  const [testo, setTesto] = useState(valore ?? "");
  useEffect(() => setTesto(valore ?? ""), [valore]);
  const segnaposto = auto != null && auto !== "" ? Number(auto).toFixed(2) : "";
  return (
    <>
      <span>{etichetta}</span>
      <input
        className="input py-1 text-sm !w-20 text-right"
        inputMode="decimal"
        value={testo}
        placeholder={segnaposto}
        onChange={(e) => setTesto(e.target.value)}
        onBlur={() => {
          const v = testo.replace(",", ".").trim();
          if (v !== (valore ?? "")) onSalva(v);
        }}
        onKeyDown={(e) => e.key === "Enter" && (e.target as HTMLInputElement).blur()}
        aria-label={`Prezzo ${etichetta}`}
      />
    </>
  );
}

/** true sotto i 768px (il "md" di Tailwind): telefono. Una sola resa
 * alla volta, invece di tabella e schede nascoste via CSS: ogni riga ha il
 * suo stato (prezzo in modifica, venduti a mano) e doppiarla lo
 * sdoppierebbe. */
function useMobile(): boolean {
  const [mobile, setMobile] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia("(max-width: 767px)");
    const aggiorna = () => setMobile(mq.matches);
    aggiorna();
    mq.addEventListener("change", aggiorna);
    return () => mq.removeEventListener("change", aggiorna);
  }, []);
  return mobile;
}

function RigaCarta({
  layout,
  carta: c,
  scelta,
  onScelta,
  onCambiata,
  onRicarica,
  st,
  vociGruppo,
}: {
  layout: "riga" | "scheda";
  carta: PersonalCard;
  scelta: boolean;
  onScelta: (v: boolean) => void;
  onCambiata: (c: PersonalCard) => void;
  onRicarica: () => void;
  st: StatoScanner | null;
  /** Carte nella stessa inserzione con varianti (se la carta ne fa parte). */
  vociGruppo?: number;
}) {
  const [busy, setBusy] = useState(false);
  const [nota, setNota] = useState<string | null>(null);
  const [aMano, setAMano] = useState(false);
  const [prezziEbay, setPrezziEbay] = useState("");


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

  async function salvaPrezzo(campo: "list_price" | "list_price_cardtrader" | "list_price_ebay", v: string) {
    await azione(async () => onCambiata(await aggiornaCarta(c.id, { [campo]: v || null })));
  }

  async function apriVenduti() {
    const { url } = await urlVendutiEbay(c.id);
    window.open(url, "_blank", "noopener");
    setAMano(true);
  }

  const scan = c.images?.[0];
  // In italiano dove lo si conosce; l'inglese di CardTrader sotto, piccolo.
  const nome = c.name_it || c.name;
  const inglese = c.name_it && c.name_it !== c.name ? c.name : null;

  const dettagli = (
    <>
      {inglese && <span className="block text-[11px] text-ink-soft italic">{inglese}</span>}
      <span className="block text-xs text-ink-soft">
        {c.collection_it || c.collection} · {c.printed_code || c.card_number}
      </span>
      <span className="block text-xs text-ink-soft">
        {(c.language || "").toUpperCase()} · {c.condition}
        {c.reverse && " · reverse"}
        {c.first_edition && " · 1ª ed."}
        {c.quantity > 1 && ` · ×${c.quantity}`}
        {c.status !== "IN_STOCK" && ` · ${c.status}`}
      </span>
      {canali(c).length > 0 && c.status !== "SOLD" && (
        <span className="block text-xs text-ink mt-0.5">🟢 in vendita su {canali(c).join(" · ")}</span>
      )}
      {c.status === "SOLD" && (
        <span className="block text-xs text-ink mt-0.5">
          💰 venduta{c.sold_platform ? ` su ${c.sold_platform}` : ""}{c.sale_price ? ` a ${eur(c.sale_price)}` : ""}
        </span>
      )}
      {nota && <span className="block text-xs text-pink-deep">{nota}</span>}
    </>
  );

  const venduti = (
    <>
      <span className="block text-[11px] text-ink-soft">
        {c.ebay_sold_count ? `media di ${c.ebay_sold_count}` : "nessuno"}
        {c.ebay_sold_source === "manuale" && " · a mano"}
      </span>
      <button type="button" className="text-[11px] underline text-lilac-deep py-1" onClick={() => apriVenduti().catch((e) => setNota(msg(e)))}>
        venduti ↗
      </button>
      {aMano && (
        <div className="mt-1 flex gap-1 justify-end">
          <input
            className="input py-0.5 text-xs !w-32"
            placeholder="12,50 9,90 15…"
            inputMode="decimal"
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
    </>
  );

  const rivaluta = (
    <button
      type="button"
      className="text-[11px] underline text-lilac-deep disabled:opacity-50 py-1"
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
  );

  // Tre prezzi: il sito usa quello della carta; CardTrader ed eBay il loro
  // se scritto, se no il calcolato (in grigio). Vuoto = torna al calcolato.
  const campoPrezzo = (
    <div className="grid grid-cols-[auto_auto] gap-x-2 gap-y-1 items-center justify-end text-xs text-ink-soft">
      <CampoPrezzo etichetta="Sito" valore={c.list_price} auto={c.estimated_value}
        onSalva={(v) => salvaPrezzo("list_price", v)} />
      <CampoPrezzo etichetta="CardTrader" valore={c.list_price_cardtrader} auto={c.cardtrader_price_auto}
        onSalva={(v) => salvaPrezzo("list_price_cardtrader", v)} />
      <CampoPrezzo etichetta="eBay" valore={c.list_price_ebay} auto={c.ebay_price_auto}
        onSalva={(v) => salvaPrezzo("list_price_ebay", v)} />
    </div>
  );

  const inVendita = (
    <>
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
            <span className="text-xs text-ink-soft">
              ✅ eBay{" "}
              <span className="text-ink" title={c.ebay_group_key ? `Inserzione con varianti ${c.ebay_group_key}` : undefined}>
                {c.ebay_group_key ? `(varianti${vociGruppo ? `, ${vociGruppo} carte` : ""})` : "(singola)"}
              </span>{" "}·{" "}
              {c.ebay_url && (
                <>
                  <a href={c.ebay_url} target="_blank" rel="noreferrer" className="underline">vedi</a>
                  {" · "}
                </>
              )}
              <button type="button" className="underline" disabled={busy}
                onClick={() => azione(async () => { await ritiraEbay(c.id); onRicarica(); }, "tolta da eBay")}>
                ritira
              </button>
            </span>
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
</>
  );

  if (layout === "scheda") {
    return (
      <li className={"border rounded-xl p-3 " + (scelta ? "border-lilac-deep bg-lilac/10" : "border-ink/10")}>
        <div className="flex gap-3">
          <input type="checkbox" className="h-5 w-5 mt-1 shrink-0 accent-lilac-deep" checked={scelta}
            onChange={(e) => onScelta(e.target.checked)} aria-label={`Seleziona ${c.name}`} />
          {scan && (
            <a href={scan} target="_blank" rel="noreferrer" className="shrink-0">
              <img src={thumbUrlFor(scan)} alt="" className="w-16 rounded" loading="lazy" />
            </a>
          )}
          <div className="min-w-0 flex-1">
            <strong className="text-ink block leading-tight">{nome}</strong>
            {dettagli}
          </div>
        </div>
        <dl className="grid grid-cols-3 gap-2 mt-3 text-center text-sm">
          <div className="rounded-lg bg-ink/5 py-1.5">
            <dt className="text-[10px] uppercase tracking-wide text-ink-soft">CardTrader</dt>
            <dd>{eur(c.cardtrader_price)}</dd>
          </div>
          <div className="rounded-lg bg-ink/5 py-1.5">
            <dt className="text-[10px] uppercase tracking-wide text-ink-soft">eBay</dt>
            <dd>{eur(c.ebay_sold_avg)}</dd>
          </div>
          <div className="rounded-lg bg-ink/5 py-1.5">
            <dt className="text-[10px] uppercase tracking-wide text-ink-soft">Suggerito</dt>
            <dd className="font-bold text-ink">{eur(c.estimated_value)}</dd>
          </div>
        </dl>
        <div className="flex items-start justify-between gap-2 mt-1 text-right">
          <div className="text-left">{rivaluta}</div>
          <div>{venduti}</div>
        </div>
        <div className="flex items-start justify-between gap-3 mt-2 text-sm text-ink-soft">
          Prezzi di vendita {campoPrezzo}
        </div>
        <div className="flex flex-wrap gap-x-4 gap-y-2 mt-3 pt-3 border-t border-ink/10 [&>div]:min-h-[2.25rem] [&>div]:flex [&>div]:items-center">
          {inVendita}
        </div>
      </li>
    );
  }

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
        <strong className="text-ink">{nome}</strong>
        {dettagli}
      </td>
      <td className="py-2 pr-2 text-right whitespace-nowrap">
        {eur(c.cardtrader_price)}
        {c.cardtrader_offers != null && <span className="block text-[11px] text-ink-soft">{c.cardtrader_offers} in vendita</span>}
      </td>
      <td className="py-2 pr-2 text-right whitespace-nowrap">
        {eur(c.ebay_sold_avg)}
        {venduti}
      </td>
      <td className="py-2 pr-2 text-right whitespace-nowrap">
        <strong className="text-ink">{eur(c.estimated_value)}</strong>
        <div>{rivaluta}</div>
      </td>
      <td className="py-2 pr-2 text-right">{campoPrezzo}</td>
      <td className="py-2 whitespace-nowrap space-y-1">{inVendita}</td>
    </tr>
  );
}
