"""Accès aux données des compétitions."""

from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path

from observatoire.config import DATABASE_FILE
from observatoire.models import Competition
from observatoire.repositories.base import BaseRepository


class CompetitionRepository(BaseRepository):
    """Repository chargé des opérations de lecture sur les compétitions."""

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
    def _to_model(cls, row: sqlite3.Row | None) -> Competition | None:
        """Convertit une ligne SQLite en objet Competition."""
        if row is None:
            return None

        return Competition(
            id=int(row["id"]),
            iwwf_id=row["iwwf_id"] or "",
            nom=row["nom"] or "",
            date_debut=cls._parse_date(row["date_debut"]),
            date_fin=cls._parse_date(row["date_fin"]),
            pays=row["pays"] or "",
            ville=row["ville"] or "",
            discipline=row["discipline"] or "",
        )

    def get_by_id(self, competition_id: int) -> Competition | None:
        row = self.fetch_one(
            """
            SELECT
                id,
                iwwf_id,
                nom,
                date_debut,
                date_fin,
                pays,
                ville,
                discipline
            FROM competitions
            WHERE id = ?
            """,
            (competition_id,),
        )

        return self._to_model(row)

    def get_by_iwwf_id(self, iwwf_id: str) -> Competition | None:
        row = self.fetch_one(
            """
            SELECT
                id,
                iwwf_id,
                nom,
                date_debut,
                date_fin,
                pays,
                ville,
                discipline
            FROM competitions
            WHERE iwwf_id = ?
            """,
            (iwwf_id.strip(),),
        )

        return self._to_model(row)

    def search(self, query: str, limit: int = 20) -> list[Competition]:
        normalized_query = query.strip()

        if not normalized_query:
            return []

        if limit <= 0:
            raise ValueError("La limite doit être strictement positive.")

        pattern = f"%{normalized_query}%"

        rows = self.fetch_all(
            """
            SELECT
                id,
                iwwf_id,
                nom,
                date_debut,
                date_fin,
                pays,
                ville,
                discipline
            FROM competitions
            WHERE
                iwwf_id LIKE ? COLLATE NOCASE
                OR nom LIKE ? COLLATE NOCASE
                OR pays LIKE ? COLLATE NOCASE
                OR ville LIKE ? COLLATE NOCASE
                OR discipline LIKE ? COLLATE NOCASE
            ORDER BY
                date_debut DESC,
                nom COLLATE NOCASE
            LIMIT ?
            """,
            (
                pattern,
                pattern,
                pattern,
                pattern,
                pattern,
                limit,
            ),
        )

        competitions: list[Competition] = []

        for row in rows:
            competition = self._to_model(row)

            if competition is not None:
                competitions.append(competition)

        return competitions

    def list_all(self, limit: int = 100) -> list[Competition]:
        if limit <= 0:
            raise ValueError("La limite doit être strictement positive.")

        rows = self.fetch_all(
            """
            SELECT
                id,
                iwwf_id,
                nom,
                date_debut,
                date_fin,
                pays,
                ville,
                discipline
            FROM competitions
            ORDER BY
                date_debut DESC,
                nom COLLATE NOCASE
            LIMIT ?
            """,
            (limit,),
        )

        competitions: list[Competition] = []

        for row in rows:
            competition = self._to_model(row)

            if competition is not None:
                competitions.append(competition)

        return competitions

    def count(self) -> int:
        row = self.fetch_one(
            """
            SELECT COUNT(*) AS competition_count
            FROM competitions
            """
        )

        if row is None:
            return 0

        return int(row["competition_count"])
