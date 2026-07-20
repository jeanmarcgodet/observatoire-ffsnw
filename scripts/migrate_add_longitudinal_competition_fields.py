from __future__ import annotations

from observatoire.repository import ParticipationRepository


COLUMNS_TO_ADD = {
    "annee": "INTEGER",
    "niveau": "TEXT",
    "statut_collecte": (
        "TEXT NOT NULL DEFAULT 'a_collecter'"
    ),
}


def get_columns(connection) -> set[str]:
    rows = connection.execute(
        "PRAGMA table_info(competitions)"
    ).fetchall()

    return {
        str(row["name"])
        for row in rows
    }


def add_missing_columns(connection) -> list[str]:
    existing_columns = get_columns(connection)
    added_columns: list[str] = []

    for column_name, column_definition in (
        COLUMNS_TO_ADD.items()
    ):
        if column_name in existing_columns:
            print(
                f"La colonne competitions."
                f"{column_name} existe déjà."
            )
            continue

        connection.execute(
            f"""
            ALTER TABLE competitions
            ADD COLUMN {column_name}
            {column_definition}
            """
        )

        added_columns.append(column_name)

        print(
            f"Colonne ajoutée : "
            f"competitions.{column_name}"
        )

    return added_columns


def populate_year(connection) -> int:
    cursor = connection.execute(
        """
        UPDATE competitions
        SET annee = CAST(
            SUBSTR(date_debut, 1, 4)
            AS INTEGER
        )
        WHERE annee IS NULL
          AND date_debut IS NOT NULL
          AND LENGTH(date_debut) >= 4
        """
    )

    return int(cursor.rowcount)


def initialize_current_competition(connection) -> None:
    connection.execute(
        """
        UPDATE competitions
        SET niveau = 'championnat_france'
        WHERE id = 1
          AND (
              niveau IS NULL
              OR TRIM(niveau) = ''
          )
        """
    )

    connection.execute(
        """
        UPDATE competitions
        SET statut_collecte = 'controlee'
        WHERE id = 1
        """
    )


def create_indexes(connection) -> None:
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_competitions_annee
        ON competitions(annee)
        """
    )

    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_competitions_discipline_annee
        ON competitions(
            discipline,
            annee
        )
        """
    )

    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_competitions_statut_collecte
        ON competitions(statut_collecte)
        """
    )


def print_inventory(connection) -> None:
    rows = connection.execute(
        """
        SELECT
            id,
            iwwf_id,
            nom,
            date_debut,
            annee,
            discipline,
            niveau,
            statut_collecte
        FROM competitions
        ORDER BY annee DESC, id DESC
        """
    ).fetchall()

    print()
    print("INVENTAIRE DES COMPÉTITIONS")
    print("===========================")

    for row in rows:
        print()
        print(f"Compétition locale : {row['id']}")
        print(f"IWWF              : {row['iwwf_id']}")
        print(f"Nom               : {row['nom']}")
        print(f"Date              : {row['date_debut']}")
        print(f"Année             : {row['annee']}")
        print(f"Discipline        : {row['discipline']}")
        print(f"Niveau            : {row['niveau']}")
        print(
            "Statut collecte   :",
            row["statut_collecte"],
        )


def main() -> None:
    repository = ParticipationRepository()

    with repository.connect() as connection:
        connection.execute(
            "PRAGMA foreign_keys = ON"
        )

        add_missing_columns(connection)

        years_updated = populate_year(connection)

        initialize_current_competition(
            connection
        )

        create_indexes(connection)

        connection.commit()

        print()
        print(
            "Années renseignées :",
            years_updated,
        )

        print_inventory(connection)

    print()
    print("Migration terminée.")


if __name__ == "__main__":
    main()