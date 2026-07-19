"""Calcul des statistiques relatives à une compétition."""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field

from observatoire.models import (
    CompetitionReport,
    Result,
    Rider,
    SlalomScore,
)


@dataclass(slots=True)
class CompetitionStatistics:
    """Statistiques calculées à partir d'une compétition."""

    report: CompetitionReport

    _results_by_discipline: dict[str, list[Result]] = field(
        init=False,
        repr=False,
    )

    def __post_init__(self) -> None:
        self._results_by_discipline = defaultdict(list)

        for result in self.report.results:
            discipline = result.discipline.strip().lower()

            if discipline:
                self._results_by_discipline[discipline].append(
                    result
                )

    @property
    def number_of_results(self) -> int:
        """Retourne le nombre total de résultats."""
        return len(self.report.results)

    @property
    def disciplines(self) -> list[str]:
        """Retourne les disciplines représentées."""
        return sorted(self._results_by_discipline)

    @property
    def riders(self) -> list[Rider]:
        """Retourne les riders distincts de la compétition."""
        riders_by_id: dict[int, Rider] = {}

        for result in self.report.results:
            rider = result.rider
            riders_by_id[rider.id] = rider

        return sorted(
            riders_by_id.values(),
            key=lambda rider: (
                rider.nom.lower(),
                rider.prenom.lower(),
            ),
        )

    @property
    def number_of_riders(self) -> int:
        """Retourne le nombre de riders distincts."""
        return len(self.riders)

    @property
    def nations(self) -> list[str]:
        """Retourne les nations représentées."""
        return sorted(
            {
                rider.nation.strip().upper()
                for rider in self.riders
                if rider.nation
                and rider.nation.strip()
            }
        )

    @property
    def number_of_nations(self) -> int:
        """Retourne le nombre de nations représentées."""
        return len(self.nations)

    @property
    def number_of_finals(self) -> int:
        """Compte les résultats associés à une finale."""
        return sum(
            1
            for result in self.report.results
            if "finale" in result.tour.strip().lower()
        )

    @property
    def tour_counts(self) -> dict[str, int]:
        """Compte les résultats par intitulé de tour."""
        counter = Counter(
            result.tour.strip()
            for result in self.report.results
            if result.tour
            and result.tour.strip()
        )

        return dict(
            sorted(
                counter.items(),
                key=lambda item: item[0].lower(),
            )
        )

    @property
    def nation_counts(self) -> dict[str, int]:
        """Compte les riders distincts par nation."""
        counter = Counter(
            rider.nation.strip().upper()
            for rider in self.riders
            if rider.nation
            and rider.nation.strip()
        )

        return dict(
            sorted(
                counter.items(),
                key=lambda item: (-item[1], item[0]),
            )
        )

    @property
    def gender_counts(self) -> dict[str, int]:
        """Compte les riders distincts par sexe."""
        counter = Counter(
            rider.sexe.strip().upper()
            for rider in self.riders
            if rider.sexe
            and rider.sexe.strip()
        )

        return dict(sorted(counter.items()))

    def results_for(
        self,
        discipline: str,
    ) -> list[Result]:
        """Retourne les résultats d'une discipline."""
        normalized = discipline.strip().lower()

        return list(
            self._results_by_discipline.get(
                normalized,
                [],
            )
        )

    def riders_for(
        self,
        discipline: str,
    ) -> list[Rider]:
        """Retourne les riders distincts d'une discipline."""
        riders_by_id: dict[int, Rider] = {}

        for result in self.results_for(discipline):
            riders_by_id[result.rider.id] = result.rider

        return sorted(
            riders_by_id.values(),
            key=lambda rider: (
                rider.nom.lower(),
                rider.prenom.lower(),
            ),
        )

    def best_numeric_result(
        self,
        discipline: str,
    ) -> Result | None:
        """
        Retourne le résultat possédant le score numérique maximal.

        Cette méthode convient notamment au saut et aux figures.
        """
        valid_results: list[tuple[float, Result]] = []

        for result in self.results_for(discipline):
            numeric_score = self._extract_first_number(
                result.score
            )

            if numeric_score is not None:
                valid_results.append(
                    (numeric_score, result)
                )

        if not valid_results:
            return None

        return max(
            valid_results,
            key=lambda item: item[0],
        )[1]

    def best_jump(self) -> Result | None:
        """Retourne le meilleur résultat en saut."""
        return self.best_numeric_result("jump")

    def best_tricks(self) -> Result | None:
        """Retourne le meilleur résultat en figures."""
        return self.best_numeric_result("tricks")

    def best_overall_component(self) -> Result | None:
        """Retourne la meilleure composante numérique overall."""
        return self.best_numeric_result("overall")

    def best_slalom(self) -> Result | None:
        """Retourne le meilleur résultat principal en slalom."""
        valid_results: list[tuple[SlalomScore, Result]] = []

        for result in self.results_for("slalom"):
            score = SlalomScore.parse(result.score)

            if score is not None:
                valid_results.append((score, result))

        if not valid_results:
            return None

        return max(
            valid_results,
            key=lambda item: item[0].comparison_key,
        )[1]

    @staticmethod
    def rider_name(
        result: Result | None,
    ) -> str | None:
        """Retourne le nom complet associé à un résultat."""
        if result is None:
            return None

        return (
            f"{result.rider.prenom} "
            f"{result.rider.nom}"
        )

    @staticmethod
    def _extract_first_number(
        value: str,
    ) -> float | None:
        """Extrait le premier nombre présent dans un score."""
        if not value:
            return None

        match = re.search(
            r"-?\d+(?:[.,]\d+)?",
            value,
        )

        if match is None:
            return None

        normalized = match.group(0).replace(",", ".")

        try:
            return float(normalized)
        except ValueError:
            return None