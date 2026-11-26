"use client";

import { useEffect, useState } from "react";
import { AdminShell } from "@/components/admin/AdminShell";
import { adminApi } from "@/lib/admin-api";

/* Instagram: vedere prima cosa uscira'.
 *
 * Le anteprime montano i Reel e le immagini come farebbe la pubblicazione
 * automatica (utils/instagram*, backend) ma non pubblicano niente: salvano
 * solo i file tra quelli statici del sito. "Pubblica ora" invece pubblica
 * davvero, e chiede conferma. */

interface Voce {
  id: number;
  title: string;
  price: number;
  image: string;
}

interface Stato {
  configured: boolean;
  enabled: boolean;
  story_min_price: number;
  next_carousel: Voce[];
  next_stories: Voce[];
  caption: string | null;
  fallback: Voce | null;
}

interface Statistiche {
  slot_today: string;
  reach_by_slot: Record<string, { posts: number; avg_reach: number | null }>;
  top_hashtags: Record<string, number>;
  report: string | null;
}

interface Rubrica {
  rubrica: string;
  type: "reel" | "carosello" | "foto";
  media: string | string[];
  caption: string;
  slot: string;
}

interface ReelMese {
  video: string;
  articoli: number;
  caption: string;
}

const GIORNI = [
  { day: 0, nome: "Lunedì", rubrica: "Reel nuovi arrivi della settimana" },
  { day: 1, nome: "Martedì", rubrica: "Reel quiz “Indovina il prezzo”" },
  { day: 2, nome: "Mercoledì", rubrica: "Sotto i 5 €" },
  { day: 3, nome: "Giovedì", rubrica: "Idee regalo" },
  { day: 4, nome: "Venerdì", rubrica: "Le carte salite di più" },
  { day: 5, nome: "Sabato", rubrica: "N anni fa usciva…" },
  { day: 6, nome: "Domenica", rubrica: "La rara della settimana" },
];

const MESI = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio",
  "agosto", "settembre", "ottobre", "novembre", "dicembre"];

// I file di anteprima hanno sempre lo stesso nome: senza questo il browser
// mostrerebbe quello vecchio dalla cache.
function fresco(url: string): string {
  return `${url}${url.includes("?") ? "&" : "?"}t=${Date.now()}`;
}

function messaggio(err: unknown): string {
  if (err && typeof err === "object" && "status" in err && (err as { status: number }).status === 404) {
    return "Niente da mostrare: questa rubrica oggi non ha materiale (quel giorno non uscirebbe niente).";
  }
  return err instanceof Error ? err.message : String(err);
}

function Didascalia({ testo }: { testo: string }) {
  return (
    <pre className="whitespace-pre-wrap text-sm text-ink-soft bg-white/70 rounded-2xl p-4 mt-3 font-sans">
      {testo}
    </pre>
  );
}

function Media({ tipo, media }: { tipo: string; media: string | string[] }) {
  if (tipo === "reel") {
    return (
      <video src={fresco(String(media))} controls playsInline className="w-full max-w-xs rounded-2xl shadow-lg" />
    );
  }
  const immagini = Array.isArray(media) ? media : [media];
  return (
    <div className="flex gap-3 overflow-x-auto pb-2 snap-x">
      {immagini.map((u, i) => (
        // eslint-disable-next-line @next/next/no-img-element
        <img key={i} src={fresco(u)} alt="" className="h-72 rounded-2xl shadow snap-start" loading="lazy" />
      ))}
    </div>
  );
}

