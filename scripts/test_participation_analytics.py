from __future__ import annotations

import argparse

from observatoire.analytics import (
    ParticipationAnalytics,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Teste les indicateurs de participation."
        )
    )

    parser.add_argument(
        "competition_id",
        type=int,
        help="Identifiant local de la compétition",
    )

    parser.add_argument(
        "--year",
        type=int,
        default=None,
        help=(
            "Année de référence pour le calcul "
            "des âges"
        ),
    )

    args = parser.parse_args()

    analytics = ParticipationAnalytics()

    summary = analytics.summary(
        args.competition_id,
        reference_year=args.year,
    )

    print()
    print(summary.competition_name)
    print("=" * len(summary.competition_name))
    print()

    print(
        "Identifiant IWWF        :",
        summary.competition_iwwf_id,
    )
    print(
        "Sportifs inscrits       :",
        summary.registered_riders,
    )
    print(
        "Sportifs actifs         :",
        summary.active_riders,
    )
    print(
        "Sportifs classés        :",
        summary.classified_riders,
    )
    print(
        "Forfaits / absents      :",
        summary.withdrawn_riders,
    )
    print(
        "Taux de participation   :",
        f"{summary.participation_rate:.2f} %",
    )
    print(
        "Taux de classement      :",
        f"{summary.classification_rate:.2f} %",
    )

    print()
    print("Sexe :")
    print("  Femmes                 :", summary.women)
    print("  Hommes                 :", summary.men)
    print(
        "  Sexe inconnu           :",
        summary.unknown_sex,
    )
    print(
        "  Taux de féminisation   :",
        f"{summary.women_rate:.2f} %",
    )

    print()
    print("Âge :")
    print(
        "  Âge moyen              :",
        (
            summary.average_age
            if summary.average_age is not None
            else "inconnu"
        ),
    )
    print(
        "  Âge minimum            :",
        (
            summary.minimum_age
            if summary.minimum_age is not None
            else "inconnu"
        ),
    )
    print(
        "  Âge maximum            :",
        (
            summary.maximum_age
            if summary.maximum_age is not None
            else "inconnu"
        ),
    )
    print(
        "  Années inconnues       :",
        summary.unknown_birth_year,
    )

    print()
    print("Catégories :")

    for category, count in (
        summary.categories.items()
    ):
        print(f"  {category}: {count}")

    print()
    print("Disciplines réelles :")

    for discipline, count in (
        summary.disciplines.items()
    ):
        print(f"  {discipline}: {count}")

    print()
    print("Multidiscipline :")

    for discipline_count, rider_count in (
        summary.multidiscipline.items()
    ):
        print(
            f"  {discipline_count} discipline(s): "
            f"{rider_count}"
        )

    print(
        "  Moyenne par sportif    :",
        summary.average_disciplines,
    )

    withdrawn = analytics.withdrawn_riders(
        args.competition_id
    )

    if withdrawn:
        print()
        print("Sportifs inscrits sans résultat :")

        for rider in withdrawn:
            print(
                f"  {rider.nom_complet} "
                f"(rider_id={rider.id})"
            )


if __name__ == "__main__":
    main()