"""Audit du nombre d'Open au Championnat de France EMS 2023-2025.

But
---
Réconcilier deux définitions utilisées dans les analyses précédentes :
1. présence au code précis du Championnat de France Open ;
2. indicateur large de présence à une compétition nationale/championnat.

Sorties
-------
data/processed/audit_capture_championnat_open_ems_2023_2025.csv
data/exports/audit_capture_championnat_open_ems_2023_2025.txt
"""

from __future__ import annotations

import csv
import re
import unicodedata
from pathlib import Path


YEARS = (2023, 2024, 2025)
OPEN_CHAMPIONSHIP_CODES = {
    2023: "23FRA018",
    2024: "24FRA027",
    2025: "25FRA206",
}


def root_dir() -> Path:
    return Path(__file__).resolve().parents[1]


def normalize(value: str | None) -> str:
    text = unicodedata.normalize("NFKD", str(value or "").strip())
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", text.upper()).strip()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="", errors="replace") as handle:
        sample = handle.read(8192)
        handle.seek(0)
        try:
            delimiter = csv.Sniffer().sniff(sample, delimiters=";,\t").delimiter
        except csv.Error:
            delimiter = ";"
        return list(csv.DictReader(handle, delimiter=delimiter))


def first(row: dict[str, str], *names: str) -> str:
    for name in names:
        if name in row and row[name] is not None:
            return str(row[name])
    return ""


def truthy(value: str | None) -> bool:
    return normalize(value) in {"1", "TRUE", "YES", "Y", "OUI", "X"}


def is_french(row: dict[str, str]) -> bool:
    return (
        truthy(first(row, "IsFrench", "is_french", "French"))
        or normalize(first(row, "Country", "country", "Nation")) == "FRA"
    )


