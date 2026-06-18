"use client";

import Link from "next/link";

interface Tab {
  key: string;
  href: string;
  label: string;
  icon: string;
}

const TABS: Tab[] = [
  { key: "esterne", href: "/admin/vendite/esterne", label: "Esterne", icon: "💸" },
  { key: "creazioni", href: "/admin/vendite/creazioni", label: "Creazioni", icon: "🎨" },
  { key: "contovendita", href: "/admin/vendite/contovendita", label: "Contovendita", icon: "🤝" },
  { key: "carte", href: "/admin/vendite/carte", label: "Carte sciolte", icon: "🎴" },
];

export function VenditeNav({ active }: { active: string }) {
  return (
    <div className="mb-4 border-b border-ink/10">
      <h1 className="display text-2xl text-ink mb-2">💰 Vendite</h1>
      <div className="flex gap-1 flex-wrap">
        {TABS.map((t) => {
          const isActive = active === t.key;
          return (
            <Link
              key={t.key}
              href={t.href}
              className={`px-4 py-2 text-sm font-semibold border-b-2 transition-colors ${
                isActive
                  ? "border-pink-deep text-ink"
                  : "border-transparent text-ink-soft hover:text-ink"
              }`}
            >
              {t.icon} {t.label}
            </Link>
          );
        })}
      </div>
    </div>
  );
}
