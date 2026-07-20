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

    local_registered_riders: int
    confirmed_riders: int
    unconfirmed_local_riders: int

    active_riders: int
    classified_riders: int
    withdrawn_confirmed_riders: int

    effective_participation_rate: float
    classification_rate: float
    local_confirmation_rate: float

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
    def registered_riders(self) -> int:
        """
        Alias conservé pour compatibilité.

        La population statistique de référence est désormais constituée
        des participants confirmés par l'EMS.
        """
        return self.confirmed_riders

    @property
    def withdrawn_riders(self) -> int:
        return self.withdrawn_confirmed_riders

    @property
    def participation_rate(self) -> float:
        return self.effective_participation_rate

    @property
    def total_real_discipline_entries(self) -> int:
        return sum(self.disciplines.values())


class ParticipationAnalytics:
    """
    Indicateurs statistiques de participation.

    Les indicateurs principaux portent sur les participants confirmés
    par l'EMS. Les inscriptions locales non confirmées sont conservées
    comme indicateur de qualité des données.
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

        local_riders = (
            self.repository.riders_for_competition(
                competition_id
            )
        )

        confirmed_riders = (
            self.repository.confirmed_riders_for_competition(
                competition_id
            )
        )

        unconfirmed_riders = (
            self.repository.unconfirmed_local_riders(
                competition_id
            )
        )

        confirmed_ids = {
            rider.id
            for rider in confirmed_riders
        }

        active_ids = (
            self.repository.active_rider_ids(
                competition_id
            )
            & confirmed_ids
        )

        classified_ids = (
            self.repository.classified_rider_ids(
                competition_id
            )
            & confirmed_ids
        )

        withdrawn_confirmed = [
            rider
            for rider in confirmed_riders
            if rider.id not in active_ids
        ]

        category_counts = self._category_distribution(
            competition_id,
            confirmed_ids,
        )

        discipline_counts = self._discipline_distribution(
            competition_id,
            confirmed_ids,
        )

        multidiscipline_counts, total_real_disciplines = (
            self._multidiscipline_distribution(
                competition_id,
                confirmed_riders,
            )
        )

        sex_counts = self._sex_distribution(
            confirmed_riders
        )

        local_count = len(local_riders)
        confirmed_count = len(confirmed_riders)
        active_count = len(active_ids)
        classified_count = len(classified_ids)

        effective_participation_rate = self._rate(
            active_count,
            confirmed_count,
        )

        classification_rate = self._rate(
            classified_count,
            confirmed_count,
        )

        local_confirmation_rate = self._rate(
            confirmed_count,
            local_count,
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
            confirmed_riders,
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
                / confirmed_count,
                2,
            )
            if confirmed_count
            else 0.0
        )

        return ParticipationSummary(
            competition_id=competition.id,
            competition_name=competition.nom,
            competition_iwwf_id=competition.iwwf_id,

            local_registered_riders=local_count,
            confirmed_riders=confirmed_count,
            unconfirmed_local_riders=len(
                unconfirmed_riders
            ),

            active_riders=active_count,
            classified_riders=classified_count,
            withdrawn_confirmed_riders=len(
                withdrawn_confirmed
            ),

            effective_participation_rate=(
                effective_participation_rate
            ),
            classification_rate=classification_rate,
            local_confirmation_rate=(
                local_confirmation_rate
            ),

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
                sorted(multidiscipline_counts.items())
            ),

            average_disciplines=average_disciplines,
        )

    def withdrawn_riders(
        self,
        competition_id: int,
    ) -> list[RiderRecord]:
        confirmed = (
            self.repository.confirmed_riders_for_competition(
                competition_id
            )
        )

        active_ids = self.repository.active_rider_ids(
            competition_id
        )

        return [
            rider
            for rider in confirmed
            if rider.id not in active_ids
        ]

    def unconfirmed_local_riders(
        self,
        competition_id: int,
    ) -> list[RiderRecord]:
        return self.repository.unconfirmed_local_riders(
            competition_id
        )

    def category_distribution(
        self,
        competition_id: int,
    ) -> dict[str, int]:
        confirmed_ids = {
            rider.id
            for rider in (
                self.repository
                .confirmed_riders_for_competition(
                    competition_id
                )
            )
        }

        counts = self._category_distribution(
            competition_id,
            confirmed_ids,
        )

        return dict(sorted(counts.items()))

    def discipline_distribution(
        self,
        competition_id: int,
        *,
        include_overall: bool = False,
    ) -> dict[str, int]:
        confirmed_ids = {
            rider.id
            for rider in (
                self.repository
                .confirmed_riders_for_competition(
                    competition_id
                )
            )
        }

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
            if record.rider_id in confirmed_ids
            and (
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
        confirmed_riders = (
            self.repository.confirmed_riders_for_competition(
                competition_id
            )
        )

        counts, _ = self._multidiscipline_distribution(
            competition_id,
            confirmed_riders,
        )

        return dict(sorted(counts.items()))

    def _category_distribution(
        self,
        competition_id: int,
        confirmed_ids: set[int],
    ) -> Counter[str]:
        entries = self.repository.entries_for_competition(
            competition_id
        )

        return Counter(
            self._normalized_category(
                entry.categorie
            )
            for entry in entries
            if entry.rider_id in confirmed_ids
        )

    def _discipline_distribution(
        self,
        competition_id: int,
        confirmed_ids: set[int],
    ) -> Counter[str]:
        records = (
            self.repository
            .entry_disciplines_for_competition(
                competition_id,
                include_overall=False,
            )
        )

        return Counter(
            record.discipline
            for record in records
            if record.rider_id in confirmed_ids
            and record.discipline
            in self.REAL_DISCIPLINES
        )

    def _multidiscipline_distribution(
        self,
        competition_id: int,
        confirmed_riders: list[RiderRecord],
    ) -> tuple[Counter[int], int]:
        counts: Counter[int] = Counter()
        total_real_disciplines = 0

        for rider in confirmed_riders:
            disciplines = (
                self.repository.disciplines_for_rider(
                    competition_id,
                    rider.id,
                    include_overall=False,
                )
            )

            real_disciplines = {
                discipline
                for discipline in disciplines
                if discipline in self.REAL_DISCIPLINES
            }

            discipline_count = len(
                real_disciplines
            )

            counts[discipline_count] += 1
            total_real_disciplines += discipline_count

        return counts, total_real_disciplines

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