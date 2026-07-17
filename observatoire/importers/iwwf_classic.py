import ssl
import html as html_module
import re
from dataclasses import dataclass
from datetime import datetime
from urllib.request import Request, urlopen

import certifi
from bs4 import BeautifulSoup


@dataclass(frozen=True)
class Competition:
    iwwf_id: str
    nom: str
    lieu: str
    date_debut: str
    date_fin: str
    url: str


def download_html(url: str) -> str:
    """Télécharge une page publique IWWF avec vérification HTTPS."""

    request = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 observatoire-ffsnw/0.1",
        },
    )

    ssl_context = ssl.create_default_context(cafile=certifi.where())

    with urlopen(
        request,
        timeout=30,
        context=ssl_context,
    ) as response:
        return response.read().decode("utf-8", errors="replace")


def extract_iwwf_id(url: str) -> str:
    """Extrait l’identifiant IWWF depuis l’URL."""

    return url.rstrip("/").split("/")[-1]


def parse_date_range(text: str) -> tuple[str, str]:
    """Convertit '17/19 Jul 2026' en deux dates ISO."""

    parts = text.strip().split()

    if len(parts) != 3 or "/" not in parts[0]:
        raise ValueError(f"Format de dates non reconnu : {text!r}")

    first_day, last_day = parts[0].split("/")
    month = parts[1]
    year = parts[2]

    start_date = datetime.strptime(
        f"{first_day} {month} {year}",
        "%d %b %Y",
    ).date()

    end_date = datetime.strptime(
        f"{last_day} {month} {year}",
        "%d %b %Y",
    ).date()

    return start_date.isoformat(), end_date.isoformat()


def parse_competition(url: str, html: str) -> Competition:
    """Analyse la page principale d’une compétition IWWF Classic."""

    name_match = re.search(
        r'<span\s+class=["\']PageTitle["\'][^>]*>(.*?)</span>',
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )

    detail_matches = re.findall(
        r'<span\s+class=["\']SubTitle["\'][^>]*>(.*?)</span>',
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )

    if name_match is None:
        raise ValueError("Nom de la compétition introuvable dans le HTML brut.")

    nom = BeautifulSoup(
        html_module.unescape(name_match.group(1)),
        "html.parser",
    ).get_text(" ", strip=True)

    nom = " ".join(nom.split())

    detail_text = None

    for raw_detail in detail_matches:
        candidate = BeautifulSoup(
            html_module.unescape(raw_detail),
            "html.parser",
        ).get_text(" ", strip=True)

        candidate = " ".join(candidate.split())

        if re.search(
            r"\d{1,2}/\d{1,2}\s+"
            r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
            r"\s+\d{4}",
            candidate,
            flags=re.IGNORECASE,
        ):
            detail_text = candidate
            break

    if detail_text is None:
        raise ValueError("Lieu et dates introuvables dans le HTML brut.")

    if " - " not in detail_text:
        raise ValueError(
            f"Format lieu/dates non reconnu : {detail_text!r}"
        )

    lieu, date_text = detail_text.rsplit(" - ", maxsplit=1)
    date_debut, date_fin = parse_date_range(date_text)

    return Competition(
        iwwf_id=extract_iwwf_id(url),
        nom=nom,
        lieu=lieu.strip(),
        date_debut=date_debut,
        date_fin=date_fin,
        url=url,
    )


def load_competition(url: str) -> Competition:
    """Télécharge puis analyse une compétition IWWF."""

    html = download_html(url)
    return parse_competition(url, html)