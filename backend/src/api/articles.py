"""
API endpoint per gli articoli.
"""
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status

from helpers.article import ArticleHelper, get_article_helper
from helpers.auth import require_admin
from helpers.category import CategoryHelper, get_category_helper
from helpers.user import UserHelper, get_user_helper
from models.db import (
    Article,
    ArticleCondition,
    ArticleStatus,
    Category,
    EbayStatus,
    User,
    VintedStatus,
)
from models.entities.category import CategoryResponse
from models.entities.article import (
    ArticleCreate,
    ArticleImageAdd,
    ArticleListResponse,
    ArticleResponse,
    ArticleUpdate,
    EbaySyncUpdate,
    ReorderRequest,
    VintedSyncUpdate,
)
from utils.storage import (
    UploadValidationError,
    delete_article_dir,
    delete_file_for_url,
    save_article_image,
)

router = APIRouter(prefix="/api/articles", tags=["articles"])


@router.post("/reorder", status_code=status.HTTP_204_NO_CONTENT)
def reorder_articles(
    payload: ReorderRequest,
    article_helper: ArticleHelper = Depends(get_article_helper),
    _admin: User = Depends(require_admin),
):
    """Imposta display_order in base alla posizione nell'array `order`."""
    article_helper.reorder(payload.order)
    return None


def _category_to_response(cat: Optional[Category]) -> Optional[CategoryResponse]:
    if cat is None:
        return None
    return CategoryResponse(
        id=cat.id,
        name=cat.name,
        slug=cat.slug,
        parent_id=cat.parent_id,
        display_order=cat.display_order,
    )


def _calc_inventory_metrics(article: Article) -> dict:
    """Calcola ricavo netto, profitto e fondi immobilizzati seguendo la
    stessa logica del foglio "Flipping Inventario"."""
    price = article.price or Decimal("0")
    fee = article.fee_amount or Decimal("0")
    ship = article.shipping_cost or Decimal("0")
    cost = article.cost or Decimal("0")

    sold = article.status.value == "SOLD" if article.status else False
    net_revenue = (price - fee - ship) if sold else Decimal("0")
    profit = (net_revenue - cost) if sold else Decimal("0")
    immobilizzato = cost if (not sold and cost > 0) else Decimal("0")
    return {
        "net_revenue": net_revenue,
        "profit": profit,
        "immobilizzato": immobilizzato,
    }


def _to_response(article: Article) -> ArticleResponse:
    parent_cat = article.category.parent if article.category and article.category.parent else None
    metrics = _calc_inventory_metrics(article)
    return ArticleResponse(
        id=article.id,
        user_id=article.user_id,
        title=article.title,
        description=article.description,
        price=article.price,
        shipping_price=article.shipping_price,
        currency=article.currency,
        lotto=article.lotto,
        purchase_date=article.purchase_date,
        cost=article.cost,
        purchase_platform=article.purchase_platform,
        bought_by=article.bought_by,
        sold_by=article.sold_by,
        fee_amount=article.fee_amount,
        shipping_cost=article.shipping_cost,
        quantity_sold=article.quantity_sold or 0,
        card_collection=article.card_collection,
        card_number=article.card_number,
        card_finish=article.card_finish,
        net_revenue=metrics["net_revenue"],
        profit=metrics["profit"],
        immobilizzato=metrics["immobilizzato"],
        category_id=article.category_id,
        category=_category_to_response(article.category),
        parent_category=_category_to_response(parent_cat),
        condition=article.condition.value,
        status=article.status.value,
        quantity=article.quantity,
        sku=article.sku,
        brand=article.brand,
        model=article.model,
        weight_kg=article.weight_kg,
        dimensions_cm=article.dimensions_cm,
        images=article.images or [],
        article_metadata=article.article_metadata or {},
        display_order=article.display_order or 0,
        vinted_status=article.vinted_status.value if article.vinted_status else "NOT_LISTED",
        vinted_url=article.vinted_url,
        vinted_synced_at=article.vinted_synced_at.isoformat() if article.vinted_synced_at else None,
        vinted_price=article.vinted_price,
        ebay_status=article.ebay_status.value if article.ebay_status else "NOT_LISTED",
        ebay_url=article.ebay_url,
        ebay_synced_at=article.ebay_synced_at.isoformat() if article.ebay_synced_at else None,
        ebay_price=article.ebay_price,
        created_at=article.created_at.isoformat() if article.created_at else None,
        updated_at=article.updated_at.isoformat() if article.updated_at else None,
        published_at=article.published_at.isoformat() if article.published_at else None,
        sold_at=article.sold_at.isoformat() if article.sold_at else None,
    )


