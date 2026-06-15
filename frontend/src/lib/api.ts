import type { Article, ArticleListResponse } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:7373";

export interface ListArticlesParams {
  status?: string;
  category?: string;
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

export async function getArticle(id: number | string): Promise<Article | null> {
  const res = await fetch(`${API_BASE}/api/articles/${id}`, { cache: "no-store" });
  if (res.status === 404) return null;
  if (!res.ok) {
    throw new Error(`Errore caricamento articolo: ${res.status}`);
  }
  return res.json();
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
