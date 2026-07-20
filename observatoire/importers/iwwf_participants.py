from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup


CATEGORY_MAP = {'Ope': 'Open', '-21': 'U21', '-18': 'U18', '-14': 'U14', 'OPEN': 'Open', 'open': 'Open', '-10': 'U10', '-12': 'U12', '-17': 'U17', '-8': 'U8', '- 8': 'U8', '8': 'U8'}


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


def normalize_category(category: str) -> str:
    normalized = category.strip()

    return CATEGORY_MAP.get(normalized, normalized)


def parse_participants(
    html_file: Path,
) -> list[Participant]:
    html = html_file.read_text(
        encoding="utf-8",
        errors="ignore",
    )

    soup = BeautifulSoup(html, "html.parser")
    participants: list[Participant] = []

    category_aliases = {'Ope': 'Open',
     'OPEN': 'Open',
     'open': 'Open',
     '-10': 'U10',
     '-12': 'U12',
     '-14': 'U14',
     '-17': 'U17',
     '-18': 'U18',
     '-21': 'U21',
     '-8': 'U8',
     '- 8': 'U8',
     '8': 'U8'}

    dataclass_fields = set(Participant.__dataclass_fields__)

    for row in soup.find_all("tr"):
        cells = row.find_all("td", recursive=False)

        if len(cells) < 2:
            continue

        link = cells[0].find("a", href=True, recursive=False)

        if link is None:
            continue

        iwwf_id = extract_iwwf_id(link.get("href"))

        if iwwf_id is None:
            continue

        full_name = " ".join(link.get_text(" ", strip=True).split())

        if not full_name:
            continue

        values = [" ".join(cell.get_text(" ", strip=True).split()) for cell in cells]

        raw_category: str | None = None
        sexe: str | None = None

        for value in values[1:6]:
            parts = value.rsplit(" ", maxsplit=1)

            if len(parts) != 2:
                continue

            candidate_category = parts[0].strip()
            candidate_sex = parts[1].strip().upper()

            if candidate_category and candidate_sex in {"M", "F"}:
                raw_category = candidate_category
                sexe = candidate_sex
                break

        if raw_category is None:
            continue

        categorie = category_aliases.get(raw_category, raw_category)

        annee_naissance: int | None = None

        for value in values[1:7]:
            if len(value) == 4 and value.isdigit():
                year = int(value)
                if 1900 <= year <= 2100:
                    annee_naissance = year
                    break

        nation = (
            iwwf_id[:3].upper()
            if len(iwwf_id) >= 3 and iwwf_id[:3].isalpha()
            else ""
        )

        kwargs = {
            "iwwf_id": iwwf_id,
            "nation": nation,
            "categorie": categorie,
            "sexe": sexe,
            "annee_naissance": annee_naissance,
        }

        if "nom_complet" in dataclass_fields:
            kwargs["nom_complet"] = full_name
        else:
            nom, separator, prenom = full_name.partition(" ")
            kwargs["nom"] = nom
            kwargs["prenom"] = prenom if separator else ""

        participants.append(Participant(**kwargs))

    return participants


