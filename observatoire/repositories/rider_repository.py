"""Accès aux données des sportifs."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from observatoire.config import DATABASE_FILE
from observatoire.models import Rider
from observatoire.repositories.base import BaseRepository


class RiderRepository(BaseRepository):
    """Repository chargé des opérations de lecture sur les riders."""

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
    def _to_model(row: sqlite3.Row | None) -> Rider | None:
        """Convertit une ligne SQLite en objet Rider."""
        if row is None:
            return None

        return Rider(
            id=int(row["id"]),
            iwwf_id=row["iwwf_id"] or "",
            nom=row["nom"] or "",
            prenom=row["prenom"] or "",
        )

    def get_by_id(self, rider_id: int) -> Rider | None:
        row = self.fetch_one(
            """
            SELECT
                id,
                iwwf_id,
                nom,
                prenom
            FROM riders
            WHERE id = ?
            """,
            (rider_id,),
        )

        return self._to_model(row)

    def get_by_iwwf_id(self, iwwf_id: str) -> Rider | None:
        row = self.fetch_one(
            """
            SELECT
                id,
                iwwf_id,
                nom,
                prenom
            FROM riders
            WHERE iwwf_id = ?
            """,
            (iwwf_id.strip(),),
        )

        return self._to_model(row)

    def search(self, query: str, limit: int = 20) -> list[Rider]:
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
                prenom
            FROM riders
            WHERE
                iwwf_id LIKE ? COLLATE NOCASE
                OR nom LIKE ? COLLATE NOCASE
                OR prenom LIKE ? COLLATE NOCASE
                OR TRIM(
                    COALESCE(prenom, '') || ' ' || COALESCE(nom, '')
                ) LIKE ? COLLATE NOCASE
                OR TRIM(
                    COALESCE(nom, '') || ' ' || COALESCE(prenom, '')
                ) LIKE ? COLLATE NOCASE
            ORDER BY
                nom COLLATE NOCASE,
                prenom COLLATE NOCASE,
                iwwf_id
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

        riders: list[Rider] = []

        for row in rows:
            rider = self._to_model(row)

            if rider is not None:
                riders.append(rider)

        return riders

    def count(self) -> int:
        row = self.fetch_one(
            """
            SELECT COUNT(*) AS rider_count
            FROM riders
            """
        )

        if row is None:
            return 0

        return int(row["rider_count"])
