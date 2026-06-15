"use client";

import { useState } from "react";
import { InquiryDialog } from "@/components/InquiryDialog";

interface WantedActionsProps {
  wantedId: number;
  title: string;
  fulfilled?: boolean;
}

export function WantedActions({ wantedId, title, fulfilled }: WantedActionsProps) {
  const [open, setOpen] = useState(false);

  return (
    <>
      <div className="flex flex-wrap gap-3">
        <button
          type="button"
          className="btn btn-primary"
          onClick={() => setOpen(true)}
          disabled={fulfilled}
        >
          {fulfilled ? "Già trovato" : "Ce l’ho! Te lo vendo"}
        </button>
      </div>
      <p className="mt-3 text-xs text-ink-soft">
        Apri il form: descrivi cosa hai e a quanto, ti rispondo io.
      </p>

      <InquiryDialog
        open={open}
        onClose={() => setOpen(false)}
        customSubject={`Ce l'ho: ${title} (wanted #${wantedId})`}
        dialogTitle="Te lo propongo"
        subtitle={
          <>
            per la richiesta <strong>{title}</strong>
          </>
        }
        messagePlaceholder="Ce l'ho! Condizione, prezzo, foto disponibili, eventuali difetti..."
      />
    </>
  );
}
