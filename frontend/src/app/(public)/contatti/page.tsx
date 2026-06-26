"use client";

import { useState } from "react";
import { InquiryDialog } from "@/components/InquiryDialog";

export default function ContattiPage() {
  const [open, setOpen] = useState(false);

  return (
    <section>
      <div className="hero-blob p-6 sm:p-10 md:p-12 mb-10 sm:mb-12 text-center">
        <span className="chip chip-mint mb-4 inline-flex">Scrivimi</span>
        <h1 className="display text-3xl sm:text-4xl md:text-5xl text-ink leading-tight">
          Mi serve solo una <span className="text-pink-deep">scintilla nerd</span>.
        </h1>
        <p className="text-ink-soft text-base sm:text-lg max-w-xl mx-auto mt-4">
          Hai un dubbio su un articolo? Vuoi propormi qualcosa che non vedi nel
          catalogo? Scrivimi: rispondo a tutti, prometto.
        </p>
        <div className="mt-6">
          <button type="button" className="btn btn-primary" onClick={() => setOpen(true)}>
            Apri il form 💬
          </button>
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-3">
        <div className="card p-6">
          <h3 className="display text-lg text-ink">Compri o vendi?</h3>
          <p className="text-ink-soft text-sm mt-2 leading-relaxed">
            Accetto proposte di vendita per qualsiasi nerderia retrò: console, giochi
            sigillati o usati, carte Pokémon, Funko, e altro. Scrivimi con foto.
          </p>
        </div>
        <div className="card p-6">
          <h3 className="display text-lg text-ink">Spedizione</h3>
          <p className="text-ink-soft text-sm mt-2 leading-relaxed">
            Spedisco in tutta Italia con corriere tracciato. Costo concordato in base
            a peso e valore dichiarato.
          </p>
        </div>
        <div className="card p-6">
          <h3 className="display text-lg text-ink">Tempi di risposta</h3>
          <p className="text-ink-soft text-sm mt-2 leading-relaxed">
            In genere rispondo entro 24h, sempre entro 48h nei weekend. Per richieste
            urgenti includi il numero di telefono.
          </p>
        </div>
      </div>

      <InquiryDialog open={open} onClose={() => setOpen(false)} />
    </section>
  );
}
