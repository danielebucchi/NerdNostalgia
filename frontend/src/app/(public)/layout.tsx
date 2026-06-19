import { CookieBanner } from "@/components/CookieBanner";
import { Footer, Header, Topbar } from "@/components/Header";

export default function PublicLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <Topbar />
      <Header />
      <main className="mx-auto max-w-6xl px-4 sm:px-6 py-8 sm:py-10">{children}</main>
      <Footer />
      <CookieBanner />
    </>
  );
}
