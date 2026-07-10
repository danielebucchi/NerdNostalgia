"use client";

import Link from "next/link";
import { useRouter, usePathname } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { useAuth } from "@/components/admin/AuthProvider";
import { QuickAddDialog } from "@/components/admin/QuickAddDialog";
import { useSettings } from "@/lib/settings-context";

const ALL_NAV_ITEMS = [
  { href: "/admin", label: "Dashboard", icon: "📊", exact: true },
  { href: "/admin/articles", label: "Articoli", icon: "🎮" },
  { href: "/admin/lotti", label: "Lotti (interno)", icon: "📦" },
  { href: "/admin/vendite", label: "Vendite", icon: "💰" },
  { href: "/admin/spese", label: "Spese", icon: "💰" },
  { href: "/admin/ordini", label: "Ordini", icon: "📥", requiresPayments: true },
  { href: "/admin/inquiries", label: "Richieste", icon: "💬" },
  { href: "/admin/wanted", label: "Cerco/Compro", icon: "🔍" },
  { href: "/admin/tassonomia", label: "Tassonomia", icon: "🏷" },
  { href: "/admin/import-vinted", label: "Sync Vinted", icon: "🛍" },
  { href: "/admin/markups", label: "Commissioni", icon: "💸" },
  { href: "/admin/impostazioni", label: "Impostazioni", icon: "⚙️" },
];

// Bottom bar mobile: le 4 sezioni a uso quotidiano, il resto sotto ≡.
const BOTTOM_NAV = [
  { href: "/admin", label: "Home", icon: "📊", exact: true },
  { href: "/admin/articles", label: "Articoli", icon: "🎮" },
  { href: "/admin/lotti", label: "Lotti", icon: "📦" },
  { href: "/admin/inquiries", label: "Richieste", icon: "💬" },
];

export function AdminShell({ children }: { children: React.ReactNode }) {
  const { user, loading, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [quickAddOpen, setQuickAddOpen] = useState(false);
  const { paymentsEnabled } = useSettings();

  const NAV_ITEMS = ALL_NAV_ITEMS.filter(
    (item) => !item.requiresPayments || paymentsEnabled,
  );

  // FAB contestuale (solo mobile): l'azione "aggiungi" della pagina corrente.
  type FabConfig = {
    label: string;
    icon: string;
    href?: string;
    action?: "quickadd" | "event";
  };
  const fab = useMemo((): FabConfig | null => {
    if (pathname === "/admin") {
      return { label: "Scatta e cataloga", icon: "📸", action: "quickadd" };
    }
    if (pathname === "/admin/articles") {
      return { label: "Nuovo articolo", icon: "＋", href: "/admin/articles/new" };
    }
    if (pathname === "/admin/lotti") {
      return { label: "Nuovo lotto", icon: "＋", href: "/admin/lotti/new" };
    }
    if (/^\/admin\/lotti\/\d+$/.test(pathname)) {
      // La pagina lotto ascolta l'evento e porta al form "aggiungi item"
      return { label: "Aggiungi item", icon: "＋", action: "event" };
    }
    return null;
  }, [pathname]);

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
        <div className="flex items-center justify-between px-4 py-3 gap-2">
          <Link href="/admin" className="display text-lg text-ink">
            Nerd<span className="text-lilac-deep">.</span>Nostalgia
          </Link>
          <div className="flex items-center gap-1.5">
            {/* La PWA standalone non ha la barra del browser: refresh manuale */}
            <button
              type="button"
              onClick={() => window.location.reload()}
              className="btn btn-ghost text-xs px-2.5"
              aria-label="Ricarica"
              title="Ricarica"
            >
              ↻
            </button>
            <button
              type="button"
              onClick={() => setMobileNavOpen((v) => !v)}
              className="btn btn-ghost text-xs"
              aria-expanded={mobileNavOpen}
            >
              {mobileNavOpen ? "✕" : "☰"} Menu
            </button>
          </div>
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
        {/* pb-28 mobile: spazio per bottom bar + FAB */}
        <div className="max-w-5xl mx-auto px-4 sm:px-6 py-6 sm:py-10 pb-28 md:pb-10">
          {children}
        </div>
      </main>

      {/* FAB contestuale (solo mobile), sopra la bottom bar */}
      {fab && (
        fab.href ? (
          <Link
            href={fab.href}
            aria-label={fab.label}
            title={fab.label}
            className="md:hidden fixed bottom-20 right-4 z-40 w-14 h-14 rounded-full bg-gradient-to-br from-pink to-lilac-deep text-white text-2xl flex items-center justify-center shadow-hover active:scale-95 transition-transform"
          >
            {fab.icon}
          </Link>
        ) : (
          <button
            type="button"
            aria-label={fab.label}
            title={fab.label}
            onClick={() => {
              if (fab.action === "quickadd") setQuickAddOpen(true);
              else window.dispatchEvent(new CustomEvent("nn:admin-fab"));
            }}
            className="md:hidden fixed bottom-20 right-4 z-40 w-14 h-14 rounded-full bg-gradient-to-br from-pink to-lilac-deep text-white text-2xl flex items-center justify-center shadow-hover active:scale-95 transition-transform"
          >
            {fab.icon}
          </button>
        )
      )}

      {/* Bottom navigation bar (solo mobile) */}
      <nav
        className="md:hidden fixed bottom-0 inset-x-0 z-40 bg-white/90 backdrop-blur-xl border-t border-ink/10 flex items-stretch"
        style={{ paddingBottom: "env(safe-area-inset-bottom)" }}
      >
        {BOTTOM_NAV.map((item) => {
          const active = item.exact
            ? pathname === item.href
            : pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex-1 flex flex-col items-center gap-0.5 py-2 text-[10px] font-bold ${
                active ? "text-lilac-deep" : "text-ink-soft"
              }`}
            >
              <span className={`text-xl leading-none ${active ? "" : "grayscale opacity-70"}`}>
                {item.icon}
              </span>
              {item.label}
            </Link>
          );
        })}
        <button
          type="button"
          onClick={() => {
            setMobileNavOpen((v) => !v);
            window.scrollTo({ top: 0, behavior: "smooth" });
          }}
          className={`flex-1 flex flex-col items-center gap-0.5 py-2 text-[10px] font-bold ${
            mobileNavOpen ? "text-lilac-deep" : "text-ink-soft"
          }`}
          aria-expanded={mobileNavOpen}
        >
          <span className="text-xl leading-none">≡</span>
          Menu
        </button>
      </nav>

      <QuickAddDialog open={quickAddOpen} onClose={() => setQuickAddOpen(false)} />
    </div>
  );
}
