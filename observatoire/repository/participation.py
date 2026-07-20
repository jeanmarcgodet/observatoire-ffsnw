from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from observatoire.config import DATABASE_FILE


@dataclass(frozen=True)
class CompetitionRecord:
    id: int
    iwwf_id: str
    nom: str


@dataclass(frozen=True)
class RiderRecord:
    id: int
    iwwf_id: str | None
    ems_athlete_id: str | None
    nom: str
    prenom: str
    sexe: str | None
    nation: str | None
    annee_naissance: int | None

    @property
    def nom_complet(self) -> str:
        return " ".join(
            value
            for value in (self.prenom, self.nom)
            if value
        )


@dataclass(frozen=True)
class EntryRecord:
    competition_id: int
    rider_id: int
    categorie: str | None
    club: str | None
    equipe: str | None


@dataclass(frozen=True)
class EntryDisciplineRecord:
    competition_id: int
    rider_id: int
    discipline: str
    detail: str | None
    source: str


class ParticipationRepository:
    """
    Couche d'accès aux données de participation.

    Les modules d'analyse ne doivent pas exécuter directement
    de requêtes SQL. Ils utilisent cette classe.
    """

    def __init__(
        self,
        database_file: str | Path = DATABASE_FILE,
    ) -> None:
        self.database_file = Path(database_file)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_file)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def get_competition(
        self,
        competition_id: int,
    ) -> CompetitionRecord | None:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT
                    id,
                    iwwf_id,
                    nom
                FROM competitions
                WHERE id = ?
                """,
                (competition_id,),
            ).fetchone()

        if row is None:
            return None

        return self._competition_from_row(row)

    def get_competition_by_iwwf_id(
        self,
        iwwf_id: str,
    ) -> CompetitionRecord | None:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT
                    id,
                    iwwf_id,
                    nom
                FROM competitions
                WHERE iwwf_id = ?
                """,
                (iwwf_id,),
            ).fetchone()

        if row is None:
            return None

        return self._competition_from_row(row)

    def list_competitions(
        self,
    ) -> list[CompetitionRecord]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    id,
                    iwwf_id,
                    nom
                FROM competitions
                ORDER BY id
                """
            ).fetchall()

        return [
            self._competition_from_row(row)
            for row in rows
        ]

    def get_rider(
        self,
        rider_id: int,
    ) -> RiderRecord | None:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT
                    id,
                    iwwf_id,
                    ems_athlete_id,
                    nom,
                    prenom,
                    sexe,
                    nation,
                    annee_naissance
                FROM riders
                WHERE id = ?
                """,
                (rider_id,),
            ).fetchone()

        if row is None:
            return None

        return self._rider_from_row(row)

    def riders_for_competition(
        self,
        competition_id: int,
    ) -> list[RiderRecord]:
        """
        Retourne les sportifs inscrits dans entries.

        Un sportif n'est retourné qu'une seule fois, même si une
        ancienne base contient plusieurs lignes d'inscription.
        """
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT DISTINCT
                    r.id,
                    r.iwwf_id,
                    r.ems_athlete_id,
                    r.nom,
                    r.prenom,
                    r.sexe,
                    r.nation,
                    r.annee_naissance
                FROM entries e
                JOIN riders r
                  ON r.id = e.rider_id
                WHERE e.competition_id = ?
                ORDER BY
                    r.nom,
                    r.prenom,
                    r.id
                """,
                (competition_id,),
            ).fetchall()

        return [
            self._rider_from_row(row)
            for row in rows
        ]

    def confirmed_riders_for_competition(
        self,
        competition_id: int,
    ) -> list[RiderRecord]:
        """
        Retourne les sportifs dont la participation est confirmée
        par les données EMS.

        La présence d'au moins une ligne entry_disciplines de source
        'ems' constitue la preuve de participation EMS.
        """
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT DISTINCT
                    r.id,
                    r.iwwf_id,
                    r.ems_athlete_id,
                    r.nom,
                    r.prenom,
                    r.sexe,
                    r.nation,
                    r.annee_naissance
                FROM entry_disciplines ed
                JOIN riders r
                  ON r.id = ed.rider_id
                WHERE ed.competition_id = ?
                  AND ed.source = 'ems'
                ORDER BY
                    r.nom,
                    r.prenom,
                    r.id
                """,
                (competition_id,),
            ).fetchall()

        return [
            self._rider_from_row(row)
            for row in rows
        ]

    def unconfirmed_local_riders(
        self,
        competition_id: int,
    ) -> list[RiderRecord]:
        """
        Retourne les sportifs présents dans entries mais absents
        des participations EMS.
        """
        local_riders = self.riders_for_competition(
            competition_id
        )

        confirmed_ids = {
            rider.id
            for rider in self.confirmed_riders_for_competition(
                competition_id
            )
        }

        return [
            rider
            for rider in local_riders
            if rider.id not in confirmed_ids
        ]

    def entries_for_competition(
        self,
        competition_id: int,
    ) -> list[EntryRecord]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    competition_id,
                    rider_id,
                    categorie,
                    club,
                    equipe
                FROM entries
                WHERE competition_id = ?
                ORDER BY
                    rider_id,
                    categorie
                """,
                (competition_id,),
            ).fetchall()

        return [
            self._entry_from_row(row)
            for row in rows
        ]

    def entry_disciplines_for_competition(
        self,
        competition_id: int,
        *,
        include_overall: bool = True,
    ) -> list[EntryDisciplineRecord]:
        query = """
            SELECT
                competition_id,
                rider_id,
                discipline,
                detail,
                source
            FROM entry_disciplines
            WHERE competition_id = ?
        """

        parameters: list[object] = [competition_id]

        if not include_overall:
            query += """
                AND discipline <> ?
            """
            parameters.append("overall")

        query += """
            ORDER BY
                rider_id,
                discipline
        """

        with self.connect() as connection:
            rows = connection.execute(
                query,
                parameters,
            ).fetchall()

        return [
            self._entry_discipline_from_row(row)
            for row in rows
        ]

    def disciplines_for_rider(
        self,
        competition_id: int,
        rider_id: int,
        *,
        include_overall: bool = False,
    ) -> tuple[str, ...]:
        query = """
            SELECT DISTINCT discipline
            FROM entry_disciplines
            WHERE competition_id = ?
              AND rider_id = ?
        """

        parameters: list[object] = [
            competition_id,
            rider_id,
        ]

        if not include_overall:
            query += """
                AND discipline <> ?
            """
            parameters.append("overall")

        query += """
            ORDER BY discipline
        """

        with self.connect() as connection:
            rows = connection.execute(
                query,
                parameters,
            ).fetchall()

        return tuple(
            str(row["discipline"])
            for row in rows
        )

    def active_rider_ids(
        self,
        competition_id: int,
    ) -> set[int]:
        """
        Sportifs ayant au moins un résultat dans une discipline réelle.

        Overall est exclu, car ce n'est pas une discipline pratiquée
        indépendamment.
        """
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT DISTINCT rider_id
                FROM results
                WHERE competition_id = ?
                  AND discipline <> 'overall'
                """,
                (competition_id,),
            ).fetchall()

        return {
            int(row["rider_id"])
            for row in rows
        }

    def classified_rider_ids(
        self,
        competition_id: int,
    ) -> set[int]:
        """
        Retourne les sportifs apparaissant dans les classifications.

        result_classifications est reliée à results par result_id.
        Le rider_id est donc récupéré depuis results.
        """
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT DISTINCT r.rider_id
                FROM result_classifications rc
                JOIN results r
                  ON r.id = rc.result_id
                WHERE r.competition_id = ?
                """,
                (competition_id,),
            ).fetchall()

        return {
            int(row["rider_id"])
            for row in rows
        }

    def withdrawn_riders(
        self,
        competition_id: int,
    ) -> list[RiderRecord]:
        """
        Sportifs inscrits mais sans résultat dans une discipline réelle.
        """
        registered = self.riders_for_competition(
            competition_id
        )
        active_ids = self.active_rider_ids(
            competition_id
        )

        return [
            rider
            for rider in registered
            if rider.id not in active_ids
        ]

    def iter_rider_disciplines(
        self,
        competition_id: int,
        *,
        include_overall: bool = False,
    ) -> Iterator[tuple[RiderRecord, tuple[str, ...]]]:
        for rider in self.riders_for_competition(
            competition_id
        ):
            yield (
                rider,
                self.disciplines_for_rider(
                    competition_id,
                    rider.id,
                    include_overall=include_overall,
                ),
            )

    @staticmethod
    def _competition_from_row(
        row: sqlite3.Row,
    ) -> CompetitionRecord:
        return CompetitionRecord(
            id=int(row["id"]),
            iwwf_id=str(row["iwwf_id"]),
            nom=str(row["nom"]),
        )

    @staticmethod
    def _rider_from_row(
        row: sqlite3.Row,
    ) -> RiderRecord:
        return RiderRecord(
            id=int(row["id"]),
            iwwf_id=row["iwwf_id"],
            ems_athlete_id=row["ems_athlete_id"],
            nom=str(row["nom"] or ""),
            prenom=str(row["prenom"] or ""),
            sexe=row["sexe"],
            nation=row["nation"],
            annee_naissance=row["annee_naissance"],
        )

    @staticmethod
    def _entry_from_row(
        row: sqlite3.Row,
    ) -> EntryRecord:
        return EntryRecord(
            competition_id=int(row["competition_id"]),
            rider_id=int(row["rider_id"]),
            categorie=row["categorie"],
            club=row["club"],
            equipe=row["equipe"],
        )

    @staticmethod
    def _entry_discipline_from_row(
        row: sqlite3.Row,
    ) -> EntryDisciplineRecord:
        return EntryDisciplineRecord(
            competition_id=int(row["competition_id"]),
            rider_id=int(row["rider_id"]),
            discipline=str(row["discipline"]),
            detail=row["detail"],
            source=str(row["source"]),
        )