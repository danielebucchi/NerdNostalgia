import { adminApi } from "@/lib/admin-api";
import type { PersonalCard } from "@/lib/types";

/* Scanner carte: tipi e chiamate.
 *
 * Gli scan si mandano uno alla volta: l'OCR costa qualche secondo a
 * carta, e una richiesta per scan fa vedere l'avanzamento vero invece di
 * uno spinner fermo per minuti. */

export interface Candidato {
  blueprint_id: number;
  name: string;
  version?: string | null;
  number?: string | null;
  expansion_id: number;
  expansion_code?: string | null;
  expansion_name?: string | null;
  image_url?: string | null;
  score?: number;
  number_match?: boolean;
  image_similarity?: number | null;
  variant_of_top?: boolean;
  /** Somiglianza con un tuo scan gia' confermato di questa carta */
  seen_before?: number | null;
}

/** Una misura dello scan: value null = "non so" (zona grigia). */
export interface Misura {
  value: boolean | null;
  score?: number;
  reason?: string;
  /** true = soglia tarata sulle tue conferme */
  calibrated?: boolean;
}

export interface Analisi {
  blueprint_id?: number;
  supports?: { reverse: boolean; first_edition: boolean };
  reverse?: Misura;
  first_edition?: Misura;
  condition?: {
    value: string | null;
    centering?: { lr?: number; tb?: number };
    wear_front?: number | null;
    wear_back?: number | null;
    reason?: string;
  };
  error?: string;
}

export interface Lettura {
  number?: string | null;
  total?: string | null;
  set_code?: string | null;
  set_codes?: string[];
  language?: string | null;
  printed_code?: string | null;
  name_text?: string;
  notes?: string[];
}

export interface Scan {
  id: number;
  image_url: string;
  original_filename?: string | null;
  game_id?: number | null;
  expansion_id?: number | null;
  status: "PENDING" | "CONFIRMED" | "DISCARDED";
  ocr: Lettura;
  candidates: Candidato[];
  confidence?: "alta" | "media" | "bassa" | null;
  note?: string | null;
  back_image_url?: string | null;
  features: Analisi;
  error?: string | null;
  personal_card_id?: number | null;
}

export interface StatoIndice {
  game_id: number;
  blueprints: number;
  expansions: number;
  updated_at: string | null;
  build?: { running: boolean; done: number; total: number; errors: number; error?: string };
}

export interface StatoScanner {
  ocr: boolean;
  cardtrader: boolean;
  ebay_sold: boolean;
  ebay_publish: boolean;
  ebay_env: string;
  default_game_id: number | null;
  default_language: string | null;
  index: StatoIndice[];
  pending_scans: number;
  session: { game_id: number | null; expansion_id: number | null };
  learning?: {
    references: number;
    corrections: number;
    examples: { foil?: Record<string, number>; timbro?: number; usura?: number };
    calibrated: { reverse: string[]; first_edition: boolean; condition: boolean };
  };
}

export interface Valutazione {
  card: PersonalCard;
  warnings: Record<string, string>;
  ebay_sold_url: string;
}

export const GIOCHI = [
  { id: 5, label: "Pokémon" },
  { id: 1, label: "Magic" },
  { id: 4, label: "Yu-Gi-Oh!" },
  { id: 15, label: "One Piece" },
];

const B = "/api/card-scanner";

export const stato = () => adminApi.get<StatoScanner>(`${B}/status`);

/** Gioco ed espansione valgono anche per gli scan dalla cartella osservata. */
export const salvaSessione = (game_id: number, expansion_id: number | null) =>
  adminApi.put<unknown>(`${B}/session`, { game_id, expansion_id });

export const costruisciIndice = (game_id: number, full = false) =>
  adminApi.post<{ started: boolean; detail?: string | null }>(`${B}/index/build`, { game_id, full });

/** Lo scanner salva TIFF/PNG enormi: si riducono nel browser prima di
 * mandarli. 2400px di lato lungo bastano e avanzano per leggere il numero. */
export async function riduci(file: File, lato = 2400): Promise<Blob> {
  const bmp = await createImageBitmap(file);
  const k = Math.min(1, lato / Math.max(bmp.width, bmp.height));
  const canvas = document.createElement("canvas");
  canvas.width = Math.round(bmp.width * k);
  canvas.height = Math.round(bmp.height * k);
  canvas.getContext("2d")!.drawImage(bmp, 0, 0, canvas.width, canvas.height);
  bmp.close();
  return new Promise((ok, ko) =>
    canvas.toBlob((b) => (b ? ok(b) : ko(new Error("Conversione fallita"))), "image/jpeg", 0.92),
  );
}

