"""Corrige les categories d'inscription depuis les resultats non ambigus."""

from __future__ import annotations

import argparse
import sqlite3

from observatoire.config import DATABASE_FILE


def find_mismatches(
    database: sqlite3.Connection,
    competition_code: str,
):
    return database.execute(
        """
        SELECT
            e.id,
            e.rider_id,
            r.prenom,
            r.nom,
            e.categorie,
            MIN(TRIM(rc.categorie)) AS target_category,
            COUNT(DISTINCT TRIM(rc.categorie))
        FROM entries e
        JOIN competitions c
          ON c.id = e.competition_id
        JOIN riders r
          ON r.id = e.rider_id
        JOIN results re
          ON re.competition_id = e.competition_id
         AND re.rider_id = e.rider_id
        JOIN result_classifications rc
          ON rc.result_id = re.id
        WHERE c.iwwf_id = ?
          AND rc.categorie IS NOT NULL
          AND TRIM(rc.categorie) <> ''
        GROUP BY
            e.id,
            e.rider_id,
            r.prenom,
            r.nom,
            e.categorie
        HAVING COUNT(
            DISTINCT TRIM(rc.categorie)
        ) = 1
           AND TRIM(e.categorie)
               <> MIN(TRIM(rc.categorie))
        ORDER BY
            r.nom,
            r.prenom
        """,
        (competition_code,),
    ).fetchall()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("competition_code")
    parser.add_argument(
        "--expected",
        type=int,
        default=None,
    )
    arguments = parser.parse_args()

    with sqlite3.connect(DATABASE_FILE) as database:
        database.execute(
            "PRAGMA foreign_keys = ON"
        )

        mismatches = find_mismatches(
            database,
            arguments.competition_code,
        )

        print("=" * 82)
        print("CORRECTION DES CATEGORIES D'INSCRIPTION")
        print("=" * 82)
        print(
            "Competition :",
            arguments.competition_code,
        )
        print(
            "Corrections detectees :",
            len(mismatches),
        )

        for (
            entry_id,
            rider_id,
            first_name,
            last_name,
            source_category,
            target_category,
            category_count,
        ) in mismatches:
            print(
                f" - {first_name} {last_name}: "
                f"{source_category} -> {target_category}"
            )

        if (
            arguments.expected is not None
            and len(mismatches)
            != arguments.expected
        ):
            raise RuntimeError(
                f"{arguments.expected} corrections "
                f"attendues, {len(mismatches)} obtenues."
            )

        for (
            entry_id,
            rider_id,
            first_name,
            last_name,
            source_category,
            target_category,
            category_count,
        ) in mismatches:
            database.execute(
                """
                UPDATE entries
                SET categorie = ?
                WHERE id = ?
                """,
                (
                    target_category,
                    entry_id,
                ),
            )

        database.commit()

        remaining = find_mismatches(
            database,
            arguments.competition_code,
        )

        foreign_keys = database.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()

        categories = database.execute(
            """
            SELECT
                e.categorie,
                COUNT(DISTINCT e.rider_id)
            FROM entries e
            JOIN competitions c
              ON c.id = e.competition_id
            WHERE c.iwwf_id = ?
              AND e.categorie LIKE '%+'
            GROUP BY e.categorie
            ORDER BY e.categorie
            """,
            (arguments.competition_code,),
        ).fetchall()

    print()
    print("Categories apres correction :")

    for category, participants in categories:
        print(
            f" - {category}: "
            f"{participants} participants"
        )

    print()
    print(
        "Incoherences restantes :",
        len(remaining),
    )
    print(
        "Foreign key check      :",
        foreign_keys,
    )

    if remaining:
        raise RuntimeError(
            "Des incoherences subsistent."
        )

    if foreign_keys:
        raise RuntimeError(
            "Erreur de cle etrangere."
        )

    print()
    print("CORRECTION CONFORME.")


if __name__ == "__main__":
    main()
