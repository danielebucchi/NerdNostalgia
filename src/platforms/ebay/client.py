"""
Client per l'integrazione con eBay API.
"""
from typing import List, Optional
from ebaysdk.trading import Connection as Trading
from ebaysdk.exception import ConnectionError as eBayConnectionError

from src.models.item import Item
from src.platforms.base import BasePlatform
from src.utils.logger import get_logger


logger = get_logger(__name__)


class eBayClient(BasePlatform):
    """
    Client per pubblicare articoli su eBay usando Trading API.
    """

    # Mappatura condizioni Item -> eBay
    CONDITION_MAP = {
        "new": "1000",  # New
        "used": "3000",  # Used
        "refurbished": "2000",  # Certified refurbished
        "for_parts": "7000",  # For parts or not working
    }

    def __init__(self, config: dict):
        """
        Inizializza il client eBay.

        Args:
            config: Configurazione eBay dal file config.yaml
        """
        super().__init__(config)
        self.api = None
        self.site_id = config.get("site_id", 101)  # Default: eBay Italy
        self.sandbox = config.get("sandbox", True)

    def authenticate(self) -> bool:
        """
        Autentica con eBay API.

        Returns:
            True se l'autenticazione è riuscita
        """
        try:
            domain = "api.sandbox.ebay.com" if self.sandbox else "api.ebay.com"

            self.api = Trading(
                domain=domain,
                appid=self.config.get("app_id"),
                devid=self.config.get("dev_id"),
                certid=self.config.get("cert_id"),
                token=self.config.get("token"),
                config_file=None,
                siteid=str(self.site_id)
            )

            # Test della connessione
            response = self.api.execute("GeteBayOfficialTime", {})
            logger.info(f"Autenticazione eBay riuscita. Server time: {response.reply.Timestamp}")

            self.is_authenticated = True
            return True

        except eBayConnectionError as e:
            logger.error(f"Errore di autenticazione eBay: {e}")
            self.is_authenticated = False
            return False
        except Exception as e:
            logger.error(f"Errore inaspettato durante l'autenticazione: {e}")
            self.is_authenticated = False
            return False

    def list_item(self, item: Item) -> Optional[str]:
        """
        Pubblica un articolo su eBay.

        Args:
            item: L'articolo da pubblicare

        Returns:
            Item ID di eBay se pubblicato con successo, None altrimenti
        """
        if not self.is_authenticated:
            logger.error("Non autenticato. Chiama authenticate() prima.")
            return None

        # Valida l'articolo
        is_valid, error_msg = self.validate_item(item)
        if not is_valid:
            logger.error(f"Articolo non valido: {error_msg}")
            return None

        try:
            # Prepara i dati per eBay
            listing_data = self._prepare_listing_data(item)

            # Pubblica l'articolo
            response = self.api.execute("AddFixedPriceItem", listing_data)

            if response.reply.Ack == "Success":
                item_id = response.reply.ItemID
                logger.info(f"Articolo pubblicato con successo. eBay Item ID: {item_id}")
                return item_id
            else:
                errors = response.reply.Errors if hasattr(response.reply, "Errors") else []
                logger.error(f"Errore nella pubblicazione: {errors}")
                return None

        except eBayConnectionError as e:
            logger.error(f"Errore nella chiamata API: {e}")
            return None
        except Exception as e:
            logger.error(f"Errore inaspettato: {e}")
            return None

    def _prepare_listing_data(self, item: Item) -> dict:
        """
        Prepara i dati dell'articolo per l'API eBay.

        Args:
            item: L'articolo da preparare

        Returns:
            Dizionario con i dati formattati per eBay
        """
        defaults = self.config.get("defaults", {})

        listing = {
            "Item": {
                "Title": item.title,
                "Description": item.description,
                "PrimaryCategory": {"CategoryID": item.category},
                "StartPrice": str(item.price),
                "ConditionID": self.CONDITION_MAP.get(item.condition, "3000"),
                "Country": defaults.get("country", "IT"),
                "Currency": defaults.get("currency", "EUR"),
                "DispatchTimeMax": "3",
                "ListingDuration": defaults.get("duration", "GTC"),
                "ListingType": defaults.get("listing_type", "FixedPriceItem"),
                "PaymentMethods": "PayPal",
                "PayPalEmailAddress": defaults.get("paypal_email", ""),
                "Quantity": item.quantity,
                "ReturnPolicy": {
                    "ReturnsAcceptedOption": "ReturnsAccepted",
                    "RefundOption": "MoneyBack",
                    "ReturnsWithinOption": "Days_30",
                    "ShippingCostPaidByOption": "Buyer",
                },
                "ShippingDetails": {
                    "ShippingType": "Flat",
                    "ShippingServiceOptions": {
                        "ShippingServicePriority": "1",
                        "ShippingService": "IT_RegularMail",
                        "ShippingServiceCost": "5.00",
                    },
                },
                "Site": "Italy",
            }
        }

        # Aggiungi immagini se presenti
        if item.images:
            listing["Item"]["PictureDetails"] = {
                "PictureURL": item.images[:12]  # eBay permette max 12 immagini
            }

        # Aggiungi SKU se presente
        if item.sku:
            listing["Item"]["SKU"] = item.sku

        return listing

    def update_item(self, item_id: str, item: Item) -> bool:
        """
        Aggiorna un articolo esistente su eBay.

        Args:
            item_id: ID eBay dell'articolo
            item: Nuovi dati dell'articolo

        Returns:
            True se aggiornato con successo
        """
        if not self.is_authenticated:
            logger.error("Non autenticato.")
            return False

        try:
            update_data = {
                "Item": {
                    "ItemID": item_id,
                    "Title": item.title,
                    "Description": item.description,
                    "StartPrice": str(item.price),
                    "Quantity": item.quantity,
                }
            }

            response = self.api.execute("ReviseFixedPriceItem", update_data)

            if response.reply.Ack == "Success":
                logger.info(f"Articolo {item_id} aggiornato con successo")
                return True
            else:
                logger.error(f"Errore nell'aggiornamento: {response.reply.Errors}")
                return False

        except Exception as e:
            logger.error(f"Errore nell'aggiornamento: {e}")
            return False

    def delete_item(self, item_id: str) -> bool:
        """
        Termina/rimuove un'inserzione eBay.

        Args:
            item_id: ID eBay dell'articolo

        Returns:
            True se rimosso con successo
        """
        if not self.is_authenticated:
            logger.error("Non autenticato.")
            return False

        try:
            end_data = {
                "ItemID": item_id,
                "EndingReason": "NotAvailable"
            }

            response = self.api.execute("EndFixedPriceItem", end_data)

            if response.reply.Ack == "Success":
                logger.info(f"Articolo {item_id} rimosso con successo")
                return True
            else:
                logger.error(f"Errore nella rimozione: {response.reply.Errors}")
                return False

        except Exception as e:
            logger.error(f"Errore nella rimozione: {e}")
            return False

    def get_item(self, item_id: str) -> Optional[Item]:
        """
        Recupera i dettagli di un articolo da eBay.

        Args:
            item_id: ID eBay dell'articolo

        Returns:
            Oggetto Item o None
        """
        if not self.is_authenticated:
            logger.error("Non autenticato.")
            return None

        try:
            response = self.api.execute("GetItem", {"ItemID": item_id})

            if response.reply.Ack == "Success":
                ebay_item = response.reply.Item
                # Converti i dati eBay in Item
                # (Implementazione semplificata)
                return Item(
                    title=str(ebay_item.Title),
                    description=str(ebay_item.Description),
                    price=float(ebay_item.StartPrice.value),
                    quantity=int(ebay_item.Quantity),
                    category=str(ebay_item.PrimaryCategory.CategoryID),
                    condition="used",  # Semplificato
                    ebay_id=item_id
                )
            else:
                logger.error(f"Errore nel recupero dell'articolo: {response.reply.Errors}")
                return None

        except Exception as e:
            logger.error(f"Errore nel recupero: {e}")
            return None

    def get_categories(self) -> List[dict]:
        """
        Recupera le categorie eBay.

        Returns:
            Lista di categorie
        """
        if not self.is_authenticated:
            logger.error("Non autenticato.")
            return []

        try:
            response = self.api.execute("GetCategories", {
                "CategorySiteID": self.site_id,
                "LevelLimit": "3"
            })

            if response.reply.Ack == "Success":
                categories = []
                for cat in response.reply.CategoryArray.Category:
                    categories.append({
                        "id": cat.CategoryID,
                        "name": cat.CategoryName,
                        "level": cat.CategoryLevel
                    })
                return categories
            else:
                logger.error("Errore nel recupero delle categorie")
                return []

        except Exception as e:
            logger.error(f"Errore: {e}")
            return []

    def validate_item(self, item: Item) -> tuple[bool, Optional[str]]:
        """
        Validazione specifica per eBay.

        Args:
            item: Articolo da validare

        Returns:
            (valido, messaggio_errore)
        """
        # Validazione base
        is_valid, error = super().validate_item(item)
        if not is_valid:
            return is_valid, error

        # Validazioni specifiche eBay
        if len(item.title) > 80:
            return False, "Il titolo non può superare 80 caratteri per eBay"

        if not item.category:
            return False, "La categoria è obbligatoria per eBay"

        return True, None
