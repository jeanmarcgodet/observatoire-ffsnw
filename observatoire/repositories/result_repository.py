"""Accès aux résultats sportifs."""

from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path

from observatoire.config import DATABASE_FILE
from observatoire.models import Competition, Result
from observatoire.repositories.base import BaseRepository


class ResultRepository(BaseRepository):
    """Repository chargé des opérations de lecture sur les résultats."""

    def __init__(
        self,
        database_file: str | Path = DATABASE_FILE,
        connection: sqlite3.Connection | None = None,
    ) -> None:
        super().__init__(
            database_file=database_file,
            connection=connection,
        )

    @staticmethod
    def _parse_date(value: str | None) -> date | None:
        """Convertit une date ISO SQLite en objet date."""
        if not value:
            return None

        return date.fromisoformat(value)

    @classmethod
    def _to_model(cls, row: sqlite3.Row | None) -> Result | None:
        """Convertit une ligne SQLite jointe en objet Result."""
        if row is None:
            return None

        competition = Competition(
            id=int(row["competition_id"]),
            iwwf_id=row["competition_iwwf_id"] or "",
            nom=row["competition_nom"] or "",
            date_debut=cls._parse_date(row["competition_date_debut"]),
            date_fin=cls._parse_date(row["competition_date_fin"]),
            pays=row["competition_pays"] or "",
            ville=row["competition_ville"] or "",
            discipline=row["competition_discipline"] or "",
        )

        return Result(
            id=int(row["result_id"]),
            rider_id=int(row["rider_id"]),
            competition=competition,
            discipline=row["result_discipline"] or "",
            tour=row["tour"] or "",
            score=row["score"] or "",
            document_url=row["document_url"],
        )

    def get_by_id(self, result_id: int) -> Result | None:
        """Retourne un résultat à partir de son identifiant interne."""
        row = self.fetch_one(
            """
            SELECT
                r.id AS result_id,
                r.rider_id,
                r.discipline AS result_discipline,
                r.tour,
                r.score,
                r.document_url,

                c.id AS competition_id,
                c.iwwf_id AS competition_iwwf_id,
                c.nom AS competition_nom,
                c.date_debut AS competition_date_debut,
                c.date_fin AS competition_date_fin,
                c.pays AS competition_pays,
                c.ville AS competition_ville,
                c.discipline AS competition_discipline

            FROM results AS r
            INNER JOIN competitions AS c
                ON c.id = r.competition_id
            WHERE r.id = ?
            """,
            (result_id,),
        )

        return self._to_model(row)

    def list_by_rider_id(self, rider_id: int) -> list[Result]:
        """Retourne tous les résultats connus d'un rider."""
        rows = self.fetch_all(
            """
            SELECT
                r.id AS result_id,
                r.rider_id,
                r.discipline AS result_discipline,
                r.tour,
                r.score,
                r.document_url,

                c.id AS competition_id,
                c.iwwf_id AS competition_iwwf_id,
                c.nom AS competition_nom,
                c.date_debut AS competition_date_debut,
                c.date_fin AS competition_date_fin,
                c.pays AS competition_pays,
                c.ville AS competition_ville,
                c.discipline AS competition_discipline

            FROM results AS r
            INNER JOIN competitions AS c
                ON c.id = r.competition_id
            WHERE r.rider_id = ?
            ORDER BY
                c.date_debut ASC,
                c.id ASC,
                r.id ASC
            """,
            (rider_id,),
        )

        results: list[Result] = []

        for row in rows:
            result = self._to_model(row)

            if result is not None:
                results.append(result)

        return results

    def list_by_competition_id(
        self,
        competition_id: int,
    ) -> list[Result]:
        """Retourne les résultats d'une compétition."""
        rows = self.fetch_all(
            """
            SELECT
                r.id AS result_id,
                r.rider_id,
                r.discipline AS result_discipline,
                r.tour,
                r.score,
                r.document_url,

                c.id AS competition_id,
                c.iwwf_id AS competition_iwwf_id,
                c.nom AS competition_nom,
                c.date_debut AS competition_date_debut,
                c.date_fin AS competition_date_fin,
                c.pays AS competition_pays,
                c.ville AS competition_ville,
                c.discipline AS competition_discipline

            FROM results AS r
            INNER JOIN competitions AS c
                ON c.id = r.competition_id
            WHERE r.competition_id = ?
            ORDER BY
                r.rider_id ASC,
                r.discipline ASC,
                r.tour ASC,
                r.id ASC
            """,
            (competition_id,),
        )

        results: list[Result] = []

        for row in rows:
            result = self._to_model(row)

            if result is not None:
                results.append(result)

        return results

    def count(self) -> int:
        """Retourne le nombre total de résultats."""
        row = self.fetch_one(
            """
            SELECT COUNT(*) AS result_count
            FROM results
            """
        )

        if row is None:
            return 0

        return int(row["result_count"])
