"""
Utility per il logging dell'applicazione.
"""
import logging
import sys
from pathlib import Path
from typing import Optional
import colorlog


def setup_logger(
    name: str = "NerdNostalgia",
    level: str = "INFO",
    log_file: Optional[str] = None
) -> logging.Logger:
    """
    Configura e restituisce un logger per l'applicazione.

    Args:
        name: Nome del logger
        level: Livello di log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path del file di log (opzionale)

    Returns:
        Logger configurato
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))

    # Rimuovi handler esistenti per evitare duplicati
    logger.handlers.clear()

    # Formato del log
    log_format = "%(log_color)s%(asctime)s - %(name)s - %(levelname)s%(reset)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    # Handler per console con colori
    console_handler = colorlog.StreamHandler(sys.stdout)
    console_handler.setFormatter(
        colorlog.ColoredFormatter(
            log_format,
            datefmt=date_format,
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red,bg_white',
            }
        )
    )
    logger.addHandler(console_handler)

    # Handler per file (se specificato)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        file_handler.setFormatter(logging.Formatter(file_format, datefmt=date_format))
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str = "NerdNostalgia") -> logging.Logger:
    """
    Ottieni un logger esistente o creane uno nuovo.

    Args:
        name: Nome del logger

    Returns:
        Logger
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        return setup_logger(name)
    return logger
