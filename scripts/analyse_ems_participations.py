"""Analyse annuelle des participations approuvées dans EMS."""

from __future__ import annotations

import argparse
import csv
import statistics
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Fichier introuvable : {path}")

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        return list(csv.DictReader(file, delimiter=";"))


def write_csv(
    path: Path,
    rows: list[dict[str, object]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    if not rows:
        return

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


def is_selected(value: str) -> bool:
    value = (value or "").strip()

    return bool(value and value != "-")


def main(year: int) -> None:
    input_file = ROOT / (
        f"data/processed/"
        f"ems_participations_france_waterski_{year}.csv"
    )

    rows = read_csv(input_file)

    french_rows = [
        row
        for row in rows
        if row.get("IsFrench", "").strip() == "1"
    ]

    # ------------------------------------------------------------
    # Synthèse par compétition
    # ------------------------------------------------------------

    competitions: dict[str, list[dict[str, str]]] = defaultdict(list)

    for row in rows:
        competitions[row["CompetitionCode"]].append(row)

    competition_summary: list[dict[str, object]] = []

    for code, competition_rows in competitions.items():
        french_competition_rows = [
            row
            for row in competition_rows
            if row.get("IsFrench", "").strip() == "1"
        ]

        total = len(competition_rows)
        french = len(french_competition_rows)

        competition_summary.append(
            {
                "Year": year,
                "CompetitionCode": code,
                "CompetitionDate": competition_rows[0].get(
                    "CompetitionDate",
                    "",
                ),
                "CompetitionName": competition_rows[0].get(
                    "CompetitionName",
                    "",
                ),
                "CompetitionType": competition_rows[0].get(
                    "CompetitionType",
                    "",
                ),
                "TotalApproved": total,
                "FrenchApproved": french,
                "ForeignApproved": total - french,
                "FrenchSharePercent": round(
                    100 * french / total,
                    1,
                ) if total else 0,
                "UniqueAthletes": len(
                    {
                        row["AthleteKey"]
                        for row in competition_rows
                    }
                ),
                "UniqueFrench": len(
                    {
                        row["AthleteKey"]
                        for row in french_competition_rows
                    }
                ),
            }
        )

    competition_summary.sort(
        key=lambda row: (
            str(row["CompetitionDate"]),
            str(row["CompetitionCode"]),
        )
    )

    # ------------------------------------------------------------
    # Fréquence par sportif français
    # ------------------------------------------------------------

    athletes: dict[str, list[dict[str, str]]] = defaultdict(list)

    for row in french_rows:
        athletes[row["AthleteKey"]].append(row)

    athlete_frequency: list[dict[str, object]] = []

    for athlete_key, athlete_rows in athletes.items():
        competition_count = len(
            {
                row["CompetitionCode"]
                for row in athlete_rows
            }
        )

        athlete_frequency.append(
            {
                "Year": year,
                "AthleteKey": athlete_key,
                "Name": athlete_rows[0].get("Name", ""),
                "YOB": athlete_rows[0].get("YOB", ""),
                "Category": athlete_rows[0].get("Category", ""),
                "Competitions": competition_count,
                "SlalomEntries": sum(
                    is_selected(row.get("Slalom", ""))
                    for row in athlete_rows
                ),
                "TricksEntries": sum(
                    is_selected(row.get("Tricks", ""))
                    for row in athlete_rows
                ),
                "JumpEntries": sum(
                    is_selected(row.get("Jump", ""))
                    for row in athlete_rows
                ),
                "OverallEntries": sum(
                    is_selected(row.get("Overall", ""))
                    for row in athlete_rows
                ),
            }
        )

    athlete_frequency.sort(
        key=lambda row: (
            -int(row["Competitions"]),
            str(row["Name"]),
        )
    )

    counts = [
        int(row["Competitions"])
        for row in athlete_frequency
    ]

    distribution_counter = Counter(counts)

    distribution = [
        {
            "Year": year,
            "CompetitionsPerAthlete": competition_count,
            "Athletes": athlete_count,
            "SharePercent": round(
                100 * athlete_count / len(counts),
                1,
            ),
            "ApprovedEntries": (
                competition_count * athlete_count
            ),
        }
        for competition_count, athlete_count
        in sorted(distribution_counter.items())
    ]

    total_french_entries = len(french_rows)
    unique_french = len(athlete_frequency)

    top10_entries = sum(
        int(row["Competitions"])
        for row in athlete_frequency[:10]
    )

    top20_entries = sum(
        int(row["Competitions"])
        for row in athlete_frequency[:20]
    )

    one_competition = sum(
        count == 1
        for count in counts
    )

    two_competitions = sum(
        count == 2
        for count in counts
    )

    three_or_more = sum(
        count >= 3
        for count in counts
    )

    five_or_more = sum(
        count >= 5
        for count in counts
    )

    season_summary = [
        {
            "Year": year,
            "CompetitionsAnalysed": len(competitions),
            "ApprovedEntriesAllCountries": len(rows),
            "UniqueAthletesAllCountries": len(
                {
                    row["AthleteKey"]
                    for row in rows
                }
            ),
            "ApprovedFrenchEntries": total_french_entries,
            "UniqueFrenchAthletes": unique_french,
            "FrenchSharePercent": round(
                100 * total_french_entries / len(rows),
                1,
            ),
            "MeanCompetitionsPerFrenchAthlete": round(
                total_french_entries / unique_french,
                2,
            ),
            "MedianCompetitionsPerFrenchAthlete": statistics.median(
                counts
            ),
            "AthletesOneCompetition": one_competition,
            "ShareOneCompetitionPercent": round(
                100 * one_competition / unique_french,
                1,
            ),
            "AthletesTwoCompetitions": two_competitions,
            "AthletesThreeOrMore": three_or_more,
            "ShareThreeOrMorePercent": round(
                100 * three_or_more / unique_french,
                1,
            ),
            "AthletesFiveOrMore": five_or_more,
            "Top10Entries": top10_entries,
            "Top10SharePercent": round(
                100 * top10_entries / total_french_entries,
                1,
            ),
            "Top20Entries": top20_entries,
            "Top20SharePercent": round(
                100 * top20_entries / total_french_entries,
                1,
            ),
        }
    ]

    write_csv(
        ROOT / (
            f"data/processed/"
            f"ems_synthese_competitions_{year}.csv"
        ),
        competition_summary,
    )

    write_csv(
        ROOT / (
            f"data/processed/"
            f"ems_frequence_competiteurs_francais_{year}.csv"
        ),
        athlete_frequency,
    )

    write_csv(
        ROOT / (
            f"data/processed/"
            f"ems_distribution_frequence_francais_{year}.csv"
        ),
        distribution,
    )

    write_csv(
        ROOT / (
            f"data/processed/"
            f"ems_synthese_saison_{year}.csv"
        ),
        season_summary,
    )

    print("=" * 72)
    print(f"SYNTHÈSE EMS {year}")
    print("=" * 72)

    for key, value in season_summary[0].items():
        print(f"{key:38s}: {value}")

    print()
    print("Sportifs français les plus présents :")

    for row in athlete_frequency[:20]:
        print(
            f"{row['Name']:<28} "
            f"{row['Competitions']:>2} compétitions"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "year",
        type=int,
        help="Année à analyser",
    )

    arguments = parser.parse_args()

    main(arguments.year)