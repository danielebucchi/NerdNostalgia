import type { Metadata } from "next";
import { AuthProvider } from "@/components/admin/AuthProvider";

// Manifest PWA dedicato: id/scope/start_url distinti dal sito pubblico,
// cosi' Chrome tratta l'admin come una SECONDA app installabile (altrimenti
// "questa app e' gia' installata"). Icona viola scura per distinguerla.
export const metadata: Metadata = {
  title: { default: "NN Admin", template: "%s · NN Admin" },
  manifest: "/admin-manifest.webmanifest",
  robots: { index: false, follow: false },
  icons: {
    icon: "/admin-icon-192.png",
    apple: "/admin-icon-192.png",
  },
};

export default function AdminRootLayout({ children }: { children: React.ReactNode }) {
  return <AuthProvider>{children}</AuthProvider>;
}
