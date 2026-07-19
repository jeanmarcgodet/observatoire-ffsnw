"""Repository d'accès aux résultats sportifs."""

from __future__ import annotations

import re
import sqlite3
from datetime import date

from observatoire.models import Competition, Result, Rider
from observatoire.repositories.base import BaseRepository


def parse_date(value: str | None) -> date | None:
    """Convertit une date ISO provenant de SQLite en objet date."""
    if not value:
        return None

    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


class ResultRepository(BaseRepository):
    """Accès aux résultats stockés dans SQLite."""

    BASE_QUERY = """
        SELECT
            results.id AS result_id,
            results.discipline AS result_discipline,
            results.tour AS result_tour,
            results.score AS result_score,
            results.document_url AS result_document_url,

            competitions.id AS competition_id,
            competitions.iwwf_id AS competition_iwwf_id,
            competitions.nom AS competition_nom,
            competitions.date_debut AS competition_date_debut,
            competitions.date_fin AS competition_date_fin,
            competitions.pays AS competition_pays,
            competitions.ville AS competition_ville,
            competitions.discipline AS competition_discipline,

            riders.id AS rider_id,
            riders.iwwf_id AS rider_iwwf_id,
            riders.nom AS rider_nom,
            riders.prenom AS rider_prenom,
            riders.sexe AS rider_sexe,
            riders.nation AS rider_nation,
            riders.annee_naissance AS rider_annee_naissance

        FROM results

        JOIN competitions
            ON competitions.id = results.competition_id

        JOIN riders
            ON riders.id = results.rider_id
    """

    @staticmethod
    def _to_model(row: sqlite3.Row) -> Result:
        """Transforme une ligne SQL en objet métier Result."""
        competition = Competition(
            id=row["competition_id"],
            iwwf_id=row["competition_iwwf_id"],
            nom=row["competition_nom"],
            date_debut=parse_date(
                row["competition_date_debut"]
            ),
            date_fin=parse_date(
                row["competition_date_fin"]
            ),
            pays=row["competition_pays"],
            ville=row["competition_ville"],
            discipline=row["competition_discipline"],
        )

        rider = Rider(
            id=row["rider_id"],
            iwwf_id=row["rider_iwwf_id"],
            nom=row["rider_nom"],
            prenom=row["rider_prenom"],
            sexe=row["rider_sexe"],
            nation=row["rider_nation"],
            annee_naissance=row["rider_annee_naissance"],
        )

        return Result(
            id=row["result_id"],
            competition=competition,
            rider=rider,
            discipline=row["result_discipline"] or "",
            tour=row["result_tour"] or "",
            score=row["result_score"] or "",
            document_url=row["result_document_url"],
        )

    def get_by_id(
        self,
        result_id: int,
    ) -> Result | None:
        """Recherche un résultat par son identifiant interne."""
        query = self.BASE_QUERY + """
            WHERE results.id = ?
        """

        with self.connection() as connection:
            row = connection.execute(
                query,
                (result_id,),
            ).fetchone()

        if row is None:
            return None

        return self._to_model(row)

    def list_by_rider_id(
        self,
        rider_id: int,
    ) -> list[Result]:
        """Retourne tous les résultats d'un rider."""
        query = self.BASE_QUERY + """
            WHERE results.rider_id = ?

            ORDER BY
                competitions.date_debut,
                competitions.id,
                results.id
        """

        with self.connection() as connection:
            rows = connection.execute(
                query,
                (rider_id,),
            ).fetchall()

        return [
            self._to_model(row)
            for row in rows
        ]

    def list_by_competition_id(
        self,
        competition_id: int,
    ) -> list[Result]:
        """Retourne tous les résultats d'une compétition."""
        query = self.BASE_QUERY + """
            WHERE results.competition_id = ?

            ORDER BY
                riders.nom,
                riders.prenom,
                results.discipline,
                results.tour,
                results.id
        """

        with self.connection() as connection:
            rows = connection.execute(
                query,
                (competition_id,),
            ).fetchall()

        return [
            self._to_model(row)
            for row in rows
        ]

    def list_all(self) -> list[Result]:
        """Retourne tous les résultats enregistrés."""
        query = self.BASE_QUERY + """
            ORDER BY
                competitions.date_debut,
                competitions.id,
                riders.nom,
                riders.prenom,
                results.id
        """

        with self.connection() as connection:
            rows = connection.execute(query).fetchall()

        return [
            self._to_model(row)
            for row in rows
        ]

    def count(self) -> int:
        """Retourne le nombre total de résultats."""
        query = """
            SELECT COUNT(*)
            FROM results
        """

        with self.connection() as connection:
            row = connection.execute(query).fetchone()

        if row is None:
            return 0

        return int(row[0])