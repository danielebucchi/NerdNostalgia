"""
Statistiche Instagram e scelte che ne seguono: raggiungere piu' persone.

- `importa_storico` e `aggiorna`: ogni post, Storia e Reel del profilo
  (anche quelli pubblicati a mano dall'app, per partire con dei dati) finisce
  in instagram_media con copertura, visualizzazioni, salvataggi e condivisioni.
  Le statistiche delle Storie Instagram le tiene solo 24 ore: si leggono
  spesso; quelle dei post si assestano in una settimana e si rileggono per
  30 giorni.
- `slot_di_oggi`: a che ora esce il post del giorno. Fra gli SLOT si sceglie
  quello con la copertura media migliore; uno slot con meno di MIN_DATI post
  si prova prima (si impara), e un giorno su cinque se ne prova uno a caso
  (le abitudini dei follower cambiano).
- `hashtag_per`: gli hashtag del post. Per ogni hashtag la copertura media
  dei post che l'hanno usato; si tengono i migliori del gruppo giusto
  (Pokémon, videogiochi...) piu' qualcuno mai provato, da scoprire.
- `report`: il riassunto della settimana, per email il lunedi'.

Serve l'autorizzazione instagram_manage_insights sul token: senza, le
statistiche restano vuote e le scelte ripiegano sui valori fissi.
"""
import logging
import os
import random
import re
from datetime import date, datetime, timedelta, timezone
from statistics import mean
from typing import Dict, Iterable, List, Optional
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from models.db import Article, InstagramMedia
from utils import instagram

LOGGER = logging.getLogger("instagram_stats")
ROMA = ZoneInfo("Europe/Rome")

SLOT = ["12:30", "18:30", "21:00"]
SLOT_FISSO = "18:30"
MIN_DATI = 3
ESPLORA = 0.2
FINESTRA_SCELTE = timedelta(days=90)
CHIAVE_SLOT = "instagram_slot_day"

METRICHE = {
    "post": ["reach", "views", "saved", "shares", "total_interactions"],
    "reel": ["reach", "views", "saved", "shares", "total_interactions"],
    "story": ["reach", "views", "shares", "total_interactions"],
}

# Hashtag per gruppo: i primi di ogni lista sono quelli di partenza, gli
# altri entrano a turno e restano se funzionano.
GRUPPI = {
    "base": ["#nerdnostalgia", "#collezionismo", "#vintage", "#nerd", "#anni90", "#nostalgia",
             "#retro", "#collezione", "#italia", "#mercatino", "#usato"],
    "pok": ["#pokemon", "#cartepokemon", "#pokemontcg", "#pokemonita", "#pokemoncards",
            "#pokemonitalia", "#pokemoncollection", "#pokemoncommunity", "#tcg", "#pokemoncard"],
    "videogioc": ["#retrogaming", "#videogiochi", "#retrogames", "#gamer", "#nintendo",
                  "#playstation", "#gamecollection", "#videogame", "#retrogamer", "#gaming"],
    "console": ["#retrogaming", "#console", "#retroconsole", "#nintendo", "#playstation", "#sega"],
    "funko": ["#funkopop", "#funko", "#funkopopcollection", "#funkocollector"],
    "yu-gi-oh": ["#yugioh", "#yugiohita", "#yugiohcards", "#tcg"],
    "magic": ["#mtg", "#magicthegathering", "#mtgcommunity", "#tcg"],
    "giocattol": ["#giocattolivintage", "#anni90", "#giocattoli", "#toys", "#vintagetoys"],
    "gormiti": ["#gormiti", "#giocattolivintage", "#anni2000"],
    "bakugan": ["#bakugan", "#giocattolivintage", "#anni2000"],
    "beyblade": ["#beyblade", "#beybladeburst", "#giocattolivintage"],
}
MAX_HASHTAG = 18
DA_SCOPRIRE = 3


def _ora_locale(utc: datetime) -> datetime:
    return utc.replace(tzinfo=timezone.utc).astimezone(ROMA).replace(tzinfo=None)


def _hashtag_di(testo: Optional[str]) -> List[str]:
    return sorted({t.lower() for t in re.findall(r"#\w+", testo or "")})


# ---------------------------------------------------------------------------
# Raccolta
# ---------------------------------------------------------------------------

def registra(db: Session, media_id: str, kind: str, testo: str = "", n_items: int = 1,
             fallback: bool = False, slot: Optional[str] = None, rubrica: Optional[str] = None,
             article_ids: Iterable[int] = ()) -> None:
    """Annota un contenuto appena pubblicato: le statistiche arrivano dopo."""
    if db.get(InstagramMedia, media_id) is not None:
        return
    db.add(InstagramMedia(media_id=media_id, kind=kind, published_at=datetime.now(ROMA).replace(tzinfo=None),
                          slot=slot, n_items=n_items, fallback=fallback, rubrica=rubrica,
                          article_ids=" ".join(str(i) for i in article_ids),
                          hashtags=" ".join(_hashtag_di(testo))))
    db.commit()


