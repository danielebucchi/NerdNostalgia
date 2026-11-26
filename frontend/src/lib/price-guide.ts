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

export interface GuideAvailable {
  id: number;
  title: string;
  price: number;
  image: string | null;
}

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
export const getGuideSitemap = () =>
  leggi<{ sets: { slug: string; updated_at: string }[]; cards: { set_slug: string; slug: string; updated_at: string }[] }>(
    "/sitemap",
  );

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
