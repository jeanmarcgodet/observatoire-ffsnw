"""Décompose le rebond Open 2025 et identifie la fonction réelle des compétitions.

Entrées
-------
data/processed/registre_filiere_open_ems_2023_2025.csv
data/processed/synthese_competitions_filiere_open_2023_2025.csv

Sorties
-------
data/processed/open_2025_profils_entree_detail.csv
data/processed/open_2025_profils_entree_synthese.csv
data/processed/classement_competitions_open_2025.csv
data/exports/diagnostic_rebond_open_2025.txt
"""

from __future__ import annotations

import csv
import statistics
from collections import defaultdict
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle, delimiter=";"))


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter=";")
        writer.writeheader()
        writer.writerows(rows)


def as_int(value: str | None) -> int:
    try:
        return int(str(value or "0").strip())
    except ValueError:
        return 0


def pct(numerator: int, denominator: int) -> float:
    return round(100 * numerator / denominator, 1) if denominator else 0.0


def mean(values: list[int]) -> float:
    return round(statistics.mean(values), 2) if values else 0.0


def median(values: list[int]) -> float:
    return float(statistics.median(values)) if values else 0.0


def profile_status(
    athlete_key: str,
    open_2023: set[str],
    open_2024: set[str],
) -> str:
    if athlete_key in open_2024:
        return "MAINTENU_DEPUIS_2024"
    if athlete_key in open_2023:
        return "RETOUR_APRES_INTERRUPTION"
    return "NOUVEAU_DANS_FENETRE"


def intensity_band(competitions: int) -> str:
    if competitions == 1:
        return "1_COMPETITION"
    if competitions == 2:
        return "2_COMPETITIONS"
    if competitions <= 4:
        return "3_4_COMPETITIONS"
    return "5_PLUS"


