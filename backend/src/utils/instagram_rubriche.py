"""
Le rubriche Instagram: un contenuto in piu' al giorno, uno diverso per ogni
giorno della settimana, tutti presi dal catalogo.

    lunedi'    Reel "Nuovi arrivi della settimana"
    martedi'   Reel quiz "Indovina il prezzo" (valore di mercato CardTrader)
    mercoledi' carosello "Sotto i 5 €"
    giovedi'   carosello "Idee regalo nerd", fascia di prezzo a rotazione
    venerdi'   carosello "Le carte salite di piu'" (storico dei prezzi)
    sabato     carosello "X anni fa usciva..." (data del set da TCGdex)
    domenica   post "La rara della settimana"

Se la rubrica del giorno non ha materiale (niente nuovi arrivi, niente
storico dei prezzi...) quel giorno non esce niente: non si anticipa quella
del giorno dopo.
Esce nella fascia oraria buona che non e' quella del post del giorno
(instagram_stats). Ogni rubrica invita a commentare LISTA: `rispondi_ai_commenti`
manda in privato i link degli articoli del post.
"""
import io
import json
import logging
import os
import random
from datetime import datetime, timedelta
from typing import Callable, Dict, List, Optional, Tuple

from PIL import Image, ImageDraw
from sqlalchemy.orm import Session

from models.db import (Article, ArticleStatus, CardPriceHistory, InstagramMedia, InstagramReply,
                       PersonalCard)
from utils import instagram, instagram_reel, instagram_stats

LOGGER = logging.getLogger("instagram_rubriche")

PAROLA = "LISTA"
MAX_SLIDE = 10
CHIAVE_GIORNO = "instagram_rubrica_day"
GIORNI_SENZA_RIPETERE = timedelta(days=60)
FASCE_REGALO = [(0, 10), (10, 25), (25, 60), (60, None)]
INVITO = f"💬 Commenta {PAROLA} e ti mando in privato i link di tutti i pezzi!"


def _ora() -> datetime:
    return datetime.now(instagram_stats.ROMA).replace(tzinfo=None)


def _in_vendita(db: Session):
    return (db.query(Article)
            .filter(Article.status == ArticleStatus.PUBLISHED, Article.reserved_order_id.is_(None),
                    Article.quantity > 0, Article.price > 0))


def _usati_di_recente(db: Session, rubrica: str) -> set:
    """Gli articoli gia' mostrati da questa rubrica negli ultimi 60 giorni."""
    righe = (db.query(InstagramMedia.article_ids)
             .filter(InstagramMedia.rubrica == rubrica,
                     InstagramMedia.published_at >= _ora() - GIORNI_SENZA_RIPETERE).all())
    return {int(i) for (ids,) in righe for i in (ids or "").split()}


def _con_foto(articoli) -> List[Article]:
    return [a for a in articoli if a.images]


def _carta(a: Article) -> Optional[PersonalCard]:
    from sqlalchemy.orm import object_session
    return object_session(a).query(PersonalCard).filter(PersonalCard.article_id == a.id).first()


# ---------------------------------------------------------------------------
# Grafica
# ---------------------------------------------------------------------------

