"use client";

import { useEffect, useState } from "react";

interface Props {
  storageKey: string;
  title: string;
  subtitle?: string;
  icon?: string;
  defaultOpen?: boolean;
  badge?: string;
  children: React.ReactNode;
}

const PREFIX = "nn:dash:collapse:";

export function CollapsibleSection({
  storageKey, title, subtitle, icon, defaultOpen = true, badge, children,
}: Props) {
  const [open, setOpen] = useState(defaultOpen);
  const [hydrated, setHydrated] = useState(false);

  // Carica stato persistito dopo il mount (evita hydration mismatch)
  useEffect(() => {
    try {
      const saved = localStorage.getItem(PREFIX + storageKey);
      if (saved === "1") setOpen(true);
      else if (saved === "0") setOpen(false);
    } catch {
      // ignore
    }
    setHydrated(true);
  }, [storageKey]);

  function toggle() {
    setOpen((prev) => {
      const next = !prev;
      try {
        localStorage.setItem(PREFIX + storageKey, next ? "1" : "0");
      } catch {
        // ignore
      }
      return next;
    });
  }

  return (
    <div className="mb-3">
      <button
        type="button"
        onClick={toggle}
        className="w-full flex items-center justify-between gap-3 p-3 card hover:bg-pink-soft/20 transition-colors text-left"
        aria-expanded={open}
      >
        <div className="flex items-center gap-2 min-w-0 flex-1">
          {icon && <span className="text-lg shrink-0">{icon}</span>}
          <div className="min-w-0 flex-1">
            <h3 className="display text-base text-ink">{title}</h3>
            {subtitle && <p className="text-[11px] text-ink-soft truncate">{subtitle}</p>}
          </div>
          {badge && (
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-lilac-soft text-lilac-deep font-semibold shrink-0">
              {badge}
            </span>
          )}
        </div>
        <span
          className={`text-ink-soft transition-transform shrink-0 ${open ? "rotate-180" : ""}`}
          aria-hidden
        >▾</span>
      </button>
      {hydrated && open && <div className="mt-2">{children}</div>}
    </div>
  );
}
