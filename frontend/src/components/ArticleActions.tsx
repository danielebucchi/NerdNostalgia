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
        {sold ? (
          <span className="chip chip-pink text-sm">Venduto</span>
        ) : (
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => setOpen(true)}
          >
            Chiedi info
          </button>
        )}
      </div>

      <InquiryDialog
        open={open}
        onClose={() => setOpen(false)}
        articleId={articleId}
        articleTitle={articleTitle}
      />
    </>
  );
}