def is_open(value: str | None) -> bool:
    category = normalize(value)
    return "OPEN" in category or bool(
        re.search(r"(^|[^A-Z])PRO([^A-Z]|$)", category)
    )


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter=";")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    root = root_dir()
    register_path = (
        root / "data/processed/registre_filiere_open_ems_2023_2025.csv"
    )
    if not register_path.exists():
        raise FileNotFoundError(register_path)

    register = read_csv(register_path)
    register_headers = list(register[0].keys()) if register else []

    # Colonnes candidates de l'ancien indicateur large.
    broad_columns = [
        column
        for column in register_headers
        if "CHAMP" in normalize(column)
        or "NATCH" in normalize(column)
        or "NATIONAL" in normalize(column)
    ]

    register_open: dict[int, set[str]] = {year: set() for year in YEARS}
    broad_flagged: dict[int, set[str]] = {year: set() for year in YEARS}

    for row in register:
        year_text = first(row, "Year", "year")
        try:
            year = int(year_text)
        except (TypeError, ValueError):
            continue
        if year not in YEARS:
            continue

        athlete = first(row, "AthleteKey", "athlete_key", "RiderKey").strip()
        if not athlete:
            continue

        has_open = first(row, "HasOpen", "has_open")
        if normalize(has_open) not in {"1", "TRUE", "YES", "Y", "OUI", "X"}:
            continue

        register_open[year].add(athlete)

        if any(truthy(row.get(column)) for column in broad_columns):
            broad_flagged[year].add(athlete)

    exact_code: dict[int, set[str]] = {year: set() for year in YEARS}
    all_national_like: dict[int, set[str]] = {year: set() for year in YEARS}
    details: dict[tuple[int, str], dict[str, str]] = {}

    for year in YEARS:
        annual_path = (
            root
            / f"data/processed/ems_participations_france_waterski_{year}.csv"
        )
        if not annual_path.exists():
            raise FileNotFoundError(annual_path)

        for row in read_csv(annual_path):
            if not is_french(row):
                continue
            if not is_open(first(row, "Category", "category", "Categorie")):
                continue

            athlete = first(
                row, "AthleteKey", "athlete_key", "RiderKey"
            ).strip()
            code = first(
                row, "CompetitionCode", "competition_code", "Code"
            ).strip()
            name = first(
                row, "AthleteName", "Name", "name", "RiderName"
            ).strip()
            comp_name = first(
                row, "CompetitionName", "competition_name"
            ).strip()
            comp_type = first(
                row, "CompetitionType", "competition_type", "Type"
            ).strip()

            if not athlete or not code:
                continue

            details[(year, athlete)] = {
                "Name": name,
            }

            if code == OPEN_CHAMPIONSHIP_CODES[year]:
                exact_code[year].add(athlete)

            national_marker = normalize(
                " ".join(
                    [
                        code,
                        comp_name,
                        comp_type,
                        first(row, "NatCH", "NationalChampionship"),
                    ]
                )
            )
            if (
                "CHAMPIONNAT" in national_marker
                or "NATIONAL" in national_marker
                or "NATCH" in national_marker
            ):
                all_national_like[year].add(athlete)

    output_rows: list[dict[str, object]] = []
    report: list[str] = []
    report.append("AUDIT DE CAPTURE DU CHAMPIONNAT DE FRANCE OPEN — EMS 2023-2025")
    report.append("=" * 86)
    report.append("")
    report.append(
        "Colonnes larges détectées dans le registre : "
        + (", ".join(broad_columns) if broad_columns else "aucune")
    )
    report.append("")

    for year in YEARS:
        open_total = register_open[year]
        exact = exact_code[year]
        broad = broad_flagged[year]
        national_like = all_national_like[year]

        report.append(
            f"{year} : Open distincts={len(open_total)} ; "
            f"code Open précis={len(exact)} ; "
            f"indicateur large du registre={len(broad)} ; "
            f"toute compétition nationale détectée={len(national_like)}."
        )

        union = exact | broad | national_like
        for athlete in sorted(union):
            output_rows.append(
                {
                    "Year": year,
                    "AthleteKey": athlete,
                    "Name": details.get((year, athlete), {}).get("Name", ""),
                    "InExactOpenChampionshipCode": int(athlete in exact),
                    "InBroadRegisterFlag": int(athlete in broad),
                    "InAnyNationalLikeCompetition": int(
                        athlete in national_like
                    ),
                    "BroadButNotExact": int(
                        athlete in (broad | national_like)
                        and athlete not in exact
                    ),
                }
            )

        extras = sorted((broad | national_like) - exact)
        report.append(
            f"       Présences larges hors code Open précis : {len(extras)}."
        )
        for athlete in extras:
            report.append(
                f"       - {athlete} — "
                f"{details.get((year, athlete), {}).get('Name', '')}"
            )

    report.append("")
    report.append("INTERPRÉTATION")
    report.append("- Le code précis mesure la captation par le Championnat de France Open.")
    report.append(
        "- L'indicateur large peut inclure une présence Open dans un autre "
        "championnat national, notamment Senior."
    )
    report.append(
        "- Pour le rapport central sur la catégorie reine, le code précis doit "
        "être retenu."
    )
    report.append("")
    report.append("FIN DE L'AUDIT")

    processed = (
        root / "data/processed/audit_capture_championnat_open_ems_2023_2025.csv"
    )
    exports = (
        root / "data/exports/audit_capture_championnat_open_ems_2023_2025.txt"
    )

    write_csv(
        processed,
        output_rows,
        [
            "Year",
            "AthleteKey",
            "Name",
            "InExactOpenChampionshipCode",
            "InBroadRegisterFlag",
            "InAnyNationalLikeCompetition",
            "BroadButNotExact",
        ],
    )
    exports.parent.mkdir(parents=True, exist_ok=True)
    exports.write_text("\n".join(report), encoding="utf-8")

    print("=" * 88)
    print("AUDIT DE CAPTURE DU CHAMPIONNAT OPEN TERMINE")
    print("=" * 88)
    print(f"Diagnostic : {exports}")
    print("Aucun fichier existant n'a été modifié.")


if __name__ == "__main__":
    main()
