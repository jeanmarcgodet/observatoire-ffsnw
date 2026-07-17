from pathlib import Path

from observatoire.importers.iwwf_classic import parse_competition


URL = "https://www.iwwfed-ea.org/classic/26FRA021/"
HTML_FILE = Path("data/raw/iwwf/26FRA021.html")


if __name__ == "__main__":
    html = HTML_FILE.read_text(encoding="utf-8")
    competition = parse_competition(URL, html)

    print(f"Identifiant : {competition.iwwf_id}")
    print(f"Nom         : {competition.nom}")
    print(f"Lieu        : {competition.lieu}")
    print(f"Début       : {competition.date_debut}")
    print(f"Fin         : {competition.date_fin}")