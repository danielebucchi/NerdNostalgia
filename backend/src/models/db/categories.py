"""
Modello Category per SQLAlchemy. Gerarchia a 2 livelli (categoria/sottocategoria)
ma il modello supporta auto-relazione di profondita' arbitraria.
"""
from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from .base import BaseModel


class Category(BaseModel):
    __tablename__ = "categories"

    name = Column(String(100), nullable=False)
    slug = Column(String(120), nullable=False, unique=True, index=True)
    parent_id = Column(
        Integer,
        ForeignKey("categories.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    display_order = Column(Integer, nullable=False, default=0)

    parent = relationship("Category", remote_side="Category.id", backref="children")

    def __repr__(self):
        return f"<Category(id={self.id}, slug='{self.slug}', parent_id={self.parent_id})>"
