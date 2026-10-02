import type { Metadata } from "next";
import Link from "next/link";
import { SITE_NAME } from "@/lib/seo";

export const metadata: Metadata = {
  title: "Informativa Privacy",
  description: `Informativa sul trattamento dei dati personali — ${SITE_NAME}`,
  alternates: { canonical: "/privacy" },
  robots: { index: true, follow: false },
};

const LAST_UPDATE = "2 ottobre 2026";

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
            href="mailto:nerdnostalgiaita@gmail.com"
            className="text-lilac-deep font-semibold hover:underline"
          >
            nerdnostalgiaita@gmail.com
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
          <strong>Se ci scrivi</strong>, dal form di contatto o di richiesta
          acquisto:
        </p>
        <ul>
          <li>Nome (o nickname)</li>
          <li>Indirizzo email</li>
          <li>Numero di telefono (opzionale)</li>
          <li>Testo del messaggio</li>
          <li>Articolo a cui la richiesta è collegata (se applicabile)</li>
        </ul>

        <p>
          <strong>Se compri</strong>, per preparare il pacco e farlo arrivare:
        </p>
        <ul>
          <li>Nome e cognome</li>
          <li>Indirizzo email</li>
          <li>
            Numero di telefono — facoltativo, ma lo chiediamo perché il
            corriere lo usa quando non trova nessuno a casa
          </li>
          <li>
            Indirizzo di spedizione (via, città, CAP, provincia), oppure il
            punto di ritiro InPost che hai scelto sulla mappa
          </li>
          <li>Articoli acquistati, importi e stato dell&apos;ordine</li>
          <li>
            Codice di tracciamento della spedizione, quando il pacco parte
          </li>
        </ul>
        <p>
          <strong>I dati della carta non passano da noi e non li vediamo
          mai.</strong> Il pagamento avviene sulle pagine di PayPal (o di
          Stripe, quando attivo): a noi torna solo l&apos;esito, l&apos;importo
          e il codice della transazione.
        </p>

        <p>
          <strong>Se ti registri</strong>, per darti un profilo con i tuoi
          ordini:
        </p>
        <ul>
          <li>Indirizzo email (è anche il nome con cui accedi)</li>
          <li>
            Password, salvata <em>cifrata con hash</em>: nemmeno noi possiamo
            leggerla, e se la dimentichi non possiamo dirtela
          </li>
          <li>Nome (facoltativo)</li>
          <li>
            Se hai accettato le email promozionali, e la data in cui hai fatto
            — o ritirato — quella scelta
          </li>
          <li>
            Gli ordini fatti in precedenza con la stessa email, che vengono
            collegati al profilo così li ritrovi nello storico
          </li>
        </ul>

        <p>
          <strong>Se lasci una recensione</strong>: il voto, il testo che
          scrivi e il nome indicato nell&apos;ordine. Vedi la sezione 6.
        </p>

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
            Contenuto del <em>carrello</em> (ID degli articoli e quantità)
          </li>
          <li>
            Token di sessione (JWT) di chi ha fatto l&apos;accesso — il tuo, se
            hai un profilo cliente, oppure quello dell&apos;area
            amministrativa. Serve a restare dentro fra una pagina e
            l&apos;altra; esce dal browser solo come prova d&apos;identità
            nelle chiamate al sito
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
            <strong>Gestione dell&apos;ordine</strong> (incasso, preparazione,
            spedizione, assistenza, eventuale reso) — base giuridica:
            esecuzione del contratto che hai concluso acquistando (art. 6.1.b
            GDPR). Questi dati sono necessari: senza, l&apos;ordine non si può
            evadere.
          </li>
          <li>
            <strong>Obblighi fiscali e contabili</strong> sulle vendite — base
            giuridica: obbligo di legge (art. 6.1.c GDPR).
          </li>
          <li>
            <strong>Account cliente</strong> (accesso, storico ordini,
            tracking) — base giuridica: esecuzione del contratto di servizio
            che accetti registrandoti (art. 6.1.b GDPR).
          </li>
          <li>
            <strong>Email promozionali</strong> — base giuridica:{" "}
            <strong>il tuo consenso</strong> (art. 6.1.a GDPR), che è
            facoltativo, separato dalla registrazione e revocabile in
            qualsiasi momento. Vedi la sezione 7.
          </li>
          <li>
            <strong>Pubblicazione delle recensioni</strong> — base giuridica:
            il consenso che presti scegliendo di scriverne una, dato che
            lasciarla è una tua libera scelta (art. 6.1.a GDPR).
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
            <strong>Dati degli ordini</strong>: 10 anni, come impone la legge
            per le scritture contabili (art. 2220 Codice Civile). È un termine
            che non possiamo accorciare, nemmeno se lo chiedi: per quel periodo
            la conservazione è un obbligo, non una nostra scelta.
          </li>
          <li>
            <strong>Account cliente</strong>: finché il profilo esiste. Se
            chiedi di cancellarlo lo eliminiamo, ma i dati dell&apos;ordine
            restano per il termine qui sopra.
          </li>
          <li>
            <strong>Scelta sulle email promozionali</strong>: teniamo traccia
            anche della revoca, e della sua data. Serve a dimostrare che
            abbiamo smesso di scriverti quando ce l&apos;hai chiesto.
          </li>
          <li>
            <strong>Recensioni</strong>: finché restano pubblicate. Se chiedi
            di toglierla, la togliamo.
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
            il provider del servizio email usato per mandare e ricevere i
            messaggi;
          </li>
          <li>
            <strong>PayPal</strong> (e <strong>Stripe</strong>, quando
            attivo), che gestiscono il pagamento sulle loro pagine. Ricevono
            quello che serve a incassare; a noi torna solo l&apos;esito. Sono
            titolari autonomi del trattamento per la parte di pagamento, con
            le loro informative;
          </li>
          <li>
            <strong>InPost</strong>, se scegli il ritiro in un punto di
            raccolta: riceve il punto scelto e i dati necessari alla consegna.
            La mappa dei punti è caricata da InPost e, mentre la usi, vede il
            tuo indirizzo IP;
          </li>
          <li>
            <strong>Il corriere</strong> che porta il pacco, e la piattaforma
            con cui compriamo la spedizione: ricevono nome, indirizzo,
            telefono se l&apos;hai lasciato, ed email per gli avvisi di
            consegna. Senza, il pacco non parte;
          </li>
          <li>
            <strong>Geoapify</strong> (server nell&apos;Unione Europea), che
            riceve solo quello che scrivi nel campo indirizzo del checkout, per
            proporti i suggerimenti di completamento. Non riceve il tuo nome,
            la tua email né l&apos;ordine: solo il testo parziale
            dell&apos;indirizzo mentre lo digiti. Se preferisci evitarlo, puoi
            scrivere l&apos;indirizzo per intero senza scegliere nessun
            suggerimento.
          </li>
        </ul>
        <p>
          Hosting, provider email e Geoapify agiscono come{" "}
          <em>responsabili del trattamento</em> ai sensi dell&apos;art. 28
          GDPR. PayPal, Stripe, InPost e il corriere trattano i dati come
          titolari autonomi, ciascuno secondo la propria informativa.
        </p>
        <p>
          <strong>Trasferimenti fuori dall&apos;Unione Europea</strong>: PayPal
          e Stripe sono società con sede anche negli Stati Uniti e possono
          trattare i dati fuori dallo Spazio Economico Europeo, sulla base
          delle clausole contrattuali standard approvate dalla Commissione
          Europea (art. 46 GDPR) e, dove applicabile, del{" "}
          <em>Data Privacy Framework</em>. Gli altri fornitori operano su
          server nell&apos;Unione Europea.
        </p>
        <p>
          <strong>Non vendiamo i tuoi dati a nessuno</strong> e non li
          cediamo per finalità pubblicitarie di terzi.
        </p>
      </Section>

      <Section title="6. Recensioni pubbliche">
        <p>
          Lasciare una recensione è facoltativo. L&apos;invito ti arriva solo
          se hai comprato davvero e l&apos;ordine è stato completato: non si
          può recensire senza aver ricevuto un pacco.
        </p>
        <p>
          Se decidi di scriverne una, vengono pubblicati sul sito{" "}
          <strong>il nome indicato nell&apos;ordine, il voto e il testo</strong>.
          Non vengono pubblicati l&apos;email, l&apos;indirizzo, il telefono,
          né cosa hai comprato. Tienine conto quando scegli cosa scrivere: la
          recensione è visibile a chiunque, e indicizzabile dai motori di
          ricerca.
        </p>
        <p>
          Le recensioni passano da un controllo prima di comparire. Puoi
          chiedere in qualsiasi momento di modificarla o toglierla scrivendo
          all&apos;indirizzo in fondo.
        </p>
      </Section>

      <Section title="7. Email: quali ricevi e come smettere">
        <p>
          <strong>Email legate ai tuoi ordini</strong> — conferma,
          spedizione, codice di tracciamento. Non sono pubblicità: servono a
          farti avere il pacco, fanno parte del contratto e arrivano anche se
          non hai dato nessun consenso promozionale.
        </p>
        <p>
          <strong>Email promozionali</strong> — solo se hai spuntato la
          casella apposita, che è separata dalla registrazione e parte vuota.
          Puoi ritirare il consenso quando vuoi, senza dare spiegazioni e
          senza che questo tocchi i tuoi ordini:
        </p>
        <ul>
          <li>
            dal link <em>Disiscriviti</em> in fondo a ogni email promozionale,
            che funziona senza bisogno di accedere;
          </li>
          <li>
            dalla spunta nel tuo{" "}
            <Link
              href="/profilo"
              className="text-lilac-deep font-semibold hover:underline"
            >
              profilo
            </Link>
            ;
          </li>
          <li>scrivendoci, e ti togliamo noi dalla lista.</li>
        </ul>
        <p>
          Ritirare il consenso vale da quel momento in poi e non rende
          illecito quello che è stato mandato prima (art. 7.3 GDPR).
        </p>
      </Section>

      <Section title="8. I tuoi diritti">
        <p>In qualsiasi momento puoi:</p>
        <ul>
          <li>accedere ai tuoi dati (art. 15 GDPR);</li>
          <li>chiederne la rettifica (art. 16);</li>
          <li>chiederne la cancellazione (art. 17);</li>
          <li>limitarne il trattamento (art. 18);</li>
          <li>opporti al trattamento (art. 21);</li>
          <li>ricevere i dati in formato portabile (art. 20);</li>
          <li>
            revocare in qualsiasi momento un consenso che hai dato, con la
            stessa facilità con cui l&apos;hai prestato (art. 7.3).
          </li>
        </ul>
        <p>
          Per esercitarli scrivi a{" "}
          <a
            href="mailto:nerdnostalgiaita@gmail.com"
            className="text-lilac-deep font-semibold hover:underline"
          >
            nerdnostalgiaita@gmail.com
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

      <Section title="9. Cookie e storage locale">
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

      <Section title="10. Modifiche a questa informativa">
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
