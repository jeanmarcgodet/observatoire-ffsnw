"""Téléchargement des pages d'une compétition IWWF Classic.

Le téléchargeur démarre depuis la page publique de la compétition :

    https://www.iwwfed-ea.org/classic/26FRA021/

Cette page contient les liens vers les différentes vues de la compétition,
servies par l'endpoint :

    https://www.iwwfed-ea.org/competition.php
        ?cc=T-26FRA021
        &page=...

Le module découvre automatiquement les pages appartenant à la compétition,
les télécharge et les archive dans :

    data/raw/iwwf/<code_competition>/

Ce module ne réalise aucun import dans SQLite.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from collections import deque
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Final
from urllib.parse import parse_qs, urlencode, urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

LOGGER = logging.getLogger(__name__)

DEFAULT_SITE_ROOT: Final[str] = "https://www.iwwfed-ea.org"
DEFAULT_COMPETITION_ENDPOINT: Final[str] = (
    "https://www.iwwfed-ea.org/competition.php"
)
DEFAULT_OUTPUT_ROOT: Final[Path] = Path("data/raw/iwwf")

DEFAULT_TIMEOUT_SECONDS: Final[float] = 30.0
DEFAULT_DELAY_SECONDS: Final[float] = 0.35
DEFAULT_MAX_PAGES: Final[int] = 300

COMPETITION_CODE_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^[0-9]{2}[A-Z]{3}[0-9]{3}$"
)

SAFE_FILENAME_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"[^A-Za-z0-9._-]+"
)

IGNORED_URL_PREFIXES: Final[tuple[str, ...]] = (
    "javascript:",
    "mailto:",
    "tel:",
    "#",
)


class IWWFDownloadError(RuntimeError):
    """Erreur rencontrée pendant le téléchargement IWWF."""


@dataclass(frozen=True)
class DownloadedPage:
    """Métadonnées d'une page HTML archivée."""

    page: str
    url: str
    filename: str
    status_code: int
    content_type: str
    size_bytes: int
    sha256: str
    downloaded_at: str
    discovered_from: str | None
    reused: bool


@dataclass(frozen=True)
class DownloadReport:
    """Rapport final du téléchargement d'une compétition."""

    competition_code: str
    competition_key: str
    source_url: str
    output_directory: str
    started_at: str
    completed_at: str
    pages_discovered: int
    pages_downloaded: int
    pages_reused: int
    pages_failed: int
    manifest_path: str
    pages: tuple[DownloadedPage, ...]
    errors: tuple[str, ...]


def normalize_competition_code(raw_code: str) -> str:
    """Normalise et valide un code de compétition IWWF.

    Les formats suivants sont acceptés :

    - 26FRA021
    - T-26FRA021
    """

    code = raw_code.strip().upper()

    if code.startswith("T-"):
        code = code[2:]

    if not COMPETITION_CODE_PATTERN.fullmatch(code):
        raise ValueError(
            "Code de compétition IWWF invalide. "
            "Format attendu : 26FRA021."
        )

    return code


def build_competition_key(competition_code: str) -> str:
    """Construit la valeur du paramètre cc attendue par le site."""

    return f"T-{normalize_competition_code(competition_code)}"


def build_competition_home_url(
    competition_code: str,
    *,
    site_root: str = DEFAULT_SITE_ROOT,
) -> str:
    """Construit l'URL publique d'entrée d'une compétition."""

    normalized_code = normalize_competition_code(competition_code)
    root = site_root.rstrip("/")

    return f"{root}/classic/{normalized_code}/"


def build_competition_page_url(
    competition_code: str,
    *,
    page: str,
    endpoint: str = DEFAULT_COMPETITION_ENDPOINT,
) -> str:
    """Construit l'URL canonique d'une vue de compétition."""

    normalized_code = normalize_competition_code(competition_code)
    competition_key = build_competition_key(normalized_code)

    parsed_endpoint = urlparse(endpoint)

    query = urlencode(
        [
            ("cc", competition_key),
            ("page", page),
        ]
    )

    return urlunparse(
        (
            parsed_endpoint.scheme,
            parsed_endpoint.netloc,
            parsed_endpoint.path,
            "",
            query,
            "",
        )
    )


