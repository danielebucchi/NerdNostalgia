import { API_BASE, PUBLIC_API_BASE } from "@/lib/api";

/* Guida prezzi delle carte Pokémon (backend api/price_guide.py): i dati si
 * aggiornano una volta a settimana, le pagine si rigenerano ogni ora. */

export interface GuideSet {
  slug: string;
  name: string;
  name_en: string;
  release_date: string | null;
  card_count: number | null;
  serie: string | null;
  logo: string | null;
  cards_priced: number | null;
  updated_at: string | null;
}

export interface GuideCopy {
  id: number;
  title: string;
  price: number;
  image: string | null;
  /** Solo per le carte della collezione (scanner). */
  condition: Condizione | null;
  language: string | null;
}

/** La copia piu' economica, e in copies tutte quelle che abbiamo. */
export interface GuideAvailable extends GuideCopy {
  copies?: GuideCopy[];
}

/** Prezzo di mercato e offerta per una lingua e una condizione. */
export interface GuideCell {
  price: number | null;
  buy_offer: number | null;
  buy_bulk: { era: string; eur_per_kg: number } | null;
  buy_none: boolean;
}

export type Lingua = "it" | "en";
export type Versione = "normale" | "1ed" | "reverse";

export const VERSIONI: { id: Versione; nome: string; spiegazione: string }[] = [
  { id: "normale", nome: "Normale", spiegazione: "La carta come esce dalle buste, senza simboli particolari." },
  { id: "1ed", nome: "1ª edizione", spiegazione: "Con il simbolo \"Edition 1\" (il cerchietto nero) a sinistra sotto l'illustrazione." },
  { id: "reverse", nome: "Reverse holo", spiegazione: "Lucida su tutta la carta tranne l'illustrazione." },
];
export type Condizione = "NM" | "SP" | "MP" | "PL" | "PO";

export const LINGUE: { id: Lingua; nome: string }[] = [
  { id: "it", nome: "Italiana" },
  { id: "en", nome: "Inglese" },
];

/** Le condizioni, dalla migliore, con una spiegazione per chi vende. */
export const CONDIZIONI: { id: Condizione; nome: string; spiegazione: string }[] = [
  { id: "NM", nome: "Near Mint", spiegazione: "Come nuova: angoli e bordi perfetti, nessun graffio." },
  { id: "SP", nome: "Slightly Played", spiegazione: "Quasi perfetta: qualche segno leggero sui bordi o sul retro." },
  { id: "MP", nome: "Moderately Played", spiegazione: "Usata: bordi e angoli consumati, graffi visibili, nessuna piega." },
  { id: "PL", nome: "Played", spiegazione: "Molto usata: usura forte, graffi evidenti, piccole pieghe." },
  { id: "PO", nome: "Poor", spiegazione: "Rovinata: pieghe, strappi, macchie o scritte." },
];

export interface GuideCard {
  slug: string;
  set_slug: string;
  set_name: string;
  number: string;
  name: string;
  name_en: string;
  image: string | null;
  min_price: number | null;
  offers: number;
  available: GuideAvailable | null;
  /** Quanto diamo al massimo per una copia in ottime condizioni (Impostazioni). */
  buy_offer: number | null;
  /** Sotto 0,50 €: non singola ma a peso, al prezzo della sua epoca. */
  buy_bulk: { era: string; eur_per_kg: number } | null;
  /** Energie sotto 0,50 €: non le compriamo. */
  buy_none: boolean;
  /** Prezzo e offerta per versione, lingua e condizione. */
  prices: Partial<Record<Versione, Partial<Record<Lingua, Partial<Record<Condizione, GuideCell>>>>>>;
}

/** L'offerta in una riga, per testi e oggetto della richiesta. */
export function testoOfferta(c: GuideCell): string | null {
  if (c.buy_offer != null) return `Ti diamo fino a ${euro(c.buy_offer)}`;
  if (c.buy_bulk) return `La compriamo a peso: ${euro(c.buy_bulk.eur_per_kg)} al kg (carte ${c.buy_bulk.era})`;
  if (c.buy_none) return "Le energie a peso non le compriamo";
  return null;
}

export interface GuideSetDetail extends GuideSet {
  cards: GuideCard[];
}

export interface GuideCardDetail extends GuideCard {
  set: GuideSet;
  updated_at: string | null;
  other_versions: GuideCard[];
}

async function leggi<T>(path: string): Promise<T | null> {
  try {
    const res = await fetch(`${API_BASE}/api/price-guide${path}`, { next: { revalidate: 3600 } });
    if (res.status === 404) return null;
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

export const getGuideSets = () => leggi<GuideSet[]>("/sets");
export const getGuideSet = (slug: string) => leggi<GuideSetDetail>(`/sets/${encodeURIComponent(slug)}`);
export const getGuideCard = (setSlug: string, slug: string) =>
  leggi<GuideCardDetail>(`/cards/${encodeURIComponent(setSlug)}/${encodeURIComponent(slug)}`);
/** Per la sitemap: niente cache di Next.js, la risposta e' grande. */
export async function getGuideSitemap(): Promise<{ sets: { slug: string; updated_at: string }[]; cards: [string, string][] } | null> {
  try {
    const res = await fetch(`${API_BASE}/api/price-guide/sitemap`, { cache: "no-store" });
    return res.ok ? await res.json() : null;
  } catch {
    return null;
  }
}

/** Dal browser: la ricerca di "Valuta la tua carta". */
export async function searchGuide(q: string): Promise<GuideCard[]> {
  const res = await fetch(`${PUBLIC_API_BASE}/api/price-guide/search?q=${encodeURIComponent(q)}`);
  if (!res.ok) throw new Error(res.status === 429 ? "Troppe ricerche: riprovi fra un minuto." : `Errore ${res.status}`);
  return res.json();
}

export function euro(v: number | null | undefined): string {
  return v == null ? "—" : `${v.toFixed(2).replace(".", ",")} €`;
}

export function anno(data: string | null): string {
  return data ? data.slice(0, 4) : "";
}

const MESI = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto",
  "settembre", "ottobre", "novembre", "dicembre"];

export function dataItaliana(iso: string | null): string {
  if (!iso) return "";
  const [a, m, g] = iso.slice(0, 10).split("-").map(Number);
  return `${g} ${MESI[m - 1]} ${a}`;
}

export function formatDataBreve(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return `${d.getDate()}/${d.getMonth() + 1}/${d.getFullYear()}`;
}
