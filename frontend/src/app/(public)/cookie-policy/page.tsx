import type { Metadata } from "next";
import Link from "next/link";
import { SITE_NAME } from "@/lib/seo";

export const metadata: Metadata = {
  title: "Cookie Policy",
  description: `Cookie e storage locale utilizzati da ${SITE_NAME}`,
  alternates: { canonical: "/cookie-policy" },
  robots: { index: true, follow: false },
};

const LAST_UPDATE = "19 giugno 2026";

export default function CookiePolicyPage() {
  return (
    <article className="prose-nn max-w-3xl mx-auto">
      <Link href="/" className="btn btn-ghost text-sm mb-8">
        ← Catalogo
      </Link>

      <h1 className="display text-3xl sm:text-4xl text-ink leading-tight mb-2">
        Cookie Policy
      </h1>
      <p className="text-ink-soft text-sm mb-8">
        Ultimo aggiornamento: {LAST_UPDATE}
      </p>

      <Section title="In breve">
        <p>
          <strong>{SITE_NAME} non usa cookie di profilazione, di marketing o
          di terze parti.</strong> Non c&apos;è tracciamento pubblicitario, non
          c&apos;è analytics di terze parti, non vendiamo dati. Per questa
          ragione, ai sensi delle{" "}
          <a
            href="https://www.garanteprivacy.it/cookie"
            target="_blank"
            rel="noopener noreferrer"
            className="text-lilac-deep font-semibold hover:underline"
          >
            Linee Guida del Garante (10 giugno 2021)
          </a>
          , non è richiesto un banner di consenso preventivo: tutto ciò che
          salviamo lato client è strettamente tecnico e funzionale.
        </p>
      </Section>

      <Section title="1. Cosa salviamo nel tuo browser">
        <p>
          Usiamo lo storage locale del browser (<code>localStorage</code>) — non
          cookie HTTP — per memorizzare:
        </p>
        <table className="w-full text-sm border-collapse my-4">
          <thead>
            <tr className="border-b border-ink/20">
              <th className="text-left py-2 pr-4 font-semibold text-ink">Chiave</th>
              <th className="text-left py-2 pr-4 font-semibold text-ink">Contenuto</th>
              <th className="text-left py-2 font-semibold text-ink">Durata</th>
            </tr>
          </thead>
          <tbody className="text-ink-soft">
            <tr className="border-b border-ink/10">
              <td className="py-2 pr-4 align-top">
                <code>nn:wishlist:v1</code>
              </td>
              <td className="py-2 pr-4 align-top">
                Elenco numerico degli articoli che hai aggiunto ai Preferiti.
              </td>
              <td className="py-2 align-top">
                Finché non lo cancelli o non svuoti i Preferiti.
              </td>
            </tr>
            <tr className="border-b border-ink/10">
              <td className="py-2 pr-4 align-top">
                <code>nn:cookie-notice:v1</code>
              </td>
              <td className="py-2 pr-4 align-top">
                Memorizza che hai letto questa informativa, così non te la
                rimostriamo.
              </td>
              <td className="py-2 align-top">Persistente fino a rimozione.</td>
            </tr>
            <tr className="border-b border-ink/10">
              <td className="py-2 pr-4 align-top">
                <code>nn:admin:*</code>
              </td>
              <td className="py-2 pr-4 align-top">
                Solo per l&apos;area amministrativa: token di sessione e stato
                aperto/chiuso di alcune sezioni. Non viene mai impostato per i
                visitatori del catalogo.
              </td>
              <td className="py-2 align-top">
                Token: scade alla disconnessione. Preferenze UI: persistenti.
              </td>
            </tr>
          </tbody>
        </table>
      </Section>

      <Section title="2. Cookie HTTP">
        <p>
          Il sito <strong>non imposta cookie HTTP</strong> propri. L&apos;unico
          dato di sessione tecnica è il token JWT dell&apos;area
          amministrativa, salvato in <code>localStorage</code> e usato solo per
          gli account autorizzati.
        </p>
      </Section>

      <Section title="3. Terze parti">
        <p>
          Non sono integrati strumenti di terze parti che impostino cookie o
          identificatori — niente Google Analytics, niente Meta Pixel, niente
          ad network, niente embed che traccino l&apos;utente.
        </p>
        <p>
          Se in futuro dovessimo aggiungere strumenti di analisi o terze parti
          con effetti di profilazione, questa pagina sarà aggiornata e
          comparirà un banner di consenso preventivo.
        </p>
      </Section>

      <Section title="4. Come gestire o eliminare i dati">
        <p>
          Puoi cancellare i dati salvati nel browser in due modi:
        </p>
        <ul>
          <li>
            usando il pulsante <strong>Svuota preferiti</strong> nella pagina{" "}
            <Link
              href="/preferiti"
              className="text-lilac-deep font-semibold hover:underline"
            >
              /preferiti
            </Link>
            ;
          </li>
          <li>
            dalle impostazioni del browser: <em>Impostazioni → Privacy →
            Cancella dati dei siti</em>, oppure mirando solo a{" "}
            <code>nerdnostalgia.it</code>.
          </li>
        </ul>
        <p>
          La cancellazione non comporta perdita di funzionalità: rivedrai
          semplicemente l&apos;avviso informativo e la lista preferiti vuota.
        </p>
      </Section>

      <Section title="5. Riferimenti">
        <ul>
          <li>
            <Link
              href="/privacy"
              className="text-lilac-deep font-semibold hover:underline"
            >
              Informativa Privacy
            </Link>{" "}
            — finalità, base giuridica, diritti dell&apos;interessato.
          </li>
          <li>
            Contatti per richieste:{" "}
            <a
              href="mailto:info@nerdnostalgia.it"
              className="text-lilac-deep font-semibold hover:underline"
            >
              info@nerdnostalgia.it
            </a>
          </li>
        </ul>
      </Section>
    </article>
  );
}

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="mb-8">
      <h2 className="display text-xl sm:text-2xl text-ink mb-3">{title}</h2>
      <div className="text-ink-soft text-base leading-relaxed space-y-3 [&_ul]:list-disc [&_ul]:pl-6 [&_ul]:space-y-1 [&_code]:bg-ink/5 [&_code]:px-1.5 [&_code]:py-0.5 [&_code]:rounded [&_code]:text-xs [&_code]:text-ink">
        {children}
      </div>
    </section>
  );
}
