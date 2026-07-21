from __future__ import annotations

import argparse
from pathlib import Path

from observatoire.importers.iwwf_participants_importer import (
    import_participants,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Importe les participants d'une compétition IWWF "
            "depuis la page all_skiers_list.html."
        )
    )

    parser.add_argument(
        "competition_code",
        help="Code IWWF de la compétition, par exemple 25FRA206.",
    )

    parser.add_argument(
        "--html-file",
        type=Path,
        default=None,
        help=(
            "Chemin facultatif vers all_skiers_list.html. "
            "Par défaut : "
            "data/raw/iwwf/<competition_code>/all_skiers_list.html"
        ),
    )

    return parser.parse_args()


def normalize_competition_code(value: str) -> str:
    competition_code = value.strip().upper()

    if competition_code.startswith("T-"):
        competition_code = competition_code[2:]

    if not competition_code:
        raise ValueError(
            "Le code de compétition ne peut pas être vide."
        )

    return competition_code


def main() -> None:
    args = parse_args()

    competition_code = normalize_competition_code(
        args.competition_code
    )

    html_file = args.html_file

    if html_file is None:
        competition_directory = (
            Path("data")
            / "raw"
            / "iwwf"
            / competition_code
        )

        default_candidates = [
            competition_directory
            / "all_skiers_list.html",
            *sorted(
                competition_directory.glob(
                    "identity_candidates*.json"
                )
            ),
        ]

        html_file = next(
            (
                candidate
                for candidate in default_candidates
                if candidate.is_file()
            ),
            competition_directory
            / "all_skiers_list.html",
        )

    if not html_file.is_file():
        raise FileNotFoundError(
            "Fichier des participants introuvable : "
            f"{html_file}\n"
            "Télécharge d'abord la compétition avec :\n"
            "python scripts/download_competition.py "
            f"{competition_code}"
        )

    riders_count, entries_count = import_participants(
        competition_code=competition_code,
        html_file=html_file,
    )

    print()
    print(f"Compétition          : {competition_code}")
    print(f"Fichier source       : {html_file}")
    print(f"Riders uniques       : {riders_count}")
    print(f"Inscriptions ajoutées: {entries_count}")


if __name__ == "__main__":
    main()
