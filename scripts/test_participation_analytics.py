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

    title = (
        summary.competition_name
        or f"Compétition {summary.competition_id}"
    )

    print()
    print(title)
    print("=" * len(title))
    print()

    print(
        "Identifiant IWWF             :",
        summary.competition_iwwf_id,
    )

    print()
    print("Populations :")
    print(
        "  Inscriptions locales       :",
        summary.local_registered_riders,
    )
    print(
        "  Participants EMS confirmés :",
        summary.confirmed_riders,
    )
    print(
        "  Non confirmés par l'EMS    :",
        summary.unconfirmed_local_riders,
    )
    print(
        "  Participants effectifs     :",
        summary.active_riders,
    )
    print(
        "  Participants classés       :",
        summary.classified_riders,
    )
    print(
        "  Forfaits EMS               :",
        summary.withdrawn_confirmed_riders,
    )

    print()
    print("Taux :")
    print(
        "  Participation effective    :",
        f"{summary.effective_participation_rate:.2f} %",
    )
    print(
        "  Classement                 :",
        f"{summary.classification_rate:.2f} %",
    )
    print(
        "  Confirmation des entrées   :",
        f"{summary.local_confirmation_rate:.2f} %",
    )

    print()
    print("Sexe — population EMS :")
    print(
        "  Femmes                     :",
        summary.women,
    )
    print(
        "  Hommes                     :",
        summary.men,
    )
    print(
        "  Sexe inconnu               :",
        summary.unknown_sex,
    )
    print(
        "  Taux de féminisation       :",
        f"{summary.women_rate:.2f} %",
    )

    print()
    print("Âge — population EMS :")
    print(
        "  Âge moyen                  :",
        (
            summary.average_age
            if summary.average_age is not None
            else "inconnu"
        ),
    )
    print(
        "  Âge minimum                :",
        (
            summary.minimum_age
            if summary.minimum_age is not None
            else "inconnu"
        ),
    )
    print(
        "  Âge maximum                :",
        (
            summary.maximum_age
            if summary.maximum_age is not None
            else "inconnu"
        ),
    )
    print(
        "  Années inconnues           :",
        summary.unknown_birth_year,
    )

    print()
    print("Catégories EMS :")

    for category, count in (
        summary.categories.items()
    ):
        print(f"  {category}: {count}")

    print()
    print("Disciplines réelles EMS :")

    for discipline, count in (
        summary.disciplines.items()
    ):
        print(f"  {discipline}: {count}")

    print()
    print("Multidiscipline EMS :")

    for discipline_count, rider_count in (
        summary.multidiscipline.items()
    ):
        print(
            f"  {discipline_count} discipline(s): "
            f"{rider_count}"
        )

    print(
        "  Moyenne par sportif        :",
        summary.average_disciplines,
    )

    unconfirmed = (
        analytics.unconfirmed_local_riders(
            args.competition_id
        )
    )

    if unconfirmed:
        print()
        print(
            "Inscriptions locales non confirmées "
            "par l'EMS :"
        )

        for rider in unconfirmed:
            print(
                f"  {rider.nom_complet} "
                f"(rider_id={rider.id})"
            )

    withdrawn = analytics.withdrawn_riders(
        args.competition_id
    )

    if withdrawn:
        print()
        print(
            "Participants EMS sans résultat :"
        )

        for rider in withdrawn:
            print(
                f"  {rider.nom_complet} "
                f"(rider_id={rider.id})"
            )


if __name__ == "__main__":
    main()