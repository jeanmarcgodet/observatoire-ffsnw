"""Objet métier représentant la carrière enregistrée d'un rider."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import TYPE_CHECKING

from observatoire.models.competition import Competition
from observatoire.models.result import Result
from observatoire.models.rider import Rider

if TYPE_CHECKING:
    from observatoire.analytics import RiderStatistics


@dataclass(slots=True)
class RiderCareer:
    """Agrège un rider, ses résultats et ses compétitions."""

    rider: Rider
    results: list[Result] = field(default_factory=list)

    @property
    def competitions(self) -> list[Competition]:
        """Retourne les compétitions distinctes de la carrière."""
        competitions_by_id: dict[int, Competition] = {}

        for result in self.results:
            competitions_by_id[result.competition.id] = result.competition

        return sorted(
            competitions_by_id.values(),
            key=lambda competition: (
                competition.date_debut or date.min,
                competition.id,
            ),
        )

    @property
    def number_of_results(self) -> int:
        """Retourne le nombre de résultats enregistrés."""
        return len(self.results)

    @property
    def number_of_competitions(self) -> int:
        """Retourne le nombre de compétitions distinctes."""
        return len(self.competitions)

    @property
    def first_competition(self) -> Competition | None:
        """Retourne la première compétition connue."""
        competitions = self.competitions

        if not competitions:
            return None

        return competitions[0]

    @property
    def last_competition(self) -> Competition | None:
        """Retourne la compétition la plus récente connue."""
        competitions = self.competitions

        if not competitions:
            return None

        return competitions[-1]

    @property
    def disciplines(self) -> list[str]:
        """Retourne les disciplines distinctes pratiquées."""
        return sorted(
            {
                result.discipline
                for result in self.results
                if result.discipline
            }
        )

    @property
    def seasons(self) -> list[int]:
        """Retourne les saisons présentes dans les résultats."""
        return sorted(
            {
                result.competition.date_debut.year
                for result in self.results
                if result.competition.date_debut is not None
            }
        )

    @property
    def statistics(self) -> RiderStatistics:
        """Construit les statistiques associées à la carrière."""
        from observatoire.analytics import RiderStatistics

        return RiderStatistics(self)
