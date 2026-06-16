/**
 * Helper per le immagini articoli. Il backend salva `<uid>.webp` come
 * versione grande e `<uid>.thumb.webp` come versione card (~600px).
 * Per immagini caricate prima dell'introduzione dei thumb (o URL esterni)
 * ritorna l'URL invariato.
 */
export function thumbUrlFor(url: string): string {
  if (!url) return url;
  if (url.endsWith(".thumb.webp")) return url;
  if (url.endsWith(".webp")) return url.slice(0, -".webp".length) + ".thumb.webp";
  return url;
}

export function thumbUrlsFor(urls: string[] | null | undefined): string[] {
  return (urls ?? []).map(thumbUrlFor);
}
