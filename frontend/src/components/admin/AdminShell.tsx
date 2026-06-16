"use client";

import Link from "next/link";
import { useRouter, usePathname } from "next/navigation";
import { useEffect } from "react";
import { useAuth } from "@/components/admin/AuthProvider";

const NAV_ITEMS = [
  { href: "/admin", label: "Dashboard", icon: "✨", exact: true },
  { href: "/admin/articles", label: "Articoli", icon: "🎮" },
  { href: "/admin/inquiries", label: "Richieste", icon: "✉" },
  { href: "/admin/wanted", label: "Cerco/Compro", icon: "🔍" },
];

export function AdminShell({ children }: { children: React.ReactNode }) {
  const { user, loading, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!loading && !user) {
      router.replace("/admin/login");
    }
  }, [loading, user, router]);

  if (loading || !user) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="display text-ink-soft">Caricamento area admin…</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen grid md:grid-cols-[260px_1fr]">
      <aside className="bg-cream border-r-2 border-ink/15 p-6">
        <Link href="/" className="display text-xl text-ink block mb-1">
          Nerd<span className="text-pink-deep">.</span>Nostalgia
        </Link>
        <p className="text-xs text-ink-soft uppercase tracking-wider mb-6">Admin panel</p>

        <nav className="space-y-1">
          {NAV_ITEMS.map((item) => {
            const active = item.exact
              ? pathname === item.href
              : pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={
                  "flex items-center gap-3 px-3 py-2 rounded-xl border-2 transition-colors " +
                  (active
                    ? "bg-pink text-ink border-ink"
                    : "border-transparent text-ink-soft hover:text-ink hover:bg-pink-soft")
                }
              >
                <span>{item.icon}</span>
                <span className="font-semibold">{item.label}</span>
              </Link>
            );
          })}
        </nav>

        <div className="mt-10 pt-6 border-t-2 border-ink/15 text-sm">
          <p className="text-ink-soft">Loggato come</p>
          <p className="display text-ink">{user.username}</p>
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

      <main className="bg-white/40 backdrop-blur-sm">
        <div className="max-w-5xl mx-auto px-6 py-10">{children}</div>
      </main>
    </div>
  );
}