@router.post("/", response_model=ArticleResponse, status_code=status.HTTP_201_CREATED)
def create_article(
    article_data: ArticleCreate,
    article_helper: ArticleHelper = Depends(get_article_helper),
    user_helper: UserHelper = Depends(get_user_helper),
    _admin: User = Depends(require_admin),
):
    """Crea un nuovo articolo."""
    owner = user_helper.get("id", article_data.user_id)
    if not owner:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Utente con ID {article_data.user_id} non trovato",
        )

    if article_data.sku:
        existing = article_helper.get("sku", article_data.sku)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"SKU '{article_data.sku}' gia' utilizzato",
            )

    new_article = Article(
        user_id=article_data.user_id,
        title=article_data.title,
        description=article_data.description,
        price=article_data.price,
        shipping_price=article_data.shipping_price,
        currency=article_data.currency,
        lotto=article_data.lotto,
        purchase_date=article_data.purchase_date,
        cost=article_data.cost,
        purchase_platform=article_data.purchase_platform,
        bought_by=article_data.bought_by,
        sold_by=article_data.sold_by,
        fee_amount=article_data.fee_amount,
        shipping_cost=article_data.shipping_cost,
        quantity_sold=article_data.quantity_sold or 0,
        card_collection=article_data.card_collection,
        card_number=article_data.card_number,
        card_finish=article_data.card_finish,
        category_id=article_data.category_id,
        condition=ArticleCondition(article_data.condition.value),
        status=ArticleStatus(article_data.status.value),
        quantity=article_data.quantity,
        sku=article_data.sku,
        brand=article_data.brand,
        model=article_data.model,
        weight_kg=article_data.weight_kg,
        dimensions_cm=article_data.dimensions_cm,
        images=article_data.images,
        article_metadata=article_data.article_metadata,
    )
    article_helper.save(new_article)
    return _to_response(new_article)


@router.get("/", response_model=ArticleListResponse)
def list_articles(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status_filter: Optional[ArticleStatus] = Query(None, alias="status"),
    category_id: Optional[int] = Query(
        None,
        description="Filtra per categoria. Se la categoria ha figli, include anche gli articoli delle sottocategorie.",
    ),
    condition: Optional[ArticleCondition] = None,
    brand: Optional[str] = None,
    user_id: Optional[int] = None,
    min_price: Optional[Decimal] = Query(None, ge=0),
    max_price: Optional[Decimal] = Query(None, ge=0),
    search: Optional[str] = Query(None, description="Ricerca full-text su titolo e descrizione"),
    article_helper: ArticleHelper = Depends(get_article_helper),
    category_helper: CategoryHelper = Depends(get_category_helper),
):
    """Lista articoli con paginazione, filtri e ricerca full-text."""
    db_status = ArticleStatus(status_filter.value) if status_filter else None
    db_condition = ArticleCondition(condition.value) if condition else None

    category_ids = None
    if category_id is not None:
        category_ids = category_helper.get_descendant_ids(category_id)

    items, total = article_helper.gets(
        skip=skip,
        limit=limit,
        status=db_status,
        category_ids=category_ids,
        condition=db_condition,
        brand=brand,
        user_id=user_id,
        min_price=min_price,
        max_price=max_price,
        search=search,
    )

    return ArticleListResponse(
        items=[_to_response(a) for a in items],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{article_id}", response_model=ArticleResponse)
def get_article(
    article_id: int,
    article_helper: ArticleHelper = Depends(get_article_helper),
):
    """Ottieni un articolo per ID."""
    article = article_helper.get("id", article_id)
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Articolo con ID {article_id} non trovato",
        )
    return _to_response(article)


@router.get("/sku/{sku}", response_model=ArticleResponse)
def get_article_by_sku(
    sku: str,
    article_helper: ArticleHelper = Depends(get_article_helper),
):
    """Ottieni un articolo per SKU."""
    article = article_helper.get("sku", sku)
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Articolo con SKU '{sku}' non trovato",
        )
    return _to_response(article)


@router.patch("/{article_id}", response_model=ArticleResponse)
def update_article(
    article_id: int,
    article_data: ArticleUpdate,
    article_helper: ArticleHelper = Depends(get_article_helper),
    _admin: User = Depends(require_admin),
):
    """Aggiorna un articolo."""
    article = article_helper.get("id", article_id)
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Articolo con ID {article_id} non trovato",
        )

    if article_data.sku and article_data.sku != article.sku:
        existing = article_helper.get("sku", article_data.sku)
        if existing and existing.id != article_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"SKU '{article_data.sku}' gia' utilizzato",
            )

    article_helper.update(article_data, article)
    return _to_response(article)


@router.delete("/{article_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_article(
    article_id: int,
    article_helper: ArticleHelper = Depends(get_article_helper),
    _admin: User = Depends(require_admin),
):
    """Elimina un articolo e tutti i suoi file immagine caricati."""
    article = article_helper.get("id", article_id)
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Articolo con ID {article_id} non trovato",
        )
    article_helper.delete(article)
    delete_article_dir(article_id)
    return None


