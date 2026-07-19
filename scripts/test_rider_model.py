from observatoire.models import Rider


def main():
    rider = Rider(
        id=1,
        iwwf_id="FRA692015508",
        nom="Anguenot",
        prenom="Ines",
    )

    print(rider)
    print(rider.nom_complet)
    print(rider.iwwf_id)


if __name__ == "__main__":
    main()