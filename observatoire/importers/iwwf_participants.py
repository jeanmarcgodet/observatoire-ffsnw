from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from datetime import datetime
from bs4 import BeautifulSoup


@dataclass
class Participant:
    iwwf_id: str
    nom: str
    prenom: str
    nation: str
    categorie: str
    sexe: str
    annee_naissance: int | None


@dataclass
class CompetitionMetadata:
    nom: str
    sous_titre: str | None
    lieu: str | None
    date_debut: str | None
    date_fin: str | None


def extract_iwwf_id(href: str) -> str | None:
    query = parse_qs(urlparse(href).query)
    values = query.get("skier")

    if not values:
        return None

    return values[0].strip() or None

def split_participant_name(full_name: str) -> tuple[str, str]:
    parts = full_name.strip().split(" ", maxsplit=1)

    if len(parts) == 1:
        return parts[0], ""

    return parts[0], parts[1]

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
        nom, prenom = split_participant_name(nom_complet)

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
                nom=nom,
                prenom=prenom,
                nation=nation,
                categorie=categorie,
                sexe=sexe,
                annee_naissance=annee_naissance,
            )
        )

    return participants

def parse_competition_metadata(html_file: Path) -> CompetitionMetadata:
    html = html_file.read_text(
        encoding="utf-8",
        errors="ignore",
    )

    soup = BeautifulSoup(html, "html.parser")

    title_element = soup.find("span", class_="PageTitle")
    subtitle_element = soup.find("span", class_="SubTitle")

    nom = (
        " ".join(title_element.get_text(" ", strip=True).split())
        if title_element
        else html_file.parent.name
    )


    sous_titre = (
        " ".join(subtitle_element.get_text(" ", strip=True).split())
        if subtitle_element
        else None
    )

    lieu = None
    date_debut = None
    date_fin = None

    if sous_titre and " - " in sous_titre:
        lieu, dates = sous_titre.rsplit(" - ", 1)

        date_parts = dates.split("/", 1)

    if len(date_parts) == 2:
        debut_jour = date_parts[0].strip()
        fin_complete = date_parts[1].strip()

        try:
            date_fin_obj = datetime.strptime(
                fin_complete,
                "%d %b %Y",
            )

            date_debut_obj = date_fin_obj.replace(
                day=int(debut_jour),
            )

            date_debut = date_debut_obj.date().isoformat()
            date_fin = date_fin_obj.date().isoformat()

        except (ValueError, TypeError):
            date_debut = debut_jour
            date_fin = fin_complete

    return CompetitionMetadata(
        nom=nom,
        sous_titre=sous_titre,
        lieu=lieu,
        date_debut=date_debut,
        date_fin=date_fin,
    )