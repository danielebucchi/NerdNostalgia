import { describe, it, expect, vi, afterEach } from "vitest";

import { listAllArticles } from "@/lib/api";

afterEach(() => vi.unstubAllGlobals());

/** Finto backend con `total` articoli, pagine da `limit` come quello vero. */
function mockCatalog(total: number, shifted = false) {
  const fetchMock = vi.fn(async (url: string) => {
    const qs = new URL(url).searchParams;
    const skip = Number(qs.get("skip"));
    const limit = Number(qs.get("limit"));
    // shifted: un articolo nuovo spinge tutto avanti di uno tra una pagina e l'altra
    const start = shifted && skip > 0 ? skip - 1 : skip;
    const items = Array.from({ length: Math.max(0, Math.min(limit, total - start)) }, (_, i) => ({
      id: start + i + 1,
      title: `art ${start + i + 1}`,
    }));
    return new Response(JSON.stringify({ items, total, skip, limit }), { status: 200 });
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

describe("listAllArticles", () => {
  it("prende tutte le pagine, non solo le prime 100", async () => {
    const fetchMock = mockCatalog(321);
    const all = await listAllArticles({ status: "PUBLISHED" });
    expect(all).toHaveLength(321);
    expect(fetchMock).toHaveBeenCalledTimes(4);
  });

  it("con meno di 100 articoli basta una chiamata", async () => {
    const fetchMock = mockCatalog(42);
    expect(await listAllArticles()).toHaveLength(42);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("non duplica un articolo finito su due pagine", async () => {
    mockCatalog(150, true);
    const all = await listAllArticles();
    expect(new Set(all.map((a) => a.id)).size).toBe(all.length);
  });
});
