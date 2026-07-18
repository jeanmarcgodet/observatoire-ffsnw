from pathlib import Path

from observatoire.importers.iwwf_participants_importer import (
    import_participants,
)


def main() -> None:
    competition_code = "26FRA021"

    html_file = Path(
        "data/raw/iwwf"
    ) / competition_code / "all_skiers_list.html"

    riders_count, entries_count = import_participants(
        competition_code=competition_code,
        html_file=html_file,
    )

    print(f"Compétition : {competition_code}")
    print(f"Riders uniques : {riders_count}")
    print(f"Inscriptions ajoutées : {entries_count}")


if __name__ == "__main__":
    main()
