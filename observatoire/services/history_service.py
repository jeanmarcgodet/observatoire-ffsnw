"""Services de consultation de l'historique sportif."""

from __future__ import annotations

from observatoire.models import (
    Competition,
    CompetitionReport,
    Rider,
    RiderCareer,
)
from observatoire.repositories import (
    CompetitionRepository,
    ResultRepository,
    RiderRepository,
)


class HistoryService:
    """Service regroupant les consultations historiques."""

    def __init__(self) -> None:
        self.rider_repository = RiderRepository()
        self.competition_repository = CompetitionRepository()
        self.result_repository = ResultRepository()

    def get_rider(
        self,
        iwwf_id: str,
    ) -> Rider | None:
        """Recherche un rider par son identifiant IWWF."""
        return self.rider_repository.get_by_iwwf_id(iwwf_id)

    def get_rider_by_id(
        self,
        rider_id: int,
    ) -> Rider | None:
        """Recherche un rider par son identifiant interne."""
        return self.rider_repository.get_by_id(rider_id)

    def search_riders(
        self,
        query: str,
    ) -> list[Rider]:
        """Recherche des riders par leur nom ou leur prénom."""
        return self.rider_repository.search(query)

    def get_competition(
        self,
        iwwf_id: str,
    ) -> Competition | None:
        """Recherche une compétition par son identifiant IWWF."""
        return self.competition_repository.get_by_iwwf_id(
            iwwf_id
        )

    def list_competitions(self) -> list[Competition]:
        """Retourne toutes les compétitions."""
        return self.competition_repository.list_all()

    def get_rider_career(
        self,
        iwwf_id: str,
    ) -> RiderCareer | None:
        """Retourne un rider accompagné de ses résultats."""
        rider = self.rider_repository.get_by_iwwf_id(iwwf_id)

        if rider is None:
            return None

        results = self.result_repository.list_by_rider_id(
            rider.id
        )

        return RiderCareer(
            rider=rider,
            results=results,
        )

    def get_competition_report(
        self,
        iwwf_id: str,
    ) -> CompetitionReport | None:
        """Retourne une compétition accompagnée de ses résultats."""
        competition = (
            self.competition_repository.get_by_iwwf_id(iwwf_id)
        )

        if competition is None:
            return None

        results = (
            self.result_repository.list_by_competition_id(
                competition.id
            )
        )

        return CompetitionReport(
            competition=competition,
            results=results,
        )