"""
Parser per file CSV contenenti articoli.
"""
import pandas as pd
from pathlib import Path
from typing import List
from decimal import Decimal

from src.models.item import Item


class CSVParser:
    """
    Parser per leggere articoli da file CSV.
    """

    REQUIRED_COLUMNS = ["title", "description", "price", "quantity", "category", "condition"]

    def __init__(self, csv_path: str):
        """
        Inizializza il parser.

        Args:
            csv_path: Path del file CSV
        """
        self.csv_path = Path(csv_path)
        if not self.csv_path.exists():
            raise FileNotFoundError(f"File CSV non trovato: {csv_path}")

    def parse(self) -> List[Item]:
        """
        Legge il CSV e restituisce una lista di Item.

        Returns:
            Lista di oggetti Item

        Raises:
            ValueError: Se il CSV non ha le colonne richieste
        """
        # Leggi il CSV
        df = pd.read_csv(self.csv_path)

        # Verifica colonne richieste
        missing_columns = set(self.REQUIRED_COLUMNS) - set(df.columns)
        if missing_columns:
            raise ValueError(
                f"Colonne mancanti nel CSV: {', '.join(missing_columns)}\n"
                f"Colonne richieste: {', '.join(self.REQUIRED_COLUMNS)}"
            )

        # Converti in lista di Item
        items = []
        for idx, row in df.iterrows():
            try:
                item = self._row_to_item(row)
                items.append(item)
            except Exception as e:
                print(f"Errore alla riga {idx + 2}: {e}")
                # Continua con le altre righe
                continue

        return items

    def _row_to_item(self, row: pd.Series) -> Item:
        """
        Converte una riga del CSV in un oggetto Item.

        Args:
            row: Riga del DataFrame pandas

        Returns:
            Oggetto Item
        """
        # Campi richiesti
        item_data = {
            "title": str(row["title"]),
            "description": str(row["description"]),
            "price": Decimal(str(row["price"])),
            "quantity": int(row["quantity"]),
            "category": str(row["category"]),
            "condition": str(row["condition"]),
        }

        # Campi opzionali
        optional_fields = ["sku", "brand", "shipping_weight"]
        for field in optional_fields:
            if field in row and pd.notna(row[field]):
                item_data[field] = row[field]

        # Gestione immagini (separati da ; o ,)
        if "images" in row and pd.notna(row["images"]):
            images_str = str(row["images"])
            if ";" in images_str:
                item_data["images"] = [img.strip() for img in images_str.split(";")]
            else:
                item_data["images"] = [img.strip() for img in images_str.split(",")]

        # Gestione tags (separati da ; o ,)
        if "tags" in row and pd.notna(row["tags"]):
            tags_str = str(row["tags"])
            if ";" in tags_str:
                item_data["tags"] = [tag.strip() for tag in tags_str.split(";")]
            else:
                item_data["tags"] = [tag.strip() for tag in tags_str.split(",")]

        return Item(**item_data)

    @staticmethod
    def get_template_columns() -> List[str]:
        """
        Restituisce le colonne da usare per un template CSV.

        Returns:
            Lista di nomi di colonne
        """
        return [
            "title",
            "description",
            "price",
            "quantity",
            "category",
            "condition",
            "sku",
            "brand",
            "images",
            "tags",
            "shipping_weight",
        ]
