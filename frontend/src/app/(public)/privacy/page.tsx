import type { Metadata } from "next";
import Link from "next/link";
import { SITE_NAME } from "@/lib/seo";

export const metadata: Metadata = {
  title: "Informativa Privacy",
  description: `Informativa sul trattamento dei dati personali — ${SITE_NAME}`,
  alternates: { canonical: "/privacy" },
  robots: { index: true, follow: false },
};

const LAST_UPDATE = "19 giugno 2026";

export default function PrivacyPage() {
  return (
    <article className="prose-nn max-w-3xl mx-auto">
      <Link href="/" className="btn btn-ghost text-sm mb-8">
        ← Catalogo
      </Link>

      <h1 className="display text-3xl sm:text-4xl text-ink leading-tight mb-2">
        Informativa Privacy
      </h1>
      <p className="text-ink-soft text-sm mb-8">
        Ultimo aggiornamento: {LAST_UPDATE}
      </p>

      <Section title="1. Chi tratta i tuoi dati">
        <p>
          Il titolare del trattamento è il gestore di <strong>{SITE_NAME}</strong>,
          contattabile all&apos;indirizzo{" "}
          <a
            href="mailto:info@nerdnostalgia.it"
            className="text-lilac-deep font-semibold hover:underline"
          >
            info@nerdnostalgia.it
          </a>
          .
        </p>
        <p>
          Questa informativa è resa ai sensi degli artt. 13 e 14 del Regolamento
          UE 2016/679 (GDPR) e del D.Lgs. 196/2003 e ss.mm.ii. (Codice Privacy).
        </p>
      </Section>

      <Section title="2. Quali dati raccogliamo">
        <p>
          <strong>Dati che fornisci tu</strong>, compilando il form di contatto
          o di richiesta acquisto:
        </p>
        <ul>
          <li>Nome (o nickname)</li>
          <li>Indirizzo email</li>
          <li>Numero di telefono (opzionale)</li>
          <li>Testo del messaggio</li>
          <li>Articolo a cui la richiesta è collegata (se applicabile)</li>
        </ul>

        <p>
          <strong>Dati tecnici automatici</strong>, salvati esclusivamente nel
          tuo browser tramite <em>localStorage</em>:
        </p>
        <ul>
          <li>
            Lista degli articoli che hai aggiunto ai <em>Preferiti</em> (solo ID
            numerici, mai dati personali)
          </li>
          <li>
            Stato di apertura/chiusura di alcune sezioni dell&apos;interfaccia
            (solo per area amministrativa, non riguarda i visitatori)
          </li>
          <li>
            Token di sessione (JWT) per l&apos;area amministrativa, valido solo
            per gli account autorizzati
          </li>
        </ul>
        <p>
          Questi dati restano nel tuo browser e non vengono inviati ai nostri
          server, salvo quando esegui un&apos;azione che lo richiede
          esplicitamente (es. invio del form).
        </p>

        <p>
          <strong>Log tecnici lato server</strong>: il server registra
          temporaneamente indirizzo IP, user agent e timestamp delle richieste
          per finalità di sicurezza e diagnosi (max 30 giorni).
        </p>
      </Section>

      <Section title="3. Perché trattiamo i tuoi dati (finalità e base giuridica)">
        <ul>
          <li>
            <strong>Risposta a richieste di contatto / acquisto</strong> — base
            giuridica: misure precontrattuali e legittimo interesse (art. 6.1.b
            e 6.1.f GDPR).
          </li>
          <li>
            <strong>Funzionalità del sito</strong> (preferiti, navigazione,
            area admin) — base giuridica: legittimo interesse a fornire un
            servizio funzionante (art. 6.1.f GDPR).
          </li>
          <li>
            <strong>Sicurezza informatica</strong> (log, rate limiting,
            protezione anti-spam) — base giuridica: legittimo interesse alla
            protezione del sito (art. 6.1.f GDPR).
          </li>
        </ul>
        <p>
          <strong>Non facciamo profilazione, non vendiamo i tuoi dati, non
          usiamo cookie di marketing o di terze parti.</strong>
        </p>
      </Section>

      <Section title="4. Per quanto tempo conserviamo i dati">
        <ul>
          <li>
            <strong>Messaggi di contatto</strong>: fino a 24 mesi
            dall&apos;ultima interazione, salvo necessità di conservazione più
            lunga per obblighi di legge.
          </li>
          <li>
            <strong>Log tecnici server</strong>: massimo 30 giorni.
          </li>
          <li>
            <strong>Dati in localStorage</strong>: restano nel tuo browser
            finché non li cancelli tu (impostazioni browser &gt; cancella dati
            sito).
          </li>
        </ul>
      </Section>

      <Section title="5. A chi vengono comunicati">
        <p>
          I dati non vengono ceduti a terzi. I soli soggetti che possono
          accedervi tecnicamente sono:
        </p>
        <ul>
          <li>
            il fornitore di hosting su cui gira il sito (server europeo);
          </li>
          <li>
            il provider del servizio email usato per ricevere i messaggi.
          </li>
        </ul>
        <p>
          Entrambi agiscono come <em>responsabili del trattamento</em> ai sensi
          dell&apos;art. 28 GDPR.
        </p>
      </Section>

      <Section title="6. I tuoi diritti">
        <p>In qualsiasi momento puoi:</p>
        <ul>
          <li>accedere ai tuoi dati (art. 15 GDPR);</li>
          <li>chiederne la rettifica (art. 16);</li>
          <li>chiederne la cancellazione (art. 17);</li>
          <li>limitarne il trattamento (art. 18);</li>
          <li>opporti al trattamento (art. 21);</li>
          <li>ricevere i dati in formato portabile (art. 20).</li>
        </ul>
        <p>
          Per esercitarli scrivi a{" "}
          <a
            href="mailto:info@nerdnostalgia.it"
            className="text-lilac-deep font-semibold hover:underline"
          >
            info@nerdnostalgia.it
          </a>
          . Hai inoltre diritto a presentare reclamo al{" "}
          <a
            href="https://www.garanteprivacy.it"
            target="_blank"
            rel="noopener noreferrer"
            className="text-lilac-deep font-semibold hover:underline"
          >
            Garante per la protezione dei dati personali
          </a>
          .
        </p>
      </Section>

      <Section title="7. Cookie e storage locale">
        <p>
          Per dettagli su quali dati tecnici vengono salvati nel tuo browser,
          consulta la{" "}
          <Link
            href="/cookie-policy"
            className="text-lilac-deep font-semibold hover:underline"
          >
            Cookie Policy
          </Link>
          .
        </p>
      </Section>

      <Section title="8. Modifiche a questa informativa">
        <p>
          Eventuali aggiornamenti saranno pubblicati su questa pagina con la
          relativa data di revisione.
        </p>
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
      <div className="text-ink-soft text-base leading-relaxed space-y-3 [&_ul]:list-disc [&_ul]:pl-6 [&_ul]:space-y-1 [&_a]:underline-offset-2">
        {children}
      </div>
    </section>
  );
}
