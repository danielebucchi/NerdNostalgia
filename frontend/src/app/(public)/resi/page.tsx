import type { Metadata } from "next";
import Link from "next/link";
import { SITE_NAME } from "@/lib/seo";

export const metadata: Metadata = {
  title: "Resi e diritto di recesso",
  description: `Come restituire un articolo acquistato su ${SITE_NAME}: 14 giorni per il recesso, rimborso entro 14 giorni.`,
  alternates: { canonical: "/resi" },
};

const LAST_UPDATE = "25 novembre 2026";
const EMAIL = "nerdnostalgiaita@gmail.com";

/* Politica di reso. Serve ai clienti e a Google Merchant Center, che la
 * chiede per mostrare i prodotti su Google Shopping: le condizioni scritte
 * qui (14 giorni, ritorno a carico del cliente) devono restare uguali a
 * quelle impostate in Merchant Center. */
export default function ResiPage() {
  const mail = (
    <a href={`mailto:${EMAIL}`} className="text-lilac-deep font-semibold hover:underline">
      {EMAIL}
    </a>
  );
  return (
    <article className="prose-nn max-w-3xl mx-auto">
      <Link href="/" className="btn btn-ghost text-sm mb-8">
        ← Catalogo
      </Link>

      <h1 className="display text-3xl sm:text-4xl text-ink leading-tight mb-2">
        Resi e diritto di recesso
      </h1>
      <p className="text-ink-soft text-sm mb-8">Ultimo aggiornamento: {LAST_UPDATE}</p>

      <Section title="1. Quanto tempo ha">
        <p>
          Se ha acquistato sul sito <strong>{SITE_NAME}</strong>, può recedere dall&apos;acquisto{" "}
          <strong>entro 14 giorni</strong> dal giorno in cui ha ricevuto l&apos;articolo, senza dover
          dare spiegazioni (artt. 52 e seguenti del Codice del Consumo, D.Lgs. 206/2005).
        </p>
        <p>
          Il diritto di recesso vale per gli acquisti fatti da consumatori. Per gli articoli comprati
          su altre piattaforme (eBay, Vinted, CardTrader) valgono le regole di quella piattaforma.
        </p>
      </Section>

      <Section title="2. Come restituire un articolo">
        <ul>
          <li>
            Ci scriva a {mail} indicando il numero dell&apos;ordine e l&apos;articolo da restituire,
            entro i 14 giorni.
          </li>
          <li>
            Le risponderemo con l&apos;indirizzo a cui spedire il reso. Spedisca l&apos;articolo entro
            14 giorni dalla Sua comunicazione.
          </li>
          <li>
            L&apos;articolo deve tornare nelle stesse condizioni in cui l&apos;ha ricevuto, ben
            protetto: per le carte collezionabili, in bustina e con un rinforzo rigido.
          </li>
        </ul>
      </Section>

      <Section title="3. Spese di restituzione">
        <p>
          Le spese per spedire indietro l&apos;articolo sono <strong>a Suo carico</strong>. Le
          consigliamo una spedizione tracciata: fino a quando il pacco non ci arriva, il rischio
          del trasporto resta a carico di chi spedisce.
        </p>
        <p>
          Se l&apos;articolo è arrivato <strong>danneggiato, difettoso o diverso dalla descrizione</strong>,
          ci scriva con qualche foto: in questo caso la spedizione di ritorno la paghiamo noi.
        </p>
      </Section>

      <Section title="4. Rimborso">
        <p>
          Rimborsiamo il prezzo dell&apos;articolo e le spese di spedizione dell&apos;ordine (nella
          misura della spedizione standard) <strong>entro 14 giorni</strong> da quando ci ha
          comunicato il recesso, con lo stesso metodo di pagamento usato per l&apos;acquisto. Possiamo
          attendere di aver ricevuto l&apos;articolo, o la prova che l&apos;ha spedito, prima di
          rimborsare.
        </p>
        <p>
          Se l&apos;articolo torna danneggiato o in condizioni peggiori di come è partito per un uso
          che va oltre quello necessario a verificarlo, il rimborso può essere ridotto della perdita
          di valore.
        </p>
      </Section>

      <Section title="5. Cambi">
        <p>
          Gli articoli sono pezzi unici o quasi: se preferisce un altro articolo invece del
          rimborso, ci scriva e vediamo insieme cosa è disponibile.
        </p>
      </Section>

      <Section title="6. Garanzia">
        <p>
          Oltre al recesso, sugli articoli venduti a consumatori vale la garanzia legale di
          conformità prevista dal Codice del Consumo. Per gli articoli usati la descrizione e le foto
          indicano le condizioni reali del pezzo, che fanno parte di ciò che ha acquistato.
        </p>
      </Section>

      <Section title="7. Contatti">
        <p>Per qualsiasi dubbio su un reso: {mail}.</p>
      </Section>
    </article>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mb-8">
      <h2 className="display text-xl sm:text-2xl text-ink mb-3">{title}</h2>
      <div className="text-ink-soft text-base leading-relaxed space-y-3 [&_ul]:list-disc [&_ul]:pl-6 [&_ul]:space-y-1 [&_a]:underline-offset-2">
        {children}
      </div>
    </section>
  );
}
