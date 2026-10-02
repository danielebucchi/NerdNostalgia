"use client";

import Link from "next/link";
import { useCustomer } from "@/lib/customer-auth";

/**
 * Invito a creare il profilo, dopo l'acquisto.
 *
 * Qui e non al checkout: in mezzo al pagamento ogni passaggio in piu' fa
 * perdere acquirenti, mentre a ordine concluso l'offerta è concreta — ha
 * appena comprato qualcosa e vuole sapere dove sta il suo pacco.
 *
 * Non compare a chi è già dentro.
 */
export function RegistrationInvite() {
  const { user, loading } = useCustomer();
  if (loading || user) return null;

  return (
    <div className="rounded-2xl bg-lilac-deep/10 ring-1 ring-lilac-deep/35 p-5 text-left mb-8">
      <p className="display text-lg text-ink mb-1">
        Vuoi seguire la spedizione?
      </p>
      <p className="text-sm text-ink-soft leading-snug mb-4">
        Crea un profilo con la stessa email dell&apos;ordine: questo acquisto
        ci finisce dentro da solo, con il codice di tracciamento appena
        spedisco. E al prossimo ordine non riscrivi nome e indirizzo.
      </p>
      <Link href="/registrati" className="btn btn-primary text-sm">
        Crea il profilo →
      </Link>
    </div>
  );
}
