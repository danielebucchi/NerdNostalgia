import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Contatti",
  description:
    "Scrivici per qualsiasi domanda sui nostri pezzi nerd, per propormi un acquisto o " +
    "per una consulenza. Rispondiamo entro 24-48 ore.",
  alternates: { canonical: "/contatti" },
  openGraph: {
    title: "Contatti — NerdNostalgia",
    description: "Scrivici per informazioni o per vendere i tuoi pezzi nerd.",
    url: "/contatti",
  },
};

export default function ContattiLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
