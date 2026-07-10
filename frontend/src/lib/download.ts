/**
 * Utility download/condivisione file lato client.
 * Il download via <a download> non funziona cross-origin (api.* vs sito):
 * si passa sempre da fetch → blob → object URL.
 */

export function saveBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  // revoca dopo il click, con margine per Safari
  setTimeout(() => URL.revokeObjectURL(url), 4000);
}

/** Scarica una risorsa pubblica (es. /static/...) come file. */
export async function downloadUrl(url: string, filename: string): Promise<void> {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Download fallito (${res.status})`);
  saveBlob(await res.blob(), filename);
}

/**
 * Condivide un'immagine via share sheet di sistema (mobile): da li' si puo'
 * salvare in galleria o mandarla dritta a Vinted/WhatsApp. Ritorna false se
 * il browser non supporta la condivisione di file.
 */
export async function shareImageUrl(url: string, filename: string): Promise<boolean> {
  if (typeof navigator === "undefined" || !navigator.canShare) return false;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Download fallito (${res.status})`);
  const blob = await res.blob();
  const file = new File([blob], filename, { type: blob.type || "image/webp" });
  if (!navigator.canShare({ files: [file] })) return false;
  try {
    await navigator.share({ files: [file] });
  } catch {
    // utente ha annullato lo share sheet: non e' un errore
  }
  return true;
}

/**
 * Porta TUTTE le foto sul dispositivo in un colpo:
 * - mobile: share sheet con tutti i file insieme → "Salva in Galleria"/
 *   Google Foto (o direttamente Vinted/WhatsApp)
 * - fallback desktop/browser senza share: un download per file
 *   (niente zip: sul telefono non ci si fa nulla)
 */
export async function shareOrDownloadAll(
  urls: string[],
  baseName: string,
): Promise<void> {
  const files: File[] = [];
  for (let i = 0; i < urls.length; i++) {
    const res = await fetch(urls[i]);
    if (!res.ok) throw new Error(`Download foto ${i + 1} fallito (${res.status})`);
    const blob = await res.blob();
    const ext = blob.type === "image/jpeg" ? "jpg" : "webp";
    files.push(
      new File([blob], `${baseName}-${String(i + 1).padStart(2, "0")}.${ext}`, {
        type: blob.type || "image/webp",
      }),
    );
  }
  if (
    typeof navigator !== "undefined" &&
    navigator.canShare &&
    navigator.canShare({ files })
  ) {
    try {
      await navigator.share({ files });
    } catch {
      // annullato dall'utente
    }
    return;
  }
  for (const f of files) {
    saveBlob(f, f.name);
    // pausa breve: alcuni browser bloccano i download a raffica
    await new Promise((r) => setTimeout(r, 300));
  }
}
