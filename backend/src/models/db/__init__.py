"""
Database models package.
"""
from .base import Base, BaseModel
from .users import User, UserRole
from .categories import Category
from .articles import (
    Article,
    ArticleCondition,
    ArticleStatus,
    EbayStatus,
    VintedStatus,
)
from .card_purchases import CardPurchase
from .card_scan import CardBlueprint, CardReference, CardScan, CardScanStatus, OcrCorrection
from .category_alert import CategoryAlert
from .consignment_sale import ConsignmentSale
from .expense import Expense
from .inquiries import Inquiry, InquiryStatus
from .inventory import InventoryItem, InventoryItemStatus
from .lot import Lot, LotStatus
from .marketplace_fees import MarketplaceFee
from .orders import Order, OrderItem, OrderStatus
from .reviews import Review, ReviewStatus
from .platform import Platform
from .setting import Setting
from .shipping_addresses import ShippingAddress
from .misc_sales import MiscSale, MiscSaleKind
from .newsletter_subscriber import NewsletterSubscriber
from .instagram_media import CardPriceHistory, InstagramMedia, InstagramReply
from .personal_card import PersonalCard, PersonalCardStatus
from .vinted import VintedSettings, VintedSyncLog
from .wanted import WantedItem, WantedStatus

__all__ = [
    "Base",
    "BaseModel",
    "User",
    "UserRole",
    "Category",
    "Article",
    "ArticleCondition",
    "ArticleStatus",
    "VintedStatus",
    "EbayStatus",
    "CardPurchase",
    "CardBlueprint",
    "CardScan",
    "CardScanStatus",
    "CardReference",
    "OcrCorrection",
    "CategoryAlert",
    "NewsletterSubscriber",
    "InstagramMedia",
    "InstagramReply",
    "CardPriceHistory",
    "ConsignmentSale",
    "Expense",
    "Inquiry",
    "InquiryStatus",
    "InventoryItem",
    "InventoryItemStatus",
    "Lot",
    "LotStatus",
    "MiscSale",
    "MiscSaleKind",
    "PersonalCard",
    "PersonalCardStatus",
    "VintedSettings",
    "VintedSyncLog",
    "WantedItem",
    "WantedStatus",
    "MarketplaceFee",
    "Order",
    "Review",
    "ReviewStatus",
    "OrderItem",
    "OrderStatus",
    "Platform",
    "Setting",
    "ShippingAddress",
]
