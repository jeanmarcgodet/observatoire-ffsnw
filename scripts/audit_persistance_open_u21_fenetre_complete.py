"""Contrôle strict de la persistance Open selon l'origine U21.

Périmètre comparable :
- première apparition Open observée entre 2020 et 2023 ;
- trois années antérieures disponibles pour rechercher un parcours U21 ;
- trois années postérieures disponibles pour mesurer la persistance Open.

Cette restriction évite :
- la troncature à gauche des cohortes 2018-2019 ;
- la censure à droite des cohortes 2024-2026.

Entrée
------
data/processed/persistance_open_cohortes_comparables_2018_2025.csv

Sorties
-------
data/processed/persistance_open_u21_fenetre_complete_2020_2023.csv
data/exports/diagnostic_persistance_open_u21_fenetre_complete.txt
"""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path


FIRST_YEAR = 2020
LAST_YEAR = 2023


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="", errors="replace") as handle:
        return list(csv.DictReader(handle, delimiter=";"))


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter=";")
        writer.writeheader()
        writer.writerows(rows)


def integer(value: str | None) -> int:
    try:
        return int(str(value or "0").strip())
    except ValueError:
        return 0


def percentage(numerator: int, denominator: int) -> float:
    return round(100 * numerator / denominator, 1) if denominator else 0.0


def main() -> None:
    root = repo_root()
    source = (
        root
        / "data/processed/persistance_open_cohortes_comparables_2018_2025.csv"
    )

    if not source.exists():
        raise FileNotFoundError(source)

    rows = [
        row
        for row in read_csv(source)
        if FIRST_YEAR <= integer(row.get("FirstOpenYear")) <= LAST_YEAR
    ]

    groups: dict[str, list[dict[str, str]]] = defaultdict(list)

    for row in rows:
        group = (
            "U21_DANS_LES_3_ANS_AVANT_OU_MEME_ANNEE"
            if integer(row.get("RecentU21Pathway")) == 1
            else "AUCUN_U21_OBSERVE_DANS_LES_3_ANS"
        )
        groups[group].append(row)

    summary_rows: list[dict[str, object]] = []

    for group_name in (
        "U21_DANS_LES_3_ANS_AVANT_OU_MEME_ANNEE",
        "AUCUN_U21_OBSERVE_DANS_LES_3_ANS",
    ):
        group = groups.get(group_name, [])
        next_year = sum(integer(row.get("OpenNextYear")) for row in group)
        within_two = sum(integer(row.get("OpenWithin2Years")) for row in group)
        within_three = sum(integer(row.get("OpenWithin3Years")) for row in group)
        continuous_three = sum(
            integer(row.get("ContinuousThrough3Years"))
            for row in group
        )

        summary_rows.append(
            {
                "Group": group_name,
                "FirstObservedOpenAthletes": len(group),
                "OpenNextYear": next_year,
                "OpenNextYearRatePercent": percentage(next_year, len(group)),
                "OpenWithin2Years": within_two,
                "OpenWithin2YearsRatePercent": percentage(within_two, len(group)),
                "OpenWithin3Years": within_three,
                "OpenWithin3YearsRatePercent": percentage(within_three, len(group)),
                "ContinuousThrough3Years": continuous_three,
                "ContinuousThrough3YearsRatePercent": percentage(
                    continuous_three, len(group)
                ),
            }
        )

    processed = root / "data/processed"
    exports = root / "data/exports"

    write_csv(
        processed / "persistance_open_u21_fenetre_complete_2020_2023.csv",
        summary_rows,
        [
            "Group",
            "FirstObservedOpenAthletes",
            "OpenNextYear",
            "OpenNextYearRatePercent",
            "OpenWithin2Years",
            "OpenWithin2YearsRatePercent",
            "OpenWithin3Years",
            "OpenWithin3YearsRatePercent",
            "ContinuousThrough3Years",
            "ContinuousThrough3YearsRatePercent",
        ],
    )

    lines: list[str] = []
    lines.append("PERSISTANCE OPEN SELON L'ORIGINE U21 — FENÊTRE COMPLÈTE")
    lines.append("=" * 82)
    lines.append("")
    lines.append(
        "Cohortes de première apparition Open observée 2020-2023 : "
        "trois ans de recul avant et après."
    )
    lines.append("")

    for row in summary_rows:
        lines.append(row["Group"])
        lines.append("-" * 82)
        lines.append(
            f"Effectif : {row['FirstObservedOpenAthletes']}."
        )
        lines.append(
            f"Open l'année suivante : {row['OpenNextYear']}/"
            f"{row['FirstObservedOpenAthletes']} "
            f"({str(row['OpenNextYearRatePercent']).replace('.', ',')} %)."
        )
        lines.append(
            f"Réapparition sous deux ans : {row['OpenWithin2Years']}/"
            f"{row['FirstObservedOpenAthletes']} "
            f"({str(row['OpenWithin2YearsRatePercent']).replace('.', ',')} %)."
        )
        lines.append(
            f"Réapparition sous trois ans : {row['OpenWithin3Years']}/"
            f"{row['FirstObservedOpenAthletes']} "
            f"({str(row['OpenWithin3YearsRatePercent']).replace('.', ',')} %)."
        )
        lines.append(
            f"Présence continue jusqu'à trois ans : "
            f"{row['ContinuousThrough3Years']}/"
            f"{row['FirstObservedOpenAthletes']} "
            f"({str(row['ContinuousThrough3YearsRatePercent']).replace('.', ',')} %)."
        )
        lines.append("")

    total = len(rows)
    u21_total = len(groups.get("U21_DANS_LES_3_ANS_AVANT_OU_MEME_ANNEE", []))

    lines.append("PRÉCAUTIONS")
    lines.append("-" * 82)
    lines.append(
        f"Effectif total : {total}, dont {u21_total} avec un parcours U21 récent."
    )
    lines.append(
        "- La première apparition Open observée n'est pas nécessairement la "
        "première participation Open de toute la carrière."
    )
    lines.append(
        "- Les effectifs restent trop faibles pour attribuer une causalité au parcours U21."
    )
    lines.append(
        "- Une absence au Championnat de France ne signifie pas une absence "
        "de toute compétition."
    )
    lines.append("")
    lines.append("FIN DU DIAGNOSTIC")

    output = exports / "diagnostic_persistance_open_u21_fenetre_complete.txt"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")

    print("=" * 88)
    print("CONTROLE STRICT U21 ET PERSISTANCE OPEN TERMINE")
    print("=" * 88)
    print(f"Sportifs analysés : {total}")
    print(f"Diagnostic : {output}")
    print("Aucun fichier existant n'a été modifié.")


if __name__ == "__main__":
    main()
