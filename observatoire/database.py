import sqlite3

from observatoire.config import DATABASE_FILE, PROJECT_ROOT


def create_database() -> None:
    """Crée ou met à jour la base SQLite à partir du schéma SQL."""

    DATABASE_FILE.parent.mkdir(parents=True, exist_ok=True)

    schema_file = PROJECT_ROOT / "sql" / "schema.sql"

    with schema_file.open(encoding="utf-8") as file:
        schema = file.read()

    with sqlite3.connect(DATABASE_FILE) as connection:
        connection.executescript(schema)

    print(f"Base créée : {DATABASE_FILE}")