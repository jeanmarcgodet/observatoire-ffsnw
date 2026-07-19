from observatoire.models import Rider
from observatoire.repositories.rider_repository import RiderRepository


def display_rider(rider: Rider) -> None:
    """Affiche un rider de manière lisible."""
    print(
        f"{rider.id:>3} | "
        f"{rider.iwwf_id:<16} | "
        f"{rider.nom_complet}"
    )


def main() -> None:
    repository = RiderRepository()

    print(f"Nombre total de riders : {repository.count()}")

    print()
    print("Recherche « Anguenot »")
    print("----------------------")

    riders = repository.search("Anguenot")

    if not riders:
        print("Aucun rider trouvé.")
        return

    for rider in riders:
        display_rider(rider)

    selected_rider = repository.get_by_id(riders[0].id)

    print()
    print("Recherche par identifiant interne")
    print("---------------------------------")

    if selected_rider is not None:
        display_rider(selected_rider)

    iwwf_id = riders[0].iwwf_id
    selected_rider = repository.get_by_iwwf_id(iwwf_id)

    print()
    print("Recherche par identifiant IWWF")
    print("------------------------------")

    if selected_rider is not None:
        display_rider(selected_rider)


if __name__ == "__main__":
    main()