def main() -> None:
    root = repo_root()
    register_path = root / "data/processed/registre_filiere_open_ems_2023_2025.csv"
    competitions_path = root / "data/processed/synthese_competitions_filiere_open_2023_2025.csv"

    register = read_csv(register_path)
    competitions = read_csv(competitions_path)

    open_rows_by_year: dict[int, list[dict[str, str]]] = defaultdict(list)
    for row in register:
        year = as_int(row["Year"])
        if as_int(row["HasOpen"]) == 1:
            open_rows_by_year[year].append(row)

    open_2023 = {row["AthleteKey"] for row in open_rows_by_year[2023]}
    open_2024 = {row["AthleteKey"] for row in open_rows_by_year[2024]}

    detail_rows: list[dict[str, object]] = []
    for row in sorted(
        open_rows_by_year[2025],
        key=lambda item: (-as_int(item["CompetitionsOpen"]), item["Name"]),
    ):
        competitions_open = as_int(row["CompetitionsOpen"])
        status = profile_status(row["AthleteKey"], open_2023, open_2024)
        age = as_int(row["Age"])

        detail_rows.append({
            "AthleteKey": row["AthleteKey"],
            "Name": row["Name"],
            "Sex": row["Sex"],
            "YOB": row["YOB"],
            "Age2025": age,
            "AgeProfile": (
                "21_OU_MOINS"
                if age <= 21
                else "22_34"
                if age <= 34
                else "35_PLUS"
            ),
            "OpenStatus2025": status,
            "OpenCompetitions2025": competitions_open,
            "IntensityBand2025": intensity_band(competitions_open),
            "OpenChampionship2025": as_int(row["OpenChampionshipParticipation"]),
            "PhysicalDisciplinesOpen": row["PhysicalDisciplinesOpen"],
            "PhysicalDisciplineCountOpen": as_int(row["PhysicalDisciplineCountOpen"]),
            "HasU212025": as_int(row["HasU21"]),
            "HasSenior2025": as_int(row["HasSenior"]),
        })

    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in detail_rows:
        grouped[str(row["OpenStatus2025"])].append(row)

    status_order = (
        "MAINTENU_DEPUIS_2024",
        "RETOUR_APRES_INTERRUPTION",
        "NOUVEAU_DANS_FENETRE",
    )
    summary_rows: list[dict[str, object]] = []

    for status in status_order:
        rows = grouped.get(status, [])
        competition_counts = [int(row["OpenCompetitions2025"]) for row in rows]
        championship_count = sum(int(row["OpenChampionship2025"]) for row in rows)

        summary_rows.append({
            "OpenStatus2025": status,
            "Athletes": len(rows),
            "ShareOfOpen2025Percent": pct(len(rows), len(detail_rows)),
            "Women": sum(row["Sex"] == "F" for row in rows),
            "Men": sum(row["Sex"] == "M" for row in rows),
            "Age21OrLess": sum(row["AgeProfile"] == "21_OU_MOINS" for row in rows),
            "Age22To34": sum(row["AgeProfile"] == "22_34" for row in rows),
            "Age35Plus": sum(row["AgeProfile"] == "35_PLUS" for row in rows),
            "CompetitionParticipations": sum(competition_counts),
            "MeanCompetitions": mean(competition_counts),
            "MedianCompetitions": median(competition_counts),
            "OneCompetition": sum(value == 1 for value in competition_counts),
            "ThreeOrMoreCompetitions": sum(value >= 3 for value in competition_counts),
            "FiveOrMoreCompetitions": sum(value >= 5 for value in competition_counts),
            "OpenChampionshipAthletes": championship_count,
            "OpenChampionshipCapturePercent": pct(championship_count, len(rows)),
            "AlsoU21": sum(int(row["HasU212025"]) for row in rows),
            "AlsoSenior": sum(int(row["HasSenior2025"]) for row in rows),
        })

    competition_rows: list[dict[str, object]] = []
    for row in competitions:
        if as_int(row["Year"]) != 2025:
            continue
        competition_rows.append({
            "CompetitionCode": row["CompetitionCode"],
            "CompetitionDate": row["CompetitionDate"],
            "CompetitionName": row["CompetitionName"],
            "CompetitionType": row["CompetitionType"],
            "Homologation": row["Homologation"],
            "Site": row["Site"],
            "FrenchAthletesAll": as_int(row["FrenchAthletesAll"]),
            "FrenchTargetAthletes": as_int(row["FrenchTargetAthletes"]),
            "FrenchU17": as_int(row["FrenchU17"]),
            "FrenchU21": as_int(row["FrenchU21"]),
            "FrenchOpen": as_int(row["FrenchOpen"]),
            "FrenchSenior": as_int(row["FrenchSenior"]),
            "OpenSharePercent": row["OpenSharePercent"],
            "SeniorSharePercent": row["SeniorSharePercent"],
            "AnalyticalProfile": row["AnalyticalProfile"],
        })

    competition_rows.sort(
        key=lambda row: (
            -int(row["FrenchOpen"]),
            -int(row["FrenchU21"]),
            str(row["CompetitionCode"]),
        )
    )

    output_dir = root / "data/processed"
    export_dir = root / "data/exports"

    write_csv(
        output_dir / "open_2025_profils_entree_detail.csv",
        detail_rows,
        list(detail_rows[0].keys()),
    )
    write_csv(
        output_dir / "open_2025_profils_entree_synthese.csv",
        summary_rows,
        list(summary_rows[0].keys()),
    )
    write_csv(
        output_dir / "classement_competitions_open_2025.csv",
        competition_rows,
        list(competition_rows[0].keys()),
    )

    lines: list[str] = []
    lines.append("DÉCOMPOSITION DU REBOND OPEN 2025")
    lines.append("=" * 78)
    lines.append("")
    lines.append("1. ORIGINE DES 49 OPEN")
    lines.append("-" * 78)

    for row in summary_rows:
        lines.append(
            f"{row['OpenStatus2025']} : {row['Athletes']} sportifs "
            f"({str(row['ShareOfOpen2025Percent']).replace('.', ',')} %) ; "
            f"{row['CompetitionParticipations']} participations-compétitions ; "
            f"médiane={row['MedianCompetitions']} ; "
            f"une seule compétition={row['OneCompetition']} ; "
            f"3+={row['ThreeOrMoreCompetitions']} ; "
            f"Championnat de France={row['OpenChampionshipAthletes']} "
            f"({str(row['OpenChampionshipCapturePercent']).replace('.', ',')} %)."
        )
        lines.append(
            f"    Âges : ≤21={row['Age21OrLess']} ; "
            f"22-34={row['Age22To34']} ; 35+={row['Age35Plus']} ; "
            f"également U21={row['AlsoU21']} ; également Senior={row['AlsoSenior']}."
        )

    lines.append("")
    lines.append("2. PROFONDEUR DES COMPÉTITIONS OPEN EN 2025")
    lines.append("-" * 78)

    with_open = [row for row in competition_rows if int(row["FrenchOpen"]) > 0]
    lines.append(
        f"Compétitions avec au moins un Open : {len(with_open)} sur "
        f"{len(competition_rows)}."
    )
    lines.append(
        f"Compétitions avec 1-4 Open : "
        f"{sum(1 <= int(row['FrenchOpen']) <= 4 for row in competition_rows)}."
    )
    lines.append(
        f"Compétitions avec 5-9 Open : "
        f"{sum(5 <= int(row['FrenchOpen']) <= 9 for row in competition_rows)}."
    )
    lines.append(
        f"Compétitions avec au moins 10 Open : "
        f"{sum(int(row['FrenchOpen']) >= 10 for row in competition_rows)}."
    )
    lines.append("")
    lines.append("Dix compétitions réunissant le plus d'Open :")

    for row in competition_rows[:10]:
        lines.append(
            f"- {row['CompetitionCode']} — {row['CompetitionName']} : "
            f"Open={row['FrenchOpen']} ; U21={row['FrenchU21']} ; "
            f"Seniors={row['FrenchSenior']} ; total français={row['FrenchAthletesAll']} ; "
            f"profil={row['AnalyticalProfile']}."
        )

    lines.append("")
    lines.append("3. INTERPRÉTATION À VALIDER")
    lines.append("-" * 78)
    lines.append(
        "- Le rebond du nombre d'Open doit être distingué d'un élargissement "
        "durable : une entrée limitée à une seule compétition reste périphérique."
    )
    lines.append(
        "- La captation par le Championnat de France est calculée à partir "
        "des inscriptions EMS ; elle n'est pas affectée par l'incomplétude "
        "des résultats U21/Open 2025."
    )
    lines.append(
        "- Les sportifs de 35 ans ou plus inscrits en Open restent comptés "
        "dans Open, conformément à la catégorie réellement disputée."
    )
    lines.append(
        "- Les nouveaux dans la fenêtre 2023-2025 ne sont pas nécessairement "
        "des débutants ou de nouveaux licenciés."
    )
    lines.append("")
    lines.append("FIN DU DIAGNOSTIC")

    diagnostic_path = export_dir / "diagnostic_rebond_open_2025.txt"
    diagnostic_path.parent.mkdir(parents=True, exist_ok=True)
    diagnostic_path.write_text("\n".join(lines), encoding="utf-8")

    print("=" * 88)
    print("DECOMPOSITION DU REBOND OPEN 2025 TERMINEE")
    print("=" * 88)
    print(f"Diagnostic : {diagnostic_path}")
    print("Aucun fichier existant n'a été modifié.")


if __name__ == "__main__":
    main()
