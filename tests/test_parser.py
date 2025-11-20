"""
Test per il parser CSV.
"""
import pytest
from pathlib import Path
from decimal import Decimal

from src.parsers.csv_parser import CSVParser
from src.models.item import Item


def test_parse_example_csv():
    """Test parsing del file example.csv"""
    csv_path = Path(__file__).parent.parent / "data" / "example.csv"

    parser = CSVParser(str(csv_path))
    items = parser.parse()

    # Verifica che siano stati parsati gli articoli
    assert len(items) > 0

    # Verifica il primo articolo
    first_item = items[0]
    assert isinstance(first_item, Item)
    assert first_item.title is not None
    assert first_item.price > 0
    assert first_item.quantity >= 0


def test_item_validation():
    """Test validazione di un Item"""
    # Item valido
    item = Item(
        title="Test Item",
        description="Questo è un test item con una descrizione sufficientemente lunga",
        price=Decimal("10.00"),
        quantity=1,
        category="123",
        condition="new"
    )
    assert item.condition == "new"

    # Prezzo negativo dovrebbe fallire
    with pytest.raises(ValueError):
        Item(
            title="Test",
            description="Test description",
            price=Decimal("-10.00"),
            quantity=1,
            category="123",
            condition="new"
        )

    # Condizione non valida dovrebbe fallire
    with pytest.raises(ValueError):
        Item(
            title="Test",
            description="Test description",
            price=Decimal("10.00"),
            quantity=1,
            category="123",
            condition="invalid_condition"
        )


def test_csv_parser_missing_file():
    """Test che il parser sollevi un errore se il file non esiste"""
    with pytest.raises(FileNotFoundError):
        CSVParser("nonexistent_file.csv")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
