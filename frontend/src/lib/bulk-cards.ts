import { adminApi } from "@/lib/admin-api";

/* Caricamento massivo di carte: tipi e chiamate.
 *
 * Il backend accetta al massimo MAX_RIGHE per richiesta perché ogni riga
 * costa due chiamate a CardTrader (prezzo + inserzione). Qui si manda a
 * pezzi, così l'avanzamento si vede davvero invece di restare fermo su
 * uno spinner per minuti. */

export const RIGHE_PER_LOTTO = 10;

export interface Blueprint {
  id: number;
  name?: string;
  collector_number?: string;
  expansion_id?: number;
}

export interface RigaCarico {
  blueprint_id: number;
  name?: string | null;
  number?: string | null;
  collection?: string | null;
  quantity: number;
  condition: string;
  language?: string | null;
  reverse: boolean;
  first_edition: boolean;
}

export interface EsitoRiga {
  index: number;
  ok: boolean;
  article_id?: number | null;
  product_id?: number | null;
  price_eur?: number | null;
  price_position?: number | null;
  price_total_offers?: number | null;
  error?: string | null;
}

export interface RigaCsv {
  index: number;
  name?: string | null;
  number?: string | null;
  collection?: string | null;
  quantity: number;
  condition: string;
  language?: string | null;
  reverse: boolean;
  first_edition: boolean;
  candidates: Blueprint[];
  error?: string | null;
}

export function cercaBlueprint(
  expansionId: number,
  search: string,
): Promise<Blueprint[]> {
  const qs = new URLSearchParams({ expansion_id: String(expansionId) });
  if (search.trim()) qs.set("search", search.trim());
  return adminApi.get<Blueprint[]>(`/api/cardtrader/blueprints?${qs}`);
}

export function leggiCsv(input: {
  csv_text: string;
  expansion_id?: number | null;
}): Promise<RigaCsv[]> {
  return adminApi.post<RigaCsv[]>("/api/cards/bulk/parse-csv", input);
}

/** Pubblica a lotti, riportando l'avanzamento dopo ognuno. */
export async function pubblica(
  righe: RigaCarico[],
  pricePosition: number,
  onProgresso: (fatte: number, esiti: EsitoRiga[]) => void,
): Promise<EsitoRiga[]> {
  const tutti: EsitoRiga[] = [];
  for (let i = 0; i < righe.length; i += RIGHE_PER_LOTTO) {
    const lotto = righe.slice(i, i + RIGHE_PER_LOTTO);
    const esiti = await adminApi.post<EsitoRiga[]>("/api/cards/bulk/publish", {
      price_position: pricePosition,
      rows: lotto,
    });
    // Gli indici tornano relativi al lotto: li riporto sulla lista intera,
    // se no la seconda decina sovrascriverebbe la prima in tabella.
    esiti.forEach((e) => tutti.push({ ...e, index: e.index + i }));
    onProgresso(Math.min(i + RIGHE_PER_LOTTO, righe.length), [...tutti]);
  }
  return tutti;
}
