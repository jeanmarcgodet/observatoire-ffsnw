"""Modèle métier représentant un rider."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Rider:
    """Représentation métier d'un sportif."""

    id: int
    iwwf_id: str
    nom: str
    prenom: str

    @property
    def nom_complet(self) -> str:
        """Retourne le prénom suivi du nom."""
        return f"{self.prenom} {self.nom}".strip()

    def __str__(self) -> str:
        return self.nom_complet