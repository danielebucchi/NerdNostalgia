import type { Metadata, Viewport } from "next";
import "./globals.css";
import { Footer, Header, Topbar } from "@/components/Header";

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
      <body>
        <Topbar />
        <Header />
        <main className="mx-auto max-w-6xl px-6 py-10">{children}</main>
        <Footer />
      </body>
    </html>
  );
}
