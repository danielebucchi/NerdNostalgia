"use client";

import { useEffect, useState } from "react";
import { PUBLIC_API_BASE } from "@/lib/api";
import type { Platform, PlatformListResponse } from "@/lib/types";

interface State {
  items: Platform[];
  loading: boolean;
  error: string | null;
  reload: () => void;
}

export function usePlatforms(activeOnly: boolean = true): State {
  const [items, setItems] = useState<Platform[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [bump, setBump] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    const qs = activeOnly ? "?active_only=true" : "";
    fetch(`${PUBLIC_API_BASE}/api/platforms/${qs}`, { cache: "no-store" })
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json() as Promise<PlatformListResponse>;
      })
      .then((d) => {
        if (!cancelled) setItems(d.items || []);
      })
      .catch((err) => {
        if (!cancelled) setError(String(err));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [bump, activeOnly]);

  return {
    items,
    loading,
    error,
    reload: () => setBump((b) => b + 1),
  };
}
