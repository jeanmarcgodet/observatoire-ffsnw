from __future__ import annotations

from collections import defaultdict
from typing import Any

from observatoire.repository import ParticipationRepository


TABLES_TO_INSPECT = (
    "competitions",
    "riders",
    "entries",
    "entry_disciplines",
    "results",
    "result_classifications",
)


def get_table_names(connection: Any) -> set[str]:
    rows = connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        ORDER BY name
        """
    ).fetchall()

    return {
        str(row["name"])
        for row in rows
    }


def get_columns(
    connection: Any,
    table_name: str,
) -> list[dict[str, Any]]:
    rows = connection.execute(
        f'PRAGMA table_info("{table_name}")'
    ).fetchall()

    return [
        {
            "position": int(row["cid"]),
            "name": str(row["name"]),
            "type": str(row["type"] or ""),
            "required": bool(row["notnull"]),
            "default": row["dflt_value"],
            "primary_key": bool(row["pk"]),
        }
        for row in rows
    ]


def get_foreign_keys(
    connection: Any,
    table_name: str,
) -> list[dict[str, Any]]:
    rows = connection.execute(
        f'PRAGMA foreign_key_list("{table_name}")'
    ).fetchall()

    return [
        {
            "from": str(row["from"]),
            "to_table": str(row["table"]),
            "to_column": str(row["to"]),
        }
        for row in rows
    ]


def get_indexes(
    connection: Any,
    table_name: str,
) -> list[str]:
    rows = connection.execute(
        f'PRAGMA index_list("{table_name}")'
    ).fetchall()

    return [
        str(row["name"])
        for row in rows
    ]


def count_rows(
    connection: Any,
    table_name: str,
) -> int:
    row = connection.execute(
        f'SELECT COUNT(*) AS total FROM "{table_name}"'
    ).fetchone()

    return int(row["total"])


def print_schema(
    connection: Any,
    table_name: str,
) -> None:
    print()
    print(table_name)
    print("-" * len(table_name))

    total = count_rows(
        connection,
        table_name,
    )

    print(f"Lignes : {total}")
    print()
    print("Colonnes :")

    for column in get_columns(
        connection,
        table_name,
    ):
        markers: list[str] = []

        if column["primary_key"]:
            markers.append("PK")

        if column["required"]:
            markers.append("NOT NULL")

        marker_text = (
            f" [{', '.join(markers)}]"
            if markers
            else ""
        )

        default_text = (
            f" DEFAULT {column['default']}"
            if column["default"] is not None
            else ""
        )

        print(
            f"  {column['name']:<28}"
            f"{column['type']:<14}"
            f"{marker_text}"
            f"{default_text}"
        )

    foreign_keys = get_foreign_keys(
        connection,
        table_name,
    )

    if foreign_keys:
        print()
        print("Clés étrangères :")

        for foreign_key in foreign_keys:
            print(
                f"  {foreign_key['from']} -> "
                f"{foreign_key['to_table']}."
                f"{foreign_key['to_column']}"
            )

    indexes = get_indexes(
        connection,
        table_name,
    )

    if indexes:
        print()
        print("Index :")

        for index_name in indexes:
            print(f"  {index_name}")


def print_competition_inventory(
    connection: Any,
) -> None:
    table_names = get_table_names(connection)

    if "competitions" not in table_names:
        return

    columns = {
        column["name"]
        for column in get_columns(
            connection,
            "competitions",
        )
    }

    preferred_columns = (
        "id",
        "iwwf_id",
        "nom",
        "name",
        "annee",
        "year",
        "date",
        "date_debut",
        "start_date",
        "lieu",
        "location",
        "discipline",
        "niveau",
        "status",
        "statut_collecte",
    )

    selected_columns = [
        column
        for column in preferred_columns
        if column in columns
    ]

    if not selected_columns:
        print()
        print(
            "Impossible d'afficher l'inventaire : "
            "aucune colonne reconnue."
        )
        return

    sql_columns = ", ".join(
        f'"{column}"'
        for column in selected_columns
    )

    order_column = (
        "annee"
        if "annee" in columns
        else (
            "year"
            if "year" in columns
            else (
                "date"
                if "date" in columns
                else "id"
            )
        )
    )

    rows = connection.execute(
        f"""
        SELECT {sql_columns}
        FROM competitions
        ORDER BY "{order_column}" DESC, id DESC
        """
    ).fetchall()

    print()
    print("INVENTAIRE ACTUEL DES COMPÉTITIONS")
    print("=================================")

    if not rows:
        print("Aucune compétition.")
        return

    for row in rows:
        values = []

        for column in selected_columns:
            values.append(
                f"{column}={row[column]!r}"
            )

        print("  " + " | ".join(values))


def print_relational_counts(
    connection: Any,
) -> None:
    tables = get_table_names(connection)

    required_tables = {
        "competitions",
        "entries",
        "entry_disciplines",
        "results",
    }

    if not required_tables.issubset(tables):
        return

    entry_columns = {
        column["name"]
        for column in get_columns(
            connection,
            "entries",
        )
    }

    result_columns = {
        column["name"]
        for column in get_columns(
            connection,
            "results",
        )
    }

    discipline_columns = {
        column["name"]
        for column in get_columns(
            connection,
            "entry_disciplines",
        )
    }

    if "competition_id" not in entry_columns:
        return

    if "competition_id" not in result_columns:
        return

    if "competition_id" not in discipline_columns:
        return

    rows = connection.execute(
        """
        SELECT
            c.id AS competition_id,

            (
                SELECT COUNT(*)
                FROM entries e
                WHERE e.competition_id = c.id
            ) AS entries_count,

            (
                SELECT COUNT(DISTINCT e.rider_id)
                FROM entries e
                WHERE e.competition_id = c.id
            ) AS local_riders_count,

            (
                SELECT COUNT(DISTINCT ed.rider_id)
                FROM entry_disciplines ed
                WHERE ed.competition_id = c.id
                  AND ed.source = 'ems'
            ) AS ems_riders_count,

            (
                SELECT COUNT(*)
                FROM results r
                WHERE r.competition_id = c.id
            ) AS results_count,

            (
                SELECT COUNT(DISTINCT r.rider_id)
                FROM results r
                WHERE r.competition_id = c.id
            ) AS riders_with_results_count

        FROM competitions c
        ORDER BY c.id
        """
    ).fetchall()

    print()
    print("COUVERTURE PAR COMPÉTITION")
    print("==========================")

    for row in rows:
        print()
        print(
            f"Compétition {row['competition_id']}"
        )
        print(
            "  Inscriptions locales :",
            row["entries_count"],
        )
        print(
            "  Sportifs locaux      :",
            row["local_riders_count"],
        )
        print(
            "  Sportifs EMS         :",
            row["ems_riders_count"],
        )
        print(
            "  Résultats             :",
            row["results_count"],
        )
        print(
            "  Sportifs avec résultat:",
            row["riders_with_results_count"],
        )


def print_longitudinal_readiness(
    connection: Any,
) -> None:
    tables = get_table_names(connection)

    print()
    print("ÉTAT DE PRÉPARATION LONGITUDINALE")
    print("================================")

    checks = {
        "Table competitions": (
            "competitions" in tables
        ),
        "Table riders": (
            "riders" in tables
        ),
        "Table entries": (
            "entries" in tables
        ),
        "Table entry_disciplines": (
            "entry_disciplines" in tables
        ),
        "Table results": (
            "results" in tables
        ),
        "Table result_classifications": (
            "result_classifications" in tables
        ),
    }

    if "competitions" in tables:
        competition_columns = {
            column["name"]
            for column in get_columns(
                connection,
                "competitions",
            )
        }

        checks.update(
            {
                "Année de compétition": bool(
                    {
                        "annee",
                        "year",
                    }
                    & competition_columns
                ),
                "Date de compétition": bool(
                    {
                        "date",
                        "date_debut",
                        "start_date",
                    }
                    & competition_columns
                ),
                "Discipline sportive": (
                    "discipline"
                    in competition_columns
                ),
                "Niveau de compétition": (
                    "niveau"
                    in competition_columns
                ),
                "Statut de collecte": bool(
                    {
                        "statut_collecte",
                        "collection_status",
                    }
                    & competition_columns
                ),
            }
        )

    for label, passed in checks.items():
        status = "OK" if passed else "À AJOUTER"
        print(f"  {status:<10} {label}")


def main() -> None:
    repository = ParticipationRepository()

    with repository.connect() as connection:
        connection.execute(
            "PRAGMA foreign_keys = ON"
        )

        table_names = get_table_names(
            connection
        )

        print()
        print("AUDIT DU SCHÉMA LONGITUDINAL")
        print("============================")
        print()
        print(
            "Tables détectées :",
            len(table_names),
        )

        for table_name in sorted(table_names):
            print(f"  {table_name}")

        for table_name in TABLES_TO_INSPECT:
            if table_name not in table_names:
                print()
                print(table_name)
                print("-" * len(table_name))
                print("TABLE ABSENTE")
                continue

            print_schema(
                connection,
                table_name,
            )

        print_competition_inventory(
            connection
        )

        print_relational_counts(
            connection
        )

        print_longitudinal_readiness(
            connection
        )


if __name__ == "__main__":
    main()