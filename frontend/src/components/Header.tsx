import Link from "next/link";
import { LogoImage } from "@/components/LogoImage";

export function Topbar() {
  return (
    <div className="topbar">
      <span className="sparkle">
        Compro · Vendo · Scambio · Videogiochi, carte Pokémon e nerderie · Spedizioni in tutta Italia
      </span>
    </div>
  );
}

export function Header() {
  return (
    <header className="site-header">
      <div className="mx-auto max-w-6xl px-6 py-4 flex items-center justify-between gap-4">
        <Link href="/" className="flex items-center gap-3" aria-label="NerdNostalgia home">
          <LogoImage
            size={48}
            alt="NerdNostalgia"
            className="w-12 h-12 rounded-full ring-1 ring-ink/10 object-cover bg-white shadow-soft"
          />
          <span className="display text-2xl sm:text-3xl text-ink leading-none">
            Nerd<span className="text-lilac-deep">.</span>Nostalgia
          </span>
        </Link>

        <nav className="hidden md:flex items-center gap-2">
          <Link href="/" className="btn btn-ghost text-sm">Catalogo</Link>
          <Link href="/cerco-compro" className="btn btn-ghost text-sm">Cerco/Compro</Link>
          <Link href="/contatti" className="btn btn-primary text-sm">Contattami</Link>
        </nav>

        <nav className="flex md:hidden gap-2">
          <Link href="/" className="btn btn-ghost text-xs px-3 py-2">Catalogo</Link>
          <Link href="/cerco-compro" className="btn btn-ghost text-xs px-3 py-2">Cerco</Link>
          <Link href="/contatti" className="btn btn-primary text-xs px-3 py-2">Scrivi</Link>
        </nav>
      </div>
    </header>
  );
}

export function Footer() {
  return (
    <footer className="mt-20 border-t-2 border-ink/20 bg-cream/60 backdrop-blur">
      <div className="mx-auto max-w-6xl px-6 py-10 grid gap-8 sm:grid-cols-3">
        <div>
          <h3 className="display text-xl text-ink">Nerd.Nostalgia</h3>
          <p className="text-ink-soft mt-2 text-sm leading-relaxed">
            Un piccolo angolo nerd dove ridare casa a videogiochi, carte e gadget che
            hanno fatto la storia (almeno la mia).
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
          <p className="text-sm text-pink-deep font-semibold mt-2">
            info@nerdnostalgia.it
          </p>
        </div>
      </div>
      <div className="text-center text-xs text-ink-soft pb-6">
        © {new Date().getFullYear()} NerdNostalgia · made with <span className="text-pink-deep">♥</span>
      </div>
    </footer>
  );
}
