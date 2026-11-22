import { describe, it, expect } from "vitest";

import { descriviGruppo, doppioniInCoda } from "@/lib/card-scanner";

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

describe("doppioniInCoda", () => {
  it("tiene la prima di ogni carta e scarta le altre", () => {
    const coda = [{ id: 1 }, { id: 2 }, { id: 3 }, { id: 4 }];
    const chiavi = { 1: "10||", 2: "10||", 3: "11||", 4: "10||" };
    expect(doppioniInCoda(coda, chiavi).map((s) => s.id)).toEqual([2, 4]);
  });

  it("1ª edizione e reverse sono carte diverse, non doppioni", () => {
    const coda = [{ id: 1 }, { id: 2 }, { id: 3 }];
    const chiavi = { 1: "66||", 2: "66||1", 3: "66|r|" };
    expect(doppioniInCoda(coda, chiavi)).toEqual([]);
  });

  it("gli scan senza carta scelta non sono mai doppioni", () => {
    const coda = [{ id: 1 }, { id: 2 }];
    expect(doppioniInCoda(coda, { 1: null })).toEqual([]);
  });
});
