"use client";

import Link from "next/link";
import { useCustomer } from "@/lib/customer-auth";

interface Props {
  variant?: "desktop" | "mobile";
}

/**
 * Accesso all'area cliente. Mostra "Accedi" a chi non ha una sessione e il
 * profilo a chi ce l'ha.
 *
 * Finché la sessione non è letta dal localStorage non mostra nulla: far
 * lampeggiare "Accedi" a chi è già dentro sembra un logout avvenuto.
 */
export function CustomerNavLink({ variant = "desktop" }: Props) {
  const { user, loading } = useCustomer();
  if (loading) return null;

  const href = user ? "/profilo" : "/accedi";
  const nome = user?.full_name?.split(" ")[0] || "Profilo";

  if (variant === "mobile") {
    return (
      <Link
        href={href}
        className="btn btn-ghost text-xs px-2.5 py-1.5"
        aria-label={user ? "Il tuo profilo" : "Accedi"}
        title={user ? "Il tuo profilo" : "Accedi"}
      >
        {user ? "👤" : "Accedi"}
      </Link>
    );
  }

  return (
    <Link href={href} className="btn btn-ghost text-sm inline-flex items-center gap-1.5">
      <span aria-hidden="true">👤</span>
      <span>{user ? nome : "Accedi"}</span>
    </Link>
  );
}
