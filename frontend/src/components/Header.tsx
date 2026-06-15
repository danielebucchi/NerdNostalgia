import Link from "next/link";

export function Header() {
  return (
    <header className="border-b-4 border-retro-accent bg-[#11042a] relative">
      <div className="mx-auto max-w-6xl px-6 py-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <Link href="/" className="block">
          <h1 className="text-retro-sun glow text-2xl sm:text-3xl leading-tight">
            NERD<span className="text-retro-neon">.</span>NOSTALGIA
          </h1>
          <p className="font-retro text-retro-neon text-lg mt-2">
            *** PRESS START — vintage games, pokemon &amp; cose nerd ***
          </p>
        </Link>
        <nav className="flex flex-wrap gap-3 text-sm">
          <Link href="/" className="pixel-btn ghost">CATALOGO</Link>
          <a href="#" className="pixel-btn ghost opacity-60 cursor-not-allowed" aria-disabled>CERCO/COMPRO</a>
          <a href="#" className="pixel-btn opacity-60 cursor-not-allowed" aria-disabled>CONTATTAMI</a>
        </nav>
      </div>
    </header>
  );
}

export function Footer() {
  return (
    <footer className="border-t-4 border-retro-neon mt-16 py-6 text-center font-retro text-lg text-retro-neon">
      <p>&copy; {new Date().getFullYear()} NerdNostalgia — Game Over? Continue?</p>
      <p className="text-retro-sun text-sm mt-1 tracking-wider">
        ★ INSERT COIN TO PLAY ★
      </p>
    </footer>
  );
}
