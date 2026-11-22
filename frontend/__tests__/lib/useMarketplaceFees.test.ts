import { describe, it, expect } from "vitest";

import { feeLabel, getFeesFor, priceCoveringFee } from "@/lib/useMarketplaceFees";

const commissioneCarte = { id: 1, marketplace: "ebay", category_id: 7, markup_percent: "6.5", fixed_fee: "0.35" };

describe("prezzo che copre la commissione", () => {
  it("carta da 3 euro con 6,5% + 0,35: 3,59 copre la commissione, su eBay all'euro sopra: 4", () => {
    const [f] = getFeesFor([commissioneCarte] as never, "ebay", 7);
    expect(priceCoveringFee("3.00", f, "ebay")).toBe("4.00");
    expect(priceCoveringFee("3.00", f, "vinted")).toBe("3.59");
    expect(feeLabel(f)).toBe("+6.5% +0,35 €");
  });

  it("su eBay mai sotto 1 euro, sugli altri si", () => {
    const f = { percent: 6.5, fixed: 0.35 };
    expect(priceCoveringFee("0.13", f, "ebay")).toBe("1.00");
    expect(priceCoveringFee("0.13", f, "vinted")).toBe("0.52");
  });

  it("dalla categoria padre se la sottocategoria non ne ha", () => {
    expect(getFeesFor([commissioneCarte] as never, "ebay", 99, 7)).toEqual([{ percent: 6.5, fixed: 0.35 }]);
  });
});
