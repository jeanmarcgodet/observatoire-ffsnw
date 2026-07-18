"""Télécharge et archive les pages d'une compétition IWWF Classic."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from observatoire.importers.iwwf_downloader import (
    DEFAULT_DELAY_SECONDS,
    DEFAULT_MAX_PAGES,
    DEFAULT_OUTPUT_ROOT,
    DEFAULT_TIMEOUT_SECONDS,
    IWWFDownloadError,
    download_competition,
)


def build_argument_parser() -> argparse.ArgumentParser:
    """Construit l'analyseur des arguments de la ligne de commande."""

    parser = argparse.ArgumentParser(
        description=(
            "Télécharge les pages HTML d'une compétition IWWF Classic "
            "et les archive localement."
        )
    )

    parser.add_argument(
        "competition_code",
        help=(
            "Code de la compétition IWWF, par exemple 26FRA021 "
            "ou T-26FRA021."
        ),
    )

    parser.add_argument(
        "--output-root",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
        help=(
            "Répertoire racine des archives. "
            f"Valeur par défaut : {DEFAULT_OUTPUT_ROOT}"
        ),
    )

    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help=(
            "Délai maximal d'une requête HTTP en secondes. "
            f"Valeur par défaut : {DEFAULT_TIMEOUT_SECONDS}"
        ),
    )

    parser.add_argument(
        "--delay",
        type=float,
        default=DEFAULT_DELAY_SECONDS,
        help=(
            "Délai entre deux requêtes HTTP en secondes. "
            f"Valeur par défaut : {DEFAULT_DELAY_SECONDS}"
        ),
    )

    parser.add_argument(
        "--max-pages",
        type=int,
        default=DEFAULT_MAX_PAGES,
        help=(
            "Nombre maximal de pages pouvant être téléchargées. "
            f"Valeur par défaut : {DEFAULT_MAX_PAGES}"
        ),
    )

    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Télécharge à nouveau les fichiers déjà présents.",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Affiche le détail des téléchargements.",
    )

    return parser


def configure_logging(verbose: bool) -> None:
    """Configure les messages de journalisation."""

    logging.basicConfig(
        level=logging.INFO if verbose else logging.WARNING,
        format="%(levelname)s: %(message)s",
    )


def print_report(report: object) -> None:
    """Affiche le rapport synthétique du téléchargement."""

    print()
    print(f"Compétition       : {report.competition_code}")
    print(f"URL source        : {report.source_url}")
    print(f"Répertoire        : {report.output_directory}")
    print(f"Pages découvertes : {report.pages_discovered}")
    print(f"Pages enregistrées: {report.pages_downloaded}")
    print(f"Pages réutilisées : {report.pages_reused}")
    print(f"Pages en échec    : {report.pages_failed}")
    print(f"Manifeste         : {report.manifest_path}")

    if report.errors:
        print()
        print("Erreurs :")

        for error in report.errors:
            print(f"  - {error}")


def main() -> int:
    """Point d'entrée du script."""

    parser = build_argument_parser()
    arguments = parser.parse_args()

    configure_logging(arguments.verbose)

    try:
        report = download_competition(
            arguments.competition_code,
            output_root=arguments.output_root,
            timeout_seconds=arguments.timeout,
            delay_seconds=arguments.delay,
            max_pages=arguments.max_pages,
            overwrite=arguments.overwrite,
        )
    except (ValueError, IWWFDownloadError) as exc:
        print(
            f"Erreur : {exc}",
            file=sys.stderr,
        )
        return 1
    except KeyboardInterrupt:
        print(
            "\nTéléchargement interrompu.",
            file=sys.stderr,
        )
        return 130

    print_report(report)

    return 1 if report.pages_failed else 0


if __name__ == "__main__":
    raise SystemExit(main())