from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from observatoire.importers.iwwf_results_importer import (  # noqa: E402
    import_competition_results,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Importe dans SQLite les résultats IWWF "
            "d'une compétition déjà téléchargée."
        )
    )

    parser.add_argument(
        "competition_code",
        help="Code IWWF de la compétition, par exemple 26FRA021",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Affiche le détail de chaque fichier importé.",
    )

    return parser

def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    try:
        report = import_competition_results(
            competition_code=args.competition_code,
            verbose=args.verbose,
        )
    except Exception as exc:
        print(
            f"Erreur : {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc

    print()
    print(f"Compétition : {report.competition_code}")
    print(f"Fichiers détectés : {report.fichiers_detectes}")
    print(f"Fichiers importés : {report.fichiers_importes}")
    print(f"Résultats parsés : {report.resultats_parses}")
    print(f"Résultats ajoutés : {report.resultats_ajoutes}")
    print(f"Résultats déjà présents : {report.resultats_existants}")
    print(f"Classifications ajoutées : {report.classifications_ajoutees}")
    print(
        f"Classifications déjà présentes : "
        f"{report.classifications_existantes}"
    )
    print(f"Riders introuvables : {report.riders_introuvables}")
    print(f"Fichiers en erreur : {report.erreurs}")

if __name__ == "__main__":
    main()