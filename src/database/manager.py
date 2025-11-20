"""
Database manager per NerdNostalgia.
Gestisce tutte le operazioni CRUD sul database.
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path
import json

from sqlalchemy import create_engine, and_, or_
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError

from .models import (
    Base,
    User,
    Item,
    Platform,
    Listing,
    ListingHistory,
    UserRole,
    ItemCondition,
    ListingStatus,
)
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DatabaseManager:
    """Manager per operazioni database."""

    def __init__(self, database_url: str = "sqlite:///data/nerdnostalgia.db"):
        """
        Inizializza il database manager.

        Args:
            database_url: URL di connessione al database
        """
        # Crea directory se SQLite
        if database_url.startswith("sqlite:///"):
            db_path = Path(database_url.replace("sqlite:///", ""))
            db_path.parent.mkdir(parents=True, exist_ok=True)

        self.engine = create_engine(database_url, echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine, expire_on_commit=False)

        logger.info(f"Database manager inizializzato: {database_url}")

    def create_tables(self):
        """Crea tutte le tabelle nel database."""
        Base.metadata.create_all(self.engine)
        logger.info("Tabelle database create")

        # Inizializza piattaforme default
        with self.get_session() as session:
            self._init_default_platforms(session)

    def drop_tables(self):
        """Elimina tutte le tabelle (ATTENZIONE!)."""
        Base.metadata.drop_all(self.engine)
        logger.warning("Tabelle database eliminate")

    def get_session(self) -> Session:
        """
        Ottiene una sessione database.

        Returns:
            Session SQLAlchemy
        """
        return self.SessionLocal()

    def _init_default_platforms(self, session: Session):
        """Inizializza piattaforme default se non esistono."""
        platforms_data = [
            {"name": "ebay", "display_name": "eBay"},
            {"name": "amazon", "display_name": "Amazon"},
            {"name": "subito", "display_name": "Subito.it"},
            {"name": "vinted", "display_name": "Vinted"},
        ]

        for platform_data in platforms_data:
            existing = session.query(Platform).filter_by(name=platform_data["name"]).first()
            if not existing:
                platform = Platform(**platform_data)
                session.add(platform)

        session.commit()
        logger.info("Piattaforme default inizializzate")

    # ==================== USER OPERATIONS ====================

    def create_user(
        self,
        username: str,
        email: str,
        full_name: Optional[str] = None,
        role: UserRole = UserRole.USER,
    ) -> Optional[User]:
        """Crea un nuovo utente."""
        with self.get_session() as session:
            try:
                user = User(
                    username=username,
                    email=email,
                    full_name=full_name,
                    role=role,
                )
                session.add(user)
                session.commit()
                session.refresh(user)
                logger.info(f"Utente creato: {username}")
                return user
            except IntegrityError as e:
                session.rollback()
                logger.error(f"Errore creazione utente: {e}")
                return None

    def get_user(self, user_id: Optional[int] = None, username: Optional[str] = None) -> Optional[User]:
        """Ottiene un utente per ID o username."""
        with self.get_session() as session:
            if user_id:
                return session.query(User).filter_by(id=user_id).first()
            elif username:
                return session.query(User).filter_by(username=username).first()
            return None

    def get_or_create_user(self, username: str, email: str, **kwargs) -> User:
        """Ottiene un utente esistente o ne crea uno nuovo."""
        user = self.get_user(username=username)
        if not user:
            user = self.create_user(username=username, email=email, **kwargs)
        return user

    def list_users(self, active_only: bool = True) -> List[User]:
        """Lista tutti gli utenti."""
        with self.get_session() as session:
            query = session.query(User)
            if active_only:
                query = query.filter_by(is_active=True)
            return query.all()

    # ==================== ITEM OPERATIONS ====================

    def create_item(self, user_id: int, item_data: Dict[str, Any]) -> Optional[Item]:
        """
        Crea un nuovo articolo.

        Args:
            user_id: ID utente proprietario
            item_data: Dati articolo

        Returns:
            Item creato o None se errore
        """
        with self.get_session() as session:
            try:
                # Converti liste in JSON se presenti
                if "images" in item_data and isinstance(item_data["images"], list):
                    item_data["images"] = json.dumps(item_data["images"])
                if "tags" in item_data and isinstance(item_data["tags"], list):
                    item_data["tags"] = json.dumps(item_data["tags"])

                # Converti condition se stringa
                if "condition" in item_data and isinstance(item_data["condition"], str):
                    item_data["condition"] = ItemCondition(item_data["condition"])

                item = Item(user_id=user_id, **item_data)
                session.add(item)
                session.commit()
                session.refresh(item)
                logger.info(f"Articolo creato: {item.title} (ID: {item.id})")
                return item
            except Exception as e:
                session.rollback()
                logger.error(f"Errore creazione articolo: {e}")
                return None

    def get_item(self, item_id: int) -> Optional[Item]:
        """Ottiene un articolo per ID."""
        with self.get_session() as session:
            return session.query(Item).filter_by(id=item_id).first()

    def get_item_by_sku(self, sku: str) -> Optional[Item]:
        """Ottiene un articolo per SKU."""
        with self.get_session() as session:
            return session.query(Item).filter_by(sku=sku).first()

    def list_items(
        self,
        user_id: Optional[int] = None,
        category: Optional[str] = None,
        condition: Optional[ItemCondition] = None,
    ) -> List[Item]:
        """Lista articoli con filtri opzionali."""
        with self.get_session() as session:
            query = session.query(Item)

            if user_id:
                query = query.filter_by(user_id=user_id)
            if category:
                query = query.filter_by(category=category)
            if condition:
                query = query.filter_by(condition=condition)

            return query.order_by(Item.created_at.desc()).all()

    def update_item(self, item_id: int, updates: Dict[str, Any]) -> bool:
        """Aggiorna un articolo."""
        with self.get_session() as session:
            try:
                item = session.query(Item).filter_by(id=item_id).first()
                if not item:
                    return False

                for key, value in updates.items():
                    if hasattr(item, key):
                        setattr(item, key, value)

                session.commit()
                logger.info(f"Articolo {item_id} aggiornato")
                return True
            except Exception as e:
                session.rollback()
                logger.error(f"Errore aggiornamento articolo: {e}")
                return False

    def delete_item(self, item_id: int) -> bool:
        """Elimina un articolo."""
        with self.get_session() as session:
            try:
                item = session.query(Item).filter_by(id=item_id).first()
                if not item:
                    return False

                session.delete(item)
                session.commit()
                logger.info(f"Articolo {item_id} eliminato")
                return True
            except Exception as e:
                session.rollback()
                logger.error(f"Errore eliminazione articolo: {e}")
                return False

    # ==================== LISTING OPERATIONS ====================

    def create_listing(
        self,
        item_id: int,
        platform_name: str,
        platform_item_id: str,
        listed_price: float,
        url: Optional[str] = None,
    ) -> Optional[Listing]:
        """Crea un nuovo listing."""
        with self.get_session() as session:
            try:
                # Ottieni item e platform
                item = session.query(Item).filter_by(id=item_id).first()
                if not item:
                    logger.error(f"Item {item_id} non trovato")
                    return None

                platform = session.query(Platform).filter_by(name=platform_name).first()
                if not platform:
                    logger.error(f"Platform {platform_name} non trovata")
                    return None

                listing = Listing(
                    item_id=item_id,
                    platform_id=platform.id,
                    user_id=item.user_id,
                    platform_item_id=platform_item_id,
                    listed_price=listed_price,
                    url=url,
                    status=ListingStatus.ACTIVE,
                    published_at=datetime.utcnow(),
                )
                session.add(listing)

                # Aggiungi entry nello storico
                history = ListingHistory(
                    listing=listing,
                    event_type="created",
                    event_data=json.dumps({"price": str(listed_price)}),
                )
                session.add(history)

                session.commit()
                session.refresh(listing)
                logger.info(f"Listing creato: {platform_name} - {platform_item_id}")
                return listing
            except Exception as e:
                session.rollback()
                logger.error(f"Errore creazione listing: {e}")
                return None

    def get_listing(self, listing_id: int) -> Optional[Listing]:
        """Ottiene un listing per ID."""
        with self.get_session() as session:
            return session.query(Listing).filter_by(id=listing_id).first()

    def get_listing_by_platform_id(
        self, platform_name: str, platform_item_id: str
    ) -> Optional[Listing]:
        """Ottiene un listing per ID piattaforma."""
        with self.get_session() as session:
            platform = session.query(Platform).filter_by(name=platform_name).first()
            if not platform:
                return None

            return (
                session.query(Listing)
                .filter_by(platform_id=platform.id, platform_item_id=platform_item_id)
                .first()
            )

    def list_listings(
        self,
        user_id: Optional[int] = None,
        platform_name: Optional[str] = None,
        status: Optional[ListingStatus] = None,
    ) -> List[Listing]:
        """Lista listing con filtri opzionali."""
        with self.get_session() as session:
            query = session.query(Listing)

            if user_id:
                query = query.filter_by(user_id=user_id)
            if platform_name:
                platform = session.query(Platform).filter_by(name=platform_name).first()
                if platform:
                    query = query.filter_by(platform_id=platform.id)
            if status:
                query = query.filter_by(status=status)

            return query.order_by(Listing.created_at.desc()).all()

    def update_listing_status(
        self, listing_id: int, status: ListingStatus, notes: Optional[str] = None
    ) -> bool:
        """Aggiorna lo stato di un listing."""
        with self.get_session() as session:
            try:
                listing = session.query(Listing).filter_by(id=listing_id).first()
                if not listing:
                    return False

                old_status = listing.status
                listing.status = status

                # Aggiorna date specifiche
                if status == ListingStatus.SOLD:
                    listing.sold_at = datetime.utcnow()
                    listing.ended_at = datetime.utcnow()
                elif status == ListingStatus.ENDED:
                    listing.ended_at = datetime.utcnow()

                # Aggiungi history
                history = ListingHistory(
                    listing_id=listing_id,
                    event_type="status_changed",
                    event_data=json.dumps({
                        "old_status": old_status.value,
                        "new_status": status.value,
                    }),
                    notes=notes,
                )
                session.add(history)

                session.commit()
                logger.info(f"Listing {listing_id} status: {old_status.value} -> {status.value}")
                return True
            except Exception as e:
                session.rollback()
                logger.error(f"Errore aggiornamento status listing: {e}")
                return False

    # ==================== STATISTICS ====================

    def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """Ottiene statistiche per un utente."""
        with self.get_session() as session:
            stats = {
                "total_items": session.query(Item).filter_by(user_id=user_id).count(),
                "total_listings": session.query(Listing).filter_by(user_id=user_id).count(),
                "active_listings": (
                    session.query(Listing)
                    .filter_by(user_id=user_id, status=ListingStatus.ACTIVE)
                    .count()
                ),
                "sold_listings": (
                    session.query(Listing)
                    .filter_by(user_id=user_id, status=ListingStatus.SOLD)
                    .count()
                ),
            }
            return stats

    def get_platform_stats(self, platform_name: str) -> Dict[str, Any]:
        """Ottiene statistiche per una piattaforma."""
        with self.get_session() as session:
            platform = session.query(Platform).filter_by(name=platform_name).first()
            if not platform:
                return {}

            stats = {
                "total_listings": (
                    session.query(Listing).filter_by(platform_id=platform.id).count()
                ),
                "active_listings": (
                    session.query(Listing)
                    .filter_by(platform_id=platform.id, status=ListingStatus.ACTIVE)
                    .count()
                ),
                "sold_listings": (
                    session.query(Listing)
                    .filter_by(platform_id=platform.id, status=ListingStatus.SOLD)
                    .count()
                ),
            }
            return stats
