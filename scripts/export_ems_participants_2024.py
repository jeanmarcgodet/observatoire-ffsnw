"""Extrait les participations approuvées des compétitions EMS françaises 2024."""

from __future__ import annotations

import csv
import re
import time
import unicodedata
from pathlib import Path

from playwright.sync_api import (
    TimeoutError as PlaywrightTimeoutError,
    sync_playwright,
)


ROOT = Path(__file__).resolve().parents[1]

INPUT_FILE = ROOT / (
    "data/processed/"
    "ems_competitions_france_waterski_2024_avec_urls.csv"
)

OUTPUT_FILE = ROOT / (
    "data/processed/"
    "ems_participations_france_waterski_2024.csv"
)

FAILURES_FILE = ROOT / (
    "data/processed/"
    "ems_participations_france_waterski_2024_echecs.csv"
)

CANCELLED_PATTERN = re.compile(
    r"cancelled|canceled|annul",
    flags=re.IGNORECASE,
)


def normalize_text(value: str) -> str:
    """Normalise un texte pour construire une clé de sportif."""

    value = unicodedata.normalize("NFD", value or "")

    value = "".join(
        character
        for character in value
        if unicodedata.category(character) != "Mn"
    )

    value = re.sub(r"\s+", " ", value).strip().upper()

    return value


def read_calendar() -> list[dict[str, str]]:
    """Lit le registre 2024 avec les URL EMS."""

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Fichier d'entrée introuvable : {INPUT_FILE}"
        )

    with INPUT_FILE.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        return list(
            csv.DictReader(
                file,
                delimiter=";",
            )
        )


def is_cancelled(row: dict[str, str]) -> bool:
    """Détermine si la compétition est indiquée comme annulée."""

    text = " ".join(
        [
            row.get("Date", ""),
            row.get("Name", ""),
        ]
    )

    return bool(CANCELLED_PATTERN.search(text))


def reveal_approved_participations(page) -> None:
    """Ouvre la rubrique Approved Participations si nécessaire."""

    page.evaluate(
        """
        () => {
          const elements = [...document.querySelectorAll("body *")];

          const title = elements.find((element) => {
            const text = (element.textContent || "").trim();

            return (
              element.children.length === 0 &&
              /Approved Participations/i.test(text)
            );
          });

          if (!title) {
            return false;
          }

          let container = title;

          for (let depth = 0; depth < 8 && container; depth += 1) {
            const controls = [
              ...container.querySelectorAll(
                "button, a, input[type='button']"
              ),
            ];

            const control = controls.find((element) => {
              const text = (
                element.textContent ||
                element.value ||
                ""
              ).trim();

              return /show\\/hide|show|display/i.test(text);
            });

            if (control) {
              control.click();
              return true;
            }

            container = container.parentElement;
          }

          return false;
        }
        """
    )


def wait_for_participant_table(page) -> None:
    """Attend l'apparition du tableau des participations approuvées."""

    page.wait_for_function(
        """
        () => {
          return [...document.querySelectorAll("table")].some(
            (table) => {
              const text = (
                table.innerText || ""
              ).replace(/\\s+/g, " ");

              return (
                table.offsetParent !== null &&
                text.includes("Name") &&
                text.includes("Country") &&
                text.includes("Categ.") &&
                text.includes("YOB") &&
                (
                  text.includes("Slalom") ||
                  text.includes("Tricks") ||
                  text.includes("Jump")
                )
              );
            }
          );
        }
        """,
        timeout=20_000,
    )


def extract_table(page) -> list[dict[str, str]]:
    """Extrait le tableau visible des participations approuvées."""

    return page.evaluate(
        """
        () => {
          const table = [...document.querySelectorAll("table")].find(
            (candidate) => {
              const text = (
                candidate.innerText || ""
              ).replace(/\\s+/g, " ");

              return (
                candidate.offsetParent !== null &&
                text.includes("Name") &&
                text.includes("Country") &&
                text.includes("Categ.") &&
                text.includes("YOB") &&
                (
                  text.includes("Slalom") ||
                  text.includes("Tricks") ||
                  text.includes("Jump")
                )
              );
            }
          );

          if (!table) {
            return [];
          }

          const rows = [...table.querySelectorAll("tr")];

          if (rows.length < 2) {
            return [];
          }

          const headers = [
            ...rows[0].querySelectorAll("th, td"),
          ].map((cell, index) => {
            const value = (
              cell.innerText || ""
            ).trim().replace(/\\s+/g, " ");

            return value || `Colonne_${index + 1}`;
          });

          return rows
            .slice(1)
            .map((row) => {
              const cells = [
                ...row.querySelectorAll("th, td"),
              ];

              const values = cells.map((cell) =>
                (cell.innerText || "")
                  .trim()
                  .replace(/\\s+/g, " ")
              );

              const record = {};

              headers.forEach((header, index) => {
                record[header] = values[index] || "";
              });

              return record;
            })
            .filter((record) =>
              String(record.Name || "").trim() !== ""
            );
        }
        """
    )


