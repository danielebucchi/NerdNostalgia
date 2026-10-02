import type {
  Article,
  ArticleListResponse,
  Inquiry,
  InquiryCreate,
  WantedItem,
  WantedListResponse,
} from "./types";

// Due URL diversi:
// - Lato browser: NEXT_PUBLIC_API_BASE_URL (es. http://localhost:7373 in dev,
//   https://api.nerdnostalgia.it in prod). Baked nel bundle al build time.
// - Lato server (SSR/RSC/route handlers): API_BASE_URL_INTERNAL, runtime env,
//   tipicamente http://backend:7373 (service name Docker network) in dev.
//   In prod (single host con Caddy esterno) puo' usare anche localhost dato che
//   Caddy gira sull'host e i container espongono porte loopback.
export const API_BASE =
  typeof window === "undefined"
    ? (process.env.API_BASE_URL_INTERNAL ??
       process.env.NEXT_PUBLIC_API_BASE_URL ??
       "http://backend:7373")
    : (process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:7373");
export const PUBLIC_API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:7373";

export interface ListArticlesParams {
  status?: string;
  category_id?: number;
  condition?: string;
  search?: string;
  min_price?: number;
  max_price?: number;
  skip?: number;
  limit?: number;
}

export async function listArticles(params: ListArticlesParams = {}): Promise<ArticleListResponse> {
  const qs = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") {
      qs.set(key, String(value));
    }
  }
  if (!qs.has("status")) qs.set("status", "PUBLISHED");
  if (!qs.has("limit")) qs.set("limit", "24");

  const res = await fetch(`${API_BASE}/api/articles/?${qs.toString()}`, {
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Errore caricamento catalogo: ${res.status}`);
  }
  return res.json();
}

/** Settings pubbliche runtime (usabile anche server-side nei RSC). */
export async function getPublicSettings(): Promise<Record<string, string>> {
  try {
    const res = await fetch(`${API_BASE}/api/settings/public`, {
      // 60s di cache: le settings cambiano di rado, niente hit per pagina
      next: { revalidate: 60 },
    });
    if (!res.ok) return {};
    return res.json();
  } catch {
    return {};
  }
}

export async function getArticle(id: number | string): Promise<Article | null> {
  const res = await fetch(`${API_BASE}/api/articles/${id}`, { cache: "no-store" });
  if (res.status === 404) return null;
  if (!res.ok) {
    throw new Error(`Errore caricamento articolo: ${res.status}`);
  }
  return res.json();
}

export async function submitInquiry(payload: InquiryCreate): Promise<Inquiry> {
  const res = await fetch(`${API_BASE}/api/inquiries/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    let detail = `${res.status}`;
    try {
      const body = await res.json();
      if (body?.detail) {
        detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
      }
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return res.json();
}

export interface ListWantedParams {
  status?: string;
  category_id?: number;
  search?: string;
  max_budget?: number;
  skip?: number;
  limit?: number;
}

export async function listWantedItems(params: ListWantedParams = {}): Promise<WantedListResponse> {
  const qs = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") {
      qs.set(key, String(value));
    }
  }
  if (!qs.has("limit")) qs.set("limit", "24");

  const res = await fetch(`${API_BASE}/api/wanted/?${qs.toString()}`, {
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Errore caricamento wanted: ${res.status}`);
  }
  return res.json();
}

export async function getWantedItem(id: number | string): Promise<WantedItem | null> {
  const res = await fetch(`${API_BASE}/api/wanted/${id}`, { cache: "no-store" });
  if (res.status === 404) return null;
  if (!res.ok) {
    throw new Error(`Errore caricamento wanted: ${res.status}`);
  }
  return res.json();
}

export function formatMaxPrice(item: Pick<WantedItem, "max_price" | "currency">): string | null {
  if (!item.max_price) return null;
  const value = Number(item.max_price);
  if (Number.isNaN(value)) return item.max_price;
  return new Intl.NumberFormat("it-IT", {
    style: "currency",
    currency: item.currency || "EUR",
    maximumFractionDigits: 2,
  }).format(value);
}

export interface OrderItemInput {
  article_id: number;
  quantity: number;
}

export interface OrderCreateInput {
  buyer_name: string;
  buyer_email: string;
  buyer_phone?: string;
  /** Locker di ritiro. Obbligatorio solo quando la mappa InPost e' attiva:
   *  senza token il sito ripiega sulla consegna a domicilio. */
  inpost_point_id?: string;
  inpost_point_name?: string;
  ship_street: string;
  ship_city: string;
  ship_postal_code: string;
  ship_province?: string;
  ship_country?: string;
  items: OrderItemInput[];
  notes?: string;
  /** Assicurazione spedizione scelta dal compratore. Omesso = default della
   *  fascia (attiva dai 50 € in su). */
  insured?: boolean;
  website?: string; // honeypot
}

export interface OrderConfirmation {
  id: number;
  buyer_name: string;
  buyer_email: string;
  subtotal: string;
  shipping_total: string;
  grand_total: string;
  currency: string;
  status: string;
  /** Serve a interrogare /status senza autenticarsi. Da conservare in locale. */
  public_token: string | null;
  items: Array<{
    id: number;
    article_id: number | null;
    title_snapshot: string;
    price_snapshot: string;
    quantity: number;
  }>;
}

export async function createOrder(payload: OrderCreateInput): Promise<OrderConfirmation> {
  const res = await fetch(`${API_BASE}/api/orders/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    let detail = `${res.status}`;
    try {
      const body = await res.json();
      if (body?.detail) {
        detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
      }
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return res.json();
}

/** Crea una Checkout Session Stripe per un ordine e ritorna l'URL a cui redirigere. */
export async function createStripeCheckout(orderId: number): Promise<string> {
  const res = await fetch(`${API_BASE}/api/orders/${orderId}/checkout`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) {
    let detail = `${res.status}`;
    try {
      const body = await res.json();
      if (body?.detail) detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  const data = await res.json();
  return data.url as string;
}

export interface OrderPublicStatus {
  id: number;
  status: string;
  paid: boolean;
  cancelled: boolean;
}

/**
 * Stato di un ordine letto dal compratore (non autenticato): serve l'id piu'
 * il token ricevuto alla creazione. Ritorna null se l'ordine non esiste o il
 * token non corrisponde — il chiamante tratta null come "non so", non come
 * "non pagato", per non buttare via il carrello per un errore di rete.
 */
export async function getOrderPublicStatus(
  orderId: number,
  token: string,
): Promise<OrderPublicStatus | null> {
  try {
    const res = await fetch(
      `${API_BASE}/api/orders/${orderId}/status?token=${encodeURIComponent(token)}`,
      { cache: "no-store" },
    );
    if (!res.ok) return null;
    return (await res.json()) as OrderPublicStatus;
  } catch {
    return null;
  }
}

export interface AddressSuggestion {
  label: string;
  street: string;
  postal_code: string;
  city: string;
  province: string;
  country: string;
  /** Coordinate del risultato: centrano la mappa dei locker. */
  lat: number | null;
  lon: number | null;
}

/**
 * Suggerimenti per il campo indirizzo. Il backend fa da proxy verso Geoapify
 * (la chiave non sta nel bundle). Lista vuota se il servizio non e'
 * configurato o non risponde: il form resta compilabile a mano.
 */
export async function fetchAddressSuggestions(
  query: string,
  signal?: AbortSignal,
): Promise<AddressSuggestion[]> {
  const q = query.trim();
  if (q.length < 3) return [];
  try {
    const res = await fetch(
      `${API_BASE}/api/address/autocomplete?q=${encodeURIComponent(q)}`,
      { signal, cache: "no-store" },
    );
    if (!res.ok) return [];
    const body = await res.json();
    return (body?.suggestions ?? []) as AddressSuggestion[];
  } catch {
    return [];
  }
}

export interface PaypalConfig {
  configured: boolean;
  client_id: string;
  sandbox: boolean;
  webhook_ready: boolean;
}

/** Config pubblica per caricare l'SDK PayPal (il client id e' pubblico). */
export async function getPaypalConfig(): Promise<PaypalConfig | null> {
  try {
    const res = await fetch(`${API_BASE}/api/paypal/config`, { cache: "no-store" });
    if (!res.ok) return null;
    return (await res.json()) as PaypalConfig;
  } catch {
    return null;
  }
}

async function postOrThrow(url: string): Promise<Record<string, unknown>> {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) {
    let detail = `${res.status}`;
    try {
      const body = await res.json();
      if (body?.detail) {
        detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
      }
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return res.json();
}

/** Crea l'ordine su PayPal per un nostro ordine PENDING. Ritorna l'id PayPal. */
export async function createPaypalOrder(orderId: number): Promise<string> {
  const data = await postOrThrow(`${API_BASE}/api/paypal/orders/${orderId}`);
  return data.id as string;
}

/** Incassa dopo l'approvazione nel popup: il backend porta l'ordine a PAGATO. */
export async function capturePaypalOrder(orderId: number): Promise<void> {
  await postOrThrow(`${API_BASE}/api/paypal/orders/${orderId}/capture`);
}

export interface InpostConfig {
  configured: boolean;
  token: string;
  script_url: string;
  style_url: string;
  widget_config: string;
  language: string;
}

/** Config della mappa locker. Il token e' pubblico ma legato al dominio. */
export async function getInpostConfig(): Promise<InpostConfig | null> {
  try {
    const res = await fetch(`${API_BASE}/api/inpost/config`, { cache: "no-store" });
    if (!res.ok) return null;
    return (await res.json()) as InpostConfig;
  } catch {
    return null;
  }
}

export function formatPrice(article: Pick<Article, "price" | "currency">): string {
  const value = Number(article.price);
  if (Number.isNaN(value)) return article.price;
  const currency = article.currency || "EUR";
  return new Intl.NumberFormat("it-IT", {
    style: "currency",
    currency,
    maximumFractionDigits: 2,
  }).format(value);
}
