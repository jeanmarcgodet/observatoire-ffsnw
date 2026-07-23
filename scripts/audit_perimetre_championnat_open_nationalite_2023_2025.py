"""Réconcilie les effectifs Open du Championnat de France selon la nationalité.

Compare, pour les codes Open précis 2023-2025 :
- tous les Open approuvés dans les exports EMS ;
- les Open français ;
- les Open non français ;
- les sportifs français inclus dans l'ancien indicateur large mais absents
  du code Open précis.

Sorties
-------
data/processed/audit_perimetre_championnat_open_nationalite_2023_2025.csv
data/exports/audit_perimetre_championnat_open_nationalite_2023_2025.txt
"""

from __future__ import annotations

import csv
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path


CODES = {
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


def is_open(value: str | None) -> bool:
    category = normalize(value)
    return "OPEN" in category or bool(
        re.search(r"(^|[^A-Z])PRO([^A-Z]|$)", category)
    )


def country(row: dict[str, str]) -> str:
    value = first(row, "Country", "country", "Nation", "Federation")
    normalized = normalize(value)
    if normalized:
        return normalized
    if truthy(first(row, "IsFrench", "is_french", "French")):
        return "FRA"
    return "INCONNU"


def is_french(row: dict[str, str]) -> bool:
    return (
        truthy(first(row, "IsFrench", "is_french", "French"))
        or country(row) == "FRA"
    )


def athlete_key(row: dict[str, str]) -> str:
    key = first(row, "AthleteKey", "athlete_key", "RiderKey").strip()
    if key:
        return key

    name = normalize(
        first(row, "AthleteName", "RiderName", "Name", "name")
    )
    yob = first(row, "YOB", "YearOfBirth", "BirthYear").strip()
    nation = country(row)
    return f"{nation}|{yob}|{name}"


def athlete_name(row: dict[str, str]) -> str:
    return first(
        row, "AthleteName", "RiderName", "Name", "name"
    ).strip()


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter=";")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    root = root_dir()
    detail_rows: list[dict[str, object]] = []
    report: list[str] = []

    report.append("PÉRIMÈTRE DU CHAMPIONNAT DE FRANCE OPEN — NATIONALITÉ 2023-2025")
    report.append("=" * 88)
    report.append("")

    for year, code in CODES.items():
        path = (
            root
            / f"data/processed/ems_participations_france_waterski_{year}.csv"
        )
        if not path.exists():
            raise FileNotFoundError(path)

        exact: dict[str, dict[str, str]] = {}

        for row in read_csv(path):
            row_code = first(
                row, "CompetitionCode", "competition_code", "Code"
            ).strip()
            category = first(row, "Category", "category", "Categorie")

            if row_code != code or not is_open(category):
                continue

            key = athlete_key(row)
            exact.setdefault(
                key,
                {
                    "Name": athlete_name(row),
                    "Country": country(row),
                    "IsFrench": "1" if is_french(row) else "0",
                },
            )

        french = {
            key: value
            for key, value in exact.items()
            if value["IsFrench"] == "1"
        }
        foreign = {
            key: value
            for key, value in exact.items()
            if value["IsFrench"] == "0"
        }
        country_counts = Counter(value["Country"] for value in foreign.values())

        report.append(
            f"{year} — {code} : tous Open={len(exact)} ; "
            f"Open français={len(french)} ; "
            f"Open non français={len(foreign)}."
        )

        if country_counts:
            report.append(
                "       Nationalités non françaises : "
                + ", ".join(
                    f"{nation}={count}"
                    for nation, count in sorted(country_counts.items())
                )
                + "."
            )

        for key, value in sorted(foreign.items()):
            report.append(
                f"       - {value['Country']} — {key} — {value['Name']}"
            )

        for key, value in sorted(exact.items()):
            detail_rows.append(
                {
                    "Year": year,
                    "CompetitionCode": code,
                    "AthleteKey": key,
                    "Name": value["Name"],
                    "Country": value["Country"],
                    "IsFrench": value["IsFrench"],
                }
            )

        report.append("")

    prior_audit = (
        root / "data/processed/audit_capture_championnat_open_ems_2023_2025.csv"
    )
    report.append("ANCIEN INDICATEUR LARGE : EXTRAS FRANÇAIS HORS CODE OPEN PRÉCIS")
    report.append("-" * 88)

    if prior_audit.exists():
        rows = read_csv(prior_audit)
        extras_by_year: dict[int, list[dict[str, str]]] = defaultdict(list)

        for row in rows:
            try:
                year = int(first(row, "Year"))
            except ValueError:
                continue

            if (
                first(row, "InBroadRegisterFlag") == "1"
                and first(row, "InExactOpenChampionshipCode") == "0"
            ):
                extras_by_year[year].append(row)

        for year in CODES:
            extras = extras_by_year.get(year, [])
            report.append(f"{year} : {len(extras)} extras.")
            for row in extras:
                report.append(
                    f"       - {first(row, 'AthleteKey')} — "
                    f"{first(row, 'Name')}"
                )
    else:
        report.append("Fichier d'audit précédent absent.")

    report.append("")
    report.append("INTERPRÉTATION")
    report.append("- La série française doit retenir uniquement IsFrench=1.")
    report.append(
        "- La série tous participants peut être supérieure si des étrangers "
        "sont admis au Championnat."
    )
    report.append(
        "- Les extras de l'indicateur large sont un phénomène distinct : "
        "ce sont des Français comptés hors du code Open précis."
    )
    report.append("")
    report.append("FIN DE L'AUDIT")

    output_csv = (
        root
        / "data/processed/audit_perimetre_championnat_open_nationalite_2023_2025.csv"
    )
    output_txt = (
        root
        / "data/exports/audit_perimetre_championnat_open_nationalite_2023_2025.txt"
    )

    write_csv(
        output_csv,
        detail_rows,
        [
            "Year",
            "CompetitionCode",
            "AthleteKey",
            "Name",
            "Country",
            "IsFrench",
        ],
    )
    output_txt.parent.mkdir(parents=True, exist_ok=True)
    output_txt.write_text("\n".join(report), encoding="utf-8")

    print("=" * 88)
    print("AUDIT DU PÉRIMÈTRE NATIONALITÉ TERMINÉ")
    print("=" * 88)
    print(f"Diagnostic : {output_txt}")
    print("Aucun fichier existant n'a été modifié.")


if __name__ == "__main__":
    main()
