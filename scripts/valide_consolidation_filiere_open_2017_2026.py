"""Valide et finalise la consolidation de la filière Open.

Actions
-------
1. Vérifie la présence des quatre sorties consolidées.
2. Contrôle les valeurs structurantes attendues.
3. Vérifie que le diagnostic et le rapport consolidés n'utilisent plus
   l'ancien taux de captation 2023 (51,2 % ou 21/41).
4. Corrige deux formulations :
   - "volume national" -> "volume au Championnat" ;
   - ajoute une note sur les dénominateurs différents des horizons Senior.

Le script ne modifie que :
- data/exports/diagnostic_consolide_filiere_open_2017_2026.txt
- reports/rapport_filiere_open_2017_2026_v1.md
"""

from __future__ import annotations

import csv
import re
from pathlib import Path


EXPECTED = {
    ("U21_OPEN_H1", "horizon_1_an"): (8, 42, 19.0),
    ("U21_OPEN_H2", "horizon_2_an"): (13, 35, 37.1),
    ("U21_OPEN_H3", "horizon_3_an"): (13, 31, 41.9),
    ("OPEN_REAPPARITION_H3", "horizon_3_an"): (18, 39, 46.2),
    ("OPEN_CONTINUITE_H3", "horizon_3_an"): (4, 39, 10.3),
    ("CHAMP_OPEN_CAPTURE_FR", "2023"): (18, 41, 43.9),
    ("CHAMP_OPEN_CAPTURE_FR", "2024"): (16, 37, 43.2),
    ("CHAMP_OPEN_CAPTURE_FR", "2025"): (14, 49, 28.6),
    ("OPEN_SENIOR_EVENTUEL", "jusqu_a_2026"): (5, 24, 20.8),
}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle, delimiter=";"))


def integer(value: str | None) -> int:
    return int(float(str(value or "0").replace(",", ".")))


def number(value: str | None) -> float:
    return float(str(value or "0").replace(",", "."))


def assert_close(actual: float, expected: float, label: str) -> None:
    if abs(actual - expected) > 0.05:
        raise AssertionError(
            f"{label}: attendu={expected}, obtenu={actual}"
        )


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        if new in text:
            return text
        raise RuntimeError(f"Texte à remplacer introuvable : {label}")
    return text.replace(old, new, 1)


def main() -> None:
    root = repo_root()

    csv_path = (
        root
        / "data/processed/indicateurs_consolides_filiere_open_2017_2026.csv"
    )
    diagnostic_path = (
        root
        / "data/exports/diagnostic_consolide_filiere_open_2017_2026.txt"
    )
    stale_path = (
        root
        / "data/exports/references_perimees_championnat_open.txt"
    )
    report_path = (
        root
        / "reports/rapport_filiere_open_2017_2026_v1.md"
    )

    required = [csv_path, diagnostic_path, stale_path, report_path]
    missing = [path for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(
            "Sorties manquantes : "
            + ", ".join(str(path) for path in missing)
        )

    rows = read_csv(csv_path)
    lookup = {
        (row["IndicatorCode"], row["Period"]): row
        for row in rows
    }

    for key, (expected_num, expected_den, expected_value) in EXPECTED.items():
        if key not in lookup:
            raise AssertionError(f"Indicateur absent : {key}")

        row = lookup[key]
        actual_num = integer(row["Numerator"])
        actual_den = integer(row["Denominator"])
        actual_value = number(row["Value"])

        if actual_num != expected_num:
            raise AssertionError(
                f"{key} numérateur : attendu={expected_num}, "
                f"obtenu={actual_num}"
            )
        if actual_den != expected_den:
            raise AssertionError(
                f"{key} dénominateur : attendu={expected_den}, "
                f"obtenu={actual_den}"
            )
        assert_close(actual_value, expected_value, f"{key} valeur")

    diagnostic = diagnostic_path.read_text(
        encoding="utf-8",
        errors="replace",
    )
    report = report_path.read_text(
        encoding="utf-8",
        errors="replace",
    )

    forbidden = [
        (re.compile(r"\b51[,.]2\s*%"), "51,2 %"),
        (re.compile(r"\b21\s*/\s*41\b"), "21/41"),
    ]
    for text_name, text in (
        ("diagnostic consolidé", diagnostic),
        ("rapport consolidé", report),
    ):
        for pattern, label in forbidden:
            if pattern.search(text):
                raise AssertionError(
                    f"{text_name} contient encore l'ancienne valeur {label}"
                )

    diagnostic = replace_once(
        diagnostic,
        "1. CATÉGORIE OPEN : VOLUME NATIONAL",
        "1. CATÉGORIE OPEN : VOLUME AU CHAMPIONNAT",
        "titre du diagnostic",
    )

    senior_sentence = (
        "Chevauchements Open/Senior : 8 sportifs.\n"
        "Senior est une population d'aval et de continuité ; elle ne mesure pas "
        "le renouvellement de la catégorie reine."
    )
    senior_replacement = (
        "Chevauchements Open/Senior : 8 sportifs.\n"
        "Les horizons 1, 2 et 3 saisons reposent sur des cohortes différentes : "
        "leurs pourcentages ne doivent pas être comparés comme une progression "
        "temporelle.\n"
        "Senior est une population d'aval et de continuité ; elle ne mesure pas "
        "le renouvellement de la catégorie reine."
    )
    diagnostic = replace_once(
        diagnostic,
        senior_sentence,
        senior_replacement,
        "précaution Senior du diagnostic",
    )

    report = replace_once(
        report,
        "## 2. Évolution de la catégorie Open",
        "## 2. Évolution du volume Open au Championnat",
        "titre du rapport",
    )

    report_senior = (
        "Ces données renseignent la continuité de pratique ; elles ne mesurent "
        "pas la santé de la filière de performance."
    )
    report_senior_replacement = (
        "Les taux calculés à un, deux et trois ans utilisent des cohortes de "
        "tailles différentes et ne décrivent donc pas une progression dans le "
        "temps. Ces données renseignent la continuité de pratique ; elles ne "
        "mesurent pas la santé de la filière de performance."
    )
    report = replace_once(
        report,
        report_senior,
        report_senior_replacement,
        "précaution Senior du rapport",
    )

    diagnostic_path.write_text(diagnostic, encoding="utf-8")
    report_path.write_text(report, encoding="utf-8")

    print("=" * 88)
    print("CONSOLIDATION VALIDÉE")
    print("=" * 88)
    print(f"Indicateurs contrôlés : {len(EXPECTED)}")
    print("Anciennes valeurs absentes du diagnostic et du rapport : OUI")
    print("Précaution sur les horizons Senior ajoutée : OUI")
    print("Titre du périmètre historique clarifié : OUI")
    print(f"Diagnostic : {diagnostic_path}")
    print(f"Rapport    : {report_path}")


if __name__ == "__main__":
    main()
