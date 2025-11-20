"""
Classe base per tutte le integrazioni con piattaforme e-commerce.
"""
from abc import ABC, abstractmethod
from typing import List, Optional
from src.models.item import Item


class BasePlatform(ABC):
    """
    Classe base astratta per integrazioni con piattaforme e-commerce.
    Tutte le piattaforme devono implementare questi metodi.
    """

    def __init__(self, config: dict):
        """
        Inizializza la piattaforma.

        Args:
            config: Dizionario con le configurazioni della piattaforma
        """
        self.config = config
        self.is_authenticated = False

    @abstractmethod
    def authenticate(self) -> bool:
        """
        Autentica con la piattaforma.

        Returns:
            True se l'autenticazione è riuscita, False altrimenti
        """
        pass

    @abstractmethod
    def list_item(self, item: Item) -> Optional[str]:
        """
        Pubblica un articolo sulla piattaforma.

        Args:
            item: L'articolo da pubblicare

        Returns:
            ID dell'articolo pubblicato, None se fallito
        """
        pass

    @abstractmethod
    def update_item(self, item_id: str, item: Item) -> bool:
        """
        Aggiorna un articolo esistente.

        Args:
            item_id: ID dell'articolo da aggiornare
            item: Dati aggiornati dell'articolo

        Returns:
            True se l'aggiornamento è riuscito, False altrimenti
        """
        pass

    @abstractmethod
    def delete_item(self, item_id: str) -> bool:
        """
        Rimuove un articolo dalla piattaforma.

        Args:
            item_id: ID dell'articolo da rimuovere

        Returns:
            True se la rimozione è riuscita, False altrimenti
        """
        pass

    @abstractmethod
    def get_item(self, item_id: str) -> Optional[Item]:
        """
        Recupera i dettagli di un articolo.

        Args:
            item_id: ID dell'articolo

        Returns:
            Oggetto Item con i dettagli, None se non trovato
        """
        pass

    @abstractmethod
    def get_categories(self) -> List[dict]:
        """
        Recupera le categorie disponibili sulla piattaforma.

        Returns:
            Lista di dizionari con informazioni sulle categorie
        """
        pass

    def validate_item(self, item: Item) -> tuple[bool, Optional[str]]:
        """
        Valida un articolo prima della pubblicazione.

        Args:
            item: L'articolo da validare

        Returns:
            Tupla (valido, messaggio_errore)
        """
        # Validazioni base (possono essere sovrascritte dalle sottoclassi)
        if not item.title or len(item.title) < 5:
            return False, "Il titolo deve avere almeno 5 caratteri"

        if not item.description or len(item.description) < 20:
            return False, "La descrizione deve avere almeno 20 caratteri"

        if item.price <= 0:
            return False, "Il prezzo deve essere maggiore di zero"

        if item.quantity < 0:
            return False, "La quantità non può essere negativa"

        return True, None

    def __str__(self) -> str:
        """Rappresentazione stringa della piattaforma."""
        return f"{self.__class__.__name__}(authenticated={self.is_authenticated})"
