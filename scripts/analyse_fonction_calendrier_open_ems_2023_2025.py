"""Analyse la fonction effective du calendrier Open EMS 2023-2025.

Questions traitées
------------------
1. Le calendrier rassemble-t-il des champs Open suffisamment profonds ?
2. Les entrants/retours apparaissent-ils surtout dans des compétitions peu fournies ?
3. La répétition des compétitions et la présence au Championnat de France sont-elles
   associées à une présence Open l'année suivante ?
4. Les compétitions forment-elles un circuit commun ou des sous-ensembles fragmentés ?

Entrées
-------
data/processed/registre_filiere_open_ems_2023_2025.csv
data/processed/ems_participations_france_waterski_2023.csv
data/processed/ems_participations_france_waterski_2024.csv
data/processed/ems_participations_france_waterski_2025.csv

Sorties
-------
data/processed/fonction_competitions_open_ems_2023_2025.csv
data/processed/retention_open_selon_intensite_ems_2023_2024.csv
data/processed/fragmentation_calendrier_open_ems_2023_2025.csv
data/processed/paires_competitions_open_ems_2023_2025.csv
data/exports/diagnostic_fonction_calendrier_open_ems_2023_2025.txt

Précautions
-----------
- Les données EMS sont des inscriptions approuvées.
- Une association entre fréquence et rétention ne démontre pas un effet causal.
- La saison 2025 ne permet pas d'observer la rétention en 2026.
- Les entrants 2023 ne sont pas identifiables sans données EMS 2022 comparables.
"""

from __future__ import annotations

import csv
import re
import statistics
import unicodedata
from collections import defaultdict, deque
from pathlib import Path
from typing import Callable


YEARS = (2023, 2024, 2025)
CHAMPIONSHIP_CODES = {
    2023: "23FRA018",
    2024: "24FRA027",
    2025: "25FRA206",
}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def normalize(value: str | None) -> str:
    text = unicodedata.normalize("NFKD", (value or "").strip())
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = re.sub(r"\s+", " ", text.upper())
    return text.strip()


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


def truthy(value: str | None) -> bool:
    return normalize(value) in {"1", "TRUE", "YES", "Y", "OUI", "X"}


def percentage(numerator: int, denominator: int) -> float:
    return round(100 * numerator / denominator, 1) if denominator else 0.0


def median(values: list[float | int]) -> float:
    return round(float(statistics.median(values)), 3) if values else 0.0


def mean(values: list[float | int]) -> float:
    return round(float(statistics.mean(values)), 3) if values else 0.0


def is_open_category(value: str | None) -> bool:
    category = normalize(value)
    return (
        "OPEN" in category
        or bool(re.search(r"(^|[^A-Z])PRO([^A-Z]|$)", category))
    )


def first_existing(row: dict[str, str], *names: str) -> str:
    for name in names:
        if name in row and row[name] is not None:
            return str(row[name])
    return ""


def is_french(row: dict[str, str]) -> bool:
    french_flag = first_existing(row, "IsFrench", "is_french", "French")
    country = first_existing(row, "Country", "country", "Nation")
    return truthy(french_flag) or normalize(country) == "FRA"


def depth_band(open_count: int) -> str:
    if open_count <= 0:
        return "0"
    if open_count <= 2:
        return "1_2"
    if open_count <= 4:
        return "3_4"
    if open_count <= 9:
        return "5_9"
    return "10_PLUS"


def intensity_band(competitions: int) -> str:
    if competitions <= 1:
        return "1_COMPETITION"
    if competitions == 2:
        return "2_COMPETITIONS"
    if competitions <= 4:
        return "3_4_COMPETITIONS"
    return "5_PLUS"


def connected_components(
    nodes: set[str],
    adjacency: dict[str, set[str]],
) -> list[set[str]]:
    remaining = set(nodes)
    components: list[set[str]] = []

    while remaining:
        start = next(iter(remaining))
        component: set[str] = set()
        queue: deque[str] = deque([start])
        remaining.remove(start)

        while queue:
            node = queue.popleft()
            component.add(node)

            for neighbour in adjacency.get(node, set()):
                if neighbour in remaining:
                    remaining.remove(neighbour)
                    queue.append(neighbour)

        components.append(component)

    return sorted(components, key=lambda item: (-len(item), sorted(item)))


