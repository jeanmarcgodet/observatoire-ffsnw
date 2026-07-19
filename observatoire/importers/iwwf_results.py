from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup
from bs4.element import Tag


@dataclass(frozen=True)
class IWWFResult:
    iwwf_id: str
    nom_complet: str
    ligue: str | None
    categorie: str | None
    sexe: str | None
    discipline: str
    tour: str
    rang_classement: int | None
    score: str
    document_url: str | None
    fichier_source: str


def extract_iwwf_id(href: str | None) -> str | None:
    """Extrait l'identifiant IWWF du paramètre ?skier=..."""
    if not href:
        return None

    query = parse_qs(urlparse(href).query)
    values = query.get("skier")

    if not values:
        return None

    iwwf_id = values[0].strip()
    return iwwf_id or None


def normalize_text(value: str) -> str:
    return " ".join(value.replace("\xa0", " ").split())

def normalize_score(score: str) -> str:
    normalized = normalize_text(score)

    tie_break_pattern = re.compile(
        r"\s*\(Tie break:\s*([^)]+)\)",
        flags=re.IGNORECASE,
    )

    seen_tie_breaks: set[str] = set()
    tie_breaks: list[str] = []

    for match in tie_break_pattern.finditer(normalized):
        tie_break_score = normalize_text(match.group(1))

        if tie_break_score not in seen_tie_breaks:
            seen_tie_breaks.add(tie_break_score)
            tie_breaks.append(tie_break_score)

    main_score = tie_break_pattern.sub("", normalized).strip()

    if not tie_breaks:
        return main_score

    formatted_tie_breaks = " ".join(
        f"(Tie break: {tie_break_score})"
        for tie_break_score in tie_breaks
    )

    return f"{main_score} {formatted_tie_breaks}"

def normalize_header(value: str) -> str:
    return normalize_text(value).strip().lower()


def parse_integer(value: str) -> int | None:
    match = re.search(r"\d+", value)

    if match is None:
        return None

    return int(match.group())


def split_category_and_sex(
    value: str,
) -> tuple[str | None, str | None]:
    """
    Exemples :
        '-21 M' -> ('-21', 'M')
        'Ope F' -> ('Ope', 'F')
        '45+ M' -> ('45+', 'M')
    """
    normalized = normalize_text(value)

    if not normalized:
        return None, None

    match = re.match(r"^(.*?)(?:\s+([MF]))$", normalized, re.IGNORECASE)

    if match is None:
        return normalized, None

    categorie = match.group(1).strip() or None
    sexe = match.group(2).upper()

    return categorie, sexe


def detect_discipline(
    soup: BeautifulSoup,
    html_file: Path,
) -> str:
    """
    Détecte d'abord la discipline dans le contenu HTML,
    puis utilise le nom du fichier comme solution de repli.
    """
    page_text = normalize_text(soup.get_text(" ", strip=True)).lower()
    filename = html_file.name.lower()

    patterns = (
        ("slalom", "slalom"),
        ("tricks", "tricks"),
        ("trick", "tricks"),
        ("figures", "tricks"),
        ("jump", "jump"),
        ("saut", "jump"),
        ("overall", "overall"),
        ("combiné", "overall"),
        ("combine", "overall"),
    )

    # Le nom du fichier est souvent plus précis que le texte global,
    # qui peut contenir tous les liens du menu.
    for needle, discipline in patterns:
        if needle in filename:
            return discipline

    for needle, discipline in patterns:
        if re.search(
            rf"\b(?:men|women|boys|girls)?\s*{re.escape(needle)}\s+results?\b",
            page_text,
        ):
            return discipline

    raise ValueError(
        f"Discipline non reconnue dans le fichier : {html_file}"
    )


def get_direct_cells(row: Tag) -> list[Tag]:
    return row.find_all(["th", "td"], recursive=False)


def get_cell_text(cells: list[Tag], index: int) -> str:
    if index < 0 or index >= len(cells):
        return ""

    return normalize_text(cells[index].get_text(" ", strip=True))


def find_results_table(
    soup: BeautifulSoup,
) -> tuple[Tag, list[str]]:
    """
    Recherche une table contenant au minimum les colonnes
    Name et Categ.
    """
    for table in soup.find_all("table"):
        for row in table.find_all("tr"):
            cells = get_direct_cells(row)

            if not cells:
                continue

            headers = [
                normalize_text(cell.get_text(" ", strip=True))
                for cell in cells
            ]
            normalized = [normalize_header(value) for value in headers]

            if "name" in normalized and any(
                header in {"categ.", "categ", "category"}
                for header in normalized
            ):
                return table, headers

    raise RuntimeError("Aucune table de résultats reconnue")


