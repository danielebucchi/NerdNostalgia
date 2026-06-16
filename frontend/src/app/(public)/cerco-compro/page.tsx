import type { Metadata } from "next";
import Link from "next/link";
import { listWantedItems } from "@/lib/api";
import { WantedCard } from "@/components/WantedCard";

export const metadata: Metadata = {
  title: "Cerco / Compro",
  description:
    "Stiamo cercando questi pezzi nerd: videogiochi vintage, carte Pokémon, console, " +
    "Funko Pop. Hai qualcosa che fa al caso nostro? Scrivici.",
  alternates: { canonical: "/cerco-compro" },
  openGraph: {
    title: "Cerco / Compro — NerdNostalgia",
    description:
      "I pezzi che stiamo cercando. Vendi i tuoi cimeli nerd in Italia: pagamento veloce.",
    url: "/cerco-compro",
  },
};

export default async function CercoCompoPage() {
  let items: Awaited<ReturnType<typeof listWantedItems>>["items"] = [];
  let total = 0;
  let error: string | null = null;

  try {
    const data = await listWantedItems({ status: "ACTIVE", limit: 50 });
    items = data.items;
    total = data.total;
  } catch (err) {
    error = err instanceof Error ? err.message : "Errore sconosciuto";
  }

  return (
    <section>
      <div className="hero-blob p-6 sm:p-10 md:p-12 mb-10 sm:mb-12">
        <div className="text-center md:text-left">
          <span className="chip chip-ghost mb-4 inline-flex">Sto cercando</span>
          <h1 className="display text-3xl sm:text-4xl md:text-5xl text-ink leading-tight">
            Cerco questi <span className="text-pink-deep">pezzi nerd</span>.
          </h1>
          <p className="text-ink-soft text-base sm:text-lg mt-4 max-w-xl mx-auto md:mx-0">
            Hai una di queste cose in cantina? Scrivimi e ne parliamo. Pago in
            fretta, ritiro o spedizione a mio carico.
          </p>
        </div>
      </div>

      {error && (
        <div className="card p-6 text-center">
          <p className="display text-lg text-pink-deep mb-1">Backend non raggiungibile</p>
          <p className="text-sm text-ink-soft">{error}</p>
        </div>
      )}

      {!error && items.length === 0 && (
        <div className="card p-10 text-center">
          <p className="display text-xl text-ink mb-2">Per ora non cerco niente</p>
          <p className="text-ink-soft">
            Torna a trovarmi: pubblico nuove richieste quando ho un wishlist da svaligiare.
          </p>
          <Link href="/" className="btn btn-primary mt-6 inline-flex">
            Vai al catalogo
          </Link>
        </div>
      )}

      {items.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {items.map((item) => (
            <WantedCard key={item.id} item={item} />
          ))}
        </div>
      )}
    </section>
  );
}
