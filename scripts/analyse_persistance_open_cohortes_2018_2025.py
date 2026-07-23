"""Analyse la pérennité Open sur des cohortes comparables, 2018-2025.

Objectifs
---------
- exclure la cohorte 2017, tronquée à gauche ;
- appliquer un recul identique selon l'horizon étudié ;
- distinguer réapparition et continuité annuelle ;
- comparer les entrants issus d'un parcours U21 observable aux autres entrants.

Entrées
-------
data/processed/registre_championnats_filiere_open_2017_2026.csv
data/processed/cohortes_entree_open_persistance_2017_2026.csv

Sorties
-------
data/processed/persistance_open_cohortes_comparables_2018_2025.csv
data/processed/synthese_persistance_open_cohortes_2018_2025.csv
data/processed/persistance_open_selon_origine_u21_2018_2023.csv
data/exports/diagnostic_persistance_open_cohortes_2018_2025.txt
"""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path


START_COHORT = 2018
END_YEAR = 2026


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


def integer(value: str | None) -> int | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def flag(value: str | None) -> bool:
    return integer(value) == 1


def percentage(numerator: int, denominator: int) -> float:
    return round(100 * numerator / denominator, 1) if denominator else 0.0


def parse_years(value: str | None) -> set[int]:
    years: set[int] = set()
    for part in str(value or "").split("|"):
        parsed = integer(part.strip())
        if parsed is not None:
            years.add(parsed)
    return years


def origin_u21(
    rider_id: int,
    first_open: int,
    register_lookup: dict[tuple[int, int], dict[str, str]],
) -> str:
    if flag(register_lookup.get((first_open, rider_id), {}).get("HasU21")):
        return "U21_MEME_ANNEE"

    if flag(register_lookup.get((first_open - 1, rider_id), {}).get("HasU21")):
        return "U21_UN_AN_AVANT"

    if any(
        flag(register_lookup.get((year, rider_id), {}).get("HasU21"))
        for year in (first_open - 2, first_open - 3)
    ):
        return "U21_DEUX_TROIS_ANS_AVANT"

    if any(
        flag(register_lookup.get((year, rider_id), {}).get("HasU21"))
        for year in range(2017, first_open - 3)
    ):
        return "U21_PLUS_ANCIEN_OBSERVE"

    return "SANS_U21_OBSERVE_AVANT_OPEN"


