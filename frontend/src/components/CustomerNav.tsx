"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { AlertBell } from "@/components/AlertBell";
import { WishlistNavLink } from "@/components/WishlistNavLink";
import { useCustomer } from "@/lib/customer-auth";
import { useWishlist } from "@/lib/useWishlist";

/* Zona cliente dell'header.
 *
 * Da sloggato restano i bottoni sciolti: senza un profilo non c'è niente
 * sotto cui raccoglierli, e "Accedi" deve restare la cosa più visibile.
 *
 * Da loggato Preferiti e Avvisami finiscono dentro il menù del profilo:
 * sono roba sua, e in una barra che tiene già ricerca, carrello e
 * "Contattami" ogni icona in meno è spazio guadagnato dove serve.
 *
 * Il carrello resta fuori in entrambi i casi: è la strada per comprare,
 * non un'impostazione del profilo. */

export function CustomerNav({
  variant = "desktop",
}: {
  variant?: "desktop" | "mobile";
}) {
  const { user, loading } = useCustomer();

  // Finché la sessione non è letta non disegniamo niente: far lampeggiare
  // "Accedi" a chi è già dentro sembra un logout avvenuto.
  if (loading) return null;

  if (!user) {
    return (
      <>
        <AlertBell variant={variant} />
        <WishlistNavLink variant={variant} />
        <Link
          href="/accedi"
          className={
            variant === "mobile"
              ? "btn btn-ghost text-xs px-2.5 py-1.5"
              : "btn btn-ghost text-sm inline-flex items-center gap-1.5"
          }
        >
          {variant === "mobile" ? (
            "Accedi"
          ) : (
            <>
              <span aria-hidden="true">👤</span>
              <span>Accedi</span>
            </>
          )}
        </Link>
      </>
    );
  }

  return <MenuProfilo nome={user.full_name?.split(" ")[0] || "Profilo"} variant={variant} />;
}

function MenuProfilo({
  nome,
  variant,
}: {
  nome: string;
  variant: "desktop" | "mobile";
}) {
  const router = useRouter();
  const { logout } = useCustomer();
  const { count, hydrated } = useWishlist();
  const [aperto, setAperto] = useState(false);
  const [campanella, setCampanella] = useState(false);
  const box = useRef<HTMLDivElement>(null);

  // Chiusura al clic fuori e con Esc: un menù che resta aperto mentre
  // navighi copre quello che stai guardando.
  useEffect(() => {
    if (!aperto) return;
    function fuori(e: MouseEvent) {
      if (box.current && !box.current.contains(e.target as Node)) {
        setAperto(false);
      }
    }
    function esc(e: KeyboardEvent) {
      if (e.key === "Escape") setAperto(false);
    }
    document.addEventListener("mousedown", fuori);
    document.addEventListener("keydown", esc);
    return () => {
      document.removeEventListener("mousedown", fuori);
      document.removeEventListener("keydown", esc);
    };
  }, [aperto]);

  function vai(href: string) {
    setAperto(false);
    router.push(href);
  }

  return (
    <div className="relative" ref={box}>
      <button
        type="button"
        onClick={() => setAperto((v) => !v)}
        aria-expanded={aperto}
        aria-haspopup="menu"
        aria-label="Il tuo profilo"
        className={
          variant === "mobile"
            ? "btn btn-ghost text-xs px-2.5 py-1.5 relative"
            : "btn btn-ghost text-sm inline-flex items-center gap-1.5"
        }
      >
        <span aria-hidden="true">👤</span>
        {variant === "desktop" && <span>{nome}</span>}
        <span aria-hidden="true" className="text-[10px] opacity-70">
          ▾
        </span>
        {/* Il pallino dei preferiti deve restare visibile a menù chiuso,
            se no chiuderli dentro la tendina vuol dire nasconderli. */}
        {hydrated && count > 0 && (
          <span className="absolute -top-1 -right-1 min-w-4 h-4 px-1 rounded-full bg-pink-deep text-white text-[9px] font-bold inline-flex items-center justify-center">
            {count}
          </span>
        )}
      </button>

      {aperto && (
        <div
          role="menu"
          className="absolute right-0 top-full mt-2 z-50 w-56 rounded-2xl bg-white shadow-xl ring-1 ring-ink/10 py-2"
        >
          <Voce onClick={() => vai("/profilo")}>👤 Il tuo profilo</Voce>
          <Voce onClick={() => vai("/preferiti")}>
            ♥ Preferiti
            {hydrated && count > 0 && (
              <span className="ml-auto inline-flex items-center justify-center min-w-5 h-5 px-1 rounded-full bg-pink-deep text-white text-[10px] font-bold">
                {count}
              </span>
            )}
          </Voce>
          <Voce
            onClick={() => {
              setAperto(false);
              setCampanella(true);
            }}
          >
            🔔 Avvisami dei nuovi arrivi
          </Voce>

          <div className="my-1.5 border-t border-ink/10" />

          <Voce
            onClick={() => {
              setAperto(false);
              logout();
              router.push("/");
            }}
          >
            ↩ Esci
          </Voce>
        </div>
      )}

      {/* Fuori dal pannello di proposito: dentro, chiudere il menù
          smonterebbe il dialog un istante dopo averlo aperto. */}
      <AlertBell open={campanella} onOpenChange={setCampanella} />
    </div>
  );
}

function Voce({
  children,
  onClick,
}: {
  children: React.ReactNode;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      role="menuitem"
      onClick={onClick}
      className="w-full flex items-center gap-2 px-4 py-2 text-sm text-left text-ink hover:bg-lilac-soft transition-colors"
    >
      {children}
    </button>
  );
}