def build_output_record(
    competition: dict[str, str],
    participant: dict[str, str],
) -> dict[str, str]:
    """Construit une ligne consolidée compétition-sportif."""

    name = participant.get("Name", "").strip()
    country = participant.get("Country", "").strip().upper()
    yob = participant.get("YOB", "").strip()

    normalized_name = normalize_text(name)

    return {
        "Year": "2024",
        "CompetitionCode": competition.get("EMS Code", "").strip(),
        "CompetitionDate": competition.get("Date", "").strip(),
        "CompetitionName": competition.get("Name", "").strip(),
        "CompetitionType": competition.get("Type", "").strip(),
        "Homologation": competition.get("Homol.", "").strip(),
        "Site": competition.get("Site", "").strip(),
        "CompetitionUrl": competition.get(
            "CompetitionUrl",
            "",
        ).strip(),
        "AthleteKey": f"{country}|{yob}|{normalized_name}",
        "Name": name,
        "NormalizedName": normalized_name,
        "Country": country,
        "IsFrench": "1" if country == "FRA" else "0",
        "Category": participant.get("Categ.", "").strip(),
        "YOB": yob,
        "Slalom": participant.get("Slalom", "").strip(),
        "Tricks": participant.get("Tricks", "").strip(),
        "Jump": participant.get("Jump", "").strip(),
        "Overall": participant.get("Overall", "").strip(),
    }


def write_csv(
    path: Path,
    rows: list[dict[str, str]],
) -> None:
    """Écrit une liste de dictionnaires dans un CSV UTF-8."""

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if not rows:
        print(f"Aucune ligne à écrire dans {path.name}.")
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


def main() -> None:
    competitions = read_calendar()

    active_competitions = [
        competition
        for competition in competitions
        if not is_cancelled(competition)
    ]

    all_participations: list[dict[str, str]] = []
    failures: list[dict[str, str]] = []

    print("=" * 80)
    print("EXTRACTION EMS — PARTICIPATIONS APPROUVÉES 2024")
    print("=" * 80)
    print(f"Compétitions dans le registre : {len(competitions)}")
    print(f"Compétitions non annulées      : {len(active_competitions)}")
    print()

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=False,
            slow_mo=80,
        )

        page = browser.new_page(
            viewport={
                "width": 1440,
                "height": 1000,
            }
        )

        for index, competition in enumerate(
            active_competitions,
            start=1,
        ):
            code = competition.get("EMS Code", "").strip()
            name = competition.get("Name", "").strip()
            url = competition.get("CompetitionUrl", "").strip()

            print(
                f"[{index:02d}/{len(active_competitions):02d}] "
                f"{code} — {name}"
            )

            if not url:
                failures.append(
                    {
                        "CompetitionCode": code,
                        "CompetitionName": name,
                        "CompetitionUrl": url,
                        "Reason": "URL absente",
                    }
                )
                print("  ÉCHEC : URL absente")
                continue

            try:
                page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=60_000,
                )

                page.wait_for_timeout(800)

                reveal_approved_participations(page)

                wait_for_participant_table(page)

                participants = extract_table(page)

                if not participants:
                    raise RuntimeError(
                        "Tableau trouvé mais aucune participation extraite"
                    )

                records = [
                    build_output_record(
                        competition,
                        participant,
                    )
                    for participant in participants
                ]

                all_participations.extend(records)

                french_count = sum(
                    record["IsFrench"] == "1"
                    for record in records
                )

                print(
                    f"  {len(records)} participants, "
                    f"dont {french_count} Français"
                )

            except (
                PlaywrightTimeoutError,
                RuntimeError,
                Exception,
            ) as error:
                failures.append(
                    {
                        "CompetitionCode": code,
                        "CompetitionName": name,
                        "CompetitionUrl": url,
                        "Reason": str(error),
                    }
                )

                print(f"  ÉCHEC : {error}")

            time.sleep(0.3)

        browser.close()

    write_csv(
        OUTPUT_FILE,
        all_participations,
    )

    if failures:
        write_csv(
            FAILURES_FILE,
            failures,
        )
    elif FAILURES_FILE.exists():
        FAILURES_FILE.unlink()

    athlete_keys = {
        row["AthleteKey"]
        for row in all_participations
    }

    french_keys = {
        row["AthleteKey"]
        for row in all_participations
        if row["IsFrench"] == "1"
    }

    print()
    print("=" * 80)
    print("BILAN")
    print("=" * 80)
    print(f"Participations extraites : {len(all_participations)}")
    print(f"Sportifs uniques         : {len(athlete_keys)}")
    print(f"Sportifs français uniques: {len(french_keys)}")
    print(f"Échecs                   : {len(failures)}")
    print(f"CSV principal            : {OUTPUT_FILE}")
    print(f"CSV des échecs           : {FAILURES_FILE}")


if __name__ == "__main__":
    main()