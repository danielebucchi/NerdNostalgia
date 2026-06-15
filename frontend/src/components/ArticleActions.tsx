"use client";

import { useState } from "react";
import { InquiryDialog } from "@/components/InquiryDialog";

interface ArticleActionsProps {
  articleId: number;
  articleTitle: string;
  sold?: boolean;
}

export function ArticleActions({ articleId, articleTitle, sold }: ArticleActionsProps) {
  const [open, setOpen] = useState(false);

  return (
    <>
      <div className="flex flex-wrap gap-3">
        <button type="button" className="btn btn-primary" disabled>
          {sold ? "Venduto" : "Aggiungi al carrello"}
        </button>
        <button type="button" className="btn btn-ghost" onClick={() => setOpen(true)}>
          Chiedi info
        </button>
      </div>
      <p className="mt-3 text-xs text-ink-soft">
        Carrello in arrivo — per ora scrivimi dal bottone &laquo;Chiedi info&raquo;.
      </p>

      <InquiryDialog
        open={open}
        onClose={() => setOpen(false)}
        articleId={articleId}
        articleTitle={articleTitle}
      />
    </>
  );
}
