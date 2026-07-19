"""Modèle métier représentant un résultat sportif."""

from __future__ import annotations

from dataclasses import dataclass

from observatoire.models.competition import Competition


@dataclass(slots=True)
class Result:
    """Résultat obtenu par un rider lors d'un tour de compétition."""

    id: int
    rider_id: int
    competition: Competition
    discipline: str
    tour: str
    score: str
    document_url: str | None = None

    @property
    def competition_id(self) -> int:
        """Retourne l'identifiant interne de la compétition."""
        return self.competition.id

    def __str__(self) -> str:
        return (
            f"{self.competition.nom} — "
            f"{self.discipline} — "
            f"{self.tour} — "
            f"{self.score}"
        )