def find_header_row(
    table: Tag,
) -> tuple[Tag, list[str]]:
    for row in table.find_all("tr"):
        cells = get_direct_cells(row)

        if not cells:
            continue

        headers = [
            normalize_text(cell.get_text(" ", strip=True))
            for cell in cells
        ]
        normalized = [normalize_header(value) for value in headers]

        if "name" in normalized and any(
            header in {"categ.", "categ", "category"}
            for header in normalized
        ):
            return row, headers

    raise RuntimeError("Ligne d'en-tête introuvable")


def find_column(
    headers: list[str],
    accepted_names: set[str],
) -> int:
    normalized = [normalize_header(value) for value in headers]

    for index, header in enumerate(normalized):
        if header in accepted_names:
            return index

    raise RuntimeError(
        f"Colonne introuvable parmi {sorted(accepted_names)}. "
        f"En-têtes détectés : {headers}"
    )


def is_score_column(
    index: int,
    header: str,
    category_index: int,
) -> bool:
    if index <= category_index:
        return False

    normalized = normalize_header(header)

    if not normalized:
        return False

    excluded = {
        "points",
        "total",
        "rank",
        "rang",
        "place",
        "remark",
        "remarks",
        "comment",
        "comments",
    }

    return normalized not in excluded


def parse_results_file(
    html_file: str | Path,
) -> list[IWWFResult]:
    path = Path(html_file)

    if not path.exists():
        raise FileNotFoundError(f"Fichier introuvable : {path}")

    html = path.read_text(
        encoding="utf-8",
        errors="ignore",
    )

    # Le parseur html.parser est volontairement utilisé :
    # les anciennes pages IWWF sont parfois mal formées.
    soup = BeautifulSoup(html, "html.parser")

    discipline = detect_discipline(soup, path)
    table, _ = find_results_table(soup)
    header_row, headers = find_header_row(table)

    name_index = find_column(headers, {"name"})
    league_index = find_column(
        headers,
        {"league", "federation", "nation", "country"},
    )
    category_index = find_column(
        headers,
        {"categ.", "categ", "category"},
    )

    score_columns = [
        (index, normalize_text(header))
        for index, header in enumerate(headers)
        if is_score_column(index, header, category_index)
    ]

    if not score_columns:
        raise RuntimeError(
            f"Aucune colonne de score détectée dans {path.name}. "
            f"En-têtes : {headers}"
        )

    all_rows = table.find_all("tr")
    header_position = all_rows.index(header_row)

    parsed: list[IWWFResult] = []

    for row in all_rows[header_position + 1 :]:
        cells = get_direct_cells(row)

        if len(cells) <= max(name_index, category_index):
            continue

        name_cell = cells[name_index]
        rider_link = name_cell.find("a", href=True)

        if rider_link is None:
            continue

        iwwf_id = extract_iwwf_id(rider_link.get("href"))

        if iwwf_id is None:
            continue

        nom_complet = normalize_text(
            rider_link.get_text(" ", strip=True)
        )

        if not nom_complet:
            continue

        rank_text = get_cell_text(cells, 0)
        rang_classement = parse_integer(rank_text)

        ligue_raw = get_cell_text(cells, league_index)
        ligue = ligue_raw.lstrip("*").strip() or None

        category_raw = get_cell_text(cells, category_index)
        categorie, sexe = split_category_and_sex(category_raw)

        for column_index, tour in score_columns:
            if column_index >= len(cells):
                continue

            score_cell = cells[column_index]
            score = normalize_score(
                score_cell.get_text(" ", strip=True)
        )

            if not score:
                continue

            score_link = score_cell.find("a", href=True)
            document_url = (
                score_link.get("href")
                if score_link is not None
                else None
            )

            parsed.append(
                IWWFResult(
                    iwwf_id=iwwf_id,
                    nom_complet=nom_complet,
                    ligue=ligue,
                    categorie=categorie,
                    sexe=sexe,
                    discipline=discipline,
                    tour=tour,
                    rang_classement=rang_classement,
                    score=score,
                    document_url=document_url,
                    fichier_source=path.name,
                )
            )

    return parsed