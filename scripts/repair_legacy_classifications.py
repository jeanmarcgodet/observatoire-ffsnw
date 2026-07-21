"""Normalise les classifications historiques depuis les inscriptions."""

import argparse
import sqlite3

from observatoire.config import DATABASE_FILE


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("competition_code")
    args = parser.parse_args()

    code = args.competition_code.strip().upper()

    with sqlite3.connect(DATABASE_FILE) as db:
        competition = db.execute(
            """
            SELECT id
            FROM competitions
            WHERE iwwf_id = ?
            """,
            (code,),
        ).fetchone()

        if competition is None:
            raise RuntimeError(
                f"Competition absente : {code}"
            )

        competition_id = competition[0]

        results = db.execute(
            """
            SELECT
                re.id,
                r.sexe,
                e.categorie
            FROM results re
            JOIN riders r
              ON r.id = re.rider_id
            JOIN entries e
              ON e.competition_id = re.competition_id
             AND e.rider_id = re.rider_id
            WHERE re.competition_id = ?
            ORDER BY re.id
            """,
            (competition_id,),
        ).fetchall()

        repaired = 0
        deleted = 0

        for result_id, sex, category in results:
            classifications = db.execute(
                """
                SELECT id
                FROM result_classifications
                WHERE result_id = ?
                ORDER BY id
                """,
                (result_id,),
            ).fetchall()

            if not classifications:
                raise RuntimeError(
                    f"Resultat sans classification : {result_id}"
                )

            label = (
                f"{category} Women"
                if sex == "F"
                else f"{category} Men"
            )

            kept_id = classifications[0][0]

            db.execute(
                """
                UPDATE result_classifications
                SET categorie = ?,
                    classement = ?
                WHERE id = ?
                """,
                (
                    category,
                    label,
                    kept_id,
                ),
            )

            for duplicate in classifications[1:]:
                db.execute(
                    """
                    DELETE FROM result_classifications
                    WHERE id = ?
                    """,
                    (duplicate[0],),
                )
                deleted += 1

            repaired += 1

        db.commit()

        totals = db.execute(
            """
            SELECT
                COUNT(DISTINCT e.rider_id),
                COUNT(DISTINCT e.id),
                COUNT(DISTINCT re.id),
                COUNT(DISTINCT rc.id)
            FROM competitions c
            LEFT JOIN entries e
              ON e.competition_id = c.id
            LEFT JOIN results re
              ON re.competition_id = c.id
            LEFT JOIN result_classifications rc
              ON rc.result_id = re.id
            WHERE c.iwwf_id = ?
            """,
            (code,),
        ).fetchone()

        checks = {
            "Categories classement vides": """
                SELECT COUNT(*)
                FROM result_classifications
                WHERE categorie IS NULL
                   OR TRIM(categorie) = ''
            """,
            "Resultats sans classification": """
                SELECT COUNT(*)
                FROM results re
                LEFT JOIN result_classifications rc
                  ON rc.result_id = re.id
                WHERE rc.id IS NULL
            """,
            "Resultats sans inscription": """
                SELECT COUNT(*)
                FROM results re
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM entries e
                    WHERE e.competition_id = re.competition_id
                      AND e.rider_id = re.rider_id
                )
            """,
            "Classifications multiples": """
                SELECT COUNT(*)
                FROM (
                    SELECT rc.result_id
                    FROM result_classifications rc
                    JOIN results re
                      ON re.id = rc.result_id
                    WHERE re.competition_id = ?
                    GROUP BY rc.result_id
                    HAVING COUNT(*) <> 1
                )
            """,
            "Classifications Open 19FRA03": """
                SELECT COUNT(*)
                FROM result_classifications rc
                JOIN results re
                  ON re.id = rc.result_id
                WHERE re.competition_id = ?
                  AND rc.classement IN (
                      'Open Men',
                      'Open Women'
                  )
            """,
        }

        print()
        print(code)
        print("Riders          :", totals[0])
        print("Inscriptions    :", totals[1])
        print("Resultats       :", totals[2])
        print("Classifications :", totals[3])
        print("Resultats repares :", repaired)
        print("Doublons supprimes :", deleted)

        failures = []

        for label, query in checks.items():
            parameters = (
                (competition_id,)
                if "?" in query
                else ()
            )

            value = db.execute(
                query,
                parameters,
            ).fetchone()[0]

            print(f"{label:<38}: {value}")

            if value != 0:
                failures.append(
                    f"{label}={value}"
                )

        foreign_keys = db.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()

        print(
            f"{'Foreign key check':<38}:",
            foreign_keys,
        )

        if totals != (27, 27, 95, 95):
            failures.append(
                f"totaux={totals}"
            )

        if foreign_keys:
            failures.append("foreign keys")

        if failures:
            raise RuntimeError(
                "Audit non conforme : "
                + ", ".join(failures)
            )

        print()
        print("TOUS LES CONTROLES SONT CONFORMES.")


if __name__ == "__main__":
    main()
