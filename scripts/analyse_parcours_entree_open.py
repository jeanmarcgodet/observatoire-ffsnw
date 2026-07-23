"""Analyse les voies d'entrée en Open et la pérennité des entrants.

Objectifs
---------
1. Classer les entrants Open 2024 et 2025 selon leur parcours observable :
   - retour en Open ;
   - U21 la même année ;
   - U21 l'année précédente ;
   - U21 plus ancien dans la fenêtre ;
   - U17 observable sans U21 ;
   - Senior observable sans U21 ;
   - entrée directe sans parcours préalable observable.
2. Mesurer la rétention en Open en 2025 des entrants Open 2024.
3. Identifier les compétitions 2024 fréquentées par les entrants Open et la
   proportion de ces entrants encore présents en Open en 2025.

Attention
---------
- "Entrant" signifie première apparition Open dans la fenêtre EMS 2023-2025,
  ou retour après interruption. Ce n'est pas nécessairement un débutant.
- Les données EMS représentent des inscriptions approuvées.
- Une même personne peut fréquenter plusieurs compétitions : la présence d'un
  entrant dans une compétition ne prouve pas que cette compétition a causé
  son entrée ou sa fidélisation.

Entrées
-------
data/processed/registre_filiere_open_ems_2023_2025.csv
data/processed/ems_participations_france_waterski_2024.csv

Sorties
-------
data/processed/open_entrees_parcours_2024_2025.csv
data/processed/open_entrants_2024_retention_2025.csv
data/processed/competitions_frequentees_entrants_open_2024.csv
data/exports/diagnostic_parcours_entree_open_2024_2025.txt
"""

from __future__ import annotations

import csv
import re
import statistics
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path


YEARS = (2023, 2024, 2025)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="", errors="replace") as handle:
        sample = handle.read(8192)
        handle.seek(0)
        try:
            delimiter = csv.Sniffer().sniff(sample, delimiters=";,\t").delimiter
        except csv.Error:
            delimiter = ";"
        return list(csv.DictReader(handle, delimiter=delimiter))


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


def normalize(value: str | None) -> str:
    text = unicodedata.normalize("NFKD", (value or "").strip())
    text = "".join(character for character in text if not unicodedata.combining(character))
    text = re.sub(r"\s+", " ", text.upper())
    return text.strip()


def truthy(value: str | None) -> bool:
    return normalize(value) in {"1", "TRUE", "YES", "Y", "OUI", "X"}


def is_open_category(category: str | None) -> bool:
    text = normalize(category)
    return "OPEN" in text or bool(re.search(r"(^| )PRO( |$)", text))


def percentage(numerator: int, denominator: int) -> float:
    return round(100 * numerator / denominator, 1) if denominator else 0.0


def mean(values: list[int]) -> float:
    return round(statistics.mean(values), 2) if values else 0.0


def median(values: list[int]) -> float:
    return float(statistics.median(values)) if values else 0.0


def pathway(
    athlete_key: str,
    year: int,
    lookup: dict[tuple[int, str], dict[str, str]],
) -> str:
    earlier_open_years = [
        previous_year
        for previous_year in YEARS
        if previous_year < year
        and integer(lookup.get((previous_year, athlete_key), {}).get("HasOpen")) == 1
    ]
    if earlier_open_years:
        return "RETOUR_OPEN"

    current = lookup.get((year, athlete_key), {})
    if integer(current.get("HasU21")) == 1:
        return "U21_MEME_ANNEE"

    previous = lookup.get((year - 1, athlete_key), {})
    if integer(previous.get("HasU21")) == 1:
        return "U21_ANNEE_PRECEDENTE"

    if any(
        integer(lookup.get((previous_year, athlete_key), {}).get("HasU21")) == 1
        for previous_year in YEARS
        if previous_year < year - 1
    ):
        return "U21_PLUS_ANCIEN_DANS_FENETRE"

    if integer(current.get("HasU17")) == 1 or any(
        integer(lookup.get((previous_year, athlete_key), {}).get("HasU17")) == 1
        for previous_year in YEARS
        if previous_year < year
    ):
        return "U17_SANS_U21_OBSERVE"

    if integer(current.get("HasSenior")) == 1 or any(
        integer(lookup.get((previous_year, athlete_key), {}).get("HasSenior")) == 1
        for previous_year in YEARS
        if previous_year < year
    ):
        return "SENIOR_SANS_U21_OBSERVE"

    return "ENTREE_DIRECTE_SANS_PARCOURS_OBSERVE"


