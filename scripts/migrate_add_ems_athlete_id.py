import sqlite3

from observatoire.config import DATABASE_FILE


def column_exists(
    connection: sqlite3.Connection,
    table_name: str,
    column_name: str,
) -> bool:
    columns = connection.execute(
        f"PRAGMA table_info({table_name})"
    ).fetchall()

    return any(column[1] == column_name for column in columns)


def main() -> None:
    with sqlite3.connect(DATABASE_FILE) as connection:
        if not column_exists(connection, "riders", "ems_athlete_id"):
            connection.execute(
                """
                ALTER TABLE riders
                ADD COLUMN ems_athlete_id TEXT
                """
            )
            print("Colonne riders.ems_athlete_id ajoutée.")
        else:
            print("La colonne riders.ems_athlete_id existe déjà.")

        connection.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS
            idx_riders_ems_athlete_id
            ON riders (ems_athlete_id)
            WHERE ems_athlete_id IS NOT NULL
            """
        )

        connection.commit()

    print("Migration terminée.")


if __name__ == "__main__":
    main()