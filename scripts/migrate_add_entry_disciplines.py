from __future__ import annotations

import sqlite3

from observatoire.config import DATABASE_FILE


def main() -> None:
    with sqlite3.connect(DATABASE_FILE) as connection:
        connection.execute("PRAGMA foreign_keys = ON")

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS entry_disciplines (
                competition_id INTEGER NOT NULL,
                rider_id INTEGER NOT NULL,
                discipline TEXT NOT NULL,
                detail TEXT,
                source TEXT NOT NULL DEFAULT 'ems',

                PRIMARY KEY (
                    competition_id,
                    rider_id,
                    discipline
                ),

                FOREIGN KEY (competition_id)
                    REFERENCES competitions(id)
                    ON DELETE CASCADE,

                FOREIGN KEY (rider_id)
                    REFERENCES riders(id)
                    ON DELETE CASCADE
            )
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_entry_disciplines_competition
            ON entry_disciplines (competition_id)
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_entry_disciplines_rider
            ON entry_disciplines (rider_id)
            """
        )

        connection.commit()

    print("Table entry_disciplines prête.")


if __name__ == "__main__":
    main()