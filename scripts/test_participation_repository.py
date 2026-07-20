from __future__ import annotations

import argparse
from collections import Counter

from observatoire.repository import ParticipationRepository


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Vérifie la couche repository de participation."
        )
    )

    parser.add_argument(
        "competition_id",
        type=int,
        help="Identifiant local de la compétition",
    )

    args = parser.parse_args()

    repository = ParticipationRepository()

    competition = repository.get_competition(
        args.competition_id
    )

    if competition is None:
        raise SystemExit(
            "Compétition locale introuvable : "
            f"{args.competition_id}"
        )

    riders = repository.riders_for_competition(
        competition.id
    )

    entries = repository.entries_for_competition(
        competition.id
    )

    entry_disciplines = (
        repository.entry_disciplines_for_competition(
            competition.id,
            include_overall=True,
        )
    )

    active_ids = repository.active_rider_ids(
        competition.id
    )

    classified_ids = repository.classified_rider_ids(
        competition.id
    )

    withdrawn = repository.withdrawn_riders(
        competition.id
    )

    category_counts = Counter(
        entry.categorie
        for entry in entries
    )

    discipline_counts = Counter(
        item.discipline
        for item in entry_disciplines
    )

    multidiscipline_counts: Counter[int] = Counter()

    for rider, disciplines in (
        repository.iter_rider_disciplines(
            competition.id,
            include_overall=False,
        )
    ):
        multidiscipline_counts[len(disciplines)] += 1

    print()
    print(competition.nom)
    print("=" * len(competition.nom))
    print()

    print("Compétition locale :", competition.id)
    print("Identifiant IWWF   :", competition.iwwf_id)
    print()

    print("Sportifs inscrits  :", len(riders))
    print("Lignes entries     :", len(entries))
    print("Sportifs actifs    :", len(active_ids))
    print("Sportifs classés   :", len(classified_ids))
    print("Forfaits / absents :", len(withdrawn))
    print()

    print("Catégories :")

    for category, count in sorted(
        category_counts.items(),
        key=lambda item: str(item[0]),
    ):
        print(f"  {category}: {count}")

    print()
    print("Disciplines EMS :")

    for discipline, count in sorted(
        discipline_counts.items()
    ):
        print(f"  {discipline}: {count}")

    print()
    print(
        "Nombre de disciplines réelles par sportif :"
    )

    for discipline_count, rider_count in sorted(
        multidiscipline_counts.items()
    ):
        print(
            f"  {discipline_count} discipline(s): "
            f"{rider_count}"
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