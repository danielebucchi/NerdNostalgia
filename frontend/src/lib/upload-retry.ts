import { ApiError, adminApi } from "@/lib/admin-api";

/**
 * postForm con retry esponenziale: pensato per gli upload foto da mobile
 * su rete ballerina (mercatini). Ritenta SOLO su errori di rete/5xx:
 * un 4xx (file invalido, troppo grande, auth) fallirebbe uguale.
 */
export async function uploadWithRetry<T>(
  path: string,
  formData: FormData,
  attempts = 3,
): Promise<T> {
  let lastErr: unknown;
  for (let i = 0; i < attempts; i++) {
    try {
      return await adminApi.postForm<T>(path, formData);
    } catch (err) {
      lastErr = err;
      if (err instanceof ApiError && err.status >= 400 && err.status < 500) {
        throw err;
      }
      if (i < attempts - 1) {
        await new Promise((r) => setTimeout(r, 1000 * 2 ** i)); // 1s, 2s
      }
    }
  }
  throw lastErr;
}
