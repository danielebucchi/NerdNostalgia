import Link from "next/link";
import { listWantedItems } from "@/lib/api";
import { WantedCard } from "@/components/WantedCard";

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
      <div className="hero-blob p-8 sm:p-12 mb-12">
        <div className="grid gap-6 md:grid-cols-[2fr_1fr] items-end">
          <div>
            <span className="chip chip-mint mb-4">Sto cercando</span>
            <h1 className="display text-3xl sm:text-5xl text-ink leading-tight">
              Cerco questi <span className="text-pink-deep">pezzi nerd</span>.
            </h1>
            <p className="text-ink-soft text-lg mt-4 max-w-xl">
              Hai una di queste cose in cantina? Scrivimi e ne parliamo. Pago in fretta,
              ritiro o spedizione a mio carico.
            </p>
          </div>
          <div className="text-right">
            {!error && (
              <span className="chip chip-pink">{total} richieste attive</span>
            )}
          </div>
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
