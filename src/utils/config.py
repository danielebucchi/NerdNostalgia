"""
Utility per caricare e gestire la configurazione.
"""
import yaml
from pathlib import Path
from typing import Any, Optional
from dotenv import load_dotenv
import os


class Config:
    """
    Gestisce la configurazione dell'applicazione.
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Inizializza il config manager.

        Args:
            config_path: Path del file di configurazione YAML.
                        Se None, usa config/config.yaml
        """
        # Carica variabili d'ambiente da .env se esiste
        load_dotenv()

        # Determina il path del config
        if config_path is None:
            project_root = Path(__file__).parent.parent.parent
            config_path = project_root / "config" / "config.yaml"

        self.config_path = Path(config_path)
        self._config = self._load_config()

    def _load_config(self) -> dict:
        """
        Carica la configurazione dal file YAML.

        Returns:
            Dizionario con la configurazione
        """
        if not self.config_path.exists():
            raise FileNotFoundError(
                f"File di configurazione non trovato: {self.config_path}\n"
                f"Copia config/config.template.yaml in config/config.yaml "
                f"e inserisci le tue credenziali."
            )

        with open(self.config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        # Sostituisci i placeholder con variabili d'ambiente se presenti
        self._substitute_env_vars(config)

        return config

    def _substitute_env_vars(self, config: dict) -> None:
        """
        Sostituisce i placeholder con variabili d'ambiente.
        Modifica il dizionario in-place.

        Args:
            config: Dizionario di configurazione
        """
        for key, value in config.items():
            if isinstance(value, dict):
                self._substitute_env_vars(value)
            elif isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                # Formato: ${ENV_VAR_NAME}
                env_var = value[2:-1]
                config[key] = os.getenv(env_var, value)

    def get(self, key: str, default: Any = None) -> Any:
        """
        Ottieni un valore dalla configurazione usando dot notation.

        Args:
            key: Chiave da cercare (es. "ebay.app_id")
            default: Valore di default se la chiave non esiste

        Returns:
            Valore della configurazione
        """
        keys = key.split(".")
        value = self._config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def get_ebay_config(self) -> dict:
        """Ottieni la configurazione di eBay."""
        return self.get("ebay", {})

    def get_app_config(self) -> dict:
        """Ottieni la configurazione dell'applicazione."""
        return self.get("app", {})

    def is_sandbox(self, platform: str = "ebay") -> bool:
        """
        Controlla se una piattaforma è in modalità sandbox.

        Args:
            platform: Nome della piattaforma

        Returns:
            True se in modalità sandbox
        """
        return self.get(f"{platform}.sandbox", False)

    @property
    def config(self) -> dict:
        """Restituisce l'intera configurazione."""
        return self._config
