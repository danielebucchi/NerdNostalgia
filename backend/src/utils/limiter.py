"""
Rate limiter singleton condiviso dalla app FastAPI.
Importato da main.py per registrare middleware + handler,
e da api/*.py per applicare @limiter.limit(...) sugli endpoint.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, default_limits=[])
