/**
 * URL canonico del sito, usato per:
 *  - sitemap.xml
 *  - canonical link nelle pagine
 *  - Open Graph (og:url, og:image absolute)
 *  - JSON-LD
 *
 * In produzione settare NEXT_PUBLIC_SITE_URL=https://nerdnostalgia.it
 */
export const SITE_URL = (
  process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3737"
).replace(/\/$/, "");

export const SITE_NAME = "NerdNostalgia";
export const SITE_TAGLINE = "Compro e vendo videogiochi, carte Pokémon e nerderie";
export const SITE_DESCRIPTION =
  "Catalogo curato di videogiochi vintage, carte Pokémon, Funko Pop e gadget retro. " +
  "Compro, vendo e scambio nerderie in tutta Italia.";

export function absUrl(path: string): string {
  if (!path) return SITE_URL;
  if (path.startsWith("http")) return path;
  const slash = path.startsWith("/") ? "" : "/";
  return `${SITE_URL}${slash}${path}`;
}

/** Trunca una descrizione a N caratteri rispettando le parole. */
export function clip(text: string | null | undefined, max = 160): string {
  if (!text) return "";
  const clean = text.replace(/\s+/g, " ").trim();
  if (clean.length <= max) return clean;
  return clean.slice(0, max - 1).replace(/\s\S*$/, "") + "…";
}
