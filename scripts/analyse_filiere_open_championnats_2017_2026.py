"""Reconstruit la filière U21 -> Open aux Championnats de France 2017-2026.

Objectif
--------
Allonger l'observation au-delà de la fenêtre EMS 2023-2025 afin d'étudier :
- l'alimentation d'Open par U21 ;
- la pérennité dans la catégorie Open ;
- le renouvellement annuel d'Open ;
- la continuité éventuelle vers les catégories Seniors.

Les Seniors sont isolés comme population d'aval et ne participent pas aux
indicateurs centraux de santé de la filière.

Sources
-------
- data/observatoire.db
- data/reference/rider_identity_map.csv

Sorties
-------
- data/processed/registre_championnats_filiere_open_2017_2026.csv
- data/processed/cohortes_sortie_u21_vers_open_2017_2026.csv
- data/processed/cohortes_entree_open_persistance_2017_2026.csv
- data/processed/renouvellement_open_championnats_2017_2026.csv
- data/processed/continuite_open_senior_championnats_2017_2026.csv
- data/exports/diagnostic_filiere_open_championnats_2017_2026.txt

Précautions
-----------
- Le registre porte sur les Championnats de France présents dans la base.
- Une absence au Championnat ne signifie pas une absence de toute compétition.
- Les premières apparitions de 2017 peuvent être des parcours déjà anciens.
- Les cohortes récentes sont censurées à droite.
"""

from __future__ import annotations

import csv
import re
import sqlite3
import statistics
import unicodedata
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


START_YEAR = 2017
END_YEAR = 2026
YEARS = tuple(range(START_YEAR, END_YEAR + 1))

CHAMPIONSHIP_CODES = (
    "17FRA002", "17FRA005",
    "18FRA001", "18FRA010", "18FRA030",
    "19FRA001", "19FRA002", "19FRA03",
    "20FRA029", "20FRA030", "20FRA031",
    "21FRA044", "21FRA045", "21FRA046",
    "22FRA029", "22FRA030", "22FRA031",
    "23FRA017", "23FRA018", "23FRA023",
    "24FRA026", "24FRA027", "24FRA034",
    "25FRA016", "25FRA018", "25FRA206",
    "26FRA020", "26FRA021", "26FRA041",
)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def normalize(value: str | None) -> str:
    text = unicodedata.normalize("NFKD", (value or "").strip())
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = re.sub(r"\s+", " ", text.upper())
    return text.strip()


def classify_category(category_raw: str | None) -> str:
    category = normalize(category_raw)

    if not category:
        return "OTHER"

    if "OPEN" in category or re.search(r"(^| )PRO( |$)", category):
        return "OPEN"

    if re.search(r"(^|[^0-9])(?:35|45|55|65|70|75|80|85)\+([^0-9]|$)", category):
        return "SENIOR"

    if (
        re.search(r"(^|[^0-9])U?21([^0-9]|$)", category)
        or re.match(r"^-21(?:\s|$)", category)
        or "UNDER 21" in category
    ):
        return "U21"

    if (
        re.search(r"(^|[^0-9])U?17([^0-9]|$)", category)
        or re.match(r"^-17(?:\s|$)", category)
        or "JUNIOR" in category
    ):
        return "U17"

    if (
        re.search(r"(^|[^0-9])U?(?:8|10|12|14)([^0-9]|$)", category)
        or re.match(r"^-(?:8|10|12|14)(?:\s|$)", category)
    ):
        return "RELEVES"

    return "OTHER"


def read_alias_map(path: Path) -> dict[int, int]:
    aliases: dict[int, int] = {}
    if not path.exists():
        return aliases

    with path.open("r", encoding="utf-8-sig", newline="", errors="replace") as handle:
        reader = csv.DictReader(handle, delimiter=";")
        for row in reader:
            try:
                alias_id = int((row.get("alias_rider_id") or "").strip())
                canonical_id = int((row.get("canonical_rider_id") or "").strip())
            except ValueError:
                continue
            aliases[alias_id] = canonical_id

    return aliases


