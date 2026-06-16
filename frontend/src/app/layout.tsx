import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "NerdNostalgia — Videogiochi, Pokémon & nerderie",
  description:
    "Compro, vendo e scambio videogiochi vintage, carte Pokémon, Funko Pop e gadget nerd. Catalogo curato e spedizioni in tutta Italia.",
};

export const viewport: Viewport = {
  themeColor: "#fff7ed",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="it">
      <body>{children}</body>
    </html>
  );
}
