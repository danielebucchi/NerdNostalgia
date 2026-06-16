"use client";

import { useEffect, useState } from "react";
import { PUBLIC_API_BASE } from "@/lib/api";
import type { Category, CategoryNode } from "@/lib/types";

interface State {
  flat: Category[];
  tree: CategoryNode[];
  byId: Record<number, Category>;
  loading: boolean;
  error: string | null;
  reload: () => void;
}

function buildTree(flat: Category[]): CategoryNode[] {
  const byId: Record<number, CategoryNode> = {};
  flat.forEach((c) => {
    byId[c.id] = { ...c, children: [] };
  });
  const roots: CategoryNode[] = [];
  flat.forEach((c) => {
    const node = byId[c.id];
    if (c.parent_id == null) {
      roots.push(node);
    } else {
      const parent = byId[c.parent_id];
      if (parent) parent.children.push(node);
      else roots.push(node);
    }
  });
  return roots;
}

export function useCategories(): State {
  const [flat, setFlat] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [bump, setBump] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetch(`${PUBLIC_API_BASE}/api/categories/`, { cache: "no-store" })
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((d) => {
        if (!cancelled) setFlat(d.items || []);
      })
      .catch((err) => {
        if (!cancelled) setError(String(err));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [bump]);

  const tree = buildTree(flat);
  const byId: Record<number, Category> = {};
  flat.forEach((c) => {
    byId[c.id] = c;
  });

  return {
    flat,
    tree,
    byId,
    loading,
    error,
    reload: () => setBump((b) => b + 1),
  };
}

/** Trova la categoria top-level di una categoria (sé stessa se già top). */
export function findTopLevel(
  byId: Record<number, Category>,
  categoryId: number,
): Category | null {
  let current = byId[categoryId];
  while (current && current.parent_id != null) {
    const next = byId[current.parent_id];
    if (!next) break;
    current = next;
  }
  return current ?? null;
}
