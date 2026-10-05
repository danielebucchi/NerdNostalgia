"""Il link per seguire la spedizione deve portare dal corriere.

Senza schema il browser lo legge come un percorso del sito: incollando
"brt.it/..." il cliente finiva su nerdnostalgia.store/brt.it/... invece
che dal corriere. E quel valore entra dentro un href, sia nel profilo sia
nell'email, quindi gli schemi che eseguono codice non devono passare.
"""
import pytest

from api.orders import _link_tracciamento as link


@pytest.mark.parametrize(
    "scritto, atteso",
    [
        # il caso che si rompeva: schema dimenticato
        ("brt.it/tracking/12345", "https://brt.it/tracking/12345"),
        ("www.gls-italy.com/?id=9", "https://www.gls-italy.com/?id=9"),
        # gia' completi: si lasciano com'erano
        ("https://brt.it/x", "https://brt.it/x"),
        ("http://brt.it/x", "http://brt.it/x"),
        ("HTTPS://BRT.IT/x", "HTTPS://BRT.IT/x"),
        # spazi intorno
        ("  brt.it/x  ", "https://brt.it/x"),
        # vuoto: nessun link, non una stringa vuota
        ("", None),
        ("   ", None),
    ],
)
def test_tracking_url_is_made_absolute(scritto, atteso):
    assert link(scritto) == atteso


@pytest.mark.parametrize(
    "pericoloso",
    [
        "javascript:alert(1)",
        "JavaScript:alert(1)",
        "data:text/html,<script>alert(1)</script>",
        "vbscript:msgbox(1)",
        "ftp://chissadove/x",
    ],
)
def test_dangerous_schemes_do_not_become_links(pericoloso):
    """Finisce dentro un href nel profilo del cliente e nell'email: uno
    schema che esegue codice girerebbe nel suo browser."""
    assert link(pericoloso) is None
