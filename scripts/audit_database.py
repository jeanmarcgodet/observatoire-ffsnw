"""Audit structurel de la base SQLite de l'observatoire."""

from __future__ import annotations

import sqlite3
from pathlib import Path


DATABASE_CANDIDATES = [
    Path("data/observatoire.db"),
    Path("data/ffsnw.db"),
    Path("observatoire.db"),
    Path("ffsnw.db"),
]


def find_database() -> Path:
    """Recherche automatiquement la base SQLite du projet."""
    for path in DATABASE_CANDIDATES:
        if path.exists():
            return path

    sqlite_files = list(Path(".").rglob("*.db"))
    sqlite_files += list(Path(".").rglob("*.sqlite"))
    sqlite_files += list(Path(".").rglob("*.sqlite3"))

    if len(sqlite_files) == 1:
        return sqlite_files[0]

    if not sqlite_files:
        raise FileNotFoundError(
            "Aucune base SQLite trouvée dans le projet."
        )

    print("Plusieurs bases SQLite ont été trouvées :")

    for index, path in enumerate(sqlite_files, start=1):
        print(f"{index}. {path}")

    raise RuntimeError(
        "Indique manuellement le chemin de la base "
        "dans DATABASE_CANDIDATES."
    )


def display_table_schema(
    connection: sqlite3.Connection,
    table_name: str,
) -> None:
    """Affiche les colonnes et clés étrangères d'une table."""
    print()
    print("=" * 80)
    print(f"TABLE : {table_name}")
    print("=" * 80)

    columns = connection.execute(
        f"PRAGMA table_info({table_name})"
    ).fetchall()

    print()
    print("Colonnes")
    print("--------")

    for column in columns:
        column_id = column[0]
        name = column[1]
        data_type = column[2]
        not_null = bool(column[3])
        default_value = column[4]
        primary_key = bool(column[5])

        print(
            f"{column_id:>2} | "
            f"{name:<25} | "
            f"{data_type:<12} | "
            f"NOT NULL={not_null!s:<5} | "
            f"PK={primary_key!s:<5} | "
            f"défaut={default_value}"
        )

    foreign_keys = connection.execute(
        f"PRAGMA foreign_key_list({table_name})"
    ).fetchall()

    print()
    print("Clés étrangères")
    print("---------------")

    if not foreign_keys:
        print("Aucune clé étrangère déclarée.")
    else:
        for foreign_key in foreign_keys:
            print(
                f"{foreign_key[3]} "
                f"→ {foreign_key[2]}.{foreign_key[4]}"
            )

    count = connection.execute(
        f"SELECT COUNT(*) FROM {table_name}"
    ).fetchone()[0]

    print()
    print(f"Nombre de lignes : {count}")

    rows = connection.execute(
        f"SELECT * FROM {table_name} LIMIT 5"
    ).fetchall()

    print()
    print("Cinq premières lignes")
    print("---------------------")

    if not rows:
        print("Table vide.")
        return

    for row in rows:
        print(dict(row))


def display_distinct_values(
    connection: sqlite3.Connection,
    table_name: str,
    column_name: str,
    limit: int = 30,
) -> None:
    """Affiche les principales valeurs distinctes d'une colonne."""
    columns = {
        row[1]
        for row in connection.execute(
            f"PRAGMA table_info({table_name})"
        ).fetchall()
    }

    if column_name not in columns:
        return

    print()
    print(
        f"Valeurs de {table_name}.{column_name}"
    )
    print("-" * 80)

    rows = connection.execute(
        f"""
        SELECT
            {column_name},
            COUNT(*) AS nombre
        FROM {table_name}
        GROUP BY {column_name}
        ORDER BY nombre DESC, {column_name}
        LIMIT ?
        """,
        (limit,),
    ).fetchall()

    for row in rows:
        print(
            f"{str(row[column_name]):<40} "
            f"{row['nombre']:>6}"
        )


def main() -> None:
    database_path = find_database()

    print(f"Base utilisée : {database_path.resolve()}")

    with sqlite3.connect(database_path) as connection:
        connection.row_factory = sqlite3.Row

        tables = [
            row["name"]
            for row in connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                  AND name NOT LIKE 'sqlite_%'
                ORDER BY name
                """
            ).fetchall()
        ]

        print()
        print("Tables disponibles")
        print("-------------------")

        for table in tables:
            print(f"- {table}")

        tables_to_audit = [
            "riders",
            "competitions",
            "entries",
            "results",
            "result_classifications",
        ]

        for table_name in tables_to_audit:
            if table_name in tables:
                display_table_schema(
                    connection,
                    table_name,
                )

        for column_name in [
            "discipline",
            "tour",
            "categorie",
            "category",
            "sexe",
            "gender",
            "statut",
            "status",
        ]:
            for table_name in [
                "entries",
                "results",
                "result_classifications",
            ]:
                if table_name in tables:
                    display_distinct_values(
                        connection,
                        table_name,
                        column_name,
                    )


if __name__ == "__main__":
    main()