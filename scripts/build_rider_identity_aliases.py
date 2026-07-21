"""Construit les correspondances entre identités historiques et canoniques."""

from __future__ import annotations

import csv
import re
import sqlite3
import unicodedata
from collections import defaultdict
from pathlib import Path

from observatoire.config import DATABASE_FILE


def normalize_text(value: str) -> str:
    value = unicodedata.normalize(
        "NFKD",
        value or "",
    )

    value = "".join(
        character
        for character in value
        if not unicodedata.combining(character)
    )

    return re.sub(
        r"[^A-Z0-9]+",
        "",
        value.upper(),
    )


def main() -> None:
    output_directory = Path("data/reference")
    output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    aliases_file = (
        output_directory
        / "rider_identity_aliases.csv"
    )

    review_file = (
        output_directory
        / "rider_identity_review.csv"
    )

    with sqlite3.connect(DATABASE_FILE) as db:
        rows = db.execute(
            """
            SELECT
                r.id,
                COALESCE(r.iwwf_id, ''),
                COALESCE(r.nom, ''),
                COALESCE(r.prenom, ''),
                COALESCE(r.sexe, '')
            FROM riders r
            WHERE EXISTS (
                SELECT 1
                FROM entries e
                WHERE e.rider_id = r.id
            )
            ORDER BY r.id
            """
        ).fetchall()

        years_by_rider = defaultdict(set)

        for rider_id, year in db.execute(
            """
            SELECT DISTINCT
                e.rider_id,
                2000 + CAST(
                    SUBSTR(c.iwwf_id, 1, 2)
                    AS INTEGER
                )
            FROM entries e
            JOIN competitions c
              ON c.id = e.competition_id
            WHERE c.iwwf_id IS NOT NULL
            """
        ):
            years_by_rider[rider_id].add(year)

    groups = defaultdict(list)

    for (
        rider_id,
        iwwf_id,
        last_name,
        first_name,
        sex,
    ) in rows:
        key = (
            normalize_text(last_name),
            normalize_text(first_name),
            sex.strip().upper(),
        )

        groups[key].append(
            {
                "rider_id": rider_id,
                "iwwf_id": iwwf_id.strip().upper(),
                "nom": last_name,
                "prenom": first_name,
                "sexe": sex.strip().upper(),
            }
        )

    aliases = []
    reviews = []

    for key, riders in groups.items():
        if len(riders) < 2:
            continue

        if len(riders) != 2:
            reviews.append(
                {
                    "nom_normalise": key[0],
                    "prenom_normalise": key[1],
                    "sexe": key[2],
                    "rider_ids": ",".join(
                        str(rider["rider_id"])
                        for rider in riders
                    ),
                    "iwwf_ids": ",".join(
                        rider["iwwf_id"]
                        for rider in riders
                    ),
                    "motif": "plus_de_deux_identites",
                }
            )
            continue

        first, second = riders

        numeric = [
            rider
            for rider in riders
            if rider["iwwf_id"].isdigit()
        ]

        official = [
            rider
            for rider in riders
            if re.fullmatch(
                r"[A-Z]{3}\d+",
                rider["iwwf_id"],
            )
            and not rider["iwwf_id"].startswith("IWF")
        ]

        if (
            len(numeric) == 1
            and len(official) == 1
            and official[0]["iwwf_id"].endswith(
                numeric[0]["iwwf_id"]
            )
        ):
            alias = numeric[0]
            canonical = official[0]

            aliases.append(
                {
                    "alias_rider_id": alias["rider_id"],
                    "canonical_rider_id": (
                        canonical["rider_id"]
                    ),
                    "alias_iwwf_id": alias["iwwf_id"],
                    "canonical_iwwf_id": (
                        canonical["iwwf_id"]
                    ),
                    "nom": canonical["nom"],
                    "prenom": canonical["prenom"],
                    "sexe": canonical["sexe"],
                    "regle": (
                        "identifiant_court_suffixe_"
                        "identifiant_officiel"
                    ),
                }
            )
        else:
            reviews.append(
                {
                    "nom_normalise": key[0],
                    "prenom_normalise": key[1],
                    "sexe": key[2],
                    "rider_ids": (
                        f"{first['rider_id']},"
                        f"{second['rider_id']}"
                    ),
                    "iwwf_ids": (
                        f"{first['iwwf_id']},"
                        f"{second['iwwf_id']}"
                    ),
                    "annees": ",".join(
                        str(year)
                        for year in sorted(
                            years_by_rider[
                                first["rider_id"]
                            ]
                            | years_by_rider[
                                second["rider_id"]
                            ]
                        )
                    ),
                    "motif": (
                        "identifiants_non_equivalents"
                    ),
                }
            )

    aliases.sort(
        key=lambda row: (
            row["nom"],
            row["prenom"],
        )
    )

    reviews.sort(
        key=lambda row: (
            row["nom_normalise"],
            row["prenom_normalise"],
        )
    )

    with aliases_file.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(aliases[0]),
            delimiter=";",
        )

        writer.writeheader()
        writer.writerows(aliases)

    with review_file.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(reviews[0]),
            delimiter=";",
        )

        writer.writeheader()
        writer.writerows(reviews)

    print("=" * 78)
    print("IDENTITES CANONIQUES")
    print("=" * 78)
    print("Correspondances automatiques :", len(aliases))
    print("Cas en revue manuelle        :", len(reviews))

    if len(aliases) != 114:
        raise RuntimeError(
            f"114 correspondances attendues, "
            f"{len(aliases)} obtenues."
        )

    if len(reviews) != 3:
        raise RuntimeError(
            f"3 cas en revue attendus, "
            f"{len(reviews)} obtenus."
        )

    print()
    print("CAS EN REVUE")

    for row in reviews:
        print(
            row["nom_normalise"],
            row["prenom_normalise"],
            "| riders=",
            row["rider_ids"],
            "| iwwf=",
            row["iwwf_ids"],
            "| annees=",
            row.get("annees", ""),
        )

    print()
    print("Fichiers générés :")
    print(" -", aliases_file)
    print(" -", review_file)


if __name__ == "__main__":
    main()