def main() -> None:
    root = repo_root()
    register_path = root / "data/processed/registre_filiere_open_ems_2023_2025.csv"
    raw_2024_path = root / "data/processed/ems_participations_france_waterski_2024.csv"

    if not register_path.exists():
        raise FileNotFoundError(register_path)
    if not raw_2024_path.exists():
        raise FileNotFoundError(raw_2024_path)

    register = read_csv(register_path)
    raw_2024 = read_csv(raw_2024_path)

    lookup = {
        (integer(row["Year"]), row["AthleteKey"]): row
        for row in register
    }
    open_sets = {
        year: {
            row["AthleteKey"]
            for row in register
            if integer(row["Year"]) == year and integer(row["HasOpen"]) == 1
        }
        for year in YEARS
    }

    entry_rows: list[dict[str, object]] = []

    for year in (2024, 2025):
        entrants = sorted(open_sets[year] - open_sets[year - 1])

        for athlete_key in entrants:
            row = lookup[(year, athlete_key)]
            route = pathway(athlete_key, year, lookup)
            present_next = (
                int(athlete_key in open_sets.get(year + 1, set()))
                if year < 2025
                else ""
            )
            any_next = (
                int((year + 1, athlete_key) in lookup)
                if year < 2025
                else ""
            )

            entry_rows.append({
                "EntryYear": year,
                "AthleteKey": athlete_key,
                "Name": row["Name"],
                "Sex": row["Sex"],
                "YOB": row["YOB"],
                "Age": row["Age"],
                "EntryPathway": route,
                "OpenCompetitionsEntryYear": integer(row["CompetitionsOpen"]),
                "OpenChampionshipEntryYear": integer(row["OpenChampionshipParticipation"]),
                "OpenPhysicalDisciplineCount": integer(row["PhysicalDisciplineCountOpen"]),
                "PresentOpenNextYear": present_next,
                "PresentAnyFrenchEmsNextYear": any_next,
            })

    entrants_2024 = [row for row in entry_rows if row["EntryYear"] == 2024]

    retention_rows: list[dict[str, object]] = []
    grouping_dimensions = {
        "ALL": lambda row: "ALL",
        "PATHWAY": lambda row: str(row["EntryPathway"]),
        "INTENSITY": lambda row: (
            "1_COMPETITION"
            if int(row["OpenCompetitionsEntryYear"]) == 1
            else "2_COMPETITIONS"
            if int(row["OpenCompetitionsEntryYear"]) == 2
            else "3_PLUS_COMPETITIONS"
        ),
        "CHAMPIONNAT": lambda row: (
            "PRESENT_CHAMPIONNAT"
            if int(row["OpenChampionshipEntryYear"]) == 1
            else "ABSENT_CHAMPIONNAT"
        ),
    }

    for dimension, grouper in grouping_dimensions.items():
        grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
        for row in entrants_2024:
            grouped[grouper(row)].append(row)

        for group, rows in sorted(grouped.items()):
            retained = sum(int(row["PresentOpenNextYear"]) for row in rows)
            competition_counts = [
                int(row["OpenCompetitionsEntryYear"]) for row in rows
            ]
            retention_rows.append({
                "Dimension": dimension,
                "Group": group,
                "OpenEntrants2024": len(rows),
                "PresentOpen2025": retained,
                "AbsentOpen2025": len(rows) - retained,
                "OpenRetentionRatePercent": percentage(retained, len(rows)),
                "MeanOpenCompetitions2024": mean(competition_counts),
                "MedianOpenCompetitions2024": median(competition_counts),
            })

    entrant_2024_keys = {str(row["AthleteKey"]) for row in entrants_2024}
    retained_2025_keys = {
        str(row["AthleteKey"])
        for row in entrants_2024
        if int(row["PresentOpenNextYear"]) == 1
    }

    competition_athletes: dict[str, set[str]] = defaultdict(set)
    competition_metadata: dict[str, dict[str, str]] = {}

    for row in raw_2024:
        if not (
            truthy(row.get("IsFrench"))
            or normalize(row.get("Country")) == "FRA"
        ):
            continue
        if not is_open_category(row.get("Category")):
            continue

        code = row.get("CompetitionCode", "").strip()
        athlete_key = row.get("AthleteKey", "").strip()
        if not code or not athlete_key:
            continue

        competition_athletes[code].add(athlete_key)
        competition_metadata.setdefault(code, {
            "CompetitionName": row.get("CompetitionName", ""),
            "CompetitionDate": row.get("CompetitionDate", ""),
            "CompetitionType": row.get("CompetitionType", ""),
            "Homologation": row.get("Homologation", ""),
            "Site": row.get("Site", ""),
        })

    competition_rows: list[dict[str, object]] = []
    for code, athlete_keys in competition_athletes.items():
        entrants_here = athlete_keys & entrant_2024_keys
        if not entrants_here:
            continue

        retained_here = entrants_here & retained_2025_keys
        meta = competition_metadata[code]

        competition_rows.append({
            "CompetitionCode": code,
            "CompetitionDate": meta["CompetitionDate"],
            "CompetitionName": meta["CompetitionName"],
            "CompetitionType": meta["CompetitionType"],
            "Homologation": meta["Homologation"],
            "Site": meta["Site"],
            "FrenchOpenAthletes": len(athlete_keys),
            "OpenEntrants2024Present": len(entrants_here),
            "Entrants2024RetainedOpen2025": len(retained_here),
            "ObservedRetentionPercent": percentage(
                len(retained_here), len(entrants_here)
            ),
            "EntrantNames": " | ".join(
                sorted(
                    str(lookup[(2024, key)]["Name"])
                    for key in entrants_here
                )
            ),
        })

    competition_rows.sort(
        key=lambda row: (
            -int(row["OpenEntrants2024Present"]),
            -int(row["Entrants2024RetainedOpen2025"]),
            str(row["CompetitionCode"]),
        )
    )

    output_dir = root / "data/processed"
    export_dir = root / "data/exports"

    write_csv(
        output_dir / "open_entrees_parcours_2024_2025.csv",
        entry_rows,
        [
            "EntryYear",
            "AthleteKey",
            "Name",
            "Sex",
            "YOB",
            "Age",
            "EntryPathway",
            "OpenCompetitionsEntryYear",
            "OpenChampionshipEntryYear",
            "OpenPhysicalDisciplineCount",
            "PresentOpenNextYear",
            "PresentAnyFrenchEmsNextYear",
        ],
    )
    write_csv(
        output_dir / "open_entrants_2024_retention_2025.csv",
        retention_rows,
        [
            "Dimension",
            "Group",
            "OpenEntrants2024",
            "PresentOpen2025",
            "AbsentOpen2025",
            "OpenRetentionRatePercent",
            "MeanOpenCompetitions2024",
            "MedianOpenCompetitions2024",
        ],
    )
    write_csv(
        output_dir / "competitions_frequentees_entrants_open_2024.csv",
        competition_rows,
        [
            "CompetitionCode",
            "CompetitionDate",
            "CompetitionName",
            "CompetitionType",
            "Homologation",
            "Site",
            "FrenchOpenAthletes",
            "OpenEntrants2024Present",
            "Entrants2024RetainedOpen2025",
            "ObservedRetentionPercent",
            "EntrantNames",
        ],
    )

    lines: list[str] = []
    lines.append("PARCOURS D'ENTRÉE EN OPEN ET PÉRENNITÉ")
    lines.append("=" * 78)

    for year in (2024, 2025):
        rows = [row for row in entry_rows if row["EntryYear"] == year]
        counts = Counter(str(row["EntryPathway"]) for row in rows)
        lines.append("")
        lines.append(f"1. ENTRANTS OU RETOURS OPEN {year} : {len(rows)}")
        lines.append("-" * 78)
        for route, count in sorted(
            counts.items(),
            key=lambda item: (-item[1], item[0]),
        ):
            route_rows = [
                row for row in rows if row["EntryPathway"] == route
            ]
            one_comp = sum(
                int(row["OpenCompetitionsEntryYear"]) == 1
                for row in route_rows
            )
            championship = sum(
                int(row["OpenChampionshipEntryYear"]) == 1
                for row in route_rows
            )
            lines.append(
                f"{route} : {count} ; une seule compétition={one_comp} ; "
                f"Championnat de France={championship}."
            )

    lines.append("")
    lines.append("2. PÉRENNITÉ DES ENTRANTS OPEN 2024 EN 2025")
    lines.append("-" * 78)
    for row in retention_rows:
        if row["Dimension"] == "ALL":
            lines.append(
                f"Ensemble : {row['OpenEntrants2024']} entrants ; "
                f"{row['PresentOpen2025']} encore Open en 2025 "
                f"({str(row['OpenRetentionRatePercent']).replace('.', ',')} %)."
            )

    for dimension in ("PATHWAY", "INTENSITY", "CHAMPIONNAT"):
        lines.append("")
        lines.append(f"Par {dimension.lower()} :")
        for row in retention_rows:
            if row["Dimension"] != dimension:
                continue
            lines.append(
                f"- {row['Group']} : {row['OpenEntrants2024']} entrants ; "
                f"{row['PresentOpen2025']} maintenus ; "
                f"taux={str(row['OpenRetentionRatePercent']).replace('.', ',')} % ; "
                f"moyenne de compétitions 2024="
                f"{str(row['MeanOpenCompetitions2024']).replace('.', ',')}."
            )

    lines.append("")
    lines.append("3. COMPÉTITIONS 2024 FRÉQUENTÉES PAR LES ENTRANTS OPEN")
    lines.append("-" * 78)
    lines.append(
        "La rétention associée est descriptive : un entrant peut apparaître "
        "dans plusieurs compétitions et aucun effet causal n'est attribué."
    )
    for row in competition_rows[:15]:
        lines.append(
            f"- {row['CompetitionCode']} — {row['CompetitionName']} : "
            f"Open={row['FrenchOpenAthletes']} ; "
            f"entrants 2024={row['OpenEntrants2024Present']} ; "
            f"encore Open en 2025={row['Entrants2024RetainedOpen2025']}."
        )

    lines.append("")
    lines.append("PRÉCAUTIONS")
    lines.append("- La fenêtre 2023-2025 est trop courte pour reconstituer toute une carrière.")
    lines.append("- Une entrée directe peut masquer un parcours antérieur à 2023.")
    lines.append("- La pérennité 2025 des entrants 2025 n'est pas encore observable.")
    lines.append("- Les résultats décrivent le circuit français EMS, pas toutes les compétitions à l'étranger.")
    lines.append("")
    lines.append("FIN DU DIAGNOSTIC")

    diagnostic_path = export_dir / "diagnostic_parcours_entree_open_2024_2025.txt"
    diagnostic_path.parent.mkdir(parents=True, exist_ok=True)
    diagnostic_path.write_text("\n".join(lines), encoding="utf-8")

    print("=" * 88)
    print("PARCOURS D'ENTREE EN OPEN ANALYSES")
    print("=" * 88)
    print(f"Entrées 2024-2025 : {len(entry_rows)}")
    print(f"Compétitions 2024 avec entrants Open : {len(competition_rows)}")
    print(f"Diagnostic : {diagnostic_path}")
    print("Aucun fichier existant n'a été modifié.")


if __name__ == "__main__":
    main()
