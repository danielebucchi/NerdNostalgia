import Link from "next/link";
import { LogoImage } from "@/components/LogoImage";
import { WishlistNavLink } from "@/components/WishlistNavLink";

const TOPBAR_MESSAGES = [
  "Compro · Vendo · Scambio",
  "Videogiochi, carte Pokémon, Funko & nerderie",
  "Spedizioni in tutta Italia",
];

export function Topbar() {
  return (
    <div className="topbar overflow-hidden">
      {/* Su mobile (<sm): scorrimento orizzontale marquee */}
      <div className="sm:hidden marquee">
        <div className="marquee-track">
          {[...TOPBAR_MESSAGES, ...TOPBAR_MESSAGES].map((m, i) => (
            <span key={i} className="marquee-item">
              <span className="opacity-60">✦</span> {m}
            </span>
          ))}
        </div>
      </div>
      {/* Da sm in su: testo statico */}
      <span className="hidden sm:inline sparkle">
        {TOPBAR_MESSAGES.join(" · ")}
      </span>
    </div>
  );
}

export function Header() {
  return (
    <header className="site-header">
      <div className="mx-auto max-w-6xl px-4 sm:px-6 py-3 sm:py-4 flex items-center justify-between gap-3">
        <Link
          href="/"
          className="flex items-center gap-2 sm:gap-3 min-w-0"
          aria-label="NerdNostalgia home"
        >
          <LogoImage
            size={48}
            alt="NerdNostalgia"
            className="w-10 h-10 sm:w-12 sm:h-12 rounded-full ring-1 ring-ink/10 object-cover bg-white shadow-soft flex-shrink-0"
          />
          <span className="display text-lg sm:text-2xl md:text-3xl text-ink leading-none truncate">
            Nerd<span className="text-lilac-deep">.</span>Nostalgia
          </span>
        </Link>

        <nav className="hidden md:flex items-center gap-2 flex-shrink-0">
          <Link href="/" className="btn btn-ghost text-sm">Catalogo</Link>
          <Link href="/cerco-compro" className="btn btn-ghost text-sm">Cerco/Compro</Link>
          <WishlistNavLink variant="desktop" />
          <Link href="/contatti" className="btn btn-primary text-sm">Contattami</Link>
        </nav>

        <nav className="flex md:hidden gap-1.5 flex-shrink-0">
          <WishlistNavLink variant="mobile" />
          <Link
            href="/cerco-compro"
            className="btn btn-ghost text-xs px-2.5 py-1.5"
            aria-label="Cerco / Compro"
          >
            🔍
          </Link>
          <Link
            href="/contatti"
            className="btn btn-primary text-xs px-3 py-1.5"
          >
            Scrivi
          </Link>
        </nav>
      </div>
    </header>
  );
}

export function Footer() {
  return (
    <footer className="mt-16 sm:mt-20 border-t border-ink/15 bg-white/40 backdrop-blur">
      <div className="mx-auto max-w-6xl px-4 sm:px-6 py-8 sm:py-10 grid gap-6 sm:gap-8 sm:grid-cols-3">
        <div>
          <h3 className="display text-lg sm:text-xl text-ink">Nerd.Nostalgia</h3>
          <p className="text-ink-soft mt-2 text-sm leading-relaxed">
            Un piccolo angolo nerd dove ridare casa a videogiochi, carte e gadget
            che hanno fatto la storia (almeno la mia).
          </p>
        </div>
        <div>
          <h4 className="display text-base text-ink mb-2">Categorie</h4>
          <ul className="text-sm text-ink-soft space-y-1">
            <li>Videogiochi</li>
            <li>Carte Pokémon</li>
            <li>Funko Pop</li>
            <li>Console e accessori</li>
          </ul>
        </div>
        <div>
          <h4 className="display text-base text-ink mb-2">Contatti</h4>
          <p className="text-sm text-ink-soft">
            Scrivimi per qualsiasi richiesta o per propormi un acquisto.
          </p>
          <a
            href="mailto:info@nerdnostalgia.it"
            className="text-sm text-lilac-deep font-semibold mt-2 inline-block hover:underline"
          >
            info@nerdnostalgia.it
          </a>
        </div>
      </div>
      <div className="text-center text-xs text-ink-soft pb-6 px-4 space-y-2">
        <nav className="flex flex-wrap items-center justify-center gap-x-4 gap-y-1">
          <Link href="/privacy" className="hover:text-lilac-deep hover:underline">
            Privacy
          </Link>
          <span aria-hidden="true" className="opacity-40">·</span>
          <Link href="/cookie-policy" className="hover:text-lilac-deep hover:underline">
            Cookie Policy
          </Link>
        </nav>
        <div>
          © {new Date().getFullYear()} NerdNostalgia · made with{" "}
          <span className="text-pink-deep">♥</span>
        </div>
      </div>
    </footer>
  );
}
