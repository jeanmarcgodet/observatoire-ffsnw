from __future__ import annotations

from observatoire.repository import ParticipationRepository


POPULATIONS_BY_IWWF_ID = {
    "26FRA021": "open_u21",
    "25FRA206": "open_u21",
    "24FRA027": "open_u21",
    "23FRA018": "open_u21",
    "22FRA031": "open_u21",
    "21FRA046": "open",
    "20FRA030": "open",
    "19FRA001": "open_open_de_france",
    "18FRA001": "open",
    "17FRA002": "open_senior_handi",
}


def get_columns(connection) -> set[str]:
    rows = connection.execute(
        "PRAGMA table_info(competitions)"
    ).fetchall()

    return {
        str(row["name"])
        for row in rows
    }


def add_population_column(connection) -> bool:
    columns = get_columns(connection)

    if "population_cible" in columns:
        print(
            "La colonne competitions.population_cible "
            "existe déjà."
        )
        return False

    connection.execute(
        """
        ALTER TABLE competitions
        ADD COLUMN population_cible TEXT
        """
    )

    print(
        "Colonne ajoutée : "
        "competitions.population_cible"
    )

    return True


def populate_values(connection) -> int:
    updated = 0

    for iwwf_id, population in (
        POPULATIONS_BY_IWWF_ID.items()
    ):
        cursor = connection.execute(
            """
            UPDATE competitions
            SET population_cible = ?
            WHERE iwwf_id = ?
              AND (
                  population_cible IS NULL
                  OR TRIM(population_cible) = ''
              )
            """,
            (
                population,
                iwwf_id,
            ),
        )

        updated += int(cursor.rowcount)

    return updated


def create_index(connection) -> None:
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_competitions_population_cible
        ON competitions(population_cible)
        """
    )


def print_inventory(connection) -> None:
    rows = connection.execute(
        """
        SELECT
            id,
            iwwf_id,
            annee,
            nom,
            population_cible,
            statut_collecte
        FROM competitions
        ORDER BY annee DESC, id DESC
        """
    ).fetchall()

    print()
    print("PÉRIMÈTRES DES COMPÉTITIONS")
    print("===========================")

    for row in rows:
        print()
        print(
            f"{row['annee']} — "
            f"{row['iwwf_id']}"
        )
        print(f"  Nom        : {row['nom']}")
        print(
            "  Population :",
            row["population_cible"],
        )
        print(
            "  Collecte   :",
            row["statut_collecte"],
        )


def main() -> None:
    repository = ParticipationRepository()

    with repository.connect() as connection:
        connection.execute(
            "PRAGMA foreign_keys = ON"
        )

        add_population_column(connection)

        updated = populate_values(connection)

        create_index(connection)

        connection.commit()

        print()
        print(
            "Compétitions renseignées :",
            updated,
        )

        print_inventory(connection)

    print()
    print("Migration terminée.")


if __name__ == "__main__":
    main()