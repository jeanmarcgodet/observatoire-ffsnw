"""Construit les matrices de transition entre populations d'âge EMS."""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

SOURCE_FILE = (
    ROOT
    / "data/processed"
    / "ems_competiteurs_annee_sexe_age_2023_2025.csv"
)

OUTPUT_FILE = (
    ROOT
    / "data/processed"
    / "ems_matrice_transitions_age_2023_2025.csv"
)

AGE_ORDER = {
    "RELEVES": 1,
    "JUNIOR": 2,
    "U21": 3,
    "OPEN": 4,
    "SENIOR": 5,
    "EXIT": 9,
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        return list(
            csv.DictReader(
                file,
                delimiter=";",
            )
        )


def write_csv(
    path: Path,
    rows: list[dict[str, Any]],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=list(rows[0].keys()),
            delimiter=";",
        )
        writer.writeheader()
        writer.writerows(rows)


def percent(
    numerator: int,
    denominator: int,
) -> float:
    if denominator == 0:
        return 0.0

    return round(
        100 * numerator / denominator,
        1,
    )


def main() -> None:
    rows = read_csv(SOURCE_FILE)

    year_maps: dict[
        int,
        dict[str, dict[str, str]],
    ] = {
        2023: {},
        2024: {},
        2025: {},
    }

    for row in rows:
        year = int(row["Year"])

        year_maps[year][
            row["AthleteKey"]
        ] = row

    output_rows: list[
        dict[str, Any]
    ] = []

    for from_year, to_year in (
        (2023, 2024),
        (2024, 2025),
    ):
        source = year_maps[from_year]
        destination = year_maps[to_year]

        for sex_filter in (
            "ALL",
            "F",
            "M",
        ):
            counts: Counter[
                tuple[str, str]
            ] = Counter()

            origin_totals: Counter[
                str
            ] = Counter()

            for athlete_key, row in source.items():
                sex = row["Sex"]

                if (
                    sex_filter != "ALL"
                    and sex != sex_filter
                ):
                    continue

                origin = row["AgeBand"]

                destination_row = (
                    destination.get(
                        athlete_key
                    )
                )

                if destination_row:
                    target = (
                        destination_row[
                            "AgeBand"
                        ]
                    )
                else:
                    target = "EXIT"

                counts[
                    (
                        origin,
                        target,
                    )
                ] += 1

                origin_totals[
                    origin
                ] += 1

            for (
                origin,
                target,
            ), athletes in sorted(
                counts.items(),
                key=lambda item: (
                    AGE_ORDER.get(
                        item[0][0],
                        99,
                    ),
                    AGE_ORDER.get(
                        item[0][1],
                        99,
                    ),
                ),
            ):
                output_rows.append(
                    {
                        "FromYear": from_year,
                        "ToYear": to_year,
                        "Sex": sex_filter,
                        "OriginAgeBand": (
                            origin
                        ),
                        "DestinationAgeBand": (
                            target
                        ),
                        "Athletes": athletes,
                        "OriginAthletes": (
                            origin_totals[
                                origin
                            ]
                        ),
                        "ShareOfOriginPercent": (
                            percent(
                                athletes,
                                origin_totals[
                                    origin
                                ],
                            )
                        ),
                    }
                )

    write_csv(
        OUTPUT_FILE,
        output_rows,
    )

    print("=" * 105)
    print(
        "MATRICES DE TRANSITION ENTRE "
        "POPULATIONS D'ÂGE"
    )
    print("=" * 105)

    for from_year, to_year in (
        (2023, 2024),
        (2024, 2025),
    ):
        print()
        print(
            f"{from_year} → {to_year} — "
            f"ENSEMBLE DES COMPÉTITEURS"
        )
        print("-" * 85)

        selected = [
            row
            for row in output_rows
            if row["FromYear"]
            == from_year
            and row["Sex"] == "ALL"
        ]

        print(
            f"{'Origine':<12}"
            f"{'Destination':<14}"
            f"{'Sportifs':>10}"
            f"{'Effectif origine':>18}"
            f"{'Part':>10}"
        )
        print("-" * 65)

        for row in selected:
            print(
                f"{row['OriginAgeBand']:<12}"
                f"{row['DestinationAgeBand']:<14}"
                f"{row['Athletes']:>10}"
                f"{row['OriginAthletes']:>18}"
                f"{float(row['ShareOfOriginPercent']):>9.1f}%"
            )

    print()
    print("Fichier :", OUTPUT_FILE)


if __name__ == "__main__":
    main()