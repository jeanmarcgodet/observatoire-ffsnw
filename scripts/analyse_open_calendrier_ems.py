"""Analyse la catégorie Open et la fonction réelle du calendrier EMS 2023-2025.

Entrées :
- data/processed/registre_filiere_open_ems_2023_2025.csv
- data/processed/synthese_competitions_filiere_open_2023_2025.csv

Sorties :
- data/processed/synthese_open_annuelle_2023_2025.csv
- data/processed/renouvellement_open_2023_2025.csv
- data/processed/structure_calendrier_open_2023_2025.csv
- data/processed/transition_annuelle_u21_open_2023_2025.csv
- data/processed/continuite_open_senior_eligible_2023_2025.csv
- data/exports/diagnostic_open_calendrier_2023_2025.txt
"""

from __future__ import annotations

import csv
import statistics
from collections import Counter
from pathlib import Path


YEARS = (2023, 2024, 2025)


def root() -> Path:
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


def integer(value: str | None) -> int:
    try:
        return int(str(value or "0").strip())
    except ValueError:
        return 0


def percentage(numerator: int, denominator: int) -> float:
    return round(100 * numerator / denominator, 1) if denominator else 0.0


def gini(values: list[int]) -> float:
    clean = sorted(value for value in values if value >= 0)
    n = len(clean)
    total = sum(clean)
    if n == 0 or total == 0:
        return 0.0
    weighted = sum((index + 1) * value for index, value in enumerate(clean))
    return round((2 * weighted) / (n * total) - (n + 1) / n, 3)


def age_profile(age: int) -> str:
    if age <= 21:
        return "21_OU_MOINS"
    if age <= 34:
        return "22_34"
    return "35_ET_PLUS"


def open_depth_band(open_count: int) -> str:
    if open_count == 0:
        return "0_OPEN"
    if open_count <= 2:
        return "1_2_OPEN"
    if open_count <= 4:
        return "3_4_OPEN"
    if open_count <= 9:
        return "5_9_OPEN"
    return "10_OPEN_OU_PLUS"


