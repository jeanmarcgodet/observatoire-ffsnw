from __future__ import annotations

import argparse
import sqlite3
from dataclasses import dataclass

from observatoire.config import DATABASE_FILE


CATEGORY_NORMALIZATIONS = {
    "Ope": "Open",
    "OPEN": "Open",
    "open": "Open",
    "-21": "U21",
    "u21": "U21",
}


@dataclass
class MigrationStats:
    categories_updated: int = 0
    alias_rows_merged: int = 0


def migrate_category_aliases(
    connection: sqlite3.Connection,
    *,
    apply_changes: bool,
) -> MigrationStats:
    """
    Normalise uniquement les catégories équivalentes.

    Lorsqu'une catégorie canonique existe déjà pour le même rider
    et la même compétition, la ligne abrégée est fusionnée puis
    supprimée.

    Les vraies inscriptions multiples, telles que Open + 55+,
    sont conservées.
    """
    stats = MigrationStats()

    for old_category, new_category in (
        CATEGORY_NORMALIZATIONS.items()
    ):
        rows = connection.execute(
            """
            SELECT
                id,
                competition_id,
                rider_id,
                categorie,
                club,
                equipe
            FROM entries
            WHERE categorie = ?
            ORDER BY competition_id, rider_id, id
            """,
            (old_category,),
        ).fetchall()

        for row in rows:
            canonical_row = connection.execute(
                """
                SELECT
                    id,
                    club,
                    equipe
                FROM entries
                WHERE competition_id = ?
                  AND rider_id = ?
                  AND categorie = ?
                LIMIT 1
                """,
                (
                    row["competition_id"],
                    row["rider_id"],
                    new_category,
                ),
            ).fetchone()

            if canonical_row is not None:
                print(
                    "[FUSION] "
                    f"competition_id={row['competition_id']} "
                    f"rider_id={row['rider_id']} "
                    f"{old_category!r} -> {new_category!r}"
                )

                if apply_changes:
                    # On conserve les éventuelles informations
                    # complémentaires de la ligne abrégée.
                    connection.execute(
                        """
                        UPDATE entries
                        SET
                            club = CASE
                                WHEN club IS NULL OR TRIM(club) = ''
                                THEN ?
                                ELSE club
                            END,
                            equipe = CASE
                                WHEN equipe IS NULL OR TRIM(equipe) = ''
                                THEN ?
                                ELSE equipe
                            END
                        WHERE id = ?
                        """,
                        (
                            row["club"],
                            row["equipe"],
                            canonical_row["id"],
                        ),
                    )

                    connection.execute(
                        """
                        DELETE FROM entries
                        WHERE id = ?
                        """,
                        (row["id"],),
                    )

                stats.alias_rows_merged += 1
                continue

            print(
                "[NORMALISATION] "
                f"competition_id={row['competition_id']} "
                f"rider_id={row['rider_id']} "
                f"{old_category!r} -> {new_category!r}"
            )

            if apply_changes:
                connection.execute(
                    """
                    UPDATE entries
                    SET categorie = ?
                    WHERE id = ?
                    """,
                    (
                        new_category,
                        row["id"],
                    ),
                )

            stats.categories_updated += 1

    return stats


def show_remaining_aliases(
    connection: sqlite3.Connection,
) -> None:
    aliases = tuple(CATEGORY_NORMALIZATIONS)

    placeholders = ", ".join(
        "?"
        for _ in aliases
    )

    rows = connection.execute(
        f"""
        SELECT
            e.id,
            c.iwwf_id AS competition_code,
            r.iwwf_id AS rider_code,
            r.nom,
            r.prenom,
            e.categorie
        FROM entries e
        JOIN competitions c
          ON c.id = e.competition_id
        JOIN riders r
          ON r.id = e.rider_id
        WHERE e.categorie IN ({placeholders})
        ORDER BY c.annee DESC, r.nom, r.prenom
        """,
        aliases,
    ).fetchall()

    print()
    print("CATÉGORIES ABRÉGÉES RESTANTES")
    print("=============================")

    if not rows:
        print("Aucune.")
        return

    for row in rows:
        print(
            f"{row['competition_code']} | "
            f"{row['rider_code']} | "
            f"{row['nom']} {row['prenom'] or ''} | "
            f"{row['categorie']}"
        )


def show_multiple_categories(
    connection: sqlite3.Connection,
) -> None:
    rows = connection.execute(
        """
        SELECT
            c.iwwf_id AS competition_code,
            r.iwwf_id AS rider_code,
            r.nom,
            r.prenom,
            COUNT(*) AS category_count,
            GROUP_CONCAT(
                e.categorie,
                ', '
            ) AS categories
        FROM entries e
        JOIN competitions c
          ON c.id = e.competition_id
        JOIN riders r
          ON r.id = e.rider_id
        GROUP BY
            e.competition_id,
            e.rider_id
        HAVING COUNT(*) > 1
        ORDER BY
            c.annee DESC,
            r.nom,
            r.prenom
        """
    ).fetchall()

    print()
    print("INSCRIPTIONS MULTICATÉGORIES CONSERVÉES")
    print("======================================")

    if not rows:
        print("Aucune.")
        return

    for row in rows:
        print(
            f"{row['competition_code']} | "
            f"{row['rider_code']} | "
            f"{row['nom']} {row['prenom'] or ''} | "
            f"{row['categories']}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Normalise les catégories des inscriptions "
            "sans supprimer les vraies inscriptions "
            "multicatégories."
        )
    )

    parser.add_argument(
        "--apply",
        action="store_true",
        help="Applique réellement les modifications.",
    )

    args = parser.parse_args()

    connection = sqlite3.connect(DATABASE_FILE)
    connection.row_factory = sqlite3.Row

    try:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("BEGIN")

        stats = migrate_category_aliases(
            connection,
            apply_changes=args.apply,
        )

        if args.apply:
            connection.commit()
        else:
            connection.rollback()

        print()
        print("RÉSUMÉ")
        print("======")
        print(
            "Mode                  :",
            "APPLICATION" if args.apply else "SIMULATION",
        )
        print(
            "Catégories normalisées:",
            stats.categories_updated,
        )
        print(
            "Lignes alias fusionnées:",
            stats.alias_rows_merged,
        )

        show_remaining_aliases(connection)
        show_multiple_categories(connection)

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


if __name__ == "__main__":
    main()
