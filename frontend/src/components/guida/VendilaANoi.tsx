"use client";

import { useState } from "react";
import { InquiryDialog } from "@/components/InquiryDialog";

/* "Ce l'hai? Vendila a noi": apre il modulo richieste con l'oggetto gia'
 * scritto. Le richieste arrivano come le altre (admin → Richieste). */
export function VendilaANoi({ carta, offerta, className = "btn btn-primary" }: {
  carta: string;
  /** Il testo dell'offerta mostrata, finisce nell'oggetto della richiesta. */
  offerta?: string | null;
  className?: string;
}) {
  const [aperto, setAperto] = useState(false);
  return (
    <>
      <button type="button" className={className} onClick={() => setAperto(true)}>
        💰 Ce l&apos;hai? Vendila a noi
      </button>
      <InquiryDialog
        open={aperto}
        onClose={() => setAperto(false)}
        customSubject={`Vorrei vendere: ${carta}${offerta ? ` (${offerta})` : ""}`}
        dialogTitle="Vendila a noi"
        subtitle={<>Ci dica condizioni e lingua della carta (meglio con qualche foto): Le rispondiamo con un&apos;offerta.</>}
        messagePlaceholder="Es. italiana, condizioni buone, piccolo graffio sul retro…"
      />
    </>
  );
}