def write_csv(path: Path, rows: Iterable[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter=";")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def pct(numerator: int, denominator: int) -> float:
    return round(100 * numerator / denominator, 1) if denominator else 0.0


def longest_consecutive(years: Iterable[int]) -> int:
    ordered = sorted(set(years))
    if not ordered:
        return 0

    best = 1
    current = 1
    for previous, following in zip(ordered, ordered[1:]):
        if following == previous + 1:
            current += 1
            best = max(best, current)
        else:
            current = 1
    return best


def joined(values: Iterable[object]) -> str:
    return " | ".join(str(value) for value in sorted(set(values)))


@dataclass
class AthleteYear:
    year: int
    canonical_rider_id: int
    name: str
    sex: str
    yob: int | None
    categories: set[str] = field(default_factory=set)
    populations: set[str] = field(default_factory=set)
    competition_codes: set[str] = field(default_factory=set)

    def add(self, category: str, competition_code: str) -> None:
        self.categories.add(category)
        self.populations.add(classify_category(category))
        self.competition_codes.add(competition_code)

    def has(self, population: str) -> int:
        return int(population in self.populations)


def load_records(root: Path) -> dict[tuple[int, int], AthleteYear]:
    db_path = root / "data/observatoire.db"
    alias_path = root / "data/reference/rider_identity_map.csv"

    if not db_path.exists():
        raise FileNotFoundError(db_path)

    alias_map = read_alias_map(alias_path)
    placeholders = ",".join("?" for _ in CHAMPIONSHIP_CODES)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    query = f"""
        SELECT
            c.annee AS year,
            c.iwwf_id AS competition_code,
            c.nom AS competition_name,
            c.niveau AS competition_level,
            e.rider_id AS rider_id,
            e.categorie AS category,
            r.nom AS surname,
            r.prenom AS firstname,
            r.sexe AS sex,
            r.annee_naissance AS yob
        FROM entries e
        JOIN competitions c ON c.id = e.competition_id
        JOIN riders r ON r.id = e.rider_id
        WHERE c.iwwf_id IN ({placeholders})
        ORDER BY c.annee, c.iwwf_id, e.rider_id
    """

    rows = conn.execute(query, CHAMPIONSHIP_CODES).fetchall()
    conn.close()

    records: dict[tuple[int, int], AthleteYear] = {}

    for row in rows:
        competition_code = str(
            row["competition_code"] or ""
        ).strip()

        year = (
            int(row["year"])
            if row["year"] is not None
            else 2000 + int(competition_code[:2])
        )
        rider_id = int(row["rider_id"])
        canonical_id = alias_map.get(rider_id, rider_id)
        key = (year, canonical_id)

        name = " ".join(
            part for part in (row["firstname"], row["surname"]) if part
        ).strip()
        sex = (row["sex"] or "").strip()
        yob = int(row["yob"]) if row["yob"] is not None else None

        if key not in records:
            records[key] = AthleteYear(
                year=year,
                canonical_rider_id=canonical_id,
                name=name,
                sex=sex,
                yob=yob,
            )

        records[key].add(
            category=(row["category"] or "").strip(),
            competition_code=competition_code,
        )

    return records


def build_register(records: dict[tuple[int, int], AthleteYear]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []

    for (_, _), record in sorted(records.items()):
        rows.append({
            "Year": record.year,
            "CanonicalRiderId": record.canonical_rider_id,
            "Name": record.name,
            "Sex": record.sex,
            "YOB": record.yob if record.yob is not None else "",
            "Age": record.year - record.yob if record.yob is not None else "",
            "Categories": joined(record.categories),
            "Populations": joined(record.populations),
            "HasReleves": record.has("RELEVES"),
            "HasU17": record.has("U17"),
            "HasU21": record.has("U21"),
            "HasOpen": record.has("OPEN"),
            "HasSenior": record.has("SENIOR"),
            "HasOther": record.has("OTHER"),
            "ChampionshipCompetitions": len(record.competition_codes),
            "CompetitionCodes": joined(record.competition_codes),
        })

    return rows


def athlete_histories(
    records: dict[tuple[int, int], AthleteYear],
) -> dict[int, dict[int, AthleteYear]]:
    histories: dict[int, dict[int, AthleteYear]] = defaultdict(dict)
    for (year, rider_id), record in records.items():
        histories[rider_id][year] = record
    return histories


def build_u21_exit_cohorts(
    histories: dict[int, dict[int, AthleteYear]],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []

    for rider_id, years in sorted(histories.items()):
        u21_years = sorted(
            year for year, record in years.items() if record.has("U21")
        )
        if not u21_years:
            continue

        last_u21 = max(u21_years)
        open_years = sorted(
            year
            for year, record in years.items()
            if record.has("OPEN") and year >= last_u21
        )
        first_open = min(open_years) if open_years else None
        delay = first_open - last_u21 if first_open is not None else None
        followup_years = END_YEAR - last_u21

        if first_open is not None and delay == 0:
            outcome = "OPEN_MEME_ANNEE"
        elif first_open is not None and delay == 1:
            outcome = "OPEN_SOUS_1_AN"
        elif first_open is not None and delay == 2:
            outcome = "OPEN_SOUS_2_ANS"
        elif first_open is not None and delay == 3:
            outcome = "OPEN_SOUS_3_ANS"
        elif first_open is not None:
            outcome = "OPEN_APRES_3_ANS"
        elif followup_years >= 3:
            outcome = "SANS_OPEN_OBSERVE_3_ANS"
        else:
            outcome = "CENSURE_DROITE"

        reference = years[last_u21]
        rows.append({
            "CanonicalRiderId": rider_id,
            "Name": reference.name,
            "Sex": reference.sex,
            "YOB": reference.yob if reference.yob is not None else "",
            "U21Years": joined(u21_years),
            "LastU21Year": last_u21,
            "FirstOpenYearOnOrAfterLastU21": first_open or "",
            "DelayU21ToOpenYears": delay if delay is not None else "",
            "AvailableFollowUpYears": followup_years,
            "ConvertedWithin1Year": int(delay is not None and delay <= 1),
            "ConvertedWithin2Years": int(delay is not None and delay <= 2),
            "ConvertedWithin3Years": int(delay is not None and delay <= 3),
            "Outcome": outcome,
        })

    return rows


def build_open_entry_cohorts(
    histories: dict[int, dict[int, AthleteYear]],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []

    for rider_id, years in sorted(histories.items()):
        open_years = sorted(
            year for year, record in years.items() if record.has("OPEN")
        )
        if not open_years:
            continue

        first_open = min(open_years)
        last_open = max(open_years)
        first_record = years[first_open]

        senior_years_after = sorted(
            year
            for year, record in years.items()
            if year >= first_open and record.has("SENIOR")
        )
        first_senior_after = min(senior_years_after) if senior_years_after else None

        rows.append({
            "CanonicalRiderId": rider_id,
            "Name": first_record.name,
            "Sex": first_record.sex,
            "YOB": first_record.yob if first_record.yob is not None else "",
            "FirstOpenYear": first_open,
            "LastOpenYear": last_open,
            "OpenYears": joined(open_years),
            "OpenSeasons": len(open_years),
            "LongestConsecutiveOpenSequence": longest_consecutive(open_years),
            "PresentOpenNextYear": (
                int(first_open + 1 in open_years)
                if first_open < END_YEAR
                else ""
            ),
            "PresentOpenWithin2Years": (
                int(any(year in open_years for year in (first_open + 1, first_open + 2)))
                if first_open <= END_YEAR - 2
                else ""
            ),
            "PresentOpenWithin3Years": (
                int(any(
                    year in open_years
                    for year in (first_open + 1, first_open + 2, first_open + 3)
                ))
                if first_open <= END_YEAR - 3
                else ""
            ),
            "FirstSeniorYearAfterOpen": first_senior_after or "",
            "ObservedSeniorAfterOpen": int(first_senior_after is not None),
            "RightCensoredNextYear": int(first_open == END_YEAR),
            "RightCensoredThreeYears": int(first_open > END_YEAR - 3),
        })

    return rows


def build_open_annual(
    records: dict[tuple[int, int], AthleteYear],
) -> list[dict[str, object]]:
    open_sets = {
        year: {
            rider_id
            for (record_year, rider_id), record in records.items()
            if record_year == year and record.has("OPEN")
        }
        for year in YEARS
    }

    rows: list[dict[str, object]] = []

    for year in YEARS:
        current = open_sets[year]
        previous = open_sets.get(year - 1, set())
        earlier = set().union(*(open_sets[past] for past in YEARS if past < year - 1))

        retained = current & previous
        entrants_or_returns = current - previous
        returns = entrants_or_returns & earlier
        new_in_window = entrants_or_returns - earlier

        women = sum(
            records[(year, rider_id)].sex == "F"
            for rider_id in current
        )
        men = sum(
            records[(year, rider_id)].sex == "M"
            for rider_id in current
        )
        simultaneous_u21 = sum(
            records[(year, rider_id)].has("U21")
            for rider_id in current
        )

        rows.append({
            "Year": year,
            "OpenAthletes": len(current),
            "Women": women,
            "Men": men,
            "SimultaneousU21": simultaneous_u21,
            "RetainedFromPreviousYear": len(retained) if year > START_YEAR else "",
            "RetentionRatePercent": (
                pct(len(retained), len(previous))
                if year > START_YEAR
                else ""
            ),
            "EntrantsOrReturns": len(entrants_or_returns) if year > START_YEAR else "",
            "ReturnsAfterGap": len(returns) if year > START_YEAR else "",
            "NewInObservedWindow": len(new_in_window) if year > START_YEAR else "",
            "EntrantOrReturnSharePercent": (
                pct(len(entrants_or_returns), len(current))
                if year > START_YEAR
                else ""
            ),
        })

    return rows


def build_open_senior_continuity(
    histories: dict[int, dict[int, AthleteYear]],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []

    for rider_id, years in sorted(histories.items()):
        open_years = sorted(
            year for year, record in years.items() if record.has("OPEN")
        )
        if not open_years:
            continue

        last_open = max(open_years)
        reference = years[last_open]
        yob = reference.yob

        senior_years = sorted(
            year
            for year, record in years.items()
            if year > last_open and record.has("SENIOR")
        )
        first_senior = min(senior_years) if senior_years else None

        if yob is None:
            eligibility_year = None
        else:
            eligibility_year = yob + 35

        observable_eligibility = (
            eligibility_year is not None and eligibility_year <= END_YEAR
        )

        rows.append({
            "CanonicalRiderId": rider_id,
            "Name": reference.name,
            "Sex": reference.sex,
            "YOB": yob if yob is not None else "",
            "LastOpenYear": last_open,
            "SeniorEligibilityYear35Plus": eligibility_year or "",
            "EligibleWithinWindow": int(observable_eligibility),
            "FirstSeniorYearAfterLastOpen": first_senior or "",
            "ObservedSeniorAfterLastOpen": int(first_senior is not None),
            "DelayOpenToSeniorYears": (
                first_senior - last_open if first_senior is not None else ""
            ),
            "RightCensored": int(
                not observable_eligibility or last_open == END_YEAR
            ),
        })

    return rows


def median(values: list[int]) -> float:
    return float(statistics.median(values)) if values else 0.0


def build_diagnostic(
    register_rows: list[dict[str, object]],
    u21_rows: list[dict[str, object]],
    open_cohorts: list[dict[str, object]],
    open_annual: list[dict[str, object]],
    continuity_rows: list[dict[str, object]],
) -> str:
    lines: list[str] = []
    lines.append("FILIÈRE U21 → OPEN AUX CHAMPIONNATS DE FRANCE 2017-2026")
    lines.append("=" * 82)
    lines.append("")
    lines.append("PÉRIMÈTRE")
    lines.append(
        "Participation aux codes nationaux explicitement validés pour 2017-2026 ; le champ competitions.niveau n'est pas utilisé car il est incomplet. "
        "Open constitue la catégorie centrale ; les Seniors sont analysés en aval."
    )

    lines.append("")
    lines.append("1. EFFECTIFS ET RENOUVELLEMENT OPEN")
    lines.append("-" * 82)
    for row in open_annual:
        if row["Year"] == START_YEAR:
            lines.append(
                f"{row['Year']} : Open={row['OpenAthletes']} ; "
                f"femmes={row['Women']} ; hommes={row['Men']} ; "
                f"également U21={row['SimultaneousU21']}."
            )
        else:
            lines.append(
                f"{row['Year']} : Open={row['OpenAthletes']} ; "
                f"maintenus={row['RetainedFromPreviousYear']} "
                f"({str(row['RetentionRatePercent']).replace('.', ',')} %) ; "
                f"entrants/retours={row['EntrantsOrReturns']} "
                f"({str(row['EntrantOrReturnSharePercent']).replace('.', ',')} %) ; "
                f"retours={row['ReturnsAfterGap']} ; "
                f"nouveaux dans la fenêtre={row['NewInObservedWindow']}."
            )

    lines.append("")
    lines.append("2. SORTIE U21 → OPEN")
    lines.append("-" * 82)
    analyzable_1 = [row for row in u21_rows if int(row["AvailableFollowUpYears"]) >= 1]
    analyzable_2 = [row for row in u21_rows if int(row["AvailableFollowUpYears"]) >= 2]
    analyzable_3 = [row for row in u21_rows if int(row["AvailableFollowUpYears"]) >= 3]

    for horizon, rows, field in (
        (1, analyzable_1, "ConvertedWithin1Year"),
        (2, analyzable_2, "ConvertedWithin2Years"),
        (3, analyzable_3, "ConvertedWithin3Years"),
    ):
        converted = sum(int(row[field]) for row in rows)
        lines.append(
            f"Horizon {horizon} an(s) : {converted}/{len(rows)} sorties U21 "
            f"observées en Open ({str(pct(converted, len(rows))).replace('.', ',')} %)."
        )

    cohort_groups: dict[int, list[dict[str, object]]] = defaultdict(list)
    for row in u21_rows:
        cohort_groups[int(row["LastU21Year"])].append(row)

    lines.append("")
    lines.append("Par dernière année U21 :")
    for year in sorted(cohort_groups):
        rows = cohort_groups[year]
        followup = END_YEAR - year
        converted = sum(
            int(row["ConvertedWithin3Years"])
            for row in rows
            if int(row["AvailableFollowUpYears"]) >= 3
        )
        analyzable = sum(
            int(row["AvailableFollowUpYears"]) >= 3 for row in rows
        )
        if analyzable:
            lines.append(
                f"- {year} : {len(rows)} sorties U21 ; "
                f"{converted}/{analyzable} vers Open sous trois ans."
            )
        else:
            lines.append(
                f"- {year} : {len(rows)} sorties U21 ; "
                f"suivi disponible={followup} an(s), cohorte censurée."
            )

    lines.append("")
    lines.append("3. PÉRENNITÉ APRÈS LA PREMIÈRE APPARITION OPEN")
    lines.append("-" * 82)
    next_year_rows = [
        row for row in open_cohorts if row["PresentOpenNextYear"] != ""
    ]
    retained_next = sum(int(row["PresentOpenNextYear"]) for row in next_year_rows)
    lines.append(
        f"Encore Open l'année suivante : {retained_next}/{len(next_year_rows)} "
        f"({str(pct(retained_next, len(next_year_rows))).replace('.', ',')} %)."
    )

    three_year_rows = [
        row for row in open_cohorts if row["PresentOpenWithin3Years"] != ""
    ]
    retained_three = sum(int(row["PresentOpenWithin3Years"]) for row in three_year_rows)
    lines.append(
        f"Réapparition Open dans les trois années suivantes : "
        f"{retained_three}/{len(three_year_rows)} "
        f"({str(pct(retained_three, len(three_year_rows))).replace('.', ',')} %)."
    )

    open_seasons = [int(row["OpenSeasons"]) for row in open_cohorts]
    lines.append(
        f"Nombre médian de saisons Open observées : {median(open_seasons):.1f}."
    )
    lines.append(
        f"Une seule saison Open : "
        f"{sum(value == 1 for value in open_seasons)}/{len(open_seasons)} "
        f"({str(pct(sum(value == 1 for value in open_seasons), len(open_seasons))).replace('.', ',')} %)."
    )

    lines.append("")
    lines.append("4. OPEN → SENIOR")
    lines.append("-" * 82)
    eligible = [
        row for row in continuity_rows
        if int(row["EligibleWithinWindow"]) == 1
    ]
    observed = sum(int(row["ObservedSeniorAfterLastOpen"]) for row in eligible)
    lines.append(
        f"Anciens Open devenus éligibles 35+ dans la fenêtre : {len(eligible)} ; "
        f"observés ensuite en Senior : {observed} "
        f"({str(pct(observed, len(eligible))).replace('.', ',')} %)."
    )
    lines.append(
        "Cet indicateur décrit uniquement la continuité observable aux "
        "Championnats de France ; il ne mesure ni le revenu ni la pratique hors championnat."
    )

    lines.append("")
    lines.append("5. PRÉCAUTIONS")
    lines.append("- Les premières apparitions de 2017 sont tronquées à gauche.")
    lines.append("- Les cohortes 2024-2026 disposent d'un suivi incomplet.")
    lines.append("- Une absence au Championnat de France n'est pas un abandon sportif.")
    lines.append("- Les Seniors ne sont pas inclus dans les indicateurs centraux de renouvellement.")
    lines.append("")
    lines.append("FIN DU DIAGNOSTIC")

    return "\n".join(lines)


def main() -> None:
    root = repo_root()
    records = load_records(root)
    histories = athlete_histories(records)

    register_rows = build_register(records)
    u21_rows = build_u21_exit_cohorts(histories)
    open_cohort_rows = build_open_entry_cohorts(histories)
    open_annual_rows = build_open_annual(records)
    continuity_rows = build_open_senior_continuity(histories)

    processed = root / "data/processed"
    exports = root / "data/exports"

    write_csv(
        processed / "registre_championnats_filiere_open_2017_2026.csv",
        register_rows,
        [
            "Year",
            "CanonicalRiderId",
            "Name",
            "Sex",
            "YOB",
            "Age",
            "Categories",
            "Populations",
            "HasReleves",
            "HasU17",
            "HasU21",
            "HasOpen",
            "HasSenior",
            "HasOther",
            "ChampionshipCompetitions",
            "CompetitionCodes",
        ],
    )

    write_csv(
        processed / "cohortes_sortie_u21_vers_open_2017_2026.csv",
        u21_rows,
        [
            "CanonicalRiderId",
            "Name",
            "Sex",
            "YOB",
            "U21Years",
            "LastU21Year",
            "FirstOpenYearOnOrAfterLastU21",
            "DelayU21ToOpenYears",
            "AvailableFollowUpYears",
            "ConvertedWithin1Year",
            "ConvertedWithin2Years",
            "ConvertedWithin3Years",
            "Outcome",
        ],
    )

    write_csv(
        processed / "cohortes_entree_open_persistance_2017_2026.csv",
        open_cohort_rows,
        [
            "CanonicalRiderId",
            "Name",
            "Sex",
            "YOB",
            "FirstOpenYear",
            "LastOpenYear",
            "OpenYears",
            "OpenSeasons",
            "LongestConsecutiveOpenSequence",
            "PresentOpenNextYear",
            "PresentOpenWithin2Years",
            "PresentOpenWithin3Years",
            "FirstSeniorYearAfterOpen",
            "ObservedSeniorAfterOpen",
            "RightCensoredNextYear",
            "RightCensoredThreeYears",
        ],
    )

    write_csv(
        processed / "renouvellement_open_championnats_2017_2026.csv",
        open_annual_rows,
        [
            "Year",
            "OpenAthletes",
            "Women",
            "Men",
            "SimultaneousU21",
            "RetainedFromPreviousYear",
            "RetentionRatePercent",
            "EntrantsOrReturns",
            "ReturnsAfterGap",
            "NewInObservedWindow",
            "EntrantOrReturnSharePercent",
        ],
    )

    write_csv(
        processed / "continuite_open_senior_championnats_2017_2026.csv",
        continuity_rows,
        [
            "CanonicalRiderId",
            "Name",
            "Sex",
            "YOB",
            "LastOpenYear",
            "SeniorEligibilityYear35Plus",
            "EligibleWithinWindow",
            "FirstSeniorYearAfterLastOpen",
            "ObservedSeniorAfterLastOpen",
            "DelayOpenToSeniorYears",
            "RightCensored",
        ],
    )

    diagnostic = build_diagnostic(
        register_rows,
        u21_rows,
        open_cohort_rows,
        open_annual_rows,
        continuity_rows,
    )
    diagnostic_path = (
        exports / "diagnostic_filiere_open_championnats_2017_2026.txt"
    )
    diagnostic_path.parent.mkdir(parents=True, exist_ok=True)
    diagnostic_path.write_text(diagnostic, encoding="utf-8")

    print("=" * 88)
    print("FILIERE OPEN 2017-2026 RECONSTRUITE")
    print("=" * 88)
    print(f"Sportifs-années : {len(register_rows)}")
    print(f"Sorties U21     : {len(u21_rows)}")
    print(f"Entrants Open   : {len(open_cohort_rows)}")
    print(f"Diagnostic      : {diagnostic_path}")
    print("Aucun fichier existant n'a été modifié.")


if __name__ == "__main__":
    main()