def parse_startlist_participants(
    html_file: Path,
) -> list[Participant]:
    """
    Extrait les participants d'une page IWWF *_startlist.html.

    Lorsque la page ne contient pas de colonne Categ.,
    la cat?gorie et ?ventuellement le sexe sont d?duits
    du nom du fichier.
    """
    html = html_file.read_text(
        encoding="utf-8",
        errors="ignore",
    )

    soup = BeautifulSoup(html, "html.parser")

    category_prefixes = {
        "10": "U10",
        "12": "U12",
        "14": "U14",
        "17": "U17",
        "18": "U18",
        "21": "U21",
        "35": "35+",
        "45": "45+",
        "55": "55+",
        "65": "65+",
        "70": "70+",
        "75": "75+",
        "80": "80+",
        "85": "85+",
    }

    filename_parts = (
        html_file.stem
        .lower()
        .split("_")
    )

    inferred_category: str | None = None
    inferred_sex = ""

    if filename_parts:
        first = filename_parts[0]
        second = (
            filename_parts[1]
            if len(filename_parts) > 1
            else ""
        )

        # Les fichiers 65_70_75_* ou
        # 35_45_55_* regroupent plusieurs cat?gories :
        # aucune cat?gorie individuelle n'est alors d?duite.
        categories_in_filename = {
            part
            for part in filename_parts
            if part in category_prefixes
        }

        grouped_categories = (
            len(categories_in_filename) > 1
        )

        if (
            first in category_prefixes
            and not grouped_categories
        ):
            inferred_category = category_prefixes[first]

            if second in {"m", "f"}:
                inferred_sex = second.upper()

    participant_table = None
    header_row = None
    headers: list[str] = []

    for table in soup.find_all("table"):
        direct_rows = [
            row
            for row in table.find_all("tr")
            if row.find_parent("table") is table
        ]

        for row in direct_rows:
            cells = row.find_all(
                ["th", "td"],
                recursive=False,
            )

            row_headers = [
                " ".join(
                    cell.get_text(
                        " ",
                        strip=True,
                    ).split()
                )
                for cell in cells
            ]

            normalized_headers = [
                header.strip().lower()
                for header in row_headers
            ]

            has_name = "name" in normalized_headers

            has_category = any(
                header in {
                    "categ.",
                    "categ",
                    "category",
                }
                for header in normalized_headers
            )

            if (
                has_name
                and (
                    has_category
                    or inferred_category is not None
                )
            ):
                participant_table = table
                header_row = row
                headers = row_headers
                break

        if participant_table is not None:
            break

    if (
        participant_table is None
        or header_row is None
    ):
        return []

    normalized_headers = [
        header.strip().lower()
        for header in headers
    ]

    name_index = normalized_headers.index("name")

    category_index = next(
        (
            index
            for index, header
            in enumerate(normalized_headers)
            if header in {
                "categ.",
                "categ",
                "category",
            }
        ),
        None,
    )

    rows = [
        row
        for row in participant_table.find_all("tr")
        if row.find_parent("table")
        is participant_table
    ]

    header_position = rows.index(header_row)
    participants: list[Participant] = []

    for row in rows[header_position + 1 :]:
        cells = row.find_all(
            ["th", "td"],
            recursive=False,
        )

        required_indexes = [name_index]

        if category_index is not None:
            required_indexes.append(category_index)

        if len(cells) <= max(required_indexes):
            continue

        name_cell = cells[name_index]
        link = name_cell.find("a", href=True)

        if link is None:
            continue

        iwwf_id = extract_iwwf_id(link["href"])

        if iwwf_id is None:
            continue

        nom_complet = " ".join(
            link.get_text(
                " ",
                strip=True,
            ).split()
        )

        if not nom_complet:
            continue

        nom, prenom = split_participant_name(
            nom_complet
        )

        if category_index is not None:
            categorie_sexe = " ".join(
                cells[category_index]
                .get_text(
                    " ",
                    strip=True,
                )
                .split()
            )

            parts = categorie_sexe.rsplit(
                " ",
                1,
            )

            if (
                len(parts) == 2
                and parts[1].strip().upper()
                in {"M", "F"}
            ):
                categorie = parts[0]
                sexe = parts[1]
            else:
                categorie = categorie_sexe
                sexe = inferred_sex
        else:
            categorie = inferred_category or ""
            sexe = inferred_sex

        categorie = normalize_category(
            categorie
        )
        sexe = sexe.strip().upper()

        if not categorie:
            continue

        nation = (
            iwwf_id[:3]
            if len(iwwf_id) >= 3
            else ""
        )

        participants.append(
            Participant(
                iwwf_id=iwwf_id,
                nom=nom,
                prenom=prenom,
                nation=nation,
                categorie=categorie,
                sexe=sexe,
                annee_naissance=None,
            )
        )

    return participants


def parse_competition_metadata(
    html_file: Path,
) -> CompetitionMetadata:
    html = html_file.read_text(
        encoding="utf-8",
        errors="ignore",
    )

    soup = BeautifulSoup(html, "html.parser")

    title_element = soup.find("span", class_="PageTitle")
    subtitle_element = soup.find("span", class_="SubTitle")

    nom = (
        " ".join(
            title_element.get_text(" ", strip=True).split()
        )
        if title_element
        else html_file.parent.name
    )

    sous_titre = (
        " ".join(
            subtitle_element.get_text(" ", strip=True).split()
        )
        if subtitle_element
        else None
    )

    lieu = None
    date_debut = None
    date_fin = None
    date_parts: list[str] = []

    if sous_titre and " - " in sous_titre:
        lieu, dates = sous_titre.rsplit(" - ", 1)
        lieu = lieu.strip()
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