def main() -> None:
    repo = root()
    register_path = repo / "data/processed/registre_filiere_open_ems_2023_2025.csv"
    competitions_path = repo / "data/processed/synthese_competitions_filiere_open_2023_2025.csv"

    if not register_path.exists():
        raise FileNotFoundError(register_path)
    if not competitions_path.exists():
        raise FileNotFoundError(competitions_path)

    register = read_csv(register_path)
    competitions = read_csv(competitions_path)

    by_year = {
        year: [row for row in register if integer(row["Year"]) == year]
        for year in YEARS
    }
    open_by_year = {
        year: [row for row in by_year[year] if integer(row["HasOpen"]) == 1]
        for year in YEARS
    }
    open_sets = {
        year: {row["AthleteKey"] for row in open_by_year[year]}
        for year in YEARS
    }
    row_lookup = {
        (integer(row["Year"]), row["AthleteKey"]): row
        for row in register
    }

    annual_rows: list[dict[str, object]] = []
    for year in YEARS:
        rows = open_by_year[year]
        competitions_open = [integer(row["CompetitionsOpen"]) for row in rows]
        total_activity = sum(competitions_open)
        sorted_activity = sorted(competitions_open, reverse=True)
        championship = sum(integer(row["OpenChampionshipParticipation"]) for row in rows)
        age_counts = Counter(
            age_profile(integer(row["Age"]))
            for row in rows
            if integer(row["Age"]) > 0
        )

        annual_rows.append({
            "Year": year,
            "OpenAthletes": len(rows),
            "Women": sum(row["Sex"] == "F" for row in rows),
            "Men": sum(row["Sex"] == "M" for row in rows),
            "Age21OrLess": age_counts["21_OU_MOINS"],
            "Age22To34": age_counts["22_34"],
            "Age35Plus": age_counts["35_ET_PLUS"],
            "OpenCompetitionParticipations": total_activity,
            "MeanOpenCompetitions": round(statistics.mean(competitions_open), 2) if rows else 0,
            "MedianOpenCompetitions": statistics.median(competitions_open) if rows else 0,
            "OneCompetition": sum(value == 1 for value in competitions_open),
            "TwoCompetitions": sum(value == 2 for value in competitions_open),
            "ThreeOrMore": sum(value >= 3 for value in competitions_open),
            "FiveOrMore": sum(value >= 5 for value in competitions_open),
            "Top5ActivitySharePercent": percentage(sum(sorted_activity[:5]), total_activity),
            "Top10ActivitySharePercent": percentage(sum(sorted_activity[:10]), total_activity),
            "GiniOpenActivity": gini(competitions_open),
            "OpenChampionshipAthletes": championship,
            "OpenChampionshipCapturePercent": percentage(championship, len(rows)),
        })

    renewal_rows: list[dict[str, object]] = []
    for year in (2024, 2025):
        previous = open_sets[year - 1]
        current = open_sets[year]
        retained = current & previous
        entrants = current - previous
        exited = previous - current
        earlier = open_sets[2023] if year == 2025 else set()
        returns_after_gap = entrants & earlier
        new_in_window = entrants - earlier

        renewal_rows.append({
            "Year": year,
            "PreviousOpen": len(previous),
            "CurrentOpen": len(current),
            "RetainedFromPreviousYear": len(retained),
            "RetentionRatePercent": percentage(len(retained), len(previous)),
            "ExitedFromPreviousYear": len(exited),
            "EntrantsOrReturns": len(entrants),
            "ReturnsAfterOneYearGap": len(returns_after_gap),
            "NewInObservedWindow": len(new_in_window),
            "EntrantShareOfCurrentPercent": percentage(len(entrants), len(current)),
        })

    calendar_rows: list[dict[str, object]] = []
    for year in YEARS:
        rows = [row for row in competitions if integer(row["Year"]) == year]
        bands = Counter(open_depth_band(integer(row["FrenchOpen"])) for row in rows)
        calendar_rows.append({
            "Year": year,
            "CompetitionsWithFrenchAthletes": len(rows),
            "NoOpen": bands["0_OPEN"],
            "OneOrTwoOpen": bands["1_2_OPEN"],
            "ThreeOrFourOpen": bands["3_4_OPEN"],
            "FiveToNineOpen": bands["5_9_OPEN"],
            "TenOpenOrMore": bands["10_OPEN_OU_PLUS"],
            "CompetitionsWithOpen": sum(integer(row["FrenchOpen"]) > 0 for row in rows),
            "CompetitionsWithFiveOpen": sum(integer(row["FrenchOpen"]) >= 5 for row in rows),
            "SeniorDominantOrNoTarget": sum(
                row["AnalyticalProfile"] in {
                    "DOMINANTE_SENIOR",
                    "SENIOR_SANS_FILIERE_CIBLE",
                }
                for row in rows
            ),
        })

    u21_transition_rows: list[dict[str, object]] = []
    for year in YEARS:
        u21_rows = [row for row in by_year[year] if integer(row["HasU21"]) == 1]
        u21_keys = {row["AthleteKey"] for row in u21_rows}
        same_year_open = {
            row["AthleteKey"] for row in u21_rows if integer(row["HasOpen"]) == 1
        }

        if year < 2025:
            next_year_open = u21_keys & open_sets[year + 1]
            same_or_next = same_year_open | next_year_open
            next_only = next_year_open - same_year_open
            censored = 0
        else:
            same_or_next = same_year_open
            next_only = set()
            censored = 1

        u21_transition_rows.append({
            "U21Year": year,
            "U21Athletes": len(u21_keys),
            "OpenSameYear": len(same_year_open),
            "OpenNextYearOnly": len(next_only),
            "OpenSameOrNextYear": len(same_or_next),
            "ConversionSameOrNextPercent": percentage(len(same_or_next), len(u21_keys)),
            "RightCensoredForNextYear": censored,
        })

    senior_continuity_rows: list[dict[str, object]] = []
    for from_year, to_year in ((2023, 2024), (2024, 2025)):
        eligible_keys: set[str] = set()
        for row in open_by_year[from_year]:
            yob = integer(row["YOB"])
            if yob and to_year - yob >= 35:
                eligible_keys.add(row["AthleteKey"])

        senior_next = {
            key for key in eligible_keys
            if (to_year, key) in row_lookup
            and integer(row_lookup[(to_year, key)]["HasSenior"]) == 1
        }
        open_next = {
            key for key in eligible_keys
            if key in open_sets[to_year]
        }
        absent_next = {
            key for key in eligible_keys
            if (to_year, key) not in row_lookup
        }

        senior_continuity_rows.append({
            "FromYear": from_year,
            "ToYear": to_year,
            "OpenAthletesSeniorEligibleToYear": len(eligible_keys),
            "ObservedInSeniorToYear": len(senior_next),
            "ObservedInSeniorPercent": percentage(len(senior_next), len(eligible_keys)),
            "StillOpenToYear": len(open_next),
            "AbsentFromFrenchEmsToYear": len(absent_next),
        })

    output_dir = repo / "data/processed"
    export_dir = repo / "data/exports"

    write_csv(
        output_dir / "synthese_open_annuelle_2023_2025.csv",
        annual_rows,
        list(annual_rows[0].keys()),
    )
    write_csv(
        output_dir / "renouvellement_open_2023_2025.csv",
        renewal_rows,
        list(renewal_rows[0].keys()),
    )
    write_csv(
        output_dir / "structure_calendrier_open_2023_2025.csv",
        calendar_rows,
        list(calendar_rows[0].keys()),
    )
    write_csv(
        output_dir / "transition_annuelle_u21_open_2023_2025.csv",
        u21_transition_rows,
        list(u21_transition_rows[0].keys()),
    )
    write_csv(
        output_dir / "continuite_open_senior_eligible_2023_2025.csv",
        senior_continuity_rows,
        list(senior_continuity_rows[0].keys()),
    )

    lines: list[str] = []
    lines.append("OPEN ET FONCTION DU CALENDRIER — EMS 2023-2025")
    lines.append("=" * 78)
    lines.append("")
    lines.append("1. CATÉGORIE OPEN")
    lines.append("-" * 78)
    for row in annual_rows:
        lines.append(
            f"{row['Year']} : {row['OpenAthletes']} Open ; "
            f"âges ≤21={row['Age21OrLess']}, 22-34={row['Age22To34']}, "
            f"35+={row['Age35Plus']} ; "
            f"{row['OpenCompetitionParticipations']} participations-compétitions ; "
            f"médiane={row['MedianOpenCompetitions']} ; "
            f"championnat={row['OpenChampionshipAthletes']} "
            f"({str(row['OpenChampionshipCapturePercent']).replace('.', ',')} % du vivier Open)."
        )
        lines.append(
            f"       Une seule compétition={row['OneCompetition']} ; "
            f"3+={row['ThreeOrMore']} ; 5+={row['FiveOrMore']} ; "
            f"Top 10={str(row['Top10ActivitySharePercent']).replace('.', ',')} % "
            f"de l'activité Open ; Gini={row['GiniOpenActivity']}."
        )

    lines.append("")
    lines.append("2. RENOUVELLEMENT ET PÉRENNITÉ")
    lines.append("-" * 78)
    for row in renewal_rows:
        lines.append(
            f"{row['Year']} : {row['CurrentOpen']} Open ; "
            f"{row['RetainedFromPreviousYear']} maintenus "
            f"({str(row['RetentionRatePercent']).replace('.', ',')} %) ; "
            f"{row['EntrantsOrReturns']} entrants ou retours "
            f"({str(row['EntrantShareOfCurrentPercent']).replace('.', ',')} % du vivier annuel) ; "
            f"nouveaux dans la fenêtre={row['NewInObservedWindow']} ; "
            f"retours après interruption={row['ReturnsAfterOneYearGap']}."
        )

    lines.append("")
    lines.append("3. PROFONDEUR OPEN DES COMPÉTITIONS")
    lines.append("-" * 78)
    for row in calendar_rows:
        lines.append(
            f"{row['Year']} : {row['CompetitionsWithFrenchAthletes']} compétitions ; "
            f"sans Open={row['NoOpen']} ; 1-2 Open={row['OneOrTwoOpen']} ; "
            f"3-4 Open={row['ThreeOrFourOpen']} ; 5-9 Open={row['FiveToNineOpen']} ; "
            f"10+ Open={row['TenOpenOrMore']} ; "
            f"dominante Senior/sans cible={row['SeniorDominantOrNoTarget']}."
        )

    lines.append("")
    lines.append("4. TRANSITION ANNUELLE U21 → OPEN")
    lines.append("-" * 78)
    for row in u21_transition_rows:
        if row["RightCensoredForNextYear"]:
            lines.append(
                f"{row['U21Year']} : {row['U21Athletes']} U21 ; "
                f"{row['OpenSameYear']} également Open la même année ; "
                "passage l'année suivante non observable."
            )
        else:
            lines.append(
                f"{row['U21Year']} : {row['U21Athletes']} U21 ; "
                f"Open même année={row['OpenSameYear']} ; "
                f"Open année suivante seulement={row['OpenNextYearOnly']} ; "
                f"conversion même année ou suivante="
                f"{str(row['ConversionSameOrNextPercent']).replace('.', ',')} %."
            )

    lines.append("")
    lines.append("5. OPEN → SENIOR, UNIQUEMENT POUR LES SPORTIFS ÉLIGIBLES")
    lines.append("-" * 78)
    for row in senior_continuity_rows:
        lines.append(
            f"{row['FromYear']}→{row['ToYear']} : "
            f"{row['OpenAthletesSeniorEligibleToYear']} Open deviennent ou sont éligibles 35+ ; "
            f"{row['ObservedInSeniorToYear']} observés en Senior "
            f"({str(row['ObservedInSeniorPercent']).replace('.', ',')} %) ; "
            f"{row['StillOpenToYear']} restent également ou uniquement Open ; "
            f"{row['AbsentFromFrenchEmsToYear']} absents du circuit français EMS."
        )

    lines.append("")
    lines.append("PRÉCAUTIONS")
    lines.append("-" * 78)
    lines.append("- La saison 2025 ne permet pas d'observer le passage U21→Open en 2026.")
    lines.append("- Une entrée Open peut être une première apparition, un retour ou une entrée tardive.")
    lines.append("- Le classement 35+ repose sur l'âge, mais le statut Open repose sur la catégorie EMS réelle.")
    lines.append("- Le nombre de compétitions ne renseigne pas seul sur leur fonction dans la filière.")
    lines.append("- Les données EMS sont des inscriptions approuvées.")
    lines.append("")
    lines.append("FIN DU DIAGNOSTIC")

    diagnostic_path = export_dir / "diagnostic_open_calendrier_2023_2025.txt"
    diagnostic_path.parent.mkdir(parents=True, exist_ok=True)
    diagnostic_path.write_text("\n".join(lines), encoding="utf-8")

    print("=" * 88)
    print("ANALYSE OPEN ET CALENDRIER TERMINEE")
    print("=" * 88)
    print(f"Diagnostic : {diagnostic_path}")
    print("Aucun fichier existant n'a été modifié.")


if __name__ == "__main__":
    main()
