"""Audit corrigé de la continuité Open -> Senior, 2017-2026.

Le précédent indicateur divisait tous les anciens Open devenus éligibles 35+
dans la fenêtre, y compris ceux dont la dernière saison Open était trop récente
pour observer une transition. Ce script construit des horizons comparables.

Entrées
-------
data/processed/continuite_open_senior_championnats_2017_2026.csv
data/processed/registre_championnats_filiere_open_2017_2026.csv

Sorties
-------
data/processed/continuite_open_senior_horizons_2017_2026.csv
data/processed/chevauchements_open_senior_2017_2026.csv
data/exports/diagnostic_continuite_open_senior_2017_2026.txt
"""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path


END_YEAR = 2026


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="", errors="replace") as handle:
        return list(csv.DictReader(handle, delimiter=";"))


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


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter=";")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    root = repo_root()
    continuity_path = (
        root
        / "data/processed/continuite_open_senior_championnats_2017_2026.csv"
    )
    register_path = (
        root
        / "data/processed/registre_championnats_filiere_open_2017_2026.csv"
    )

    if not continuity_path.exists():
        raise FileNotFoundError(continuity_path)
    if not register_path.exists():
        raise FileNotFoundError(register_path)

    continuity = read_csv(continuity_path)
    register = read_csv(register_path)

    detail_rows: list[dict[str, object]] = []

    for row in continuity:
        rider_id = integer(row.get("CanonicalRiderId"))
        last_open = integer(row.get("LastOpenYear"))
        eligibility_year = integer(row.get("SeniorEligibilityYear35Plus"))
        first_senior = integer(row.get("FirstSeniorYearAfterLastOpen"))

        if rider_id is None or last_open is None:
            continue

        if eligibility_year is None:
            risk_start = None
            available = 0
        else:
            # Première saison où un passage Senior après la dernière saison Open
            # est à la fois chronologiquement et réglementairement observable.
            risk_start = max(last_open + 1, eligibility_year)
            available = (
                END_YEAR - risk_start + 1
                if risk_start <= END_YEAR
                else 0
            )

        invalid_senior_before_risk = int(
            first_senior is not None
            and risk_start is not None
            and first_senior < risk_start
        )

        def transitioned_within(horizon: int) -> object:
            if available < horizon:
                return ""
            return int(
                first_senior is not None
                and risk_start is not None
                and risk_start <= first_senior <= risk_start + horizon - 1
            )

        detail_rows.append(
            {
                "CanonicalRiderId": rider_id,
                "Name": row.get("Name", ""),
                "Sex": row.get("Sex", ""),
                "YOB": row.get("YOB", ""),
                "LastOpenYear": last_open,
                "SeniorEligibilityYear35Plus": eligibility_year or "",
                "FirstObservableSeniorYearAfterOpen": risk_start or "",
                "AvailableFollowUpSeasons": available,
                "FirstSeniorYearAfterLastOpen": first_senior or "",
                "TransitionInFirstObservableSeason": transitioned_within(1),
                "TransitionWithin2ObservableSeasons": transitioned_within(2),
                "TransitionWithin3ObservableSeasons": transitioned_within(3),
                "ObservedEventuallyBy2026": int(
                    first_senior is not None
                    and risk_start is not None
                    and first_senior >= risk_start
                ),
                "InvalidSeniorBeforeRiskStart": invalid_senior_before_risk,
            }
        )

    overlap_rows: list[dict[str, object]] = []
    overlap_by_athlete: dict[int, list[int]] = defaultdict(list)

    for row in register:
        if not (flag(row.get("HasOpen")) and flag(row.get("HasSenior"))):
            continue

        rider_id = integer(row.get("CanonicalRiderId"))
        year = integer(row.get("Year"))
        if rider_id is None or year is None:
            continue

        overlap_by_athlete[rider_id].append(year)
        overlap_rows.append(
            {
                "Year": year,
                "CanonicalRiderId": rider_id,
                "Name": row.get("Name", ""),
                "Sex": row.get("Sex", ""),
                "YOB": row.get("YOB", ""),
                "Age": row.get("Age", ""),
                "Categories": row.get("Categories", ""),
                "CompetitionCodes": row.get("CompetitionCodes", ""),
            }
        )

    processed = root / "data/processed"
    exports = root / "data/exports"

    detail_fields = [
        "CanonicalRiderId",
        "Name",
        "Sex",
        "YOB",
        "LastOpenYear",
        "SeniorEligibilityYear35Plus",
        "FirstObservableSeniorYearAfterOpen",
        "AvailableFollowUpSeasons",
        "FirstSeniorYearAfterLastOpen",
        "TransitionInFirstObservableSeason",
        "TransitionWithin2ObservableSeasons",
        "TransitionWithin3ObservableSeasons",
        "ObservedEventuallyBy2026",
        "InvalidSeniorBeforeRiskStart",
    ]
    overlap_fields = [
        "Year",
        "CanonicalRiderId",
        "Name",
        "Sex",
        "YOB",
        "Age",
        "Categories",
        "CompetitionCodes",
    ]

    write_csv(
        processed / "continuite_open_senior_horizons_2017_2026.csv",
        detail_rows,
        detail_fields,
    )
    write_csv(
        processed / "chevauchements_open_senior_2017_2026.csv",
        overlap_rows,
        overlap_fields,
    )

    lines: list[str] = []
    lines.append("CONTINUITÉ OPEN → SENIOR — HORIZONS COMPARABLES 2017-2026")
    lines.append("=" * 84)
    lines.append("")
    lines.append("1. PASSAGE APRÈS LA DERNIÈRE SAISON OPEN")
    lines.append("-" * 84)

    for horizon, field in (
        (1, "TransitionInFirstObservableSeason"),
        (2, "TransitionWithin2ObservableSeasons"),
        (3, "TransitionWithin3ObservableSeasons"),
    ):
        analyzable = [
            row
            for row in detail_rows
            if int(row["AvailableFollowUpSeasons"]) >= horizon
        ]
        transitions = sum(int(row[field]) for row in analyzable)
        lines.append(
            f"Horizon {horizon} saison(s) observable(s) : "
            f"{transitions}/{len(analyzable)} passages "
            f"({str(percentage(transitions, len(analyzable))).replace('.', ',')} %)."
        )

    any_followup = [
        row for row in detail_rows
        if int(row["AvailableFollowUpSeasons"]) >= 1
    ]
    no_followup = [
        row for row in detail_rows
        if int(row["AvailableFollowUpSeasons"]) == 0
    ]
    eventually = sum(
        int(row["ObservedEventuallyBy2026"])
        for row in any_followup
    )

    lines.append("")
    lines.append(
        f"Sportifs disposant d'au moins une saison observable après Open : "
        f"{len(any_followup)}."
    )
    lines.append(
        f"Transitions observées à un moment quelconque avant 2026 : "
        f"{eventually}/{len(any_followup)} "
        f"({str(percentage(eventually, len(any_followup))).replace('.', ',')} %)."
    )
    lines.append(
        f"Sportifs sans aucune saison de recul exploitable : {len(no_followup)}."
    )

    lines.append("")
    lines.append("2. CHEVAUCHEMENT OPEN ET SENIOR")
    lines.append("-" * 84)
    lines.append(
        f"Sportifs observés au moins une fois simultanément en Open et Senior : "
        f"{len(overlap_by_athlete)}."
    )
    lines.append(
        f"Sportifs-années de chevauchement : {len(overlap_rows)}."
    )

    if overlap_by_athlete:
        lines.append("")
        lines.append("Années de chevauchement par sportif :")
        names = {
            integer(row.get("CanonicalRiderId")): row.get("Name", "")
            for row in overlap_rows
        }
        for rider_id, years in sorted(
            overlap_by_athlete.items(),
            key=lambda item: (names.get(item[0], ""), item[0]),
        ):
            lines.append(
                f"- {names.get(rider_id, '')} : "
                + ", ".join(str(year) for year in sorted(set(years)))
                + "."
            )

    invalid = sum(
        int(row["InvalidSeniorBeforeRiskStart"])
        for row in detail_rows
    )

    lines.append("")
    lines.append("3. PRÉCAUTIONS")
    lines.append("- L'âge d'éligibilité est approximé par année de naissance + 35.")
    lines.append(
        "- Le passage est défini comme une apparition Senior après la dernière "
        "apparition Open au Championnat de France."
    )
    lines.append(
        "- Une inscription simultanée Open/Senior est décrite séparément et "
        "n'est pas assimilée à une sortie d'Open."
    )
    lines.append(
        "- Une absence au Championnat de France ne signifie pas un arrêt de pratique."
    )
    lines.append(f"- Anomalies chronologiques détectées : {invalid}.")
    lines.append("")
    lines.append("FIN DU DIAGNOSTIC")

    output = exports / "diagnostic_continuite_open_senior_2017_2026.txt"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")

    print("=" * 88)
    print("AUDIT OPEN VERS SENIOR TERMINE")
    print("=" * 88)
    print(f"Trajectoires analysées : {len(detail_rows)}")
    print(f"Chevauchements Open/Senior : {len(overlap_rows)} sportifs-années")
    print(f"Diagnostic : {output}")
    print("Aucun fichier existant n'a été modifié.")


if __name__ == "__main__":
    main()
