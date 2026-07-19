"""Modèle agrégeant une compétition et ses résultats."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from observatoire.models.competition import Competition
from observatoire.models.result import Result

if TYPE_CHECKING:
    from observatoire.analytics.competition_statistics import (
        CompetitionStatistics,
    )


@dataclass(slots=True)
class CompetitionReport:
    """Ensemble des données disponibles pour une compétition."""

    competition: Competition
    results: list[Result] = field(default_factory=list)

    @property
    def number_of_results(self) -> int:
        """Retourne le nombre de résultats enregistrés."""
        return len(self.results)

    @property
    def disciplines(self) -> list[str]:
        """Retourne les disciplines représentées."""
        return sorted(
            {
                result.discipline.strip().lower()
                for result in self.results
                if result.discipline.strip()
            }
        )

    @property
    def statistics(self) -> CompetitionStatistics:
        """Construit les statistiques de la compétition."""
        from observatoire.analytics.competition_statistics import (
            CompetitionStatistics,
        )

        return CompetitionStatistics(self)