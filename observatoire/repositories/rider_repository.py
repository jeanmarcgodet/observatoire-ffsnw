"""Accès aux données des sportifs."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from observatoire.config import DATABASE_FILE
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

    def get_by_id(self, rider_id: int) -> sqlite3.Row | None:
        return self.fetch_one(
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

    def get_by_iwwf_id(self, iwwf_id: str) -> sqlite3.Row | None:
        return self.fetch_one(
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

    def search(self, query: str, limit: int = 20) -> list[sqlite3.Row]:
        normalized_query = query.strip()

        if not normalized_query:
            return []

        if limit <= 0:
            raise ValueError("La limite doit être strictement positive.")

        pattern = f"%{normalized_query}%"

        return self.fetch_all(
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
