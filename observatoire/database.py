import sqlite3
from pathlib import Path

from observatoire.config import DATABASE_FILE, PROJECT_ROOT


def create_database():
    """Crée la base SQLite à partir du schéma SQL."""

    DATABASE_FILE.parent.mkdir(exist_ok=True)

    connection = sqlite3.connect(DATABASE_FILE)

    schema_file = PROJECT_ROOT / "sql" / "schema.sql"

    with open(schema_file, encoding="utf-8") as f:
        connection.executescript(f.read())

    connection.commit()
    connection.close()

    print(f"Base créée : {DATABASE_FILE}")