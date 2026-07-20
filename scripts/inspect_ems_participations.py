import argparse
from collections import Counter

from observatoire.importers.iwwf_ems_participations import (
    load_competition_participations,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Télécharge et inspecte les participations "
            "publiques d'une compétition EMS."
        )
    )

    parser.add_argument(
        "competition_id",
        help="UUID EMS de la compétition",
    )

    args = parser.parse_args()

    participants = load_competition_participations(
        args.competition_id
    )

    discipline_counts: Counter[str] = Counter()
    category_counts: Counter[str] = Counter()
    sex_counts: Counter[str] = Counter()

    for participant in participants:
        category_counts[participant.categorie] += 1

        if participant.sexe:
            sex_counts[participant.sexe] += 1

        for discipline in participant.disciplines:
            discipline_counts[discipline.discipline] += 1

        disciplines_text = ", ".join(
            (
                discipline.discipline
                if discipline.detail is None
                else (
                    f"{discipline.discipline}"
                    f" ({discipline.detail})"
                )
            )
            for discipline in participant.disciplines
        )

        print(
            f"{participant.nom_complet:<30} "
            f"{participant.categorie:<8} "
            f"{participant.sexe or '-'} "
            f"{participant.annee_naissance or '-'} "
            f"| {disciplines_text}"
        )

    print()
    print("Participants :", len(participants))
    print("Catégories   :", dict(category_counts))
    print("Sexes        :", dict(sex_counts))
    print("Disciplines  :", dict(discipline_counts))


if __name__ == "__main__":
    main()