import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

const getCatalog = vi.fn();
vi.mock("@/lib/api", async (orig) => ({
  ...(await orig<typeof import("@/lib/api")>()),
  getCatalog: (...a: unknown[]) => getCatalog(...a),
}));
vi.mock("@/components/ArticleCard", () => ({
  ArticleCard: ({ article }: { article: { title: string } }) => <div>{article.title}</div>,
}));

import { CatalogSection } from "@/components/CatalogSection";

const facets = {
  categories: { carte: { name: "Carte", count: 30 } }, total_all_categories: 30,
  subcategories: {}, total_all_subcategories: 0,
  conditions: { USED: 30 }, total_all_conditions: 30,
  brands: {}, total_all_brands: 30, price_min: 1, price_max: 40,
};
const pagina = (da: number, n: number) =>
  Array.from({ length: n }, (_, i) => ({ id: da + i, title: `Carta ${da + i}` }));

describe("CatalogSection", () => {
  beforeEach(() => getCatalog.mockReset());

  it("mostra la prima pagina del server e chiede la successiva", async () => {
    getCatalog.mockResolvedValue({ items: pagina(24, 6), total: 30, facets });
    render(<CatalogSection initial={{ items: pagina(0, 24), total: 30, facets } as never} />);
    expect(screen.getByText("Carta 0")).toBeInTheDocument();
    expect(getCatalog).not.toHaveBeenCalled(); // la prima pagina c'e' gia'

    await userEvent.click(screen.getByRole("button", { name: /Mostra altri \(6\)/ }));
    expect(getCatalog.mock.calls[0][0]).toMatchObject({ skip: 24, limit: 24 });
    expect(await screen.findByText("Carta 29")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Mostra altri/ })).not.toBeInTheDocument();
  });
});
