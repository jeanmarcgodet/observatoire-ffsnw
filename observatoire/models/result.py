"""Modèle métier représentant un résultat sportif."""

from __future__ import annotations

from dataclasses import dataclass

from observatoire.models.competition import Competition
from observatoire.models.rider import Rider


@dataclass(slots=True)
class Result:
    """Résultat obtenu par un rider lors d'une compétition."""

    id: int
    competition: Competition
    rider: Rider
    discipline: str
    tour: str
    score: str
    document_url: str | None = None