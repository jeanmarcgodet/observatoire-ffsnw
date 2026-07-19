from observatoire.models import Competition
from observatoire.repositories import CompetitionRepository


def display_competition(competition: Competition) -> None:
    print(f"ID          : {competition.id}")
    print(f"Code IWWF   : {competition.iwwf_id}")
    print(f"Nom         : {competition.nom}")
    print(f"Lieu        : {competition.lieu}")
    print(f"Dates       : {competition.periode}")
    print(f"Discipline  : {competition.discipline}")


def main() -> None:
    repository = CompetitionRepository()

    print(f"Nombre total de compétitions : {repository.count()}")
    print()

    competitions = repository.list_all(limit=5)

    if not competitions:
        print("Aucune compétition trouvée.")
        return

    print("Première compétition")
    print("--------------------")
    display_competition(competitions[0])

    print()
    print("Recherche par identifiant interne")
    print("---------------------------------")

    selected = repository.get_by_id(competitions[0].id)

    if selected is not None:
        display_competition(selected)

    print()
    print("Recherche par identifiant IWWF")
    print("------------------------------")

    selected = repository.get_by_iwwf_id(competitions[0].iwwf_id)

    if selected is not None:
        display_competition(selected)

    print()
    print("Recherche « France »")
    print("--------------------")

    for competition in repository.search("France"):
        print(
            f"{competition.id:>3} | "
            f"{competition.iwwf_id:<12} | "
            f"{competition.nom} | "
            f"{competition.periode}"
        )


if __name__ == "__main__":
    main()