def create_http_session(
    *,
    user_agent: str = "observatoire-ffsnw/0.1",
    retry_total: int = 4,
    retry_backoff_factor: float = 0.8,
) -> requests.Session:
    """Crée une session HTTP avec reprises automatiques."""

    retry_policy = Retry(
        total=retry_total,
        connect=retry_total,
        read=retry_total,
        status=retry_total,
        allowed_methods=frozenset({"GET", "HEAD"}),
        status_forcelist=(408, 425, 429, 500, 502, 503, 504),
        backoff_factor=retry_backoff_factor,
        respect_retry_after_header=True,
        raise_on_status=False,
    )

    adapter = HTTPAdapter(
        max_retries=retry_policy,
        pool_connections=4,
        pool_maxsize=4,
    )

    session = requests.Session()

    session.headers.update(
        {
            "User-Agent": user_agent,
            "Accept": (
                "text/html,application/xhtml+xml,"
                "application/xml;q=0.9,*/*;q=0.8"
            ),
            "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
            "Connection": "keep-alive",
        }
    )

    session.mount("https://", adapter)
    session.mount("http://", adapter)

    return session


def discover_competition_links(
    html: str,
    *,
    current_url: str,
    competition_code: str,
    endpoint: str = DEFAULT_COMPETITION_ENDPOINT,
) -> dict[str, str]:
    """Découvre les vues appartenant à la compétition.

    Les liens conservés doivent :

    - pointer vers competition.php ;
    - contenir le bon paramètre cc ;
    - contenir un paramètre page non vide.
    """

    normalized_code = normalize_competition_code(competition_code)
    expected_competition_key = build_competition_key(normalized_code)

    parsed_endpoint = urlparse(endpoint)
    expected_host = parsed_endpoint.netloc.lower()
    expected_path = parsed_endpoint.path.rstrip("/").lower()

    soup = BeautifulSoup(html, "html.parser")
    discovered: dict[str, str] = {}

    for anchor in soup.find_all("a", href=True):
        raw_href = str(anchor.get("href", "")).strip()

        if not raw_href:
            continue

        if raw_href.lower().startswith(IGNORED_URL_PREFIXES):
            continue

        absolute_url = urljoin(current_url, raw_href)
        parsed_url = urlparse(absolute_url)

        if parsed_url.netloc.lower() != expected_host:
            continue

        if parsed_url.path.rstrip("/").lower() != expected_path:
            continue

        query = parse_qs(
            parsed_url.query,
            keep_blank_values=True,
        )

        competition_values = query.get("cc", [])

        if not competition_values:
            continue

        linked_competition_key = competition_values[0].strip().upper()

        if linked_competition_key != expected_competition_key:
            continue

        page_values = query.get("page", [])

        if not page_values:
            continue

        page_name = page_values[0].strip()

        if not page_name:
            continue

        canonical_url = build_competition_page_url(
            normalized_code,
            page=page_name,
            endpoint=endpoint,
        )

        discovered.setdefault(page_name, canonical_url)

    return discovered


def make_page_filename(page_name: str) -> str:
    """Transforme un identifiant de page en nom de fichier sûr."""

    normalized_name = page_name.strip() or "page"
    normalized_name = SAFE_FILENAME_PATTERN.sub("_", normalized_name)
    normalized_name = normalized_name.strip("._-")

    if not normalized_name:
        normalized_name = "page"

    return f"{normalized_name}.html"


def sha256_bytes(content: bytes) -> str:
    """Calcule l'empreinte SHA-256 d'un contenu binaire."""

    return hashlib.sha256(content).hexdigest()


def utc_now_iso() -> str:
    """Retourne la date et l'heure UTC au format ISO 8601."""

    return datetime.now(UTC).isoformat(timespec="seconds")


def write_bytes_atomically(destination: Path, content: bytes) -> None:
    """Écrit un fichier de manière atomique."""

    destination.parent.mkdir(parents=True, exist_ok=True)

    temporary_path = destination.with_suffix(
        destination.suffix + ".tmp"
    )

    temporary_path.write_bytes(content)
    temporary_path.replace(destination)


def write_json_atomically(destination: Path, payload: object) -> None:
    """Écrit un document JSON UTF-8 de manière atomique."""

    serialized = json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
        sort_keys=False,
    )

    write_bytes_atomically(
        destination,
        serialized.encode("utf-8"),
    )