def main() -> None:
    root = repo_root()

    register_path = (
        root / "data/processed/registre_championnats_filiere_open_2017_2026.csv"
    )
    cohorts_path = (
        root / "data/processed/cohortes_entree_open_persistance_2017_2026.csv"
    )

    if not register_path.exists():
        raise FileNotFoundError(register_path)
    if not cohorts_path.exists():
        raise FileNotFoundError(cohorts_path)

    register = read_csv(register_path)
    cohorts = read_csv(cohorts_path)

    register_lookup: dict[tuple[int, int], dict[str, str]] = {}
    for row in register:
        year = integer(row.get("Year"))
        rider_id = integer(row.get("CanonicalRiderId"))
        if year is None or rider_id is None:
            continue
        register_lookup[(year, rider_id)] = row

    detail_rows: list[dict[str, object]] = []

    for row in cohorts:
        rider_id = integer(row.get("CanonicalRiderId"))
        first_open = integer(row.get("FirstOpenYear"))
        if rider_id is None or first_open is None:
            continue
        if first_open < START_COHORT:
            continue

        open_years = parse_years(row.get("OpenYears"))
        available = END_YEAR - first_open

        next_year = first_open + 1 in open_years
        within_2 = any(year in open_years for year in (first_open + 1, first_open + 2))
        within_3 = any(
            year in open_years
            for year in (first_open + 1, first_open + 2, first_open + 3)
        )

        continuous_2 = all(
            year in open_years
            for year in (first_open, first_open + 1)
        )
        continuous_3 = all(
            year in open_years
            for year in (first_open, first_open + 1, first_open + 2)
        )
        continuous_4 = all(
            year in open_years
            for year in (
                first_open,
                first_open + 1,
                first_open + 2,
                first_open + 3,
            )
        )

        origin = origin_u21(rider_id, first_open, register_lookup)
        from_u21_recent = int(
            origin in {
                "U21_MEME_ANNEE",
                "U21_UN_AN_AVANT",
                "U21_DEUX_TROIS_ANS_AVANT",
            }
        )

        detail_rows.append(
            {
                "CanonicalRiderId": rider_id,
                "Name": row.get("Name", ""),
                "Sex": row.get("Sex", ""),
                "YOB": row.get("YOB", ""),
                "FirstOpenYear": first_open,
                "OpenYears": row.get("OpenYears", ""),
                "OpenSeasonsObserved": integer(row.get("OpenSeasons")) or 0,
                "AvailableFollowUpYears": available,
                "OriginBeforeFirstOpen": origin,
                "RecentU21Pathway": from_u21_recent,
                "OpenNextYear": int(next_year) if available >= 1 else "",
                "OpenWithin2Years": int(within_2) if available >= 2 else "",
                "OpenWithin3Years": int(within_3) if available >= 3 else "",
                "ContinuousThroughNextYear": int(continuous_2) if available >= 1 else "",
                "ContinuousThrough2Years": int(continuous_3) if available >= 2 else "",
                "ContinuousThrough3Years": int(continuous_4) if available >= 3 else "",
            }
        )

    summary_rows: list[dict[str, object]] = []

    for horizon, return_field, continuous_field in (
        (1, "OpenNextYear", "ContinuousThroughNextYear"),
        (2, "OpenWithin2Years", "ContinuousThrough2Years"),
        (3, "OpenWithin3Years", "ContinuousThrough3Years"),
    ):
        analyzable = [
            row
            for row in detail_rows
            if int(row["AvailableFollowUpYears"]) >= horizon
        ]
        returned = sum(int(row[return_field]) for row in analyzable)
        continuous = sum(int(row[continuous_field]) for row in analyzable)

        summary_rows.append(
            {
                "Dimension": "ALL",
                "Group": "ALL",
                "HorizonYears": horizon,
                "AnalyzableEntrants": len(analyzable),
                "ReturnedOpen": returned,
                "ReturnRatePercent": percentage(returned, len(analyzable)),
                "ContinuousOpen": continuous,
                "ContinuousRatePercent": percentage(continuous, len(analyzable)),
            }
        )

        for origin_group, selector in (
            ("U21_RECENT", lambda row: int(row["RecentU21Pathway"]) == 1),
            ("SANS_U21_RECENT", lambda row: int(row["RecentU21Pathway"]) == 0),
        ):
            group = [row for row in analyzable if selector(row)]
            group_returned = sum(int(row[return_field]) for row in group)
            group_continuous = sum(int(row[continuous_field]) for row in group)

            summary_rows.append(
                {
                    "Dimension": "ORIGINE_U21",
                    "Group": origin_group,
                    "HorizonYears": horizon,
                    "AnalyzableEntrants": len(group),
                    "ReturnedOpen": group_returned,
                    "ReturnRatePercent": percentage(group_returned, len(group)),
                    "ContinuousOpen": group_continuous,
                    "ContinuousRatePercent": percentage(group_continuous, len(group)),
                }
            )

    cohort_summary_rows: list[dict[str, object]] = []
    by_first_year: dict[int, list[dict[str, object]]] = defaultdict(list)

    for row in detail_rows:
        by_first_year[int(row["FirstOpenYear"])].append(row)

    for year in sorted(by_first_year):
        group = by_first_year[year]
        available = END_YEAR - year
        cohort_summary_rows.append(
            {
                "FirstOpenYear": year,
                "Entrants": len(group),
                "RecentU21Pathway": sum(
                    int(row["RecentU21Pathway"]) for row in group
                ),
                "AvailableFollowUpYears": available,
                "OpenNextYear": (
                    sum(int(row["OpenNextYear"]) for row in group)
                    if available >= 1 else ""
                ),
                "OpenNextYearRatePercent": (
                    percentage(
                        sum(int(row["OpenNextYear"]) for row in group),
                        len(group),
                    )
                    if available >= 1 else ""
                ),
                "OpenWithin3Years": (
                    sum(int(row["OpenWithin3Years"]) for row in group)
                    if available >= 3 else ""
                ),
                "OpenWithin3YearsRatePercent": (
                    percentage(
                        sum(int(row["OpenWithin3Years"]) for row in group),
                        len(group),
                    )
                    if available >= 3 else ""
                ),
            }
        )

    processed = root / "data/processed"
    exports = root / "data/exports"

    write_csv(
        processed / "persistance_open_cohortes_comparables_2018_2025.csv",
        detail_rows,
        [
            "CanonicalRiderId",
            "Name",
            "Sex",
            "YOB",
            "FirstOpenYear",
            "OpenYears",
            "OpenSeasonsObserved",
            "AvailableFollowUpYears",
            "OriginBeforeFirstOpen",
            "RecentU21Pathway",
            "OpenNextYear",
            "OpenWithin2Years",
            "OpenWithin3Years",
            "ContinuousThroughNextYear",
            "ContinuousThrough2Years",
            "ContinuousThrough3Years",
        ],
    )

    write_csv(
        processed / "synthese_persistance_open_cohortes_2018_2025.csv",
        cohort_summary_rows,
        [
            "FirstOpenYear",
            "Entrants",
            "RecentU21Pathway",
            "AvailableFollowUpYears",
            "OpenNextYear",
            "OpenNextYearRatePercent",
            "OpenWithin3Years",
            "OpenWithin3YearsRatePercent",
        ],
    )

    write_csv(
        processed / "persistance_open_selon_origine_u21_2018_2023.csv",
        summary_rows,
        [
            "Dimension",
            "Group",
            "HorizonYears",
            "AnalyzableEntrants",
            "ReturnedOpen",
            "ReturnRatePercent",
            "ContinuousOpen",
            "ContinuousRatePercent",
        ],
    )

    lines: list[str] = []
    lines.append("PÉRENNITÉ OPEN — COHORTES COMPARABLES 2018-2025")
    lines.append("=" * 82)
    lines.append("")
    lines.append("1. INDICATEURS GLOBAUX")
    lines.append("-" * 82)

    for row in summary_rows:
        if row["Dimension"] != "ALL":
            continue
        lines.append(
            f"Horizon {row['HorizonYears']} an(s) : "
            f"réapparition Open={row['ReturnedOpen']}/{row['AnalyzableEntrants']} "
            f"({str(row['ReturnRatePercent']).replace('.', ',')} %) ; "
            f"continuité sans interruption={row['ContinuousOpen']}/"
            f"{row['AnalyzableEntrants']} "
            f"({str(row['ContinuousRatePercent']).replace('.', ',')} %)."
        )

    lines.append("")
    lines.append("2. SELON L'ORIGINE U21 OBSERVABLE")
    lines.append("-" * 82)

    for horizon in (1, 2, 3):
        lines.append(f"Horizon {horizon} an(s) :")
        for row in summary_rows:
            if (
                row["Dimension"] == "ORIGINE_U21"
                and int(row["HorizonYears"]) == horizon
            ):
                lines.append(
                    f"- {row['Group']} : "
                    f"{row['ReturnedOpen']}/{row['AnalyzableEntrants']} réapparaissent "
                    f"({str(row['ReturnRatePercent']).replace('.', ',')} %) ; "
                    f"{row['ContinuousOpen']} sans interruption "
                    f"({str(row['ContinuousRatePercent']).replace('.', ',')} %)."
                )

    lines.append("")
    lines.append("3. PAR COHORTE DE PREMIÈRE APPARITION OPEN")
    lines.append("-" * 82)

    for row in cohort_summary_rows:
        lines.append(
            f"{row['FirstOpenYear']} : entrants={row['Entrants']} ; "
            f"issus d'un U21 récent={row['RecentU21Pathway']} ; "
            f"recul={row['AvailableFollowUpYears']} an(s) ; "
            f"Open année suivante={row['OpenNextYear'] if row['OpenNextYear'] != '' else 'censuré'} ; "
            f"Open sous trois ans={row['OpenWithin3Years'] if row['OpenWithin3Years'] != '' else 'censuré'}."
        )

    lines.append("")
    lines.append("4. PRÉCAUTIONS")
    lines.append("- La cohorte 2017 est exclue car tronquée à gauche.")
    lines.append(
        "- Une réapparition sous trois ans peut survenir après une ou plusieurs "
        "saisons d'absence."
    )
    lines.append(
        "- La continuité mesure une présence chaque année, sans interruption."
    )
    lines.append(
        "- 'Sans U21 récent' signifie seulement qu'aucun U21 n'est observé "
        "dans les trois années précédant la première apparition Open."
    )
    lines.append(
        "- Une absence au Championnat de France ne signifie pas une sortie "
        "de toute pratique compétitive."
    )
    lines.append("")
    lines.append("FIN DU DIAGNOSTIC")

    output = exports / "diagnostic_persistance_open_cohortes_2018_2025.txt"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")

    print("=" * 88)
    print("PERSISTANCE OPEN PAR COHORTES COMPARABLES TERMINEE")
    print("=" * 88)
    print(f"Entrants Open analysés : {len(detail_rows)}")
    print(f"Diagnostic : {output}")
    print("Aucun fichier existant n'a été modifié.")


if __name__ == "__main__":
    main()
