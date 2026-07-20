"""Audit des engagements et de la participation effective."""

from __future__ import annotations

import sqlite3
from pathlib import Path


DATABASE_PATH = Path("data/observatoire.db")


def main() -> None:
    if not DATABASE_PATH.exists():
        raise FileNotFoundError(
            f"Base introuvable : {DATABASE_PATH}"
        )

    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.row_factory = sqlite3.Row

        print("1. Riders inscrits plusieurs fois")
        print("--------------------------------")

        duplicate_entries = connection.execute(
            """
            SELECT
                e.competition_id,
                e.rider_id,
                r.iwwf_id,
                r.prenom,
                r.nom,
                COUNT(*) AS nombre_engagements,
                GROUP_CONCAT(e.categorie, ', ') AS categories
            FROM entries AS e
            JOIN riders AS r
                ON r.id = e.rider_id
            GROUP BY
                e.competition_id,
                e.rider_id
            HAVING COUNT(*) > 1
            ORDER BY
                r.nom,
                r.prenom
            """
        ).fetchall()

        if duplicate_entries:
            for row in duplicate_entries:
                print(
                    f"{row['prenom']} {row['nom']} | "
                    f"{row['iwwf_id']} | "
                    f"{row['nombre_engagements']} engagements | "
                    f"{row['categories']}"
                )
        else:
            print("Aucun engagement multiple.")

        print()
        print("2. Riders inscrits sans résultat")
        print("--------------------------------")

        riders_without_results = connection.execute(
            """
            SELECT
                e.id AS entry_id,
                e.categorie,
                r.id AS rider_id,
                r.iwwf_id,
                r.prenom,
                r.nom,
                r.sexe,
                r.nation
            FROM entries AS e
            JOIN riders AS r
                ON r.id = e.rider_id
            LEFT JOIN results AS res
                ON res.competition_id = e.competition_id
               AND res.rider_id = e.rider_id
            WHERE res.id IS NULL
            ORDER BY
                r.nom,
                r.prenom
            """
        ).fetchall()

        if riders_without_results:
            for row in riders_without_results:
                print(
                    f"{row['prenom']} {row['nom']} | "
                    f"{row['iwwf_id']} | "
                    f"catégorie={row['categorie']} | "
                    f"sexe={row['sexe']} | "
                    f"nation={row['nation']}"
                )
        else:
            print("Tous les inscrits ont au moins un résultat.")

        print()
        print("3. Riders avec résultat mais sans engagement")
        print("--------------------------------------------")

        results_without_entry = connection.execute(
            """
            SELECT DISTINCT
                res.competition_id,
                res.rider_id,
                r.iwwf_id,
                r.prenom,
                r.nom
            FROM results AS res
            JOIN riders AS r
                ON r.id = res.rider_id
            LEFT JOIN entries AS e
                ON e.competition_id = res.competition_id
               AND e.rider_id = res.rider_id
            WHERE e.id IS NULL
            ORDER BY
                r.nom,
                r.prenom
            """
        ).fetchall()

        if results_without_entry:
            for row in results_without_entry:
                print(
                    f"{row['prenom']} {row['nom']} | "
                    f"{row['iwwf_id']}"
                )
        else:
            print(
                "Tous les riders ayant un résultat "
                "ont un engagement."
            )

        print()
        print("4. Nombre de disciplines par rider")
        print("----------------------------------")

        disciplines_per_rider = connection.execute(
            """
            SELECT
                r.iwwf_id,
                r.prenom,
                r.nom,
                COUNT(
                    DISTINCT CASE
                        WHEN res.discipline != 'overall'
                        THEN res.discipline
                    END
                ) AS nombre_disciplines,
                GROUP_CONCAT(
                    DISTINCT CASE
                        WHEN res.discipline != 'overall'
                        THEN res.discipline
                    END
                ) AS disciplines
            FROM riders AS r
            JOIN results AS res
                ON res.rider_id = r.id
            GROUP BY
                r.id,
                r.iwwf_id,
                r.prenom,
                r.nom
            ORDER BY
                nombre_disciplines DESC,
                r.nom,
                r.prenom
            """
        ).fetchall()

        for row in disciplines_per_rider:
            print(
                f"{row['prenom']} {row['nom']:<25} | "
                f"{row['nombre_disciplines']} | "
                f"{row['disciplines']}"
            )

        print()
        print("5. Synthèse")
        print("-----------")

        summary = connection.execute(
            """
            SELECT
                (
                    SELECT COUNT(*)
                    FROM entries
                ) AS nombre_engagements,

                (
                    SELECT COUNT(DISTINCT rider_id)
                    FROM entries
                ) AS riders_inscrits,

                (
                    SELECT COUNT(DISTINCT rider_id)
                    FROM results
                ) AS riders_avec_resultat,

                (
                    SELECT COUNT(DISTINCT rider_id)
                    FROM result_classifications AS rc
                    JOIN results AS res
                        ON res.id = rc.result_id
                ) AS riders_classes
            """
        ).fetchone()

        print(
            f"Engagements             : "
            f"{summary['nombre_engagements']}"
        )
        print(
            f"Riders inscrits         : "
            f"{summary['riders_inscrits']}"
        )
        print(
            f"Riders avec résultat    : "
            f"{summary['riders_avec_resultat']}"
        )
        print(
            f"Riders classés          : "
            f"{summary['riders_classes']}"
        )


if __name__ == "__main__":
    main()