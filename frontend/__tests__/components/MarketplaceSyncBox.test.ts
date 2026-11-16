import { describe, it, expect } from "vitest";

import { withoutOffEbayContacts } from "@/components/admin/MarketplaceSyncBox";

describe("withoutOffEbayContacts", () => {
  it("toglie link, email, telefono e altri canali", () => {
    const text = [
      "Carta in ottime condizioni",
      "Altri pezzi su www.nerdnostalgia.store",
      "Scrivimi a pippo@gmail.com",
      "WhatsApp 333 123 4567",
      "Trovi altro sul mio Vinted",
      "Spedizione Veloce",
    ].join("\n");
    expect(withoutOffEbayContacts(text)).toBe("Carta in ottime condizioni\nSpedizione Veloce");
  });

  it("lascia stare numeri di carta e date", () => {
    const text = "Numero 025/198\nUscita 12/03/2004";
    expect(withoutOffEbayContacts(text)).toBe(text);
  });
});
