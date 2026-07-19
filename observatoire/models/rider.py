"""Modèle métier représentant un rider."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Rider:
    """Rider enregistré dans l'observatoire."""

    id: int
    iwwf_id: str
    nom: str
    prenom: str
    nation: str | None = None
    annee_naissance: int | None = None
    sexe: str | None = None

    @property
    def nom_complet(self) -> str:
        """Retourne le prénom et le nom du rider."""
        return f"{self.prenom} {self.nom}".strip()

    @property
    def full_name(self) -> str:
        """Alias anglophone de nom_complet."""
        return self.nom_complet