class IWWFCompetitionDownloader:
    """Télécharge les pages accessibles d'une compétition IWWF."""

    def __init__(
        self,
        *,
        output_root: Path = DEFAULT_OUTPUT_ROOT,
        site_root: str = DEFAULT_SITE_ROOT,
        endpoint: str = DEFAULT_COMPETITION_ENDPOINT,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        delay_seconds: float = DEFAULT_DELAY_SECONDS,
        max_pages: int = DEFAULT_MAX_PAGES,
        overwrite: bool = False,
        session: requests.Session | None = None,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError(
                "Le délai d'attente HTTP doit être strictement positif."
            )

        if delay_seconds < 0:
            raise ValueError(
                "Le délai entre deux requêtes ne peut pas être négatif."
            )

        if max_pages <= 0:
            raise ValueError(
                "Le nombre maximal de pages doit être strictement positif."
            )

        self.output_root = Path(output_root)
        self.site_root = site_root
        self.endpoint = endpoint
        self.timeout_seconds = timeout_seconds
        self.delay_seconds = delay_seconds
        self.max_pages = max_pages
        self.overwrite = overwrite
        self.session = session or create_http_session()
        self._owns_session = session is None

    def __enter__(self) -> IWWFCompetitionDownloader:
        return self

    def __exit__(
        self,
        exc_type: object,
        exc: object,
        traceback: object,
    ) -> None:
        self.close()

    def close(self) -> None:
        """Ferme la session HTTP créée par le téléchargeur."""

        if self._owns_session:
            self.session.close()

    def download(self, competition_code: str) -> DownloadReport:
        """Télécharge les pages découvertes pour une compétition."""

        normalized_code = normalize_competition_code(competition_code)
        competition_key = build_competition_key(normalized_code)

        output_directory = self.output_root / normalized_code
        output_directory.mkdir(parents=True, exist_ok=True)

        source_url = build_competition_home_url(
            normalized_code,
            site_root=self.site_root,
        )

        started_at = utc_now_iso()

        pending: deque[tuple[str, str, str | None]] = deque(
            [
                (
                    "index",
                    source_url,
                    None,
                )
            ]
        )

        queued_pages: set[str] = {"index"}
        processed_pages: set[str] = set()

        archived_pages: list[DownloadedPage] = []
        errors: list[str] = []

        pages_downloaded = 0
        pages_reused = 0
        pages_failed = 0

        while pending:
            if len(processed_pages) >= self.max_pages:
                errors.append(
                    "Limite de sécurité atteinte : "
                    f"{self.max_pages} pages maximum."
                )
                break

            page_name, page_url, discovered_from = pending.popleft()

            if page_name in processed_pages:
                continue

            processed_pages.add(page_name)

            filename = make_page_filename(page_name)
            destination = output_directory / filename

            try:
                page_metadata, html = self._download_page(
                    page_name=page_name,
                    page_url=page_url,
                    destination=destination,
                    discovered_from=discovered_from,
                )
            except IWWFDownloadError as exc:
                pages_failed += 1

                message = f"{page_name}: {exc}"
                errors.append(message)

                LOGGER.error("%s", message)
                continue

            archived_pages.append(page_metadata)

            if page_metadata.reused:
                pages_reused += 1
            else:
                pages_downloaded += 1

            discovered_links = discover_competition_links(
                html,
                current_url=page_url,
                competition_code=normalized_code,
                endpoint=self.endpoint,
            )

            for discovered_page, discovered_url in sorted(
                discovered_links.items(),
                key=lambda item: item[0].lower(),
            ):
                if discovered_page in queued_pages:
                    continue

                queued_pages.add(discovered_page)

                pending.append(
                    (
                        discovered_page,
                        discovered_url,
                        page_name,
                    )
                )

            if pending and self.delay_seconds > 0:
                time.sleep(self.delay_seconds)

        completed_at = utc_now_iso()
        manifest_path = output_directory / "manifest.json"

        report = DownloadReport(
            competition_code=normalized_code,
            competition_key=competition_key,
            source_url=source_url,
            output_directory=str(output_directory),
            started_at=started_at,
            completed_at=completed_at,
            pages_discovered=len(queued_pages),
            pages_downloaded=pages_downloaded,
            pages_reused=pages_reused,
            pages_failed=pages_failed,
            manifest_path=str(manifest_path),
            pages=tuple(archived_pages),
            errors=tuple(errors),
        )

        write_json_atomically(
            manifest_path,
            {
                **asdict(report),
                "pages": [
                    asdict(page)
                    for page in report.pages
                ],
                "errors": list(report.errors),
            },
        )

        return report

    def _download_page(
        self,
        *,
        page_name: str,
        page_url: str,
        destination: Path,
        discovered_from: str | None,
    ) -> tuple[DownloadedPage, str]:
        """Télécharge une page ou réutilise le fichier déjà présent."""

        downloaded_at = utc_now_iso()
        reused = destination.exists() and not self.overwrite

        if reused:
            LOGGER.info("Réutilisation : %s", destination)

            try:
                content = destination.read_bytes()
            except OSError as exc:
                raise IWWFDownloadError(
                    f"impossible de lire le fichier local "
                    f"{destination}: {exc}"
                ) from exc

            if not content.strip():
                raise IWWFDownloadError(
                    f"le fichier local {destination} est vide"
                )

            status_code = 200
            content_type = "text/html; source=local"

        else:
            LOGGER.info("Téléchargement : %s", page_url)

            try:
                response = self.session.get(
                    page_url,
                    timeout=self.timeout_seconds,
                    allow_redirects=True,
                )
            except requests.RequestException as exc:
                raise IWWFDownloadError(
                    f"échec de la requête HTTP vers "
                    f"{page_url}: {exc}"
                ) from exc

            status_code = response.status_code
            content_type = response.headers.get(
                "Content-Type",
                "",
            )

            if response.status_code != requests.codes.ok:
                raise IWWFDownloadError(
                    f"réponse HTTP {response.status_code} "
                    f"pour {page_url}"
                )

            if not self._is_html_response(response):
                raise IWWFDownloadError(
                    "la réponse reçue n'est pas une page HTML "
                    f"(Content-Type : {content_type or 'absent'})"
                )

            content = response.content

            if not content.strip():
                raise IWWFDownloadError(
                    "la page reçue est vide"
                )

            try:
                write_bytes_atomically(
                    destination,
                    content,
                )
            except OSError as exc:
                raise IWWFDownloadError(
                    f"impossible d'enregistrer "
                    f"{destination}: {exc}"
                ) from exc

        html = self._decode_html(content)

        metadata = DownloadedPage(
            page=page_name,
            url=page_url,
            filename=destination.name,
            status_code=status_code,
            content_type=content_type,
            size_bytes=len(content),
            sha256=sha256_bytes(content),
            downloaded_at=downloaded_at,
            discovered_from=discovered_from,
            reused=reused,
        )

        return metadata, html

    @staticmethod
    def _is_html_response(response: requests.Response) -> bool:
        """Vérifie qu'une réponse HTTP contient vraisemblablement du HTML."""

        content_type = response.headers.get(
            "Content-Type",
            "",
        ).lower()

        if "text/html" in content_type:
            return True

        if "application/xhtml+xml" in content_type:
            return True

        content_prefix = response.content[:512].lstrip().lower()

        return content_prefix.startswith(
            (
                b"<!doctype html",
                b"<html",
                b"<?xml",
            )
        )

    @staticmethod
    def _decode_html(content: bytes) -> str:
        """Décode une page HTML en texte."""

        for encoding in (
            "utf-8",
            "cp1252",
            "iso-8859-1",
        ):
            try:
                return content.decode(encoding)
            except UnicodeDecodeError:
                continue

        return content.decode(
            "utf-8",
            errors="replace",
        )


def download_competition(
    competition_code: str,
    *,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    site_root: str = DEFAULT_SITE_ROOT,
    endpoint: str = DEFAULT_COMPETITION_ENDPOINT,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    delay_seconds: float = DEFAULT_DELAY_SECONDS,
    max_pages: int = DEFAULT_MAX_PAGES,
    overwrite: bool = False,
) -> DownloadReport:
    """Télécharge et archive une compétition complète."""

    with IWWFCompetitionDownloader(
        output_root=output_root,
        site_root=site_root,
        endpoint=endpoint,
        timeout_seconds=timeout_seconds,
        delay_seconds=delay_seconds,
        max_pages=max_pages,
        overwrite=overwrite,
    ) as downloader:
        return downloader.download(competition_code)

