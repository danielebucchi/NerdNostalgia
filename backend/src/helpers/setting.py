"""
Helper per la tabella settings (config runtime chiave/valore).

La SPEC delle chiavi conosciute (default, visibilita' pubblica, label per
l'admin UI) vive qui: e' il posto unico da toccare per aggiungere una chiave.
"""
from typing import Dict, Optional

from fastapi import Depends
from sqlalchemy.orm import Session

from models.db import Setting
from utils.session import get_db

# Chiavi note. `public: True` = esposta su GET /api/settings/public (letta dal
# frontend senza auth). Le altre sono visibili solo all'admin.
SETTINGS_SPEC: Dict[str, dict] = {
    "paypal_me": {
        "default": "",
        "public": True,
        "label": "Handle PayPal.me",
        "help": "Solo lo username (es. DanieleBucchi). Vuoto = usa il valore "
                "di build NEXT_PUBLIC_PAYPAL_ME (fallback).",
    },
    "payments_enabled": {
        "default": "",
        "public": True,
        "label": "Pagamenti attivi (carrello + PayPal checkout)",
        "help": "true/false. Vuoto = usa il valore di build "
                "NEXT_PUBLIC_PAYMENTS_ENABLED (fallback).",
    },
    "contact_whatsapp": {
        "default": "",
        "public": True,
        "label": "WhatsApp pubblico",
        "help": "Numero per il bottone WhatsApp sulla pagina articolo "
                "(es. 3331234567). Vuoto = bottone nascosto.",
    },
    "contact_email": {
        "default": "nerdnostalgiaita@gmail.com",
        "public": True,
        "label": "Email di contatto",
        "help": "Mostrata nelle pagine pubbliche (privacy, contatti).",
    },
    "hand_exchange_cap_prefixes": {
        "default": "56,57",
        "public": True,
        "label": "Prefissi CAP consegna a mano",
        "help": "Prime 2 cifre dei CAP abilitati, separate da virgola "
                "(56=Pisa, 57=Livorno).",
    },
    "hand_exchange_cities": {
        "default": "Livorno/Pisa",
        "public": True,
        "label": "Zone consegna a mano (testo)",
        "help": "Testo mostrato nel badge sull'articolo e nel carrello.",
    },
    "article_description_footer": {
        "default": "Spedizione veloce",
        "public": True,
        "label": "Riga finale descrizione articolo",
        "help": "Mostrata in fondo alla descrizione di OGNI articolo sul "
                "catalogo (non salvata negli articoli: cambiarla qui li "
                "aggiorna tutti). Vuoto per nasconderla.",
    },
    "marketplace_footer_vinted": {
        "default": "Spedizione Veloce\nAltri pezzi su www.nerdnostalgia.store",
        "public": False,
        "label": "Footer descrizione Vinted",
        "help": "Aggiunto in fondo alla descrizione copiata per Vinted.",
    },
    "ebay_fulfillment_policy_id": {
        "default": "",
        "public": False,
        "label": "eBay — Policy di spedizione (ID)",
        "help": "ID della business policy di spedizione (da GET /api/ebay/policies). "
                "Obbligatoria per pubblicare.",
    },
    "ebay_payment_policy_id": {
        "default": "",
        "public": False,
        "label": "eBay — Policy di pagamento (ID)",
        "help": "ID della business policy di pagamento. Obbligatoria per pubblicare.",
    },
    "ebay_return_policy_id": {
        "default": "",
        "public": False,
        "label": "eBay — Policy di reso (ID)",
        "help": "ID della business policy di reso. Obbligatoria per pubblicare.",
    },
    "ebay_merchant_location_key": {
        "default": "",
        "public": False,
        "label": "eBay — Chiave location magazzino",
        "help": "merchantLocationKey della sede di spedizione (da GET /api/ebay/policies).",
    },
    "ebay_default_category_id": {
        "default": "",
        "public": False,
        "label": "eBay — Categoria predefinita (ID)",
        "help": "Categoria eBay di fallback quando non ne troviamo una migliore "
                "(es. carte collezionabili). Da /api/ebay/category-suggestions.",
    },
    "cardtrader_footer": {
        "default": "Ask For Photos\nMore product on www.nerdnostalgia.store",
        "public": False,
        "label": "Footer descrizione CardTrader",
        "help": "Aggiunto in fondo alla descrizione dell'inserzione CardTrader "
                "(dopo la descrizione dell'articolo). Vuoto = nessun footer.",
    },
    "cardtrader_default_language": {
        "default": "it",  # vendi soprattutto carte in italiano
        "public": False,
        "label": "CardTrader — lingua predefinita carte",
        "help": "Codice lingua CardTrader usato quando non specifichi la "
                "lingua sulla singola carta (en, fr, de, it, pt, es).",
    },
    "cardtrader_default_game_id": {
        "default": "5",  # 5 = Pokémon (default: vendi soprattutto carte Pokémon)
        "public": False,
        "label": "CardTrader — gioco predefinito (game_id)",
        "help": "ID gioco CardTrader usato per l'auto-match dei blueprint "
                "(es. 5 = Pokémon, 1 = Magic). Vuoto = cerca in tutti i giochi "
                "(più lento e ambiguo). Imposta se vendi soprattutto un gioco.",
    },
    "marketplace_footer_ebay": {
        "default": "Spedizione Veloce\nAltri pezzi su www.nerdnostalgia.store",
        "public": False,
        "label": "Footer descrizione eBay",
        "help": "Aggiunto in fondo alla descrizione copiata per eBay.",
    },
}


class SettingHelper:

    def __init__(self, db: Session = Depends(get_db)):
        self.db = db

    def get_value(self, key: str, default: Optional[str] = None) -> str:
        """Valore effettivo: DB se presente e non vuoto, altrimenti il default
        della SPEC (o `default` esplicito per chiavi fuori SPEC)."""
        row = self.db.query(Setting).filter(Setting.key == key).first()
        if row is not None and row.value != "":
            return row.value
        if default is not None:
            return default
        return SETTINGS_SPEC.get(key, {}).get("default", "")

    def get_effective(self, public_only: bool = False) -> Dict[str, str]:
        """Mappa {key: valore effettivo} per tutte le chiavi della SPEC."""
        rows = {s.key: s.value for s in self.db.query(Setting).all()}
        out: Dict[str, str] = {}
        for key, spec in SETTINGS_SPEC.items():
            if public_only and not spec["public"]:
                continue
            value = rows.get(key, "")
            out[key] = value if value != "" else spec["default"]
        return out

    def upsert(self, key: str, value: str) -> None:
        row = self.db.query(Setting).filter(Setting.key == key).first()
        if row is None:
            row = Setting(key=key, value=value)
            self.db.add(row)
        else:
            row.value = value
        self.db.commit()


def get_setting_helper(db: Session = Depends(get_db)) -> SettingHelper:
    return SettingHelper(db=db)
