"use client";

import Link from "next/link";
import { useRouter, usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuth } from "@/components/admin/AuthProvider";

const NAV_ITEMS = [
  { href: "/admin", label: "Dashboard", icon: "📊", exact: true },
  { href: "/admin/articles", label: "Articoli", icon: "🎮" },
  { href: "/admin/lotti", label: "Lotti (interno)", icon: "📦" },
  { href: "/admin/vendite", label: "Vendite", icon: "💰" },
  { href: "/admin/spese", label: "Spese", icon: "💰" },
  { href: "/admin/inquiries", label: "Richieste", icon: "✉" },
  { href: "/admin/wanted", label: "Cerco/Compro", icon: "🔍" },
  { href: "/admin/tassonomia", label: "Tassonomia", icon: "🏷" },
  { href: "/admin/import-vinted", label: "Sync Vinted", icon: "🛍" },
  { href: "/admin/markups", label: "Commissioni", icon: "💸" },
];

export function AdminShell({ children }: { children: React.ReactNode }) {
  const { user, loading, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  useEffect(() => {
    if (!loading && !user) {
      router.replace("/admin/login");
    }
  }, [loading, user, router]);

  // Chiudi nav mobile al cambio rotta
  useEffect(() => {
    setMobileNavOpen(false);
  }, [pathname]);

  if (loading || !user) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="display text-ink-soft">Caricamento area admin…</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen md:grid md:grid-cols-[260px_1fr]">
      {/* Topbar mobile */}
      <div className="md:hidden sticky top-0 z-30 bg-white/80 backdrop-blur-xl border-b border-ink/10">
        <div className="flex items-center justify-between px-4 py-3">
          <Link href="/admin" className="display text-lg text-ink">
            Nerd<span className="text-lilac-deep">.</span>Nostalgia
          </Link>
          <button
            type="button"
            onClick={() => setMobileNavOpen((v) => !v)}
            className="btn btn-ghost text-xs"
            aria-expanded={mobileNavOpen}
          >
            {mobileNavOpen ? "✕" : "☰"} Menu
          </button>
        </div>
        {mobileNavOpen && (
          <nav className="px-4 pb-4 space-y-1">
            {NAV_ITEMS.map((item) => {
              const active = item.exact
                ? pathname === item.href
                : pathname.startsWith(item.href);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={
                    "flex items-center gap-3 px-3 py-2 rounded-2xl transition-all " +
                    (active
                      ? "bg-gradient-to-br from-pink to-lilac-deep text-white shadow-soft"
                      : "text-ink-soft hover:text-ink hover:bg-white/70")
                  }
                >
                  <span className="text-lg">{item.icon}</span>
                  <span className="font-semibold text-sm">{item.label}</span>
                </Link>
              );
            })}
            <div className="pt-4 mt-2 border-t border-ink/10 text-sm">
              <p className="text-xs text-ink-soft">
                Loggato come <strong className="text-ink">{user.username}</strong>
              </p>
              <button
                type="button"
                className="btn btn-ghost text-xs mt-3 w-full justify-center"
                onClick={logout}
              >
                Esci
              </button>
            </div>
          </nav>
        )}
      </div>

      {/* Sidebar desktop */}
      <aside className="hidden md:flex md:flex-col bg-white/60 backdrop-blur-xl border-r border-ink/8 p-6 sticky top-0 h-screen">
        <Link href="/" className="display text-xl text-ink block leading-tight mb-1">
          Nerd<span className="text-lilac-deep">.</span>Nostalgia
        </Link>
        <p className="text-[10px] text-ink-soft uppercase tracking-[0.16em] mb-8">
          Admin panel
        </p>

        <nav className="space-y-1 flex-1">
          {NAV_ITEMS.map((item) => {
            const active = item.exact
              ? pathname === item.href
              : pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={
                  "flex items-center gap-3 px-3 py-2.5 rounded-2xl transition-all duration-200 " +
                  (active
                    ? "bg-gradient-to-br from-pink to-lilac-deep text-white shadow-soft"
                    : "text-ink-soft hover:text-ink hover:bg-white/70")
                }
              >
                <span className="text-lg w-6 text-center">{item.icon}</span>
                <span className="font-semibold text-sm">{item.label}</span>
              </Link>
            );
          })}
        </nav>

        <div className="mt-8 pt-6 border-t border-ink/10 text-sm">
          <p className="text-xs text-ink-soft uppercase tracking-wider">Loggato come</p>
          <p className="display text-ink leading-tight mt-1">{user.username}</p>
          <p className="text-xs text-ink-soft">{user.role}</p>
          <button
            type="button"
            className="btn btn-ghost text-xs mt-4 w-full justify-center"
            onClick={logout}
          >
            Esci
          </button>
        </div>
      </aside>

      <main>
        <div className="max-w-5xl mx-auto px-4 sm:px-6 py-6 sm:py-10">
          {children}
        </div>
      </main>
    </div>
  );
}
