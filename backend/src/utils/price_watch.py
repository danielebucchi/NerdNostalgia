"""
Rivalutazione settimanale delle carte in vendita.

I prezzi di mercato invecchiano: una carta messa a 3 euro un mese fa puo'
valerne 6 adesso (o 1). Una volta a settimana si rivalutano le carte in
vendita (CardTrader + venduti eBay, come il pulsante Valuta) e si segnalano
per email quelle il cui suggerito si e' allontanato dal prezzo a cui le
stai vendendo.

I prezzi di vendita non si toccano: la valutazione aggiorna solo i prezzi
di mercato e il suggerito; cambiare il prezzo resta una scelta tua.
"""
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List

from sqlalchemy.orm import Session

from models.db import ArticleStatus, PersonalCard, PersonalCardStatus
from utils import card_listing as cl
from utils import card_pricing as cp

LOGGER = logging.getLogger("price_watch")

GIORNI = 7            # rivaluta solo le carte valutate piu' di una settimana fa
SOGLIA = 0.25         # scostamento relativo da segnalare (25%)
MINIMO_EURO = 0.50    # sotto i 50 centesimi di differenza non vale una email
PAUSA = 0.5           # tra una carta e l'altra: CardTrader ed eBay hanno limiti


def _in_vendita(card: PersonalCard) -> bool:
    sul_sito = card.article is not None and card.article.status == ArticleStatus.PUBLISHED
    return bool(sul_sito or card.cardtrader_product_id or card.ebay_listing_id)


def da_rivalutare(db: Session) -> List[PersonalCard]:
    limite = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=GIORNI)
    carte = (db.query(PersonalCard)
             .filter(PersonalCard.status.notin_([PersonalCardStatus.SOLD, PersonalCardStatus.ARCHIVED]))
             .all())
    return [c for c in carte
            if _in_vendita(c) and (c.prices_updated_at is None or c.prices_updated_at < limite)]


def run(db: Session, pausa: float = PAUSA) -> Dict[str, object]:
    segnalate: List[dict] = []
    errori = 0
    carte = da_rivalutare(db)
    for card in carte:
        prima = float(card.list_price or card.estimated_value or 0)
        mercato_prima = float(card.estimated_value or 0)
        valutata_il = card.prices_updated_at
        try:
            cp.price_card(card)
            db.commit()
        except Exception as exc:  # noqa: BLE001 — una carta non ferma le altre
            db.rollback()
            errori += 1
            LOGGER.warning("Rivalutazione carta %s fallita: %s", card.id, exc)
            continue
        dopo = float(card.estimated_value or 0)
        if dopo > 0:
            from models.db import CardPriceHistory
            if (mercato_prima > 0 and valutata_il
                    and not db.query(CardPriceHistory).filter_by(card_id=card.id).first()):
                # La prima volta si salva anche il valore di prima: da subito
                # c'e' un confronto (le carte salite, rubrica del venerdi').
                db.add(CardPriceHistory(card_id=card.id, value=mercato_prima, recorded_at=valutata_il))
            db.add(CardPriceHistory(card_id=card.id, value=dopo, recorded_at=datetime.now()))
            db.commit()
        if prima > 0 and dopo > 0 and abs(dopo - prima) >= MINIMO_EURO and abs(dopo - prima) / prima >= SOGLIA:
            segnalate.append({"card_id": card.id, "nome": cl.nome_vetrina(card),
                              "prezzo": prima, "suggerito": dopo})
        if pausa:
            time.sleep(pausa)
    if segnalate:
        _avvisa(segnalate)
    LOGGER.info("Rivalutate %d carte, %d da guardare, %d errori", len(carte), len(segnalate), errori)
    return {"rivalutate": len(carte), "segnalate": segnalate, "errori": errori}


def _avvisa(segnalate: List[dict]) -> None:
    from utils.email import _config, send_email
    righe = []
    for s in sorted(segnalate, key=lambda s: -abs(s["suggerito"] - s["prezzo"]) / s["prezzo"]):
        delta = (s["suggerito"] - s["prezzo"]) / s["prezzo"] * 100
        righe.append(f"- {s['nome']}: in vendita a {s['prezzo']:.2f} €, il mercato ora dice "
                     f"{s['suggerito']:.2f} € ({delta:+.0f}%)")
    send_email(
        to=_config()["to_admin"],
        subject=f"Prezzi da rivedere: {len(segnalate)} carte",
        text_body="Rivalutazione settimanale delle carte in vendita. I prezzi non sono "
                  "stati cambiati: se vuoi, aggiornali dallo scanner.\n\n" + "\n".join(righe),
    )
