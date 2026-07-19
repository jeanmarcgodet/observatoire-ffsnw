"""Infrastructure commune aux repositories SQLite."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable, Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from observatoire.config import DATABASE_FILE


class BaseRepository:
    """Classe de base pour les repositories de l'Observatoire.

    Elle centralise :

    - l'ouverture des connexions SQLite ;
    - l'utilisation de ``sqlite3.Row`` ;
    - l'activation des clés étrangères ;
    - les opérations de lecture courantes ;
    - l'exécution transactionnelle des écritures.

    Une connexion existante peut être injectée. Cette possibilité sera utile
    pour les tests et pour les traitements regroupant plusieurs repositories
    dans une même transaction.
    """

    def __init__(
        self,
        database_file: str | Path = DATABASE_FILE,
        connection: sqlite3.Connection | None = None,
    ) -> None:
        self.database_file = Path(database_file)
        self._connection = connection

        if self._connection is not None:
            self._configure_connection(self._connection)

    @staticmethod
    def _configure_connection(connection: sqlite3.Connection) -> None:
        """Configure une connexion SQLite utilisée par un repository."""
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")

    def _create_connection(self) -> sqlite3.Connection:
        """Crée une nouvelle connexion vers la base de données."""
        connection = sqlite3.connect(self.database_file)
        self._configure_connection(connection)
        return connection

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        """Fournit une connexion sans fermer une connexion injectée.

        Lorsque le repository crée lui-même la connexion, celle-ci est fermée
        automatiquement à la fin du bloc.
        """
        if self._connection is not None:
            yield self._connection
            return

        connection = self._create_connection()

        try:
            yield connection
        finally:
            connection.close()

    def fetch_one(
        self,
        query: str,
        parameters: Sequence[Any] = (),
    ) -> sqlite3.Row | None:
        """Retourne la première ligne d'une requête, ou ``None``."""
        with self.connection() as connection:
            return connection.execute(query, parameters).fetchone()

    def fetch_all(
        self,
        query: str,
        parameters: Sequence[Any] = (),
    ) -> list[sqlite3.Row]:
        """Retourne toutes les lignes d'une requête."""
        with self.connection() as connection:
            cursor = connection.execute(query, parameters)
            return list(cursor.fetchall())

    def execute(
        self,
        query: str,
        parameters: Sequence[Any] = (),
    ) -> int:
        """Exécute une écriture dans une transaction.

        Returns:
            L'identifiant de la ligne insérée lorsqu'il est disponible.
            Pour les mises à jour, la valeur peut être nulle.
        """
        with self.connection() as connection:
            try:
                cursor = connection.execute(query, parameters)
                connection.commit()
                return int(cursor.lastrowid or 0)
            except Exception:
                connection.rollback()
                raise

    def execute_many(
        self,
        query: str,
        parameter_sets: Iterable[Sequence[Any]],
    ) -> int:
        """Exécute une même requête pour plusieurs jeux de paramètres.

        Returns:
            Le nombre de lignes affectées lorsque SQLite peut le déterminer.
        """
        with self.connection() as connection:
            try:
                cursor = connection.executemany(query, parameter_sets)
                connection.commit()
                return cursor.rowcount
            except Exception:
                connection.rollback()
                raise

    def exists(
        self,
        query: str,
        parameters: Sequence[Any] = (),
    ) -> bool:
        """Indique si une requête retourne au moins une ligne."""
        return self.fetch_one(query, parameters) is not None