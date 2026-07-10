import { PUBLIC_API_BASE } from "@/lib/api";
import { clearToken, getToken } from "@/lib/auth-store";

const BASE = PUBLIC_API_BASE;

export class ApiError extends Error {
  status: number;
  detail: unknown;
  constructor(status: number, detail: unknown, message?: string) {
    super(message ?? (typeof detail === "string" ? detail : `HTTP ${status}`));
    this.status = status;
    this.detail = detail;
  }
}

async function request<T>(
  method: string,
  path: string,
  options: {
    json?: unknown;
    formData?: FormData;
    formUrlEncoded?: Record<string, string>;
    auth?: boolean;
  } = {},
): Promise<T> {
  const headers: Record<string, string> = {};
  let body: BodyInit | undefined;

  if (options.json !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(options.json);
  } else if (options.formData) {
    body = options.formData;
  } else if (options.formUrlEncoded) {
    headers["Content-Type"] = "application/x-www-form-urlencoded";
    body = new URLSearchParams(options.formUrlEncoded).toString();
  }

  if (options.auth !== false) {
    const token = getToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${BASE}${path}`, { method, headers, body });

  if (res.status === 401 && options.auth !== false) {
    clearToken();
    if (typeof window !== "undefined" && !window.location.pathname.startsWith("/admin/login")) {
      window.location.href = "/admin/login";
    }
  }

  if (res.status === 204) return undefined as T;

  const text = await res.text();
  let parsed: unknown = null;
  if (text) {
    try {
      parsed = JSON.parse(text);
    } catch {
      parsed = text;
    }
  }

  if (!res.ok) {
    const detail =
      parsed && typeof parsed === "object" && "detail" in (parsed as object)
        ? (parsed as { detail: unknown }).detail
        : parsed;
    const message =
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail.map((d) => (typeof d === "object" && d ? (d as { msg?: string }).msg ?? JSON.stringify(d) : String(d))).join("; ")
          : `HTTP ${res.status}`;
    throw new ApiError(res.status, detail, message);
  }

  return parsed as T;
}

/** GET autenticata che ritorna il body binario (zip, immagini…). */
async function requestBlob(path: string): Promise<Blob> {
  const headers: Record<string, string> = {};
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(`${BASE}${path}`, { headers });
  if (!res.ok) {
    throw new ApiError(res.status, null, `HTTP ${res.status}`);
  }
  return res.blob();
}

export const adminApi = {
  get: <T>(path: string) => request<T>("GET", path),
  getBlob: (path: string) => requestBlob(path),
  post: <T>(path: string, json?: unknown) => request<T>("POST", path, { json }),
  postForm: <T>(path: string, formData: FormData) => request<T>("POST", path, { formData }),
  postLogin: <T>(path: string, data: Record<string, string>) =>
    request<T>("POST", path, { formUrlEncoded: data, auth: false }),
  patch: <T>(path: string, json: unknown) => request<T>("PATCH", path, { json }),
  put: <T>(path: string, json: unknown) => request<T>("PUT", path, { json }),
  delete: <T>(path: string) => request<T>("DELETE", path),
};
