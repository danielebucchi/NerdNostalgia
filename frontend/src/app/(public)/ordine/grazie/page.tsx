import Link from "next/link";

export const metadata = {
  title: "Grazie per il tuo ordine — Nerd.Nostalgia",
};

export default async function OrderThankYouPage({
  searchParams,
}: {
  searchParams: Promise<{ order?: string }>;
}) {
  const { order } = await searchParams;
  return (
    <div className="mx-auto max-w-xl px-4 py-16 sm:py-24 text-center">
      <div className="text-5xl mb-4">🎉</div>
      <h1 className="display text-3xl sm:text-4xl text-ink mb-3">Grazie!</h1>
      <p className="text-ink-soft leading-relaxed mb-2">
        Il pagamento è andato a buon fine e il tuo ordine
        {order ? (
          <>
            {" "}
            <strong className="text-ink">#{order}</strong>
          </>
        ) : null}{" "}
        è confermato.
      </p>
      <p className="text-ink-soft leading-relaxed mb-8">
        Ti ho mandato una email di riepilogo e ti scriverò appena spedisco.
      </p>
      <Link href="/" className="btn btn-primary">
        Torna al negozio
      </Link>
    </div>
  );
}
