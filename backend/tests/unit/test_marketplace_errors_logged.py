"""Unit: gli errori di eBay e CardTrader finiscono nei log con la risposta.

Prima chi chiamava li trasformava in un 502 e la causa si perdeva: per le
varianti eBay si e' dovuto rifare la chiamata per scoprirla."""
import logging

from utils.cardtrader_client import CardTraderError
from utils.ebay_client import EbayError


def test_ebay_error_logs_the_response(caplog):
    with caplog.at_level(logging.INFO):
        EbayError("eBay 400 su /offer", 400, {"errors": [{"errorId": 25001}]})
    rec = caplog.records[-1]
    assert rec.levelno == logging.WARNING and "25001" in rec.getMessage()


def test_expected_404_is_only_informative(caplog):
    with caplog.at_level(logging.INFO):
        EbayError("eBay 404", 404)
        CardTraderError("CardTrader 404", 404)
    assert all(r.levelno == logging.INFO for r in caplog.records)


def test_cardtrader_error_logs_the_response(caplog):
    with caplog.at_level(logging.INFO):
        CardTraderError("CardTrader 422 su /products", 422, {"error": "price too low"})
    assert "price too low" in caplog.records[-1].getMessage()