def importa_storico(db: Session, quanti: int = 100) -> int:
    """I post del profilo che non conosciamo ancora (anche quelli fatti a
    mano): danno subito dei dati su orari e hashtag."""
    if not instagram.configurato(db):
        return 0
    token = instagram._token(db)
    utente = os.environ["INSTAGRAM_USER_ID"].strip()
    dati = instagram._chiama("GET", f"{utente}/media", token,
                             fields="id,caption,media_type,media_product_type,timestamp",
                             limit=str(min(quanti, 100))).get("data", [])
    nuovi = 0
    for m in dati:
        if db.get(InstagramMedia, m["id"]) is not None:
            continue
        kind = "reel" if m.get("media_product_type") == "REELS" else "post"
        quando = _ora_locale(datetime.strptime(m["timestamp"], "%Y-%m-%dT%H:%M:%S%z")
                             .astimezone(timezone.utc).replace(tzinfo=None))
        db.add(InstagramMedia(media_id=m["id"], kind=kind, published_at=quando,
                              hashtags=" ".join(_hashtag_di(m.get("caption")))))
        nuovi += 1
    db.commit()
    return nuovi


def _leggi(token: str, media_id: str, metriche: List[str]) -> Dict[str, int]:
    """Le metriche di un contenuto. Se Instagram ne rifiuta una (cambiano
    spesso nome), si chiedono una per una e si tiene quello che c'e'."""
    def valori(risposta: dict) -> Dict[str, int]:
        out = {}
        for voce in risposta.get("data", []):
            v = voce.get("values", [{}])[0].get("value") if voce.get("values") else voce.get("total_value", {}).get("value")
            if isinstance(v, (int, float)):
                out[voce["name"]] = int(v)
        return out
    try:
        return valori(instagram._chiama("GET", f"{media_id}/insights", token, metric=",".join(metriche)))
    except instagram.ErroreInstagram:
        out = {}
        for m in metriche:
            try:
                out.update(valori(instagram._chiama("GET", f"{media_id}/insights", token, metric=m)))
            except instagram.ErroreInstagram:
                continue
        return out


def aggiorna(db: Session) -> int:
    """Rilegge le statistiche: Storie delle ultime 24 ore, post e Reel degli
    ultimi 30 giorni. Torna quanti contenuti ha aggiornato."""
    if not instagram.configurato(db):
        return 0
    token = instagram._token(db)
    adesso = datetime.now(ROMA).replace(tzinfo=None)
    righe = (db.query(InstagramMedia)
             .filter(InstagramMedia.published_at >= adesso - timedelta(days=30)).all())
    fatti = 0
    for r in righe:
        if r.kind == "story" and adesso - r.published_at > timedelta(hours=24):
            continue
        valori = _leggi(token, r.media_id, METRICHE.get(r.kind, METRICHE["post"]))
        if not valori:
            continue
        r.reach = valori.get("reach", r.reach)
        r.views = valori.get("views", r.views)
        r.saved = valori.get("saved", r.saved)
        r.shares = valori.get("shares", r.shares)
        r.interactions = valori.get("total_interactions", r.interactions)
        r.insights_at = adesso
        fatti += 1
    db.commit()
    return fatti


# ---------------------------------------------------------------------------
# Scelte
# ---------------------------------------------------------------------------

def _post_con_dati(db: Session) -> List[InstagramMedia]:
    dal = datetime.now(ROMA).replace(tzinfo=None) - FINESTRA_SCELTE
    return (db.query(InstagramMedia)
            .filter(InstagramMedia.kind.in_(["post", "reel"]), InstagramMedia.reach.isnot(None),
                    InstagramMedia.published_at >= dal).all())


def _slot_vicino(quando: datetime) -> str:
    minuti = quando.hour * 60 + quando.minute
    return min(SLOT, key=lambda s: abs(int(s[:2]) * 60 + int(s[3:]) - minuti))


def copertura_per_slot(db: Session) -> Dict[str, List[int]]:
    """Le coperture dei post, divise per fascia oraria (anche quelli fatti a
    mano, assegnati allo slot piu' vicino all'ora di pubblicazione)."""
    per_slot = {s: [] for s in SLOT}
    for p in _post_con_dati(db):
        per_slot[p.slot if p.slot in per_slot else _slot_vicino(p.published_at)].append(p.reach)
    return per_slot


def scegli_slot(db: Session, giorno: date) -> str:
    per_slot = copertura_per_slot(db)
    if not any(per_slot.values()):
        return SLOT_FISSO
    caso = random.Random(giorno.toordinal())
    da_provare = [s for s in SLOT if len(per_slot[s]) < MIN_DATI]
    if da_provare:
        return min(da_provare, key=lambda s: (len(per_slot[s]), SLOT.index(s)))
    if caso.random() < ESPLORA:
        return caso.choice(SLOT)
    return max(SLOT, key=lambda s: mean(per_slot[s]))


