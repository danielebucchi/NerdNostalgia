import type { Metadata } from "next";
import "./globals.css";
import { Footer, Header } from "@/components/Header";

export const metadata: Metadata = {
  title: "NerdNostalgia — Compro e vendo nerderie",
  description:
    "Catalogo di videogiochi vintage, carte Pokemon e prodotti nerd. Compro, vendo, scambio.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="it">
      <body>
        <Header />
        <main className="mx-auto max-w-6xl px-6 py-10">{children}</main>
        <Footer />
      </body>
    </html>
  );
}
