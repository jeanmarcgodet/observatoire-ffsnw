"""Analyse la fidélisation EMS par sexe et population d'âge (2023-2025)."""
from __future__ import annotations

import csv
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
YEARS = (2023, 2024, 2025)
SOURCES = {
    y: ROOT / "data" / "processed" / f"ems_participations_france_waterski_{y}.csv"
    for y in YEARS
}
PANEL = ROOT / "data" / "processed" / "ems_panel_competiteurs_francais_2023_2025.csv"
OUT_ATHLETE_YEAR = ROOT / "data" / "processed" / "ems_competiteurs_annee_sexe_age_2023_2025.csv"
OUT_TRANSITIONS = ROOT / "data" / "processed" / "ems_retention_sexe_age_2023_2025.csv"
OUT_COHORT = ROOT / "data" / "processed" / "ems_cohorte_2023_sexe_age.csv"
OUT_PROFILES = ROOT / "data" / "processed" / "ems_profils_fidelisation_sexe_age_2023_2025.csv"
OUT_QUALITY = ROOT / "data" / "processed" / "ems_qualite_sexe_age_2023_2025.csv"

AGE_ORDER = {"RELEVES": 1, "JUNIOR": 2, "U21": 3, "OPEN": 4, "SENIOR": 5, "UNKNOWN": 9}
PROFILE_ORDER = {
    "CORE_3_YEARS": 1,
    "TWO_YEARS_2023_2024": 2,
    "TWO_YEARS_2024_2025": 3,
    "RETURN_AFTER_GAP": 4,
    "ONE_SEASON_2023": 5,
    "ONE_SEASON_2024": 6,
    "ONE_SEASON_2025": 7,
    "OTHER": 9,
}
DIMENSIONS = ("ALL", "SEX", "AGE_BAND", "SEX_X_AGE_BAND")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        if not rows:
            return
        fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";")
        w.writeheader()
        w.writerows(rows)