def slot_di_oggi(db: Session) -> str:
    """Lo slot del post di oggi: scelto una volta al mattino e ricordato."""
    oggi = datetime.now(ROMA).date().isoformat()
    impostazioni = instagram._impostazioni(db)
    giorno, _, slot = (impostazioni.get_value(CHIAVE_SLOT, default="") or "").partition("|")
    if giorno == oggi and slot in SLOT:
        return slot
    slot = scegli_slot(db, datetime.now(ROMA).date())
    impostazioni.upsert(CHIAVE_SLOT, f"{oggi}|{slot}")
    return slot


def copertura_per_hashtag(db: Session) -> Dict[str, float]:
    per_tag: Dict[str, List[int]] = {}
    for p in _post_con_dati(db):
        for t in (p.hashtags or "").split():
            per_tag.setdefault(t, []).append(p.reach)
    return {t: mean(v) for t, v in per_tag.items()}


def _gruppi(articoli: Iterable[Article]) -> List[str]:
    trovati = ["base"]
    for a in articoli:
        nomi = []
        cat = a.category
        while cat is not None:
            nomi.append((cat.name or "").lower())
            cat = cat.parent if cat.parent_id else None
        for chiave in GRUPPI:
            if chiave != "base" and chiave not in trovati and any(chiave in n for n in nomi):
                trovati.append(chiave)
    return trovati


def hashtag_per(db: Session, articoli: List[Article], seme: int = 0) -> str:
    """Gli hashtag del post: i migliori fra quelli dei gruppi degli articoli,
    piu' DA_SCOPRIRE mai (o quasi) provati."""
    punteggi = copertura_per_hashtag(db)
    candidati: List[str] = []
    for g in _gruppi(articoli):
        candidati += [t for t in GRUPPI[g] if t not in candidati]
    if not punteggi:
        # Niente dati: i primi di ogni gruppo, come prima.
        scelti = ["#nerdnostalgia"] + [t for g in _gruppi(articoli) for t in GRUPPI[g][:4] if t != "#nerdnostalgia"]
        return " ".join(list(dict.fromkeys(scelti))[:MAX_HASHTAG])
    noti = sorted((t for t in candidati if t in punteggi), key=lambda t: punteggi[t], reverse=True)
    nuovi = [t for t in candidati if t not in punteggi]
    random.Random(seme).shuffle(nuovi)
    scelti = ["#nerdnostalgia"]
    scelti += [t for t in noti if t != "#nerdnostalgia"][:MAX_HASHTAG - 1 - DA_SCOPRIRE]
    scelti += nuovi[:MAX_HASHTAG - len(scelti)]
    scelti += [t for t in noti if t not in scelti][:MAX_HASHTAG - len(scelti)]
    return " ".join(scelti[:MAX_HASHTAG])


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def report(db: Session) -> Optional[Dict[str, str]]:
    """Il riassunto degli ultimi 7 giorni, testo per email."""
    adesso = datetime.now(ROMA).replace(tzinfo=None)
    settimana = (db.query(InstagramMedia)
                 .filter(InstagramMedia.published_at >= adesso - timedelta(days=7))
                 .order_by(InstagramMedia.published_at).all())
    if not settimana:
        return None
    righe = ["Instagram, ultimi 7 giorni", ""]
    for kind, nome in (("post", "Post"), ("story", "Storie"), ("reel", "Reel")):
        gruppo = [m for m in settimana if m.kind == kind]
        if gruppo:
            copertura = sum(m.reach or 0 for m in gruppo)
            righe.append(f"{nome}: {len(gruppo)}, persone raggiunte in totale {copertura}")
    con_dati = [m for m in settimana if m.reach is not None and m.kind != "story"]
    if con_dati:
        migliore = max(con_dati, key=lambda m: m.reach)
        righe += ["", f"Post migliore: {migliore.published_at:%d/%m %H:%M}, {migliore.reach} persone, "
                      f"{migliore.saved or 0} salvataggi, {migliore.shares or 0} condivisioni"]
    per_slot = copertura_per_slot(db)
    righe += ["", "Copertura media per orario (ultimi 90 giorni):"]
    for s in SLOT:
        v = per_slot[s]
        righe.append(f"  {s}: " + (f"{round(mean(v))} persone su {len(v)} post" if v else "nessun dato"))
    tag = sorted(copertura_per_hashtag(db).items(), key=lambda kv: kv[1], reverse=True)[:8]
    if tag:
        righe += ["", "Hashtag che portano piu' persone: " + ", ".join(f"{t} ({round(v)})" for t, v in tag)]
    righe += ["", f"Orario scelto per i prossimi post: {scegli_slot(db, adesso.date())}"]
    return {"subject": "Instagram: com'e' andata la settimana", "text": "\n".join(righe)}


def manda_report(db: Session) -> bool:
    from utils.email import _config, send_email
    contenuto = report(db)
    if contenuto is None:
        return False
    return send_email(to=_config()["to_admin"], subject=contenuto["subject"], text_body=contenuto["text"])
