"""
Spese di spedizione del sito: base + assicurazione facoltativa.

SPEDIZIONE BASE (sul subtotale articoli):
  fino a  25,00 €    →   6,00 €
  25,01 – 249,99 €   →   6,00 € + 4%, con la parte % fra 1,00 € e un tetto
  da     250,00 €    →  gratis

ASSICURAZIONE: +5,70 €, sempre la stessa cifra.
  Attiva di default dai 50 € in su, ma il compratore puo' sempre cambiare
  idea nei due sensi: assicurare un ordine piccolo, o rinunciare su uno
  grande. Dai 250 € e' inclusa nella spedizione gratuita: a quel punto il
  pacco vale troppo per farlo viaggiare scoperto, e il premio ce lo mettiamo
  noi insieme alla spedizione.

Perche' il premio e' una cifra fissa e non una percentuale: fino a 1.500 € di
valore i corrieri applicano un supplemento minimo fisso (~5,68 €), e la
percentuale del 5% scatta solo oltre. Il nostro costo quindi non dipende dal
valore dell'ordine.

Perche' la quota del 4% ha un TETTO: copre l'etichetta (~5,50 €), che costa
uguale per un pacco da 30 € e per uno da 240 €. Senza tetto, su un ordine da
249 € avremmo chiesto 16 € di sola spedizione base.

Se cambiano le tariffe del corriere si ritoccano le costanti qui sotto e le
gemelle in frontend/src/lib/cart.ts (shippingFor). Il totale che fa fede e'
comunque questo: il browser mostra, non decide.
"""
from decimal import ROUND_HALF_UP, Decimal

# Soglia di spedizione gratuita (pubblicizzata sul sito)
FREE_SHIPPING_FROM = Decimal("250.00")
# Da qui in su l'assicurazione e' proposta gia' spuntata (ma si puo' togliere)
INSURED_BY_DEFAULT_FROM = Decimal("50.00")
# Premio assicurativo: cifra fissa, non percentuale (vedi docstring)
INSURANCE_FEE = Decimal("5.70")

BASE_SHIPPING = Decimal("6.00")
PERCENT_BAND_FROM = Decimal("25.00")
PERCENT_RATE = Decimal("0.04")
PERCENT_MIN = Decimal("1.00")
# Tetto alla sola quota percentuale: oltre, staremmo solo gonfiando il prezzo
PERCENT_MAX = Decimal("6.00")

CENTS = Decimal("0.01")


def _round(value: Decimal) -> Decimal:
    return value.quantize(CENTS, rounding=ROUND_HALF_UP)


def base_shipping(subtotal) -> Decimal:
    """Spedizione senza assicurazione."""
    amount = Decimal(subtotal or 0)
    if amount <= 0:
        return BASE_SHIPPING
    if amount >= FREE_SHIPPING_FROM:
        return Decimal("0.00")
    if amount <= PERCENT_BAND_FROM:
        return BASE_SHIPPING
    variable = _round(amount * PERCENT_RATE)
    variable = min(max(variable, PERCENT_MIN), PERCENT_MAX)
    return _round(BASE_SHIPPING + variable)


def insurance_fee(subtotal, insured: bool) -> Decimal:
    """Quanto costa l'assicurazione su questo ordine. Zero se non la vuole, e
    zero sopra la soglia di spedizione gratuita (li' e' inclusa)."""
    if not insured:
        return Decimal("0.00")
    if Decimal(subtotal or 0) >= FREE_SHIPPING_FROM:
        return Decimal("0.00")
    return INSURANCE_FEE


def default_insured(subtotal) -> bool:
    """Assicurazione proposta gia' attiva? Si', dai 50 € in su."""
    return Decimal(subtotal or 0) >= INSURED_BY_DEFAULT_FROM


def resolve_insured(subtotal, insured) -> bool:
    """Scelta effettiva: quella del compratore se l'ha espressa, altrimenti
    il default per quella fascia. Sopra la soglia di gratuita l'assicurazione
    c'e' comunque: un pacco da 250 € non lo mandiamo scoperto."""
    if Decimal(subtotal or 0) >= FREE_SHIPPING_FROM:
        return True
    return default_insured(subtotal) if insured is None else bool(insured)


def calc_shipping(subtotal, insured=None) -> Decimal:
    """Spedizione totale: base + eventuale assicurazione."""
    chosen = resolve_insured(subtotal, insured)
    return base_shipping(subtotal) + insurance_fee(subtotal, chosen)


def missing_for_free_shipping(subtotal) -> Decimal:
    """Quanto manca alla spedizione gratuita. Zero se ci siamo gia'."""
    amount = Decimal(subtotal or 0)
    if amount >= FREE_SHIPPING_FROM:
        return Decimal("0.00")
    return _round(FREE_SHIPPING_FROM - amount)
