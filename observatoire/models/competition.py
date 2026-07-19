"""Modèle métier représentant une compétition."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(slots=True)
class Competition:
    """Représentation métier d'une compétition IWWF."""

    id: int
    iwwf_id: str
    nom: str
    date_debut: date | None
    date_fin: date | None
    pays: str
    ville: str
    discipline: str

    @property
    def lieu(self) -> str:
        """Retourne une représentation lisible du lieu."""
        elements = [element for element in (self.ville, self.pays) if element]
        return ", ".join(elements)

    @property
    def periode(self) -> str:
        """Retourne la période de la compétition."""
        if self.date_debut is None and self.date_fin is None:
            return ""

        if self.date_debut is None:
            return self.date_fin.isoformat()

        if self.date_fin is None or self.date_fin == self.date_debut:
            return self.date_debut.isoformat()

        return f"{self.date_debut.isoformat()} → {self.date_fin.isoformat()}"

    def __str__(self) -> str:
        return self.nom
