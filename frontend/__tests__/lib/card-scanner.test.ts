import { describe, it, expect } from "vitest";

import { descriviGruppo } from "@/lib/card-scanner";

describe("descriviGruppo", () => {
  it("titolo, carte, set e data: si capisce quale inserzione e'", () => {
    const testo = descriviGruppo({
      group_key: "NN-GRP-1", listing_id: "800", count: 12, sold: 2,
      title: "Carte Pokémon singole - scegli la tua carta",
      sets: ["30° Anniversario", "Scintille Folgoranti", "Set Base"],
      updated_at: "2026-11-19T10:00:00",
    });
    expect(testo).toBe(
      "Carte Pokémon singole - scegli la tua carta · 12 carte (+2 vendute) · 30° Anniversario, Scintille Folgoranti +1 · agg. 19 nov",
    );
  });

  it("senza titolo (eBay non risponde) usa i set", () => {
    expect(descriviGruppo({ group_key: "K", listing_id: "800", count: 3, sets: ["Set Base"] }))
      .toBe("Inserzione Set Base · 3 carte");
  });
});
