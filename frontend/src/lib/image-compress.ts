/**
 * Compressione immagini client-side prima dell'upload.
 *
 * Perche': le foto scattate dalla fotocamera del telefono superano spesso
 * il limite backend di 5MB, e su iPhone escono in HEIC che il backend non
 * accetta. Ricodificare in JPEG (max 1600px, quality 0.85) risolve entrambi
 * i problemi e fa pure risparmiare banda in upload.
 *
 * I file gia' piccoli e in formato accettato passano invariati; le GIF non
 * vengono mai toccate (la ricodifica ucciderebbe l'animazione).
 */

const PASSTHROUGH_TYPES = ["image/jpeg", "image/png", "image/webp"];
const PASSTHROUGH_MAX_BYTES = 3 * 1024 * 1024; // sotto i 3MB non tocco nulla
const MAX_DIMENSION = 1600; // allineato a LARGE_MAX_WIDTH del backend
const JPEG_QUALITY = 0.85;

async function decode(file: File): Promise<ImageBitmap | HTMLImageElement> {
  // createImageBitmap: via veloce, rispetta l'orientamento EXIF.
  try {
    return await createImageBitmap(file);
  } catch {
    // Fallback <img>: copre i formati che il browser sa mostrare ma non
    // bitmap-are (es. HEIC su Safari iOS).
    return await new Promise<HTMLImageElement>((resolve, reject) => {
      const url = URL.createObjectURL(file);
      const img = new Image();
      img.onload = () => {
        URL.revokeObjectURL(url);
        resolve(img);
      };
      img.onerror = () => {
        URL.revokeObjectURL(url);
        reject(new Error("Immagine non decodificabile dal browser"));
      };
      img.src = url;
    });
  }
}

export async function compressImage(file: File): Promise<File> {
  if (file.type === "image/gif") return file;
  if (PASSTHROUGH_TYPES.includes(file.type) && file.size <= PASSTHROUGH_MAX_BYTES) {
    return file;
  }

  let source: ImageBitmap | HTMLImageElement;
  try {
    source = await decode(file);
  } catch {
    return file; // non riesco a decodificarla: tento l'upload dell'originale
  }

  const w = "naturalWidth" in source ? source.naturalWidth : source.width;
  const h = "naturalHeight" in source ? source.naturalHeight : source.height;
  const scale = Math.min(1, MAX_DIMENSION / Math.max(w, h));

  const canvas = document.createElement("canvas");
  canvas.width = Math.max(1, Math.round(w * scale));
  canvas.height = Math.max(1, Math.round(h * scale));
  const ctx = canvas.getContext("2d");
  if (!ctx) return file;
  ctx.drawImage(source, 0, 0, canvas.width, canvas.height);
  if ("close" in source) source.close();

  const blob = await new Promise<Blob | null>((resolve) =>
    canvas.toBlob(resolve, "image/jpeg", JPEG_QUALITY),
  );
  if (!blob) return file;

  const name = file.name.replace(/\.\w+$/, "") || "foto";
  return new File([blob], `${name}.jpg`, { type: "image/jpeg" });
}
