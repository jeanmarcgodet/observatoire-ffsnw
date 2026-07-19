
"""Calcul des statistiques relatives à la carrière d'un rider."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

from observatoire.models import Result, RiderCareer, SlalomScore


@dataclass(slots=True)
class RiderStatistics:
    """Statistiques calculées à partir d'une carrière."""

    career: RiderCareer
    _results_by_discipline: dict[str, list[Result]] = field(
        init=False,
        repr=False,
    )

    def __post_init__(self) -> None:
        self._results_by_discipline = {}

        for result in self.career.results:
            discipline = result.discipline.strip().lower()

            self._results_by_discipline.setdefault(
                discipline,
                [],
            ).append(result)

    @property
    def number_of_results(self) -> int:
        """Retourne le nombre total de résultats."""
        return self.career.number_of_results

    @property
    def number_of_competitions(self) -> int:
        """Retourne le nombre de compétitions distinctes."""
        return self.career.number_of_competitions

    @property
    def disciplines(self) -> list[str]:
        """Retourne les disciplines représentées."""
        return self.career.disciplines

    @property
    def seasons(self) -> list[int]:
        """Retourne les saisons présentes."""
        return self.career.seasons

    @property
    def tour_counts(self) -> dict[str, int]:
        """Compte les résultats par intitulé de tour."""
        counter = Counter(
            result.tour.strip()
            for result in self.career.results
            if result.tour.strip()
        )

        return dict(sorted(counter.items()))

    @property
    def number_of_finals(self) -> int:
        """Compte les résultats associés à une finale."""
        return sum(
            1
            for result in self.career.results
            if "finale" in result.tour.strip().lower()
        )

    def results_for(self, discipline: str) -> list[Result]:
        """Retourne les résultats d'une discipline."""
        return list(
            self._results_by_discipline.get(
                discipline.strip().lower(),
                [],
            )
        )

    def has_final(self, discipline: str) -> bool:
        """Indique si une finale est enregistrée dans la discipline."""
        return any(
            "finale" in result.tour.strip().lower()
            for result in self.results_for(discipline)
        )

    def best_numeric_score(self, discipline: str) -> float | None:
        """
        Retourne le meilleur score numérique d'une discipline.

        Cette méthode convient notamment au jump et aux tricks.
        Elle ne doit pas être utilisée pour comparer les scores de slalom.
        """
        scores: list[float] = []

        for result in self.results_for(discipline):
            score = self._extract_first_number(result.score)

            if score is not None:
                scores.append(score)

        if not scores:
            return None

        return max(scores)

    def best_jump(self) -> float | None:
        """Retourne la meilleure distance de saut en mètres."""
        return self.best_numeric_score("jump")

    def best_tricks(self) -> float | None:
        """Retourne le meilleur score figures."""
        return self.best_numeric_score("tricks")

    def best_overall_component(self) -> float | None:
        """Retourne la meilleure composante chiffrée de l'overall."""
        return self.best_numeric_score("overall")

    def best_slalom_score(self) -> SlalomScore | None:
        """Retourne la meilleure performance principale en slalom."""
        parsed_scores: list[SlalomScore] = []

        for result in self.results_for("slalom"):
            score = SlalomScore.parse(result.score)

            if score is not None:
                parsed_scores.append(score)

        if not parsed_scores:
            return None

        return max(
            parsed_scores,
            key=lambda score: score.comparison_key,
        )

    def best_slalom_text(self) -> str | None:
        """Retourne le meilleur score de slalom sous forme textuelle."""
        score = self.best_slalom_score()

        if score is None:
            return None

        return score.raw_value

    @staticmethod
    def _extract_first_number(value: str) -> float | None:
        """Extrait le premier nombre d'une chaîne de score."""
        match = re.search(r"-?\d+(?:[.,]\d+)?", value)

        if match is None:
            return None

        normalized = match.group(0).replace(",", ".")

        try:
            return float(normalized)
        except ValueError:
            return None
