import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Valuta le tue carte Pokémon: quanto valgono?",
  description:
    "Scrivi il nome della carta e scopri subito quanto vale sul mercato. Ce l'hai nel cassetto? " +
    "Vendila a noi: ti facciamo un'offerta.",
  alternates: { canonical: "/valuta-carte" },
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
