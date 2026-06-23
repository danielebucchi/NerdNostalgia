/**
 * Feature flags compilati nel bundle Next.js al build-time
 * (env var con prefisso NEXT_PUBLIC_).
 *
 * Per riattivare/disattivare nel .env del compose:
 *   NEXT_PUBLIC_PAYMENTS_ENABLED=true   # accende carrello + PayPal + ordini
 *   NEXT_PUBLIC_PAYMENTS_ENABLED=false  # nasconde tutto
 *
 * Poi: docker compose build frontend && docker compose up -d frontend
 */

const PAYMENTS_ENABLED =
  (process.env.NEXT_PUBLIC_PAYMENTS_ENABLED ?? "").toLowerCase() === "true";

/**
 * Master switch per tutta la pipeline di acquisto:
 *   - bottone PayPal sulla pagina articolo
 *   - "Aggiungi al carrello" sulla pagina articolo
 *   - badge "Consegna a mano"
 *   - link Carrello nell'header
 *   - pagina /carrello
 *   - FAB Donazione in basso a destra
 *   - link Ordini nell'admin nav
 *
 * False di default: niente UI di pagamento. L'endpoint backend
 * /api/orders esiste comunque ma e' isolato (no UI lo chiama).
 */
export function paymentsEnabled(): boolean {
  return PAYMENTS_ENABLED;
}