def main() -> None:
    root = repo_root()
    register_path = (
        root / "data/processed/registre_filiere_open_ems_2023_2025.csv"
    )

    if not register_path.exists():
        raise FileNotFoundError(register_path)

    register = read_csv(register_path)

    register_lookup: dict[tuple[int, str], dict[str, str]] = {}
    open_sets: dict[int, set[str]] = defaultdict(set)
    u21_sets: dict[int, set[str]] = defaultdict(set)

    for row in register:
        year = integer(first_existing(row, "Year", "year"))
        athlete_key = first_existing(row, "AthleteKey", "athlete_key").strip()
        if not year or not athlete_key:
            continue

        register_lookup[(year, athlete_key)] = row

        if integer(first_existing(row, "HasOpen", "has_open")) == 1:
            open_sets[year].add(athlete_key)

        if integer(first_existing(row, "HasU21", "has_u21")) == 1:
            u21_sets[year].add(athlete_key)

    competition_athletes: dict[tuple[int, str], set[str]] = defaultdict(set)
    athlete_competitions: dict[tuple[int, str], set[str]] = defaultdict(set)
    competition_meta: dict[tuple[int, str], dict[str, str]] = {}

    for year in YEARS:
        path = (
            root
            / f"data/processed/ems_participations_france_waterski_{year}.csv"
        )
        if not path.exists():
            raise FileNotFoundError(path)

        for row in read_csv(path):
            if not is_french(row):
                continue

            category = first_existing(row, "Category", "category", "Categorie")
            if not is_open_category(category):
                continue

            athlete_key = first_existing(
                row, "AthleteKey", "athlete_key", "RiderKey"
            ).strip()
            code = first_existing(
                row, "CompetitionCode", "competition_code", "Code"
            ).strip()

            if not athlete_key or not code:
                continue

            competition_athletes[(year, code)].add(athlete_key)
            athlete_competitions[(year, athlete_key)].add(code)

            competition_meta.setdefault(
                (year, code),
                {
                    "CompetitionName": first_existing(
                        row, "CompetitionName", "competition_name", "Name"
                    ),
                    "CompetitionDate": first_existing(
                        row, "CompetitionDate", "competition_date", "Date"
                    ),
                    "CompetitionType": first_existing(
                        row, "CompetitionType", "competition_type", "Type"
                    ),
                    "Homologation": first_existing(
                        row, "Homologation", "homologation"
                    ),
                    "Site": first_existing(row, "Site", "site", "Location"),
                },
            )

    competition_rows: list[dict[str, object]] = []

    for (year, code), athletes in sorted(competition_athletes.items()):
        previous_open = open_sets.get(year - 1, set())
        earlier_open = set().union(
            *(open_sets[past] for past in YEARS if past < year - 1)
        )

        maintained = athletes & previous_open
        entrants_or_returns = athletes - previous_open
        returns = entrants_or_returns & earlier_open
        new_in_window = entrants_or_returns - earlier_open

        recent_u21 = {
            athlete
            for athlete in athletes
            if athlete in u21_sets.get(year, set())
            or athlete in u21_sets.get(year - 1, set())
        }
        one_comp = {
            athlete
            for athlete in athletes
            if len(athlete_competitions[(year, athlete)]) == 1
        }

        next_open = open_sets.get(year + 1, set())
        retained_next = athletes & next_open if year < 2025 else set()
        entrant_retained_next = (
            entrants_or_returns & next_open if year < 2025 else set()
        )

        meta = competition_meta.get((year, code), {})
        is_championship = int(code == CHAMPIONSHIP_CODES.get(year))
        open_count = len(athletes)

        competition_rows.append(
            {
                "Year": year,
                "CompetitionCode": code,
                "CompetitionDate": meta.get("CompetitionDate", ""),
                "CompetitionName": meta.get("CompetitionName", ""),
                "CompetitionType": meta.get("CompetitionType", ""),
                "Homologation": meta.get("Homologation", ""),
                "Site": meta.get("Site", ""),
                "IsOpenFrenchChampionship": is_championship,
                "OpenAthletes": open_count,
                "DepthBand": depth_band(open_count),
                "MaintainedFromPreviousYear": (
                    len(maintained) if year > 2023 else ""
                ),
                "EntrantsOrReturns": (
                    len(entrants_or_returns) if year > 2023 else ""
                ),
                "ReturnsAfterGap": len(returns) if year > 2023 else "",
                "NewInObservedWindow": len(new_in_window) if year > 2023 else "",
                "RecentU21Athletes": len(recent_u21),
                "OneCompetitionAthletes": len(one_comp),
                "OpenNextYear": len(retained_next) if year < 2025 else "",
                "OpenNextYearRatePercent": (
                    percentage(len(retained_next), len(athletes))
                    if year < 2025 else ""
                ),
                "EntrantsOpenNextYear": (
                    len(entrant_retained_next)
                    if year > 2023 and year < 2025
                    else ""
                ),
                "EntrantNextYearRatePercent": (
                    percentage(
                        len(entrant_retained_next),
                        len(entrants_or_returns),
                    )
                    if year > 2023 and year < 2025
                    else ""
                ),
                "AthleteKeys": " | ".join(sorted(athletes)),
            }
        )

    # Rétention individuelle selon l'intensité et le Championnat.
    retention_rows: list[dict[str, object]] = []

    for year in (2023, 2024):
        current = open_sets[year]
        next_year = open_sets[year + 1]

        athlete_rows: list[dict[str, object]] = []
        for athlete in current:
            count = len(athlete_competitions[(year, athlete)])
            championship = int(
                CHAMPIONSHIP_CODES[year]
                in athlete_competitions[(year, athlete)]
            )
            athlete_rows.append(
                {
                    "AthleteKey": athlete,
                    "Competitions": count,
                    "IntensityBand": intensity_band(count),
                    "Championship": championship,
                    "OpenNextYear": int(athlete in next_year),
                }
            )

        dimensions: tuple[
            tuple[str, Callable[[dict[str, object]], str]], ...
        ] = (
            ("ALL", lambda row: "ALL"),
            ("INTENSITY", lambda row: str(row["IntensityBand"])),
            (
                "CHAMPIONSHIP",
                lambda row: (
                    "PRESENT_CHAMPIONNAT"
                    if int(row["Championship"]) == 1
                    else "ABSENT_CHAMPIONNAT"
                ),
            ),
        )

        for dimension, grouper in dimensions:
            groups: dict[str, list[dict[str, object]]] = defaultdict(list)
            for row in athlete_rows:
                groups[grouper(row)].append(row)

            for group_name, group in sorted(groups.items()):
                retained = sum(int(row["OpenNextYear"]) for row in group)
                counts = [int(row["Competitions"]) for row in group]
                retention_rows.append(
                    {
                        "Year": year,
                        "Dimension": dimension,
                        "Group": group_name,
                        "OpenAthletes": len(group),
                        "OpenNextYear": retained,
                        "RetentionRatePercent": percentage(
                            retained, len(group)
                        ),
                        "MeanCompetitions": mean(counts),
                        "MedianCompetitions": median(counts),
                    }
                )

    # Fragmentation et paires de compétitions.
    pair_rows: list[dict[str, object]] = []
    fragmentation_rows: list[dict[str, object]] = []

    for year in YEARS:
        codes = sorted(
            code
            for (row_year, code) in competition_athletes
            if row_year == year
        )
        adjacency: dict[str, set[str]] = defaultdict(set)
        jaccards: list[float] = []
        positive_jaccards: list[float] = []
        zero_overlap = 0

        for index, code_a in enumerate(codes):
            athletes_a = competition_athletes[(year, code_a)]

            for code_b in codes[index + 1:]:
                athletes_b = competition_athletes[(year, code_b)]
                shared = athletes_a & athletes_b
                union = athletes_a | athletes_b
                jaccard = len(shared) / len(union) if union else 0.0

                jaccards.append(jaccard)
                if shared:
                    positive_jaccards.append(jaccard)
                    adjacency[code_a].add(code_b)
                    adjacency[code_b].add(code_a)
                else:
                    zero_overlap += 1

                pair_rows.append(
                    {
                        "Year": year,
                        "CompetitionCodeA": code_a,
                        "CompetitionNameA": competition_meta.get(
                            (year, code_a), {}
                        ).get("CompetitionName", ""),
                        "CompetitionCodeB": code_b,
                        "CompetitionNameB": competition_meta.get(
                            (year, code_b), {}
                        ).get("CompetitionName", ""),
                        "OpenAthletesA": len(athletes_a),
                        "OpenAthletesB": len(athletes_b),
                        "SharedOpenAthletes": len(shared),
                        "UnionOpenAthletes": len(union),
                        "Jaccard": round(jaccard, 4),
                    }
                )

        components = connected_components(set(codes), adjacency)
        pair_count = len(jaccards)

        fragmentation_rows.append(
            {
                "Year": year,
                "CompetitionsWithOpen": len(codes),
                "CompetitionPairs": pair_count,
                "PairsWithZeroOverlap": zero_overlap,
                "ZeroOverlapSharePercent": percentage(
                    zero_overlap, pair_count
                ),
                "MeanJaccardAllPairs": mean(jaccards),
                "MedianJaccardAllPairs": median(jaccards),
                "MeanJaccardPositivePairs": mean(positive_jaccards),
                "MedianJaccardPositivePairs": median(positive_jaccards),
                "ConnectedComponents": len(components),
                "LargestComponentCompetitions": (
                    len(components[0]) if components else 0
                ),
                "IsolatedCompetitions": sum(
                    len(component) == 1 for component in components
                ),
            }
        )

    processed = root / "data/processed"
    exports = root / "data/exports"

    competition_fields = [
        "Year",
        "CompetitionCode",
        "CompetitionDate",
        "CompetitionName",
        "CompetitionType",
        "Homologation",
        "Site",
        "IsOpenFrenchChampionship",
        "OpenAthletes",
        "DepthBand",
        "MaintainedFromPreviousYear",
        "EntrantsOrReturns",
        "ReturnsAfterGap",
        "NewInObservedWindow",
        "RecentU21Athletes",
        "OneCompetitionAthletes",
        "OpenNextYear",
        "OpenNextYearRatePercent",
        "EntrantsOpenNextYear",
        "EntrantNextYearRatePercent",
        "AthleteKeys",
    ]
    retention_fields = [
        "Year",
        "Dimension",
        "Group",
        "OpenAthletes",
        "OpenNextYear",
        "RetentionRatePercent",
        "MeanCompetitions",
        "MedianCompetitions",
    ]
    fragmentation_fields = [
        "Year",
        "CompetitionsWithOpen",
        "CompetitionPairs",
        "PairsWithZeroOverlap",
        "ZeroOverlapSharePercent",
        "MeanJaccardAllPairs",
        "MedianJaccardAllPairs",
        "MeanJaccardPositivePairs",
        "MedianJaccardPositivePairs",
        "ConnectedComponents",
        "LargestComponentCompetitions",
        "IsolatedCompetitions",
    ]
    pair_fields = [
        "Year",
        "CompetitionCodeA",
        "CompetitionNameA",
        "CompetitionCodeB",
        "CompetitionNameB",
        "OpenAthletesA",
        "OpenAthletesB",
        "SharedOpenAthletes",
        "UnionOpenAthletes",
        "Jaccard",
    ]

    write_csv(
        processed / "fonction_competitions_open_ems_2023_2025.csv",
        competition_rows,
        competition_fields,
    )
    write_csv(
        processed / "retention_open_selon_intensite_ems_2023_2024.csv",
        retention_rows,
        retention_fields,
    )
    write_csv(
        processed / "fragmentation_calendrier_open_ems_2023_2025.csv",
        fragmentation_rows,
        fragmentation_fields,
    )
    write_csv(
        processed / "paires_competitions_open_ems_2023_2025.csv",
        pair_rows,
        pair_fields,
    )

    lines: list[str] = []
    lines.append("FONCTION EFFECTIVE DU CALENDRIER OPEN — EMS 2023-2025")
    lines.append("=" * 86)

    lines.append("")
    lines.append("1. PROFONDEUR, ENTRÉES ET CHAMPIONNAT")
    lines.append("-" * 86)

    for year in YEARS:
        rows = [row for row in competition_rows if int(row["Year"]) == year]
        open_total = len(open_sets[year])
        championship = next(
            (
                row for row in rows
                if int(row["IsOpenFrenchChampionship"]) == 1
            ),
            None,
        )

        lines.append(
            f"{year} : {len(rows)} compétitions avec Open ; "
            f"{open_total} Open distincts ; "
            f"1-4 Open={sum(int(row['OpenAthletes']) <= 4 for row in rows)} ; "
            f"5-9 Open={sum(5 <= int(row['OpenAthletes']) <= 9 for row in rows)} ; "
            f"10+ Open={sum(int(row['OpenAthletes']) >= 10 for row in rows)}."
        )

        if year > 2023:
            comps_with_entries = sum(
                int(row["EntrantsOrReturns"]) > 0 for row in rows
            )
            entrant_participations = sum(
                int(row["EntrantsOrReturns"]) for row in rows
            )
            shallow_entrant_participations = sum(
                int(row["EntrantsOrReturns"])
                for row in rows
                if int(row["OpenAthletes"]) <= 4
            )
            lines.append(
                f"       Compétitions accueillant au moins un entrant/retour : "
                f"{comps_with_entries}/{len(rows)} ; "
                f"participations-compétitions d'entrants/retours={entrant_participations} ; "
                f"dans des champs de 1-4 Open={shallow_entrant_participations} "
                f"({str(percentage(shallow_entrant_participations, entrant_participations)).replace('.', ',')} %)."
            )

        if championship:
            lines.append(
                f"       Championnat de France : "
                f"{championship['OpenAthletes']} Open ; "
                f"U21 récents={championship['RecentU21Athletes']} ; "
                f"une seule compétition annuelle={championship['OneCompetitionAthletes']} ; "
                f"entrants/retours={championship['EntrantsOrReturns'] if year > 2023 else 'n.d.'}."
            )

    lines.append("")
    lines.append("2. PRÉSENCE OPEN L'ANNÉE SUIVANTE")
    lines.append("-" * 86)

    for year in (2023, 2024):
        lines.append(f"{year} → {year + 1} :")
        for dimension in ("ALL", "INTENSITY", "CHAMPIONSHIP"):
            relevant = [
                row for row in retention_rows
                if int(row["Year"]) == year
                and row["Dimension"] == dimension
            ]
            for row in relevant:
                lines.append(
                    f"- {dimension}/{row['Group']} : "
                    f"{row['OpenNextYear']}/{row['OpenAthletes']} "
                    f"({str(row['RetentionRatePercent']).replace('.', ',')} %) ; "
                    f"moyenne compétitions={str(row['MeanCompetitions']).replace('.', ',')}."
                )

    lines.append("")
    lines.append("3. FRAGMENTATION ENTRE COMPÉTITIONS")
    lines.append("-" * 86)

    for row in fragmentation_rows:
        lines.append(
            f"{row['Year']} : {row['CompetitionsWithOpen']} compétitions ; "
            f"paires sans aucun Open commun={row['PairsWithZeroOverlap']}/"
            f"{row['CompetitionPairs']} "
            f"({str(row['ZeroOverlapSharePercent']).replace('.', ',')} %) ; "
            f"Jaccard médian toutes paires={row['MedianJaccardAllPairs']} ; "
            f"composantes={row['ConnectedComponents']} ; "
            f"plus grande composante={row['LargestComponentCompetitions']} ; "
            f"isolées={row['IsolatedCompetitions']}."
        )

    lines.append("")
    lines.append("4. PRÉCAUTIONS")
    lines.append("- Les données sont des inscriptions approuvées, pas nécessairement des départs.")
    lines.append(
        "- Les taux associés à une compétition sont descriptifs : un sportif "
        "peut participer à plusieurs événements."
    )
    lines.append(
        "- La fréquence de compétition peut être la conséquence, et non la cause, "
        "d'une meilleure intégration sportive."
    )
    lines.append(
        "- Les entrants 2023 ne peuvent pas être distingués des Open déjà actifs avant la fenêtre."
    )
    lines.append("")
    lines.append("FIN DU DIAGNOSTIC")

    output = exports / "diagnostic_fonction_calendrier_open_ems_2023_2025.txt"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")

    print("=" * 88)
    print("FONCTION DU CALENDRIER OPEN ANALYSEE")
    print("=" * 88)
    print(f"Compétitions-années : {len(competition_rows)}")
    print(f"Paires de compétitions : {len(pair_rows)}")
    print(f"Diagnostic : {output}")
    print("Aucun fichier existant n'a été modifié.")


if __name__ == "__main__":
    main()
