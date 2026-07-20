from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date

from observatoire.repository import (
    ParticipationRepository,
    RiderRecord,
)


@dataclass(frozen=True)
class ParticipationSummary:
    competition_id: int
    competition_name: str
    competition_iwwf_id: str

    registered_riders: int
    active_riders: int
    classified_riders: int
    withdrawn_riders: int

    participation_rate: float
    classification_rate: float

    women: int
    men: int
    unknown_sex: int
    women_rate: float

    average_age: float | None
    minimum_age: int | None
    maximum_age: int | None
    unknown_birth_year: int

    categories: dict[str, int]
    disciplines: dict[str, int]
    multidiscipline: dict[int, int]

    average_disciplines: float

    @property
    def total_real_discipline_entries(self) -> int:
        return sum(self.disciplines.values())


class ParticipationAnalytics:
    """
    Indicateurs statistiques de participation.

    Cette classe ne contient aucune requête SQL.
    Toutes les données proviennent du repository.
    """

    REAL_DISCIPLINES = {
        "slalom",
        "tricks",
        "jump",
    }

    def __init__(
        self,
        repository: ParticipationRepository | None = None,
    ) -> None:
        self.repository = (
            repository
            if repository is not None
            else ParticipationRepository()
        )

    def summary(
        self,
        competition_id: int,
        *,
        reference_year: int | None = None,
    ) -> ParticipationSummary:
        competition = self.repository.get_competition(
            competition_id
        )

        if competition is None:
            raise ValueError(
                "Compétition introuvable : "
                f"{competition_id}"
            )

        riders = self.repository.riders_for_competition(
            competition_id
        )

        entries = self.repository.entries_for_competition(
            competition_id
        )

        active_ids = self.repository.active_rider_ids(
            competition_id
        )

        classified_ids = (
            self.repository.classified_rider_ids(
                competition_id
            )
        )

        withdrawn = self.repository.withdrawn_riders(
            competition_id
        )

        category_counts = Counter(
            self._normalized_category(
                entry.categorie
            )
            for entry in entries
        )

        discipline_counts = Counter(
            item.discipline
            for item in (
                self.repository
                .entry_disciplines_for_competition(
                    competition_id,
                    include_overall=False,
                )
            )
            if item.discipline in self.REAL_DISCIPLINES
        )

        multidiscipline_counts = Counter()

        total_real_disciplines = 0

        for _, disciplines in (
            self.repository.iter_rider_disciplines(
                competition_id,
                include_overall=False,
            )
        ):
            real_disciplines = tuple(
                discipline
                for discipline in disciplines
                if discipline in self.REAL_DISCIPLINES
            )

            discipline_count = len(real_disciplines)

            multidiscipline_counts[
                discipline_count
            ] += 1

            total_real_disciplines += (
                discipline_count
            )

        sex_counts = self._sex_distribution(riders)

        registered_count = len(riders)
        active_count = len(active_ids)
        classified_count = len(classified_ids)
        withdrawn_count = len(withdrawn)

        participation_rate = self._rate(
            active_count,
            registered_count,
        )

        classification_rate = self._rate(
            classified_count,
            registered_count,
        )

        women_count = sex_counts["F"]
        men_count = sex_counts["M"]
        unknown_sex_count = sex_counts["unknown"]

        women_rate = self._rate(
            women_count,
            women_count + men_count,
        )

        if reference_year is None:
            reference_year = date.today().year

        ages, unknown_birth_year = self._ages(
            riders,
            reference_year,
        )

        average_age = (
            round(sum(ages) / len(ages), 2)
            if ages
            else None
        )

        minimum_age = min(ages) if ages else None
        maximum_age = max(ages) if ages else None

        average_disciplines = (
            round(
                total_real_disciplines
                / registered_count,
                2,
            )
            if registered_count
            else 0.0
        )

        return ParticipationSummary(
            competition_id=competition.id,
            competition_name=competition.nom,
            competition_iwwf_id=competition.iwwf_id,

            registered_riders=registered_count,
            active_riders=active_count,
            classified_riders=classified_count,
            withdrawn_riders=withdrawn_count,

            participation_rate=participation_rate,
            classification_rate=classification_rate,

            women=women_count,
            men=men_count,
            unknown_sex=unknown_sex_count,
            women_rate=women_rate,

            average_age=average_age,
            minimum_age=minimum_age,
            maximum_age=maximum_age,
            unknown_birth_year=unknown_birth_year,

            categories=dict(
                sorted(category_counts.items())
            ),

            disciplines=dict(
                sorted(discipline_counts.items())
            ),

            multidiscipline=dict(
                sorted(
                    multidiscipline_counts.items()
                )
            ),

            average_disciplines=average_disciplines,
        )

    def withdrawn_riders(
        self,
        competition_id: int,
    ) -> list[RiderRecord]:
        return self.repository.withdrawn_riders(
            competition_id
        )

    def category_distribution(
        self,
        competition_id: int,
    ) -> dict[str, int]:
        entries = (
            self.repository
            .entries_for_competition(
                competition_id
            )
        )

        counts = Counter(
            self._normalized_category(
                entry.categorie
            )
            for entry in entries
        )

        return dict(sorted(counts.items()))

    def discipline_distribution(
        self,
        competition_id: int,
        *,
        include_overall: bool = False,
    ) -> dict[str, int]:
        records = (
            self.repository
            .entry_disciplines_for_competition(
                competition_id,
                include_overall=include_overall,
            )
        )

        counts = Counter(
            record.discipline
            for record in records
            if (
                include_overall
                or record.discipline
                in self.REAL_DISCIPLINES
            )
        )

        return dict(sorted(counts.items()))

    def multidiscipline_distribution(
        self,
        competition_id: int,
    ) -> dict[int, int]:
        counts: Counter[int] = Counter()

        for _, disciplines in (
            self.repository.iter_rider_disciplines(
                competition_id,
                include_overall=False,
            )
        ):
            real_disciplines = {
                discipline
                for discipline in disciplines
                if discipline in self.REAL_DISCIPLINES
            }

            counts[len(real_disciplines)] += 1

        return dict(sorted(counts.items()))

    @staticmethod
    def _sex_distribution(
        riders: list[RiderRecord],
    ) -> dict[str, int]:
        counts = {
            "F": 0,
            "M": 0,
            "unknown": 0,
        }

        for rider in riders:
            sex = (rider.sexe or "").strip().upper()

            if sex == "F":
                counts["F"] += 1
            elif sex == "M":
                counts["M"] += 1
            else:
                counts["unknown"] += 1

        return counts

    @staticmethod
    def _ages(
        riders: list[RiderRecord],
        reference_year: int,
    ) -> tuple[list[int], int]:
        ages: list[int] = []
        unknown_birth_year = 0

        for rider in riders:
            birth_year = rider.annee_naissance

            if birth_year is None:
                unknown_birth_year += 1
                continue

            age = reference_year - birth_year

            if age < 0 or age > 110:
                unknown_birth_year += 1
                continue

            ages.append(age)

        return ages, unknown_birth_year

    @staticmethod
    def _normalized_category(
        category: str | None,
    ) -> str:
        value = (category or "").strip()

        if not value:
            return "Inconnue"

        normalizations = {
            "Ope": "Open",
            "OPEN": "Open",
            "open": "Open",
            "U21": "-21",
            "u21": "-21",
        }

        return normalizations.get(
            value,
            value,
        )

    @staticmethod
    def _rate(
        numerator: int,
        denominator: int,
    ) -> float:
        if denominator == 0:
            return 0.0

        return round(
            numerator / denominator * 100,
            2,
        )