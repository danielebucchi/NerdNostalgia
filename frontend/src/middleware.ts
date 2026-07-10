import { NextRequest, NextResponse } from "next/server";

/**
 * Sul sottodominio admin.* la root reindirizza a /admin: il sottodominio
 * esiste per avere la PWA admin su un'origin separata dal sito pubblico
 * (Chrome tratta le app per origin — su nerdnostalgia.store l'app pubblica
 * con scope "/" copriva /admin e bloccava la seconda installazione).
 */
export function middleware(req: NextRequest) {
  const host = req.headers.get("host") ?? "";
  if (host.startsWith("admin.") && req.nextUrl.pathname === "/") {
    const url = req.nextUrl.clone();
    url.pathname = "/admin";
    return NextResponse.redirect(url);
  }
  return NextResponse.next();
}

// Solo la root: zero overhead sulle altre rotte.
export const config = { matcher: ["/"] };