@router.post("/{article_id}/publish", response_model=ArticleResponse)
def publish_article(
    article_id: int,
    article_helper: ArticleHelper = Depends(get_article_helper),
    _admin: User = Depends(require_admin),
):
    """Marca l'articolo come pubblicato."""
    article = article_helper.get("id", article_id)
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Articolo con ID {article_id} non trovato",
        )
    article_helper.set_status(article, ArticleStatus.PUBLISHED)
    return _to_response(article)


@router.post("/{article_id}/sell", response_model=ArticleResponse)
def sell_article(
    article_id: int,
    article_helper: ArticleHelper = Depends(get_article_helper),
    _admin: User = Depends(require_admin),
):
    """Marca l'articolo come venduto."""
    article = article_helper.get("id", article_id)
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Articolo con ID {article_id} non trovato",
        )
    article_helper.set_status(article, ArticleStatus.SOLD)
    return _to_response(article)


@router.post("/{article_id}/archive", response_model=ArticleResponse)
def archive_article(
    article_id: int,
    article_helper: ArticleHelper = Depends(get_article_helper),
    _admin: User = Depends(require_admin),
):
    """Marca l'articolo come archiviato."""
    article = article_helper.get("id", article_id)
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Articolo con ID {article_id} non trovato",
        )
    article_helper.set_status(article, ArticleStatus.ARCHIVED)
    return _to_response(article)


@router.patch("/{article_id}/vinted", response_model=ArticleResponse)
def update_vinted_sync(
    article_id: int,
    payload: VintedSyncUpdate,
    article_helper: ArticleHelper = Depends(get_article_helper),
    _admin: User = Depends(require_admin),
):
    """Aggiorna stato e URL Vinted dell'articolo. Se vinted_status=SOLD,
    l'articolo viene marcato come SOLD anche nel catalogo principale."""
    article = article_helper.get("id", article_id)
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Articolo con ID {article_id} non trovato",
        )
    article_helper.set_vinted(
        article,
        VintedStatus(payload.vinted_status.value),
        payload.vinted_url,
        payload.vinted_price,
    )
    return _to_response(article)


@router.patch("/{article_id}/ebay", response_model=ArticleResponse)
def update_ebay_sync(
    article_id: int,
    payload: EbaySyncUpdate,
    article_helper: ArticleHelper = Depends(get_article_helper),
    _admin: User = Depends(require_admin),
):
    """Aggiorna stato e URL eBay dell'articolo. Se ebay_status=SOLD,
    l'articolo viene marcato come SOLD anche nel catalogo principale."""
    article = article_helper.get("id", article_id)
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Articolo con ID {article_id} non trovato",
        )
    article_helper.set_ebay(
        article,
        EbayStatus(payload.ebay_status.value),
        payload.ebay_url,
        payload.ebay_price,
    )
    return _to_response(article)


@router.post("/{article_id}/images", response_model=ArticleResponse)
def add_article_image(
    article_id: int,
    payload: ArticleImageAdd,
    article_helper: ArticleHelper = Depends(get_article_helper),
    _admin: User = Depends(require_admin),
):
    """Aggiunge un URL immagine all'articolo."""
    article = article_helper.get("id", article_id)
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Articolo con ID {article_id} non trovato",
        )
    article_helper.add_image(article, payload.url)
    return _to_response(article)


@router.delete("/{article_id}/images", response_model=ArticleResponse)
def remove_article_image(
    article_id: int,
    url: str = Query(..., description="URL dell'immagine da rimuovere"),
    article_helper: ArticleHelper = Depends(get_article_helper),
    _admin: User = Depends(require_admin),
):
    """Rimuove un URL immagine dall'articolo. Se l'URL e' servito dal nostro
    storage statico, cancella anche il file su disco."""
    article = article_helper.get("id", article_id)
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Articolo con ID {article_id} non trovato",
        )
    article_helper.remove_image(article, url)
    delete_file_for_url(url)
    return _to_response(article)


@router.post("/{article_id}/upload-image", response_model=ArticleResponse)
def upload_article_image(
    article_id: int,
    file: UploadFile = File(...),
    article_helper: ArticleHelper = Depends(get_article_helper),
    _admin: User = Depends(require_admin),
):
    """Carica un file immagine per l'articolo e aggiunge il suo URL pubblico
    all'array images. Accetta image/jpeg, image/png, image/webp, image/gif
    fino a MAX_UPLOAD_SIZE_MB MB (default 5)."""
    article = article_helper.get("id", article_id)
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Articolo con ID {article_id} non trovato",
        )

    try:
        url, _ = save_article_image(
            article_id=article_id,
            file_obj=file.file,
            content_type=file.content_type or "",
        )
    except UploadValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    article_helper.add_image(article, url)
    return _to_response(article)
