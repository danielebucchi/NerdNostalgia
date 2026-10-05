import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Contatti",
  description:
    "Ci scriva per qualsiasi domanda sui nostri pezzi nerd, per proporci un acquisto o " +
    "per una consulenza. Rispondiamo entro 24-48 ore.",
  alternates: { canonical: "/contatti" },
  openGraph: {
    title: "Contatti — NerdNostalgia",
    description: "Ci scriva per informazioni o per vendere i Suoi pezzi nerd.",
    url: "/contatti",
  },
};

export default function ContattiLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