def copertina(titolo: str, sottotitolo: str, formato=instagram.POST, emoji_testo: str = "",
              articoli: Optional[List[Article]] = None) -> Image.Image:
    """La prima slide di un carosello (o di un Reel) nello stile del sito:
    etichetta, titolo grande, sottotitolo e il mosaico delle prime foto."""
    from utils import social_grafica as g
    w, h = formato
    storia = h > w * 1.5
    tela = g.sfondo(formato, seme=hash(titolo) % 1000)
    g.logo(tela, 50, 50, 150 if storia else 120)
    y = int(h * 0.10) if not storia else 300
    if emoji_testo:
        g.etichetta(tela, emoji_testo, w // 2, y, g.ROSA_FORTE, g.BIANCO, 36 if not storia else 44, "centro")
        y += 90 if not storia else 110
    y = g.testo_centrato(tela, titolo, y, "titolo", 92 if not storia else 110, g.INK, 3)
    y = g.testo_centrato(tela, sottotitolo, y + 10, "testo", 46 if not storia else 56, g.INK_SOFT, 2,
                         peso="SemiBold")
    foto = [instagram._foto(a) for a in (articoli or [])[:4]]
    if any(f is not None for f in foto):
        basso = h - (150 if not storia else 260)
        g.mosaico(tela, foto, (90, y + 30, w - 90, basso))
    if not storia:
        g.etichetta(tela, "SCORRI →", w - 50, h - 100, g.INK, g.BIANCO, 32, "destra")
    else:
        g.etichetta(tela, "nerdnostalgia.store", w // 2, h - 140, g.BIANCO, g.INK, 40, "centro")
    return tela.convert("RGB")


def _jpeg(img: Image.Image) -> bytes:
    out = io.BytesIO()
    img.save(out, "JPEG", quality=90)
    return out.getvalue()


# ---------------------------------------------------------------------------
# Le rubriche: ognuna torna (testo, articoli, contenuti) o None se non ha
# materiale. I contenuti sono ("carosello", [immagini url]) o ("reel", url).
# ---------------------------------------------------------------------------

Contenuto = Tuple[str, List[Article], str, object]   # (rubrica, articoli, didascalia, media)


def _didascalia(righe: List[str], articoli: List[Article], db: Session) -> str:
    corpo = righe + ["", INVITO, "🛒 Tutto su nerdnostalgia.store (link in bio)",
                     f"💬 Le novità in tempo reale nel gruppo Telegram: {instagram.TELEGRAM_URL}",
                     "", instagram._tag(articoli, db)]
    return "\n".join(corpo)[:2200]


def _carosello(nome: str, titolo: str, sottotitolo: str, articoli: List[Article], righe: List[str],
               db: Session, emoji: str = "") -> Contenuto:
    from utils import social_grafica as g
    articoli = articoli[:MAX_SLIDE - 2]
    giorno = f"{_ora():%Y%m%d}"
    cover = instagram_reel.salva(_jpeg(copertina(titolo, sottotitolo, emoji_testo=emoji, articoli=articoli)),
                                 f"{nome}-{giorno}", "jpg")
    fine = instagram_reel.salva(_jpeg(g.finale(instagram.POST, seme=len(articoli))), f"{nome}-{giorno}-fine", "jpg")
    immagini = [cover] + [instagram.url_immagine(a, "post") for a in articoli] + [fine]
    return nome, articoli, _didascalia(righe, articoli, db), ("carosello", immagini)


def nuovi_della_settimana(db: Session) -> Optional[Contenuto]:
    articoli = _con_foto(_in_vendita(db).filter(Article.published_at >= _ora() - timedelta(days=7)).all())
    if len(articoli) < 2:
        return None
    articoli.sort(key=lambda a: float(a.price), reverse=True)
    pezzi = articoli[:instagram_reel.MAX_PEZZI]
    slide = [(copertina("Nuovi arrivi della settimana", f"{len(articoli)} pezzi appena arrivati",
                        instagram.STORIA, "NOVITÀ", articoli=pezzi), instagram_reel.INTRO)]
    for a in pezzi:
        img = Image.open(io.BytesIO(instagram.immagine(a, "storia")))
        slide.append((img, instagram_reel.PER_PEZZO))
    slide.append((instagram_reel._outro(), instagram_reel.OUTRO))
    url = instagram_reel.salva(instagram_reel.monta(slide, seme=_ora().toordinal()),
                               f"nuovi-{_ora():%Y%m%d}")
    righe = [f"🆕 I nuovi arrivi della settimana: {len(articoli)} pezzi!", ""]
    righe += [f"▪️ {a.title} — {instagram._prezzo(a)}" for a in pezzi[:10]]
    return "nuovi", pezzi, _didascalia(righe, pezzi, db), ("reel", url)


def indovina_il_prezzo(db: Session) -> Optional[Contenuto]:
    usati = _usati_di_recente(db, "quiz")
    candidati = []
    for a in _con_foto(_in_vendita(db).filter(Article.price >= 3).all()):
        carta = _carta(a)
        if a.id not in usati and carta is not None and carta.cardtrader_price:
            candidati.append((a, float(carta.cardtrader_price)))
    if not candidati:
        return None
    a, mercato = random.Random(_ora().toordinal()).choice(candidati)
    from utils import social_grafica as g
    w, h = instagram.STORIA
    base = Image.open(io.BytesIO(instagram.immagine(a, "storia", mostra_prezzo=False,
                                                    intestazione="INDOVINA IL PREZZO"))).convert("RGBA")
    domanda = base.copy()
    g.pillola(domanda, "QUANTO VALE?", w // 2, 1650, 84)
    conto = []
    for n in ("3", "2", "1"):
        img = base.copy()
        g.pillola(img, f"  {n}  ", w // 2, 1630, 120, g.LILLA_FORTE)
        conto.append((img.convert("RGB"), 1.0))
    domanda = domanda.convert("RGB")
    risposta = copertina(f"{mercato:.2f} €".replace(".", ","), f"il valore di mercato · da noi {instagram._prezzo(a)}",
                         instagram.STORIA, "LA RISPOSTA", articoli=[a])
    slide = [(domanda, 3.0)] + conto + [(risposta, 3.5), (instagram_reel._outro(), 2.5)]
    url = instagram_reel.salva(instagram_reel.monta(slide, seme=_ora().toordinal() + 7), f"quiz-{_ora():%Y%m%d}")
    righe = ["🤔 Indovina il prezzo! Quanto vale questa carta?",
             "Scrivi la tua risposta nei commenti prima di guardare la fine del video 👀", "",
             f"▪️ {a.title}"]
    return "quiz", [a], _didascalia(righe, [a], db), ("reel", url)


def sotto_i_5(db: Session) -> Optional[Contenuto]:
    usati = _usati_di_recente(db, "sotto5")
    articoli = [a for a in _con_foto(_in_vendita(db).filter(Article.price <= 5).all()) if a.id not in usati]
    if len(articoli) < 3:
        return None
    random.Random(_ora().toordinal()).shuffle(articoli)
    scelti = articoli[:MAX_SLIDE - 2]
    righe = ["💸 Sotto i 5 €: piccoli prezzi, grande nostalgia!", ""]
    righe += [f"▪️ {a.title} — {instagram._prezzo(a)}" for a in scelti]
    return _carosello("sotto5", "Sotto i 5 €", "piccoli prezzi, grande nostalgia", scelti, righe, db, "OCCASIONI")


def idee_regalo(db: Session) -> Optional[Contenuto]:
    settimana = _ora().isocalendar()[1]
    usati = _usati_di_recente(db, "regalo")
    for spostamento in range(len(FASCE_REGALO)):
        da, a_ = FASCE_REGALO[(settimana + spostamento) % len(FASCE_REGALO)]
        q = _in_vendita(db).filter(Article.price > da)
        if a_ is not None:
            q = q.filter(Article.price <= a_)
        articoli = [x for x in _con_foto(q.all()) if x.id not in usati]
        if len(articoli) >= 3:
            break
    else:
        return None
    # Varieta': un pezzo per categoria prima di ripetere.
    random.Random(_ora().toordinal()).shuffle(articoli)
    per_categoria: Dict[object, List[Article]] = {}
    for x in articoli:
        per_categoria.setdefault(x.category_id, []).append(x)
    scelti: List[Article] = []
    while len(scelti) < MAX_SLIDE - 2 and any(per_categoria.values()):
        for lista in per_categoria.values():
            if lista and len(scelti) < MAX_SLIDE - 2:
                scelti.append(lista.pop())
    fascia = f"sotto i {a_} €" if a_ is not None else f"oltre i {da} €"
    natale = _ora().month == 12 or (_ora().month == 11 and _ora().day >= 15)
    titolo = f"Idee regalo nerd {fascia}"
    sotto = "per Natale" if natale else "per chi ama collezionare"
    righe = [f"🎁 {titolo} {sotto}!", ""] + [f"▪️ {x.title} — {instagram._prezzo(x)}" for x in scelti]
    return _carosello("regalo", titolo, sotto, scelti, righe, db, "GUIDA AI REGALI")


def carte_salite(db: Session) -> Optional[Contenuto]:
    salite = []
    for a in _con_foto(_in_vendita(db).all()):
        carta = _carta(a)
        if carta is None:
            continue
        storia = (db.query(CardPriceHistory).filter(CardPriceHistory.card_id == carta.id)
                  .order_by(CardPriceHistory.recorded_at).all())
        if len(storia) < 2 or float(storia[0].value) <= 0:
            continue
        prima, dopo = float(storia[-2].value), float(storia[-1].value)
        if dopo > prima and dopo - prima >= 0.5:
            salite.append((a, prima, dopo, (dopo - prima) / prima))
    if len(salite) < 3:
        return None
    salite.sort(key=lambda s: s[3], reverse=True)
    scelti = salite[:5]
    righe = ["📈 Le carte che sono salite di più questa settimana (valore di mercato):", ""]
    righe += [f"▪️ {a.title}: da {p:.2f} € a {d:.2f} € (+{round(r * 100)}%)".replace(".", ",")
              for a, p, d, r in scelti]
    righe += ["", "Le trovi tutte da noi, finché ci sono!"]
    return _carosello("salite", "Le carte salite di più", "questa settimana", [s[0] for s in scelti],
                      righe, db, "IN SALITA")


def anni_fa(db: Session) -> Optional[Contenuto]:
    """Un set Pokémon di cui abbiamo carte, con il suo anno di uscita."""
    from utils import card_names_it
    usati = _usati_di_recente(db, "annifa")
    per_set: Dict[str, List[Article]] = {}
    for a in _con_foto(_in_vendita(db).all()):
        carta = _carta(a)
        if carta is not None and carta.collection and a.id not in usati:
            per_set.setdefault(carta.collection, []).append(a)
    candidati = []
    for nome, articoli in per_set.items():
        if len(articoli) < 3:
            continue
        set_id = card_names_it._set_pokemon(nome)
        if not set_id:
            continue
        info = card_names_it._in_cache(f"tcgdex:en:{set_id}",
                                       lambda s=set_id: card_names_it._get(f"https://api.tcgdex.net/v2/en/sets/{s}"))
        uscita = info.get("releaseDate") if isinstance(info, dict) else None
        if uscita and uscita[:4].isdigit():
            candidati.append((int(uscita[:4]), nome, articoli))
    if not candidati:
        return None
    candidati.sort()
    anno, nome, articoli = random.Random(_ora().toordinal()).choice(candidati[:5])
    quanti_anni = _ora().year - anno
    nome_it = next((c.collection_it for c in (_carta(x) for x in articoli) if c and c.collection_it), None) or nome
    articoli.sort(key=lambda a: float(a.price), reverse=True)
    titolo = f"{quanti_anni} anni fa usciva {nome_it}" if quanti_anni > 0 else f"{nome_it}, uscito quest'anno"
    righe = [f"⏳ {titolo} ({anno})! Quante di queste carte avevi?", ""]
    righe += [f"▪️ {a.title} — {instagram._prezzo(a)}" for a in articoli[:MAX_SLIDE - 2]]
    return _carosello("annifa", titolo, f"il set del {anno}", articoli, righe, db, "NOSTALGIA")


def rara_della_settimana(db: Session) -> Optional[Contenuto]:
    usati = _usati_di_recente(db, "rara")
    articoli = [a for a in _con_foto(_in_vendita(db).order_by(Article.price.desc()).limit(30).all())
                if a.id not in usati]
    if not articoli:
        return None
    a = articoli[0]
    carta = _carta(a)
    righe = ["💎 La rara della settimana!", "", f"▪️ {a.title} — {instagram._prezzo(a)}"]
    if carta is not None and carta.collection_it:
        righe.append(f"Set: {carta.collection_it}")
    if a.description:
        righe += ["", a.description.strip()[:500]]
    return "rara", [a], _didascalia(righe, [a], db), ("foto", instagram.url_immagine(a, "post"))


# Lunedi' = 0.
CALENDARIO: List[Tuple[str, Callable[[Session], Optional[Contenuto]]]] = [
    ("nuovi", nuovi_della_settimana),
    ("quiz", indovina_il_prezzo),
    ("sotto5", sotto_i_5),
    ("regalo", idee_regalo),
    ("salite", carte_salite),
    ("annifa", anni_fa),
    ("rara", rara_della_settimana),
]


def prepara(db: Session, giorno: Optional[int] = None) -> Optional[Contenuto]:
    giorno = _ora().weekday() if giorno is None else giorno
    nome, funzione = CALENDARIO[giorno % len(CALENDARIO)]
    try:
        contenuto = funzione(db)
    except Exception as exc:  # noqa: BLE001
        LOGGER.warning("Rubrica %s non preparata: %s", nome, exc)
        return None
    if contenuto is None:
        LOGGER.info("Rubrica %s: niente da pubblicare oggi", nome)
    return contenuto


def pubblica(db: Session, giorno: Optional[int] = None) -> Optional[Dict[str, object]]:
    if not instagram.acceso(db):
        return None
    contenuto = prepara(db, giorno)
    if contenuto is None:
        return None
    nome, articoli, testo, (tipo, media_url) = contenuto
    token = instagram._token(db)
    if tipo == "reel":
        contenitore = instagram._contenitore(token, media_type="REELS", video_url=media_url,
                                             caption=testo, share_to_feed="true")
        instagram._attendi(token, contenitore, tentativi=60, pausa=5.0)
    elif tipo == "foto":
        contenitore = instagram._contenitore(token, image_url=media_url, caption=testo)
    else:
        figli = [instagram._contenitore(token, image_url=u, is_carousel_item="true") for u in media_url]
        for figlio in figli:
            instagram._attendi(token, figlio)
        contenitore = instagram._contenitore(token, media_type="CAROUSEL", children=",".join(figli), caption=testo)
    media = instagram._pubblica(token, contenitore)
    instagram_stats.registra(db, media, "reel" if tipo == "reel" else "post", testo, n_items=len(articoli),
                             slot=slot_rubrica(db), rubrica=nome, article_ids=[a.id for a in articoli])
    # Come per il post del giorno, una Storia per ogni pezzo che non l'ha
    # ancora avuta. Non per il quiz: la Storia mostrerebbe il prezzo.
    if nome != "quiz":
        instagram._storie(db, token, [a for a in articoli
                                      if not (a.article_metadata or {}).get("instagram_story")])
    LOGGER.info("Instagram: rubrica %s pubblicata (%s)", nome, media)
    return {"rubrica": nome, "media": media, "articoli": [a.id for a in articoli]}


def slot_rubrica(db: Session) -> str:
    """La fascia della rubrica: la migliore fra quelle diverse da quella del
    post del giorno (senza dati, 12:30 o 21:00)."""
    from statistics import mean
    del_giorno = instagram_stats.slot_di_oggi(db)
    per_slot = instagram_stats.copertura_per_slot(db)
    altre = [s for s in instagram_stats.SLOT if s != del_giorno]
    con_dati = [s for s in altre if per_slot[s]]
    if con_dati:
        return max(con_dati, key=lambda s: mean(per_slot[s]))
    return altre[0]


def rubrica_del_giorno(db: Session, slot: str) -> Optional[Dict[str, object]]:
    """Il job di ogni fascia: la rubrica esce una volta al giorno, nella sua fascia."""
    if not instagram.acceso(db):
        return None
    oggi = _ora().date().isoformat()
    impostazioni = instagram._impostazioni(db)
    if impostazioni.get_value(CHIAVE_GIORNO, default="") == oggi or slot_rubrica(db) != slot:
        return None
    impostazioni.upsert(CHIAVE_GIORNO, oggi)
    return pubblica(db)


# ---------------------------------------------------------------------------
# Commenta LISTA → link in privato
# ---------------------------------------------------------------------------

def _messaggio_link(articoli: List[Article]) -> str:
    from utils.email import _site_url
    site = _site_url()
    righe = ["Ciao! Ecco i link dei pezzi del post 💜", ""]
    for a in articoli[:15]:
        stato = "" if a.status == ArticleStatus.PUBLISHED else " (venduto)"
        righe.append(f"▪️ {a.title} — {instagram._prezzo(a)}{stato}\n{site}/articles/{a.id}")
    righe += ["", f"Tutto il catalogo: {site}", f"Le novità in tempo reale: https://{instagram.TELEGRAM_URL}"]
    return "\n".join(righe)[:1000]


def rispondi_ai_commenti(db: Session) -> int:
    """Chi ha commentato LISTA sotto un nostro post degli ultimi 7 giorni
    riceve in privato i link degli articoli (Instagram permette una risposta
    privata per commento, entro 7 giorni). Torna quante risposte ha mandato."""
    if not instagram.acceso(db):
        return 0
    token = instagram._token(db)
    utente = os.environ["INSTAGRAM_USER_ID"].strip()
    recenti = (db.query(InstagramMedia)
               .filter(InstagramMedia.kind.in_(["post", "reel"]),
                       InstagramMedia.published_at >= _ora() - timedelta(days=7)).all())
    mandate = 0
    for media in recenti:
        try:
            commenti = instagram._chiama("GET", f"{media.media_id}/comments", token,
                                         fields="id,text,username", limit="50").get("data", [])
        except instagram.ErroreInstagram as exc:
            LOGGER.warning("Commenti di %s non letti: %s", media.media_id, exc)
            continue
        ids = [int(i) for i in (media.article_ids or "").split()]
        articoli = [a for a in (db.get(Article, i) for i in ids) if a is not None]
        for c in commenti:
            if PAROLA.lower() not in (c.get("text") or "").lower():
                continue
            if db.get(InstagramReply, c["id"]) is not None:
                continue
            testo = _messaggio_link(articoli) if articoli else (
                f"Ciao! Trovi tutto il catalogo su https://nerdnostalgia.store 💜")
            try:
                instagram._chiama("POST", f"{utente}/messages", token,
                                  recipient=json.dumps({"comment_id": c["id"]}),
                                  message=json.dumps({"text": testo}))
                instagram._chiama("POST", f"{c['id']}/replies", token,
                                  message="Ti ho scritto in privato 📩")
            except instagram.ErroreInstagram as exc:
                LOGGER.warning("Risposta al commento %s non mandata: %s", c["id"], exc)
                continue
            db.add(InstagramReply(comment_id=c["id"], media_id=media.media_id, replied_at=_ora()))
            db.commit()
            mandate += 1
    return mandate
