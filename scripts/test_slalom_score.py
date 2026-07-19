from observatoire.models import SlalomScore
from observatoire.services import HistoryService


def test_parser() -> None:
    samples = [
        "1,50/55/11.25",
        "2,00/55/11.25 (Tie break: 3,00/55/11.25)",
        "4,00/55/12.00",
    ]

    print("Analyse des scores")
    print("------------------")

    for value in samples:
        score = SlalomScore.parse(value)

        if score is None:
            print(f"Score invalide : {value}")
            continue

        print(
            f"{value:<50} | "
            f"bouées={score.buoys} | "
            f"vitesse={score.speed} | "
            f"corde={score.rope_length}"
        )


def test_comparison() -> None:
    score_a = SlalomScore.parse("1,50/55/11.25")
    score_b = SlalomScore.parse("2,00/55/11.25")
    score_c = SlalomScore.parse("4,00/55/12.00")

    assert score_a is not None
    assert score_b is not None
    assert score_c is not None

    assert score_b.is_better_than(score_a)
    assert score_a.is_better_than(score_c)

    print()
    print("Comparaisons validées")
    print("---------------------")
    print(f"{score_b} est meilleur que {score_a}")
    print(f"{score_a} est meilleur que {score_c}")


def test_career() -> None:
    service = HistoryService()
    career = service.get_rider_career("FRA692015508")

    print()
    print("Meilleur score de la carrière")
    print("-----------------------------")

    if career is None:
        print("Rider introuvable.")
        return

    best_score = career.statistics.best_slalom_score()

    if best_score is None:
        print("Aucun score de slalom.")
        return

    print(f"Score          : {best_score.raw_value}")
    print(f"Bouées         : {best_score.buoys}")
    print(f"Vitesse        : {best_score.speed}")
    print(f"Longueur corde : {best_score.rope_length} m")


def main() -> None:
    test_parser()
    test_comparison()
    test_career()


if __name__ == "__main__":
    main()