def norm(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(c for c in text if not unicodedata.combining(c)).upper()
    return re.sub(r"\s+", " ", re.sub(r"[^A-Z0-9]+", " ", text)).strip()


def identity(row: dict[str, str]) -> tuple[str, str, str, str]:
    parts = str(row.get("AthleteKey", "")).split("|")
    key_country = parts[0].strip().upper() if len(parts) >= 1 else ""
    key_yob = parts[1].strip() if len(parts) >= 2 else ""
    key_name = "|".join(parts[2:]).strip() if len(parts) >= 3 else ""
    country = str(row.get("Country", "")).strip().upper() or key_country
    yob = str(row.get("YOB", "")).strip() or key_yob
    name = str(row.get("Name", "")).strip() or key_name
    return f"{country}|{yob}|{norm(name)}", country, yob, name


def extract_sex(category: Any) -> str:
    match = re.search(r"(?<![A-Z0-9])([FM])(?![A-Z0-9])", str(category or "").upper())
    return match.group(1) if match else "UNKNOWN"


def registered_population(category: Any) -> str:
    value = str(category or "").strip().upper()
    if re.match(r"^(?:-|U)?(?:8|10|12|14)\b", value):
        return "RELEVES"
    if re.match(r"^(?:-|U)?17\b", value):
        return "JUNIOR"
    if re.match(r"^(?:-|U)?21\b", value):
        return "U21"
    if re.match(r"^(?:OPEN|PRO)\b", value):
        return "OPEN"
    if re.match(r"^\d+\+", value):
        return "SENIOR"
    return "UNKNOWN"


def age_band(year: int, yob: str) -> tuple[int | None, str]:
    try:
        age = year - int(yob)
    except (TypeError, ValueError):
        return None, "UNKNOWN"
    if age <= 14:
        return age, "RELEVES"
    if age <= 17:
        return age, "JUNIOR"
    if age <= 21:
        return age, "U21"
    if age <= 34:
        return age, "OPEN"
    return age, "SENIOR"


def pct(n: int, d: int) -> float | str:
    return round(100 * n / d, 1) if d else ""


def dimension_value(row: dict[str, Any], dimension: str) -> str:
    if dimension == "ALL":
        return "ALL"
    if dimension == "SEX":
        return str(row["Sex"])
    if dimension == "AGE_BAND":
        return str(row["AgeBand"])
    return f"{row['Sex']}|{row['AgeBand']}"


def sort_group(dimension: str, group: str) -> tuple[Any, ...]:
    sex_order = {"F": 1, "M": 2, "UNKNOWN": 9, "MULTIPLE": 10}
    if dimension == "ALL":
        return (0,)
    if dimension == "SEX":
        return (sex_order.get(group, 9),)
    if dimension == "AGE_BAND":
        return (AGE_ORDER.get(group, 9),)
    sex, _, age = group.partition("|")
    return (sex_order.get(sex, 9), AGE_ORDER.get(age, 9))


def main() -> None:
    data: dict[tuple[int, str], dict[str, Any]] = {}

    for year, path in SOURCES.items():
        if not path.exists():
            raise FileNotFoundError(path)
        for row in read_csv(path):
            athlete_key, country, yob, name = identity(row)
            if country != "FRA":
                continue
            category = str(row.get("Category", "")).strip()
            code = str(row.get("CompetitionCode", "")).strip()
            key = (year, athlete_key)
            if key not in data:
                age, population = age_band(year, yob)
                data[key] = {
                    "Year": year, "AthleteKey": athlete_key, "Country": country,
                    "YOB": yob, "Age": age, "AgeBand": population,
                    "_names": set(), "_sexes": set(), "_categories": set(),
                    "_reg_pops": set(), "_competitions": set(),
                }
            item = data[key]
            item["_names"].add(name)
            item["_sexes"].add(extract_sex(category))
            item["_categories"].add(category)
            item["_reg_pops"].add(registered_population(category))
            if code:
                item["_competitions"].add(code)

    athlete_year_rows: list[dict[str, Any]] = []
    quality_rows: list[dict[str, Any]] = []

    for item in data.values():
        known_sexes = {x for x in item["_sexes"] if x != "UNKNOWN"}
        sex = next(iter(known_sexes)) if len(known_sexes) == 1 else ("MULTIPLE" if len(known_sexes) > 1 else "UNKNOWN")
        reg_pops = {x for x in item["_reg_pops"] if x != "UNKNOWN"}
        row = {
            "Year": item["Year"],
            "AthleteKey": item["AthleteKey"],
            "Name": sorted(item["_names"], key=lambda x: (-len(x), x))[0],
            "Country": item["Country"],
            "YOB": item["YOB"],
            "Age": item["Age"] if item["Age"] is not None else "",
            "Sex": sex,
            "AgeBand": item["AgeBand"],
            "RegisteredPopulations": " | ".join(sorted(reg_pops, key=lambda x: (AGE_ORDER.get(x, 9), x))),
            "Categories": " | ".join(sorted(x for x in item["_categories"] if x)),
            "Competitions": len(item["_competitions"]),
            "PopulationAgreement": int(item["AgeBand"] in reg_pops),
        }
        athlete_year_rows.append(row)

        issues = []
        if sex in {"UNKNOWN", "MULTIPLE"}:
            issues.append("SEX_UNRESOLVED")
        if item["AgeBand"] == "UNKNOWN":
            issues.append("AGE_UNRESOLVED")
        if reg_pops and item["AgeBand"] not in reg_pops:
            issues.append("AGE_CATEGORY_DIFFERENCE")
        if len(reg_pops) > 1:
            issues.append("MULTIPLE_REGISTERED_POPULATIONS")
        for issue in issues:
            quality_rows.append({
                "Year": item["Year"], "AthleteKey": item["AthleteKey"],
                "Name": row["Name"], "Sex": sex, "Age": row["Age"],
                "AgeBand": item["AgeBand"], "RegisteredPopulations": row["RegisteredPopulations"],
                "Categories": row["Categories"], "Issue": issue,
            })

    athlete_year_rows.sort(key=lambda r: (int(r["Year"]), str(r["Sex"]), AGE_ORDER.get(str(r["AgeBand"]), 9), str(r["Name"])))
    year_maps = {y: {} for y in YEARS}
    for row in athlete_year_rows:
        year_maps[int(row["Year"])][str(row["AthleteKey"])] = row

    transition_rows: list[dict[str, Any]] = []
    for y0, y1 in ((2023, 2024), (2024, 2025)):
        previous_map, current_map = year_maps[y0], year_maps[y1]
        previous_all, current_all = set(previous_map), set(current_map)
        for dimension in DIMENSIONS:
            previous_groups: dict[str, set[str]] = defaultdict(set)
            current_groups: dict[str, set[str]] = defaultdict(set)
            for key, row in previous_map.items():
                previous_groups[dimension_value(row, dimension)].add(key)
            for key, row in current_map.items():
                current_groups[dimension_value(row, dimension)].add(key)
            for group in sorted(set(previous_groups) | set(current_groups), key=lambda g: sort_group(dimension, g)):
                previous_group = previous_groups.get(group, set())
                current_group = current_groups.get(group, set())
                retained = previous_group & current_all
                exited = previous_group - current_all
                entrants = current_group - previous_all
                transition_rows.append({
                    "FromYear": y0, "ToYear": y1, "Dimension": dimension, "Group": group,
                    "PreviousAthletes": len(previous_group), "RetainedAthletes": len(retained),
                    "ExitedAthletes": len(exited), "RetentionRatePercent": pct(len(retained), len(previous_group)),
                    "CurrentAthletes": len(current_group), "EntrantAthletes": len(entrants),
                    "EntrantShareOfCurrentPercent": pct(len(entrants), len(current_group)),
                })

    cohort_rows: list[dict[str, Any]] = []
    cohort_map, present_2024, present_2025 = year_maps[2023], set(year_maps[2024]), set(year_maps[2025])
    for dimension in DIMENSIONS:
        groups: dict[str, set[str]] = defaultdict(set)
        for key, row in cohort_map.items():
            groups[dimension_value(row, dimension)].add(key)
        for group in sorted(groups, key=lambda g: sort_group(dimension, g)):
            cohort = groups[group]
            all_three = cohort & present_2024 & present_2025
            cohort_rows.append({
                "CohortYear": 2023, "Dimension": dimension, "Group": group,
                "InitialAthletes": len(cohort),
                "Present2024": len(cohort & present_2024),
                "Present2024Percent": pct(len(cohort & present_2024), len(cohort)),
                "Present2025": len(cohort & present_2025),
                "Present2025Percent": pct(len(cohort & present_2025), len(cohort)),
                "PresentAllThreeYears": len(all_three),
                "PresentAllThreeYearsPercent": pct(len(all_three), len(cohort)),
                "ReturnAfterGap": len((cohort - present_2024) & present_2025),
            })

    panel_rows = read_csv(PANEL)
    first_observation: dict[str, dict[str, Any]] = {}
    by_athlete: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in athlete_year_rows:
        by_athlete[str(row["AthleteKey"])].append(row)
    for key, rows in by_athlete.items():
        first_observation[key] = min(rows, key=lambda r: int(r["Year"]))

    profile_counts: Counter[tuple[str, str, str]] = Counter()
    group_totals: Counter[tuple[str, str]] = Counter()
    for panel_row in panel_rows:
        key = str(panel_row["AthleteKey"])
        entry = first_observation.get(key)
        if not entry:
            continue
        profile = str(panel_row["FidelityProfile"])
        for dimension in DIMENSIONS:
            group = dimension_value(entry, dimension)
            profile_counts[(dimension, group, profile)] += 1
            group_totals[(dimension, group)] += 1

    profile_rows: list[dict[str, Any]] = []
    for (dimension, group, profile), count in sorted(
        profile_counts.items(),
        key=lambda item: (DIMENSIONS.index(item[0][0]), sort_group(item[0][0], item[0][1]), PROFILE_ORDER.get(item[0][2], 9)),
    ):
        total = group_totals[(dimension, group)]
        profile_rows.append({
            "Dimension": dimension, "EntryGroup": group, "FidelityProfile": profile,
            "Athletes": count, "ShareWithinEntryGroupPercent": pct(count, total),
            "EntryGroupTotal": total,
        })

    write_csv(OUT_ATHLETE_YEAR, athlete_year_rows)
    write_csv(OUT_TRANSITIONS, transition_rows)
    write_csv(OUT_COHORT, cohort_rows)
    write_csv(OUT_PROFILES, profile_rows)
    write_csv(OUT_QUALITY, quality_rows, [
        "Year", "AthleteKey", "Name", "Sex", "Age", "AgeBand",
        "RegisteredPopulations", "Categories", "Issue",
    ])

    print("=" * 130)
    print("RÉTENTION ANNUELLE PAR SEXE")
    print("=" * 130)
    print(f"{'Transition':<14}{'Sexe':<8}{'Départ':>9}{'Fidèles':>10}{'Sortants':>10}{'Rétention':>12}{'Arrivée':>10}{'Entrants':>10}")
    print("-" * 85)
    for row in [r for r in transition_rows if r["Dimension"] == "SEX"]:
        print(f"{row['FromYear']}→{row['ToYear']:<8}{row['Group']:<8}{row['PreviousAthletes']:>9}{row['RetainedAthletes']:>10}{row['ExitedAthletes']:>10}{float(row['RetentionRatePercent']):>11.1f}%{row['CurrentAthletes']:>10}{row['EntrantAthletes']:>10}")

    print("\n" + "=" * 130)
    print("RÉTENTION ANNUELLE PAR POPULATION D'ÂGE")
    print("=" * 130)
    print(f"{'Transition':<14}{'Population':<12}{'Départ':>9}{'Fidèles':>10}{'Sortants':>10}{'Rétention':>12}{'Arrivée':>10}{'Entrants':>10}")
    print("-" * 90)
    for row in [r for r in transition_rows if r["Dimension"] == "AGE_BAND"]:
        print(f"{row['FromYear']}→{row['ToYear']:<8}{row['Group']:<12}{row['PreviousAthletes']:>9}{row['RetainedAthletes']:>10}{row['ExitedAthletes']:>10}{float(row['RetentionRatePercent']):>11.1f}%{row['CurrentAthletes']:>10}{row['EntrantAthletes']:>10}")

    print("\n" + "=" * 130)
    print("MAINTIEN DE LA COHORTE 2023 PAR POPULATION D'ÂGE INITIALE")
    print("=" * 130)
    print(f"{'Population':<12}{'Initial':>9}{'En 2024':>10}{'En 2025':>10}{'3 saisons':>12}{'Taux 3 ans':>12}{'Retours':>10}")
    print("-" * 78)
    for row in [r for r in cohort_rows if r["Dimension"] == "AGE_BAND"]:
        print(f"{row['Group']:<12}{row['InitialAthletes']:>9}{row['Present2024']:>10}{row['Present2025']:>10}{row['PresentAllThreeYears']:>12}{float(row['PresentAllThreeYearsPercent']):>11.1f}%{row['ReturnAfterGap']:>10}")

    print("\n" + "=" * 130)
    print("QUALITÉ DES VARIABLES")
    print("=" * 130)
    issues = Counter(row["Issue"] for row in quality_rows)
    if not issues:
        print("Aucune anomalie détectée.")
    else:
        for issue, count in sorted(issues.items()):
            print(f"{issue:<38}: {count}")

    print("\nSportifs-années :", OUT_ATHLETE_YEAR)
    print("Transitions     :", OUT_TRANSITIONS)
    print("Cohorte 2023    :", OUT_COHORT)
    print("Profils         :", OUT_PROFILES)
    print("Qualité         :", OUT_QUALITY)


if __name__ == "__main__":
    main()