export default function InstagramPage() {
  const [stato, setStato] = useState<Stato | null>(null);
  const [stats, setStats] = useState<Statistiche | null>(null);
  const [errore, setErrore] = useState<string | null>(null);

  const oggi = new Date();
  const [anno, setAnno] = useState(oggi.getMonth() === 0 ? oggi.getFullYear() - 1 : oggi.getFullYear());
  const [mese, setMese] = useState(oggi.getMonth() === 0 ? 12 : oggi.getMonth());
  const [reel, setReel] = useState<ReelMese | null>(null);
  const [reelErrore, setReelErrore] = useState<string | null>(null);

  const [giorno, setGiorno] = useState<number | null>(null);
  const [rubrica, setRubrica] = useState<Rubrica | null>(null);
  const [rubricaErrore, setRubricaErrore] = useState<string | null>(null);

  const [lavoro, setLavoro] = useState<string | null>(null);
  const [esito, setEsito] = useState<string | null>(null);

  useEffect(() => {
    adminApi.get<Stato>("/api/social/instagram/status").then(setStato).catch((e) => setErrore(messaggio(e)));
    adminApi.get<Statistiche>("/api/social/instagram/stats").then(setStats).catch(() => setStats(null));
  }, []);

  async function anteprimaReel() {
    setLavoro("reel");
    setReel(null);
    setReelErrore(null);
    try {
      setReel(await adminApi.post<ReelMese>("/api/social/instagram/reel/preview", { year: anno, month: mese }));
    } catch (e) {
      setReelErrore(
        e && typeof e === "object" && "status" in e && (e as { status: number }).status === 404
          ? `Nessun articolo venduto a ${MESI[mese - 1]} ${anno}.`
          : messaggio(e),
      );
    } finally {
      setLavoro(null);
    }
  }

  async function anteprimaRubrica(day: number) {
    setGiorno(day);
    setLavoro(`rubrica-${day}`);
    setRubrica(null);
    setRubricaErrore(null);
    try {
      setRubrica(await adminApi.get<Rubrica>(`/api/social/instagram/rubrica?day=${day}`));
    } catch (e) {
      setRubricaErrore(messaggio(e));
    } finally {
      setLavoro(null);
    }
  }

  async function pubblica(cosa: "reel" | "rubrica") {
    const descrizione = cosa === "reel"
      ? `il Reel dei venduti di ${MESI[mese - 1]} ${anno}`
      : `la rubrica del ${GIORNI[giorno ?? 0].nome.toLowerCase()}`;
    if (!window.confirm(`Pubblico adesso su Instagram ${descrizione}? Non si può annullare da qui.`)) return;
    setLavoro(`pubblica-${cosa}`);
    setEsito(null);
    try {
      const body = cosa === "reel" ? { what: "reel", year: anno, month: mese } : { what: "rubrica", day: giorno };
      const r = await adminApi.post<Record<string, unknown>>("/api/social/instagram/run", body);
      const fatto = r.reel ?? r.rubrica;
      setEsito(fatto ? "✅ Pubblicato su Instagram." : "Niente da pubblicare.");
    } catch (e) {
      setEsito(`⚠ ${messaggio(e)}`);
    } finally {
      setLavoro(null);
    }
  }

  return (
    <AdminShell>
      <div className="max-w-5xl mx-auto space-y-8">
        <header>
          <h1 className="display text-3xl text-ink">📸 Instagram</h1>
          <p className="text-ink-soft mt-1">
            Le anteprime mostrano cosa uscirebbe, senza pubblicare niente.
          </p>
        </header>

        {errore && <p className="text-pink-deep font-semibold">⚠ {errore}</p>}

        {stato && (
          <section className="card p-5 flex flex-wrap gap-3 items-center">
            <span className={`chip ${stato.enabled ? "chip-mint" : "chip-pink"}`}>
              {stato.enabled ? "Acceso" : stato.configured ? "Spento" : "Non configurato"}
            </span>
            {stats && <span className="chip">Post del giorno alle {stats.slot_today}</span>}
            <span className="chip">Storie da {stato.story_min_price} € in su</span>
            <span className="text-xs text-ink-soft">
              Acceso/spento e soglia delle Storie si cambiano in Impostazioni.
            </span>
          </section>
        )}

        <section className="card p-5">
          <h2 className="display text-xl text-ink mb-3">🎬 Reel del mese: i venduti</h2>
          <p className="text-sm text-ink-soft mb-3">Esce da solo il 1° del mese alle 18:00 con il mese appena finito.</p>
          <div className="flex flex-wrap gap-2 items-center">
            <select value={mese} onChange={(e) => setMese(Number(e.target.value))} className="rounded-xl border border-ink/15 px-3 py-2 bg-white">
              {MESI.map((m, i) => <option key={m} value={i + 1}>{m}</option>)}
            </select>
            <input type="number" value={anno} onChange={(e) => setAnno(Number(e.target.value))}
              className="w-24 rounded-xl border border-ink/15 px-3 py-2 bg-white" />
            <button type="button" className="btn btn-primary text-sm" disabled={lavoro !== null} onClick={anteprimaReel}>
              {lavoro === "reel" ? "Monto il video…" : "Anteprima"}
            </button>
            {reel && (
              <button type="button" className="btn btn-ghost text-sm" disabled={lavoro !== null} onClick={() => pubblica("reel")}>
                Pubblica ora
              </button>
            )}
          </div>
          {reelErrore && <p className="text-pink-deep text-sm mt-3">⚠ {reelErrore}</p>}
          {reel && (
            <div className="mt-4 grid gap-4 sm:grid-cols-[auto_1fr]">
              <Media tipo="reel" media={reel.video} />
              <div>
                <p className="text-sm text-ink">{reel.articoli} pezzi venduti</p>
                <Didascalia testo={reel.caption} />
              </div>
            </div>
          )}
        </section>

        <section className="card p-5">
          <h2 className="display text-xl text-ink mb-3">📅 Rubriche</h2>
          <p className="text-sm text-ink-soft mb-3">
            Una al giorno, nella fascia oraria migliore dopo quella del post del giorno.
            {rubrica && ` Oggi uscirebbe alle ${rubrica.slot}.`}
          </p>
          <div className="flex flex-wrap gap-2">
            {GIORNI.map((g) => (
              <button key={g.day} type="button" disabled={lavoro !== null} onClick={() => anteprimaRubrica(g.day)}
                className={`chip cursor-pointer ${giorno === g.day ? "chip-pink" : ""}`} title={g.rubrica}>
                {lavoro === `rubrica-${g.day}` ? "…" : g.nome}
              </button>
            ))}
          </div>
          {giorno !== null && <p className="text-sm text-ink mt-3 font-semibold">{GIORNI[giorno].rubrica}</p>}
          {rubricaErrore && <p className="text-pink-deep text-sm mt-3">⚠ {rubricaErrore}</p>}
          {rubrica && (
            <div className="mt-4">
              <Media tipo={rubrica.type} media={rubrica.media} />
              <Didascalia testo={rubrica.caption} />
              <button type="button" className="btn btn-ghost text-sm mt-3" disabled={lavoro !== null}
                onClick={() => pubblica("rubrica")}>
                Pubblica ora
              </button>
            </div>
          )}
        </section>

        {esito && <p className="text-ink font-semibold">{esito}</p>}

        {stato && (
          <section className="card p-5">
            <h2 className="display text-xl text-ink mb-3">🆕 Prossimo post del giorno</h2>
            {stato.next_carousel.length > 0 ? (
              <>
                <Media tipo="carosello" media={stato.next_carousel.map((v) => v.image)} />
                {stato.caption && <Didascalia testo={stato.caption} />}
              </>
            ) : stato.fallback ? (
              <>
                <p className="text-sm text-ink-soft mb-2">Nessun nuovo arrivo: uscirebbe questo dal catalogo.</p>
                <Media tipo="foto" media={stato.fallback.image} />
              </>
            ) : (
              <p className="text-sm text-ink-soft">Niente da pubblicare.</p>
            )}
            {stato.next_stories.length > 0 && (
              <>
                <h3 className="display text-base text-ink mt-5 mb-2">Storie in coda</h3>
                <Media tipo="foto" media={stato.next_stories.map((v) => v.image)} />
              </>
            )}
          </section>
        )}

        {stats && (
          <section className="card p-5">
            <h2 className="display text-xl text-ink mb-3">📊 Statistiche</h2>
            <table className="text-sm mb-4">
              <thead>
                <tr className="text-left text-ink-soft"><th className="pr-6">Fascia</th><th className="pr-6">Post</th><th>Persone raggiunte (media)</th></tr>
              </thead>
              <tbody>
                {Object.entries(stats.reach_by_slot).map(([slot, v]) => (
                  <tr key={slot}>
                    <td className="pr-6 font-semibold">{slot}</td>
                    <td className="pr-6">{v.posts}</td>
                    <td>{v.avg_reach ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {Object.keys(stats.top_hashtags).length > 0 && (
              <p className="text-sm text-ink-soft">
                Hashtag migliori:{" "}
                {Object.entries(stats.top_hashtags).map(([t, v]) => `${t} (${Math.round(v)})`).join(", ")}
              </p>
            )}
            {stats.report && <Didascalia testo={stats.report} />}
          </section>
        )}
      </div>
    </AdminShell>
  );
}
