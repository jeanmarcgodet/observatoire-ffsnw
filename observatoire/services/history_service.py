"""Service d'accès aux données historiques de l'Observatoire."""

from __future__ import annotations

from observatoire.models import Competition, Rider
from observatoire.repositories import (
    CompetitionRepository,
    RiderRepository,
)


class HistoryService:
    """Coordonne les repositories nécessaires aux consultations historiques."""

    def __init__(
        self,
        rider_repository: RiderRepository | None = None,
        competition_repository: CompetitionRepository | None = None,
    ) -> None:
        self.riders = rider_repository or RiderRepository()
        self.competitions = competition_repository or CompetitionRepository()

    def get_rider(self, iwwf_id: str) -> Rider | None:
        """Retourne un rider à partir de son identifiant IWWF."""
        return self.riders.get_by_iwwf_id(iwwf_id)

    def get_rider_by_id(self, rider_id: int) -> Rider | None:
        """Retourne un rider à partir de son identifiant interne."""
        return self.riders.get_by_id(rider_id)

    def search_riders(self, query: str, limit: int = 20) -> list[Rider]:
        """Recherche des riders."""
        return self.riders.search(query, limit=limit)

    def get_competition(self, iwwf_id: str) -> Competition | None:
        """Retourne une compétition à partir de son identifiant IWWF."""
        return self.competitions.get_by_iwwf_id(iwwf_id)

    def get_competition_by_id(
        self,
        competition_id: int,
    ) -> Competition | None:
        """Retourne une compétition à partir de son identifiant interne."""
        return self.competitions.get_by_id(competition_id)

    def search_competitions(
        self,
        query: str,
        limit: int = 20,
    ) -> list[Competition]:
        """Recherche des compétitions."""
        return self.competitions.search(query, limit=limit)

    def list_competitions(self, limit: int = 100) -> list[Competition]:
        """Retourne les compétitions enregistrées."""
        return self.competitions.list_all(limit=limit)