export async function caricaScan(
  file: File,
  gameId: number,
  expansionId?: number | null,
  language?: string | null,
): Promise<Scan> {
  const fd = new FormData();
  const nome = file.name.replace(/\.[^.]+$/, "") + ".jpg";
  fd.append("file", new File([await riduci(file)], nome, { type: "image/jpeg" }));
  fd.append("game_id", String(gameId));
  if (expansionId) fd.append("expansion_id", String(expansionId));
  if (language) fd.append("language", language);
  return adminApi.postForm<Scan>(`${B}/scans`, fd);
}

export async function caricaRetro(scanId: number, file: File): Promise<Scan> {
  const fd = new FormData();
  fd.append("file", new File([await riduci(file)], file.name.replace(/\.[^.]+$/, "") + ".jpg", { type: "image/jpeg" }));
  return adminApi.postForm<Scan>(`${B}/scans/${scanId}/back`, fd);
}

/** "carta12_retro.jpg" → "carta12": il retro va con il fronte di nome
 * uguale. null se il file non e' un retro. */
export function nomeDelFronte(nome: string): string | null {
  const base = nome.replace(/\.[^.]+$/, "");
  const m = base.match(/^(.*?)[\s_-]*(retro|back)$/i);
  return m ? m[1] : null;
}

export const analizza = (scanId: number, blueprint_id: number) =>
  adminApi.post<Scan>(`${B}/scans/${scanId}/features`, { blueprint_id });

export const scanInAttesa = () => adminApi.get<Scan[]>(`${B}/scans?status=PENDING`);

export const ricerca = (
  scanId: number,
  correzioni: { expansion_id?: number | null; number?: string | null; name?: string | null },
) => adminApi.post<Scan>(`${B}/scans/${scanId}/rematch`, correzioni);

export const conferma = (
  scanId: number,
  // condition/reverse/first_edition assenti = quelli dell'analisi
  dati: {
    blueprint_id: number;
    condition?: string | null;
    language?: string | null;
    quantity: number;
    reverse?: boolean | null;
    first_edition?: boolean | null;
    price_now: boolean;
  },
) => adminApi.post<PersonalCard>(`${B}/scans/${scanId}/confirm`, dati);

export const scarta = (scanId: number) => adminApi.delete<void>(`${B}/scans/${scanId}`);

export const cercaNellIndice = (gameId: number, q: string, expansionId?: number | null) => {
  const qs = new URLSearchParams({ game_id: String(gameId), q });
  if (expansionId) qs.set("expansion_id", String(expansionId));
  return adminApi.get<Candidato[]>(`${B}/blueprints/search?${qs}`);
};

export const collezione = (search?: string) => {
  const qs = new URLSearchParams();
  if (search?.trim()) qs.set("search", search.trim());
  return adminApi.get<PersonalCard[]>(`${B}/cards?${qs}`);
};

export const eliminaCarta = (cardId: number) => adminApi.delete<void>(`${B}/cards/${cardId}`);

export const valuta = (cardId: number) => adminApi.post<Valutazione>(`${B}/cards/${cardId}/price`);

export const vendutiAMano = (cardId: number, prices: string) =>
  adminApi.post<Valutazione>(`${B}/cards/${cardId}/ebay-sold`, { prices });

export const urlVendutiEbay = (cardId: number) =>
  adminApi.get<{ url: string }>(`${B}/cards/${cardId}/ebay-sold-url`);

export const aggiornaCarta = (cardId: number, patch: Partial<PersonalCard>) =>
  adminApi.patch<PersonalCard>(`/api/personal-cards/${cardId}`, patch);

export const pubblicaCardTrader = (cardId: number) =>
  adminApi.post<{ product_id: number; price_eur: number }>(`${B}/cards/${cardId}/cardtrader`);
export const ritiraCardTrader = (cardId: number) => adminApi.delete<{ ok: boolean }>(`${B}/cards/${cardId}/cardtrader`);

export interface Canali {
  site: boolean;
  cardtrader: boolean;
  ebay: boolean;
}

