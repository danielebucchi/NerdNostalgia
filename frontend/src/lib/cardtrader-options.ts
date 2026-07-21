// Valori CardTrader per gli attributi carta (Pokémon). Coincidono con le
// editable_properties dell'API: condition + pokemon_language.
export const CT_CONDITIONS = [
  "Mint",
  "Near Mint",
  "Slightly Played",
  "Moderately Played",
  "Played",
  "Poor",
] as const;

export const CT_LANGUAGES: { code: string; label: string }[] = [
  { code: "it", label: "Italiano" },
  { code: "en", label: "Inglese" },
  { code: "fr", label: "Francese" },
  { code: "de", label: "Tedesco" },
  { code: "es", label: "Spagnolo" },
  { code: "pt", label: "Portoghese" },
];
