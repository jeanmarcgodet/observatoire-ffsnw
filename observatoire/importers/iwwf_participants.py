from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup


@dataclass
class Participant:
    iwwf_id: str
    nom_complet: str
    nation: str
    categorie: str
    sexe: str
    annee_naissance: int | None


def extract_iwwf_id(href: str) -> str | None:
    query = parse_qs(urlparse(href).query)
    values = query.get("skier")

    if not values:
        return None

    return values[0].strip() or None


def parse_participants(html_file: Path) -> list[Participant]:
    html = html_file.read_text(
        encoding="utf-8",
        errors="ignore",
    )

    soup = BeautifulSoup(html, "html.parser")

    participants: list[Participant] = []

    for row in soup.find_all("tr"):
        cells = row.find_all("td")

        if len(cells) < 5:
            continue

        link = cells[0].find("a", href=True)

        if link is None:
            continue

        iwwf_id = extract_iwwf_id(link["href"])

        if iwwf_id is None:
            continue

        nom_complet = link.get_text(" ", strip=True)

        nation = cells[1].get_text(" ", strip=True).lstrip("*")

        categorie_sexe = cells[3].get_text(" ", strip=True)
        parts = categorie_sexe.rsplit(" ", 1)

        if len(parts) == 2:
            categorie, sexe = parts
        else:
            categorie = categorie_sexe
            sexe = ""

        annee_text = cells[4].get_text(" ", strip=True)

        try:
            annee_naissance = int(annee_text)
        except ValueError:
            annee_naissance = None

        participants.append(
            Participant(
                iwwf_id=iwwf_id,
                nom_complet=nom_complet,
                nation=nation,
                categorie=categorie,
                sexe=sexe,
                annee_naissance=annee_naissance,
            )
        )

    return participants