/** In vendita su piu' canali insieme: un esito per canale. */
export const pubblicaOvunque = (cardId: number, canali: Canali) =>
  adminApi.post<Partial<Record<keyof Canali, { ok: boolean; detail?: string | null }>>>(
    `${B}/cards/${cardId}/publish`, canali);

export const pubblicaSito = (cardId: number) =>
  adminApi.post<{ article_id: number; price_eur: number }>(`${B}/cards/${cardId}/site`);
export const ritiraSito = (cardId: number) => adminApi.delete<{ ok: boolean }>(`${B}/cards/${cardId}/site`);

export const pubblicaEbay = (cardId: number) =>
  adminApi.post<{ listing_id: string; url: string | null; price_eur: number }>(`${B}/cards/${cardId}/ebay`);
export const ritiraEbay = (cardId: number) => adminApi.delete<{ ok: boolean }>(`${B}/cards/${cardId}/ebay`);

/** Inserzione eBay con varianti: piu' carte, una pagina, il menu "Carta". */
export interface GruppoEbay {
  group_key: string;
  listing_id: string | null;
  /** Carte ancora in vendita nell'inserzione (le vendute sono in `sold`). */
  count: number;
  /** Titolo su eBay; null se eBay non ha risposto. */
  title?: string | null;
  url?: string | null;
  sold?: number;
  /** Set delle carte in vendita (in italiano dove si conosce). */
  sets?: string[];
  updated_at?: string | null;
}

/** Come si legge l'inserzione nel menu: titolo, set, carte, data. */
export function descriviGruppo(g: GruppoEbay): string {
  const set = g.sets?.length
    ? g.sets.slice(0, 2).join(", ") + (g.sets.length > 2 ? ` +${g.sets.length - 2}` : "")
    : null;
  const quando = g.updated_at ? new Date(g.updated_at).toLocaleDateString("it-IT", { day: "numeric", month: "short" }) : null;
  return [
    g.title || (set ? `Inserzione ${set}` : `Inserzione ${g.listing_id ?? g.group_key}`),
    `${g.count} carte${g.sold ? ` (+${g.sold} vendute)` : ""}`,
    g.title && set ? set : null,
    quando && `agg. ${quando}`,
  ].filter(Boolean).join(" · ");
}

/** Vendite su CardTrader/eBay subito (il server lo fa da solo ogni 15 minuti). */
export interface EsitoVendite {
  vendute: { card_id: number; nome: string; piattaforma: string; prezzo: number | null; da_ritirare_a_mano: string[] }[];
  errori: Record<string, string>;
}
export const controllaVendite = () => adminApi.post<EsitoVendite>(`${B}/sync-sales`);

export const gruppiEbay = () => adminApi.get<GruppoEbay[]>(`${B}/ebay-groups`);

/** Le carte in un'unica inserzione con varianti; con groupKey si aggiungono
 *  a una gia' pubblicata. */
export const pubblicaGruppoEbay = (cardIds: number[], title: string, groupKey?: string) =>
  adminApi.post<GruppoEbay & { url: string | null }>(`${B}/ebay-group`, {
    card_ids: cardIds,
    title: title || null,
    group_key: groupKey || null,
  });

/** ZIP per il PC Windows dello scanner: Installa.cmd e lo script. */
export async function scaricaKitWindows(): Promise<void> {
  const blob = await adminApi.getBlob(`${B}/windows-kit`);
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "NerdNostalgia-Scanner-Windows.zip";
  a.click();
  URL.revokeObjectURL(a.href);
}

export async function scaricaCsv(): Promise<void> {
  const blob = await adminApi.getBlob(`${B}/cards/export.csv`);
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `collezione-carte-${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
  URL.revokeObjectURL(a.href);
}

/** Esegue `fn` su ogni elemento in fila, riportando l'avanzamento. Ogni
 * elemento va per conto suo: uno che fallisce non ferma gli altri. */
export async function inFila<T, R>(
  elementi: T[],
  fn: (x: T) => Promise<R>,
  onProgresso: (fatti: number, errori: { item: T; error: string }[]) => void,
): Promise<{ ok: R[]; errori: { item: T; error: string }[] }> {
  const ok: R[] = [];
  const errori: { item: T; error: string }[] = [];
  for (let i = 0; i < elementi.length; i++) {
    try {
      ok.push(await fn(elementi[i]));
    } catch (e) {
      errori.push({ item: elementi[i], error: e instanceof Error ? e.message : String(e) });
    }
    onProgresso(i + 1, [...errori]);
  }
  return { ok, errori };
}
