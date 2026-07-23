"""Consolide le diagnostic de la filière compétitive U21 -> Open.

Le script ne remplace aucun fichier d'analyse existant. Il construit une
sortie de référence à partir des modules déjà validés :

- effectifs Open aux Championnats 2017-2026 ;
- sortie U21 vers Open ;
- persistance Open à horizons comparables ;
- comparaison selon l'origine U21 sur fenêtre complète ;
- fonction et fragmentation du calendrier EMS 2023-2025 ;
- captation du vivier français par le code précis du Championnat Open ;
- continuité aval Open vers Senior.

Sorties
-------
data/processed/indicateurs_consolides_filiere_open_2017_2026.csv
data/exports/diagnostic_consolide_filiere_open_2017_2026.txt
data/exports/references_perimees_championnat_open.txt
reports/rapport_filiere_open_2017_2026_v1.md
"""

from __future__ import annotations

import csv
import math
import re
from collections import defaultdict
from pathlib import Path
from typing import Iterable


YEARS_EMS = (2023, 2024, 2025)
EXACT_OPEN_CHAMPIONSHIP_CODES = {
    2023: "23FRA018",
    2024: "24FRA027",
    2025: "25FRA206",
}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(path)

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
        errors="replace",
    ) as handle:
        sample = handle.read(8192)
        handle.seek(0)
        try:
            delimiter = csv.Sniffer().sniff(
                sample,
                delimiters=";,\t",
            ).delimiter
        except csv.Error:
            delimiter = ";"
        return list(csv.DictReader(handle, delimiter=delimiter))


def write_csv(
    path: Path,
    rows: Iterable[dict[str, object]],
    fields: list[str],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fields,
            delimiter=";",
        )
        writer.writeheader()
        writer.writerows(rows)


def integer(value: object) -> int | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return int(float(text.replace(",", ".")))
    except ValueError:
        return None


def number(value: object) -> float | None:
    text = str(value or "").strip().replace(",", ".")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def flag(value: object) -> bool:
    parsed = integer(value)
    return parsed == 1


def percentage(numerator: int, denominator: int) -> float:
    return round(100 * numerator / denominator, 1) if denominator else 0.0


def format_fr(value: object, decimals: int = 1) -> str:
    if value is None or value == "":
        return "n.d."
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if math.isclose(value, round(value)):
            return str(int(round(value)))
        return f"{value:.{decimals}f}".replace(".", ",")
    return str(value).replace(".", ",")


def require_single(
    rows: list[dict[str, str]],
    predicate,
    label: str,
) -> dict[str, str]:
    matches = [row for row in rows if predicate(row)]
    if len(matches) != 1:
        raise RuntimeError(
            f"{label}: une ligne attendue, {len(matches)} trouvée(s)."
        )
    return matches[0]


def add_indicator(
    output: list[dict[str, object]],
    *,
    section: str,
    code: str,
    period: str,
    label: str,
    numerator: int | None = None,
    denominator: int | None = None,
    value: float | int | None = None,
    unit: str,
    scope: str,
    source: str,
    interpretation: str,
    status: str = "VALIDE",
) -> None:
    if value is None and numerator is not None and denominator is not None:
        value = percentage(numerator, denominator)

    output.append(
        {
            "Section": section,
            "IndicatorCode": code,
            "Period": period,
            "Label": label,
            "Numerator": "" if numerator is None else numerator,
            "Denominator": "" if denominator is None else denominator,
            "Value": "" if value is None else value,
            "Unit": unit,
            "Scope": scope,
            "Source": source,
            "Interpretation": interpretation,
            "Status": status,
        }
    )


def search_stale_references(root: Path) -> list[tuple[Path, list[str]]]:
    targets: list[tuple[re.Pattern[str], str]] = [
        (
            re.compile(r"\b21\s*/\s*41\b"),
            "ancienne captation 2023 fondée sur 21/41",
        ),
        (
            re.compile(r"\b51[,.]2\s*%"),
            "ancien taux de captation 2023 de 51,2 %",
        ),
        (
            re.compile(r"OpenChampionshipParticipation"),
            "ancien indicateur large OpenChampionshipParticipation",
        ),
    ]

    matches: list[tuple[Path, list[str]]] = []
    roots = [root / "data/exports", root / "reports"]

    for folder in roots:
        if not folder.exists():
            continue
        for path in sorted(folder.rglob("*")):
            if path.suffix.lower() not in {".txt", ".md", ".csv"}:
                continue
            try:
                text = path.read_text(
                    encoding="utf-8-sig",
                    errors="replace",
                )
            except OSError:
                continue

            reasons = [
                label
                for pattern, label in targets
                if pattern.search(text)
            ]
            if reasons:
                matches.append((path, reasons))

    return matches


def main() -> None:
    root = repo_root()
    processed = root / "data/processed"
    exports = root / "data/exports"
    reports = root / "reports"

    annual_open = read_csv(
        processed / "renouvellement_open_championnats_2017_2026.csv"
    )
    u21_cohorts = read_csv(
        processed / "cohortes_sortie_u21_vers_open_2017_2026.csv"
    )
    persistence_summary = read_csv(
        processed / "persistance_open_selon_origine_u21_2018_2023.csv"
    )
    strict_u21_persistence = read_csv(
        processed / "persistance_open_u21_fenetre_complete_2020_2023.csv"
    )
    ems_register = read_csv(
        processed / "registre_filiere_open_ems_2023_2025.csv"
    )
    calendar_competitions = read_csv(
        processed / "fonction_competitions_open_ems_2023_2025.csv"
    )
    calendar_fragmentation = read_csv(
        processed / "fragmentation_calendrier_open_ems_2023_2025.csv"
    )
    calendar_retention = read_csv(
        processed / "retention_open_selon_intensite_ems_2023_2024.csv"
    )
    exact_capture = read_csv(
        processed
        / "audit_perimetre_championnat_open_nationalite_2023_2025.csv"
    )
    senior_continuity = read_csv(
        processed / "continuite_open_senior_horizons_2017_2026.csv"
    )
    senior_overlap = read_csv(
        processed / "chevauchements_open_senior_2017_2026.csv"
    )

    indicators: list[dict[str, object]] = []

    # ------------------------------------------------------------------
    # 1. Effectifs Open aux Championnats : base historique toutes nationalités.
    # ------------------------------------------------------------------
    annual_open_by_year: dict[int, dict[str, str]] = {}
    for row in annual_open:
        year = integer(row.get("Year"))
        if year is not None:
            annual_open_by_year[year] = row
            add_indicator(
                indicators,
                section="OPEN_CHAMPIONNATS",
                code="OPEN_CHAMP_TOTAL",
                period=str(year),
                label="Présences Open enregistrées au Championnat",
                value=integer(row.get("OpenAthletes")),
                unit="sportifs",
                scope=(
                    "Codes nationaux Open ; toutes nationalités présentes "
                    "dans la base historique"
                ),
                source=(
                    "renouvellement_open_championnats_2017_2026.csv"
                ),
                interpretation=(
                    "Série de volume du bloc Open ; ne constitue pas une "
                    "série française homogène avant 2023."
                ),
            )

    first_year = min(annual_open_by_year)
    last_year = max(annual_open_by_year)
    first_count = integer(
        annual_open_by_year[first_year].get("OpenAthletes")
    ) or 0
    last_count = integer(
        annual_open_by_year[last_year].get("OpenAthletes")
    ) or 0
    change = (
        round(100 * (last_count - first_count) / first_count, 1)
        if first_count
        else 0.0
    )
    add_indicator(
        indicators,
        section="OPEN_CHAMPIONNATS",
        code="OPEN_CHAMP_EVOLUTION",
        period=f"{first_year}-{last_year}",
        label="Évolution des présences Open au Championnat",
        numerator=last_count,
        denominator=first_count,
        value=change,
        unit="variation_percent",
        scope="Toutes nationalités de la base historique",
        source="renouvellement_open_championnats_2017_2026.csv",
        interpretation=(
            "Contraction du volume Open au Championnat sur la fenêtre."
        ),
    )

    # ------------------------------------------------------------------
    # 2. Sortie U21 -> Open.
    # ------------------------------------------------------------------
    u21_horizons: dict[int, tuple[int, int, float]] = {}

    for horizon, field in (
        (1, "ConvertedWithin1Year"),
        (2, "ConvertedWithin2Years"),
        (3, "ConvertedWithin3Years"),
    ):
        analyzable = [
            row
            for row in u21_cohorts
            if (integer(row.get("AvailableFollowUpYears")) or 0) >= horizon
        ]
        converted = sum(flag(row.get(field)) for row in analyzable)
        rate = percentage(converted, len(analyzable))
        u21_horizons[horizon] = (converted, len(analyzable), rate)

        add_indicator(
            indicators,
            section="U21_VERS_OPEN",
            code=f"U21_OPEN_H{horizon}",
            period=f"horizon_{horizon}_an",
            label=f"Sorties U21 retrouvées en Open sous {horizon} an(s)",
            numerator=converted,
            denominator=len(analyzable),
            value=rate,
            unit="percent",
            scope=(
                "Dernière présence U21 au Championnat ; cohortes avec recul "
                "suffisant"
            ),
            source="cohortes_sortie_u21_vers_open_2017_2026.csv",
            interpretation=(
                "Mesure une présence Open observable, pas la poursuite de "
                "toute pratique compétitive."
            ),
        )

    # ------------------------------------------------------------------
    # 3. Persistance Open, horizons comparables.
    # ------------------------------------------------------------------
    persistence_global: dict[int, dict[str, float | int]] = {}

    for horizon in (1, 2, 3):
        row = require_single(
            persistence_summary,
            lambda item, h=horizon: (
                item.get("Dimension") == "ALL"
                and integer(item.get("HorizonYears")) == h
            ),
            f"persistance globale horizon {horizon}",
        )

        analyzable = integer(row.get("AnalyzableEntrants")) or 0
        returned = integer(row.get("ReturnedOpen")) or 0
        continuous = integer(row.get("ContinuousOpen")) or 0
        return_rate = number(row.get("ReturnRatePercent")) or 0.0
        continuous_rate = number(
            row.get("ContinuousRatePercent")
        ) or 0.0

        persistence_global[horizon] = {
            "analyzable": analyzable,
            "returned": returned,
            "continuous": continuous,
            "return_rate": return_rate,
            "continuous_rate": continuous_rate,
        }

        add_indicator(
            indicators,
            section="PERSISTANCE_OPEN",
            code=f"OPEN_REAPPARITION_H{horizon}",
            period=f"horizon_{horizon}_an",
            label=f"Réapparition Open sous {horizon} an(s)",
            numerator=returned,
            denominator=analyzable,
            value=return_rate,
            unit="percent",
            scope=(
                "Premières apparitions Open 2018-2025 ; cohorte 2017 exclue ; "
                "recul comparable"
            ),
            source="persistance_open_selon_origine_u21_2018_2023.csv",
            interpretation=(
                "Autorise une ou plusieurs saisons d'interruption."
            ),
        )
        add_indicator(
            indicators,
            section="PERSISTANCE_OPEN",
            code=f"OPEN_CONTINUITE_H{horizon}",
            period=f"horizon_{horizon}_an",
            label=f"Présence Open continue jusqu'à {horizon} an(s)",
            numerator=continuous,
            denominator=analyzable,
            value=continuous_rate,
            unit="percent",
            scope=(
                "Premières apparitions Open 2018-2025 ; recul comparable"
            ),
            source="persistance_open_selon_origine_u21_2018_2023.csv",
            interpretation=(
                "Présence au Championnat Open chaque année, sans interruption."
            ),
        )

    # ------------------------------------------------------------------
    # 4. Origine U21 et persistance : fenêtre complète 2020-2023.
    # ------------------------------------------------------------------
    strict_by_group = {
        row.get("Group", ""): row
        for row in strict_u21_persistence
    }

    for group, code in (
        (
            "U21_DANS_LES_3_ANS_AVANT_OU_MEME_ANNEE",
            "OPEN_ORIGINE_U21_RECENTE",
        ),
        (
            "AUCUN_U21_OBSERVE_DANS_LES_3_ANS",
            "OPEN_SANS_U21_RECENTE",
        ),
    ):
        row = strict_by_group.get(group)
        if row is None:
            raise RuntimeError(f"Groupe strict absent : {group}")

        total = integer(row.get("FirstObservedOpenAthletes")) or 0
        returned = integer(row.get("OpenWithin3Years")) or 0
        continuous = integer(row.get("ContinuousThrough3Years")) or 0

        add_indicator(
            indicators,
            section="ORIGINE_U21_ET_OPEN",
            code=f"{code}_REAPPARITION_H3",
            period="cohortes_open_2020_2023",
            label=f"Réapparition Open sous trois ans — {group}",
            numerator=returned,
            denominator=total,
            value=number(row.get("OpenWithin3YearsRatePercent")),
            unit="percent",
            scope=(
                "Trois années d'historique U21 avant et trois années de "
                "recul Open après"
            ),
            source=(
                "persistance_open_u21_fenetre_complete_2020_2023.csv"
            ),
            interpretation=(
                "Association descriptive ; effectif insuffisant pour établir "
                "une causalité."
            ),
        )
        add_indicator(
            indicators,
            section="ORIGINE_U21_ET_OPEN",
            code=f"{code}_CONTINUITE_H3",
            period="cohortes_open_2020_2023",
            label=f"Continuité Open sur trois ans — {group}",
            numerator=continuous,
            denominator=total,
            value=number(
                row.get("ContinuousThrough3YearsRatePercent")
            ),
            unit="percent",
            scope=(
                "Trois années d'historique avant et après"
            ),
            source=(
                "persistance_open_u21_fenetre_complete_2020_2023.csv"
            ),
            interpretation=(
                "Présence chaque année sans interruption."
            ),
        )

    # ------------------------------------------------------------------
    # 5. Vivier EMS français et captation du code précis.
    # ------------------------------------------------------------------
    french_open_sets: dict[int, set[str]] = defaultdict(set)
    for row in ems_register:
        year = integer(row.get("Year"))
        athlete = str(row.get("AthleteKey") or "").strip()
        if year in YEARS_EMS and athlete and flag(row.get("HasOpen")):
            french_open_sets[year].add(athlete)

    exact_french: dict[int, set[str]] = defaultdict(set)
    exact_all: dict[int, set[str]] = defaultdict(set)

    for row in exact_capture:
        year = integer(row.get("Year"))
        athlete = str(row.get("AthleteKey") or "").strip()
        if year not in YEARS_EMS or not athlete:
            continue
        exact_all[year].add(athlete)
        if flag(row.get("IsFrench")):
            exact_french[year].add(athlete)

    capture_summary: dict[int, dict[str, float | int]] = {}

    for year in YEARS_EMS:
        total_french = len(french_open_sets[year])
        championship_french = len(exact_french[year])
        championship_all = len(exact_all[year])
        rate = percentage(championship_french, total_french)

        capture_summary[year] = {
            "total_french": total_french,
            "championship_french": championship_french,
            "championship_all": championship_all,
            "rate": rate,
        }

        add_indicator(
            indicators,
            section="CAPTATION_CHAMPIONNAT",
            code="CHAMP_OPEN_CAPTURE_FR",
            period=str(year),
            label="Captation des Open français par le code précis",
            numerator=championship_french,
            denominator=total_french,
            value=rate,
            unit="percent",
            scope=(
                f"Open français EMS ; code "
                f"{EXACT_OPEN_CHAMPIONSHIP_CODES[year]}"
            ),
            source=(
                "registre_filiere_open_ems_2023_2025.csv + "
                "audit_perimetre_championnat_open_nationalite_2023_2025.csv"
            ),
            interpretation=(
                "Indicateur central de rassemblement du vivier français."
            ),
        )
        add_indicator(
            indicators,
            section="CAPTATION_CHAMPIONNAT",
            code="CHAMP_OPEN_TOTAL",
            period=str(year),
            label="Participants Open du code précis, toutes nationalités",
            value=championship_all,
            unit="sportifs",
            scope=f"Code {EXACT_OPEN_CHAMPIONSHIP_CODES[year]}",
            source=(
                "audit_perimetre_championnat_open_nationalite_2023_2025.csv"
            ),
            interpretation=(
                "À distinguer du numérateur français de captation."
            ),
        )

    # ------------------------------------------------------------------
    # 6. Fonction du calendrier.
    # ------------------------------------------------------------------
    calendar_by_year: dict[int, list[dict[str, str]]] = defaultdict(list)
    for row in calendar_competitions:
        year = integer(row.get("Year"))
        if year in YEARS_EMS:
            calendar_by_year[year].append(row)

    fragmentation_by_year = {
        integer(row.get("Year")): row
        for row in calendar_fragmentation
        if integer(row.get("Year")) in YEARS_EMS
    }

    for year in YEARS_EMS:
        rows = calendar_by_year[year]
        shallow = sum(
            (integer(row.get("OpenAthletes")) or 0) <= 4
            for row in rows
        )
        competitions = len(rows)
        shallow_rate = percentage(shallow, competitions)

        add_indicator(
            indicators,
            section="CALENDRIER",
            code="CAL_OPEN_COMPETITIONS",
            period=str(year),
            label="Compétitions accueillant au moins un Open français",
            value=competitions,
            unit="competitions",
            scope="Calendrier EMS France",
            source="fonction_competitions_open_ems_2023_2025.csv",
            interpretation=(
                "Volume d'offre compétitive, non nombre de qualifications."
            ),
        )
        add_indicator(
            indicators,
            section="CALENDRIER",
            code="CAL_OPEN_CHAMPS_1_4",
            period=str(year),
            label="Compétitions avec seulement un à quatre Open",
            numerator=shallow,
            denominator=competitions,
            value=shallow_rate,
            unit="percent",
            scope="Compétitions avec Open français",
            source="fonction_competitions_open_ems_2023_2025.csv",
            interpretation=(
                "Mesure la faible profondeur des champs."
            ),
        )

        fragment = fragmentation_by_year.get(year)
        if fragment is None:
            raise RuntimeError(f"Fragmentation absente pour {year}")

        zero_pairs = integer(fragment.get("PairsWithZeroOverlap")) or 0
        pairs = integer(fragment.get("CompetitionPairs")) or 0
        zero_rate = number(fragment.get("ZeroOverlapSharePercent")) or 0.0

        add_indicator(
            indicators,
            section="CALENDRIER",
            code="CAL_ZERO_OVERLAP",
            period=str(year),
            label="Paires de compétitions sans Open commun",
            numerator=zero_pairs,
            denominator=pairs,
            value=zero_rate,
            unit="percent",
            scope="Toutes les paires de compétitions Open de la saison",
            source="fragmentation_calendrier_open_ems_2023_2025.csv",
            interpretation=(
                "Fragmentation relationnelle du calendrier."
            ),
        )
        add_indicator(
            indicators,
            section="CALENDRIER",
            code="CAL_LARGEST_COMPONENT",
            period=str(year),
            label="Compétitions appartenant à la plus grande composante",
            numerator=integer(
                fragment.get("LargestComponentCompetitions")
            ),
            denominator=integer(fragment.get("CompetitionsWithOpen")),
            unit="ratio",
            scope="Graphe des compétitions reliées par au moins un Open commun",
            source="fragmentation_calendrier_open_ems_2023_2025.csv",
            interpretation=(
                "Montre qu'un noyau multi-épreuves relie malgré tout "
                "l'essentiel du calendrier."
            ),
        )

    # Rétention selon intensité : groupes les plus lisibles.
    for year in (2023, 2024):
        for group in ("1_COMPETITION", "5_PLUS"):
            row = require_single(
                calendar_retention,
                lambda item, y=year, g=group: (
                    integer(item.get("Year")) == y
                    and item.get("Dimension") == "INTENSITY"
                    and item.get("Group") == g
                ),
                f"rétention intensité {year} {group}",
            )
            add_indicator(
                indicators,
                section="CALENDRIER",
                code=f"RETENTION_{group}",
                period=f"{year}-{year + 1}",
                label=f"Présence Open l'année suivante — {group}",
                numerator=integer(row.get("OpenNextYear")),
                denominator=integer(row.get("OpenAthletes")),
                value=number(row.get("RetentionRatePercent")),
                unit="percent",
                scope="Open français EMS",
                source="retention_open_selon_intensite_ems_2023_2024.csv",
                interpretation=(
                    "Association descriptive entre intensité et rétention ; "
                    "aucune causalité démontrée."
                ),
            )

    # ------------------------------------------------------------------
    # 7. Continuité Open -> Senior.
    # ------------------------------------------------------------------
    senior_horizons: dict[int, tuple[int, int, float]] = {}

    for horizon, field in (
        (1, "TransitionInFirstObservableSeason"),
        (2, "TransitionWithin2ObservableSeasons"),
        (3, "TransitionWithin3ObservableSeasons"),
    ):
        analyzable = [
            row
            for row in senior_continuity
            if (integer(row.get("AvailableFollowUpSeasons")) or 0) >= horizon
        ]
        transitioned = sum(flag(row.get(field)) for row in analyzable)
        rate = percentage(transitioned, len(analyzable))
        senior_horizons[horizon] = (
            transitioned,
            len(analyzable),
            rate,
        )

        add_indicator(
            indicators,
            section="OPEN_VERS_SENIOR",
            code=f"OPEN_SENIOR_H{horizon}",
            period=f"horizon_{horizon}_saison",
            label=(
                f"Passage Senior dans les {horizon} première(s) "
                "saison(s) observables"
            ),
            numerator=transitioned,
            denominator=len(analyzable),
            value=rate,
            unit="percent",
            scope=(
                "Anciens Open devenus éligibles et disposant du recul requis"
            ),
            source="continuite_open_senior_horizons_2017_2026.csv",
            interpretation=(
                "Indicateur d'aval, non indicateur central de performance."
            ),
        )

    any_followup = [
        row
        for row in senior_continuity
        if (integer(row.get("AvailableFollowUpSeasons")) or 0) >= 1
    ]
    eventual = sum(
        flag(row.get("ObservedEventuallyBy2026"))
        for row in any_followup
    )
    add_indicator(
        indicators,
        section="OPEN_VERS_SENIOR",
        code="OPEN_SENIOR_EVENTUEL",
        period="jusqu_a_2026",
        label="Anciens Open retrouvés ultérieurement en Senior",
        numerator=eventual,
        denominator=len(any_followup),
        value=percentage(eventual, len(any_followup)),
        unit="percent",
        scope="Trajectoires avec au moins une saison observable",
        source="continuite_open_senior_horizons_2017_2026.csv",
        interpretation=(
            "Décrit une continuité observable au Championnat seulement."
        ),
    )

    overlap_athletes = {
        str(row.get("CanonicalRiderId") or "").strip()
        for row in senior_overlap
        if str(row.get("CanonicalRiderId") or "").strip()
    }
    add_indicator(
        indicators,
        section="OPEN_VERS_SENIOR",
        code="OPEN_SENIOR_CHEVAUCHEMENT",
        period="2017-2026",
        label="Sportifs simultanément Open et Senior une même saison",
        value=len(overlap_athletes),
        unit="sportifs",
        scope="Championnat de France",
        source="chevauchements_open_senior_2017_2026.csv",
        interpretation=(
            "Open et Senior peuvent se chevaucher plutôt que se succéder."
        ),
    )

    # ------------------------------------------------------------------
    # 8. Références périmées.
    # ------------------------------------------------------------------
    stale = search_stale_references(root)
    stale_path = exports / "references_perimees_championnat_open.txt"
    stale_lines = [
        "RÉFÉRENCES À L'ANCIEN INDICATEUR LARGE DU CHAMPIONNAT OPEN",
        "=" * 80,
        "",
    ]

    if not stale:
        stale_lines.append("Aucune référence périmée détectée.")
    else:
        for path, reasons in stale:
            stale_lines.append(
                f"- {path.relative_to(root)} : " + " ; ".join(reasons)
            )
    stale_lines.extend(
        [
            "",
            "Valeurs de référence à utiliser :",
            "- 2023 : 18 Open français sur 41, soit 43,9 %.",
            "- 2024 : 16 Open français sur 37, soit 43,2 %.",
            "- 2025 : 14 Open français sur 49, soit 28,6 %.",
            "",
            "FIN",
        ]
    )
    stale_path.parent.mkdir(parents=True, exist_ok=True)
    stale_path.write_text("\n".join(stale_lines), encoding="utf-8")

    # ------------------------------------------------------------------
    # 9. CSV consolidé.
    # ------------------------------------------------------------------
    indicator_path = (
        processed / "indicateurs_consolides_filiere_open_2017_2026.csv"
    )
    write_csv(
        indicator_path,
        indicators,
        [
            "Section",
            "IndicatorCode",
            "Period",
            "Label",
            "Numerator",
            "Denominator",
            "Value",
            "Unit",
            "Scope",
            "Source",
            "Interpretation",
            "Status",
        ],
    )

    # ------------------------------------------------------------------
    # 10. Diagnostic texte.
    # ------------------------------------------------------------------
    u21_h3 = u21_horizons[3]
    pers_h3 = persistence_global[3]
    strict_u21 = strict_by_group[
        "U21_DANS_LES_3_ANS_AVANT_OU_MEME_ANNEE"
    ]
    strict_no_u21 = strict_by_group[
        "AUCUN_U21_OBSERVE_DANS_LES_3_ANS"
    ]

    diagnostic_lines: list[str] = []
    diagnostic_lines.append(
        "DIAGNOSTIC CONSOLIDÉ DE LA FILIÈRE U21 → OPEN — 2017-2026"
    )
    diagnostic_lines.append("=" * 88)
    diagnostic_lines.append("")
    diagnostic_lines.append("1. CATÉGORIE OPEN : VOLUME NATIONAL")
    diagnostic_lines.append("-" * 88)
    diagnostic_lines.append(
        f"Présences Open enregistrées aux Championnats : "
        f"{first_count} en {first_year}, {last_count} en {last_year}, "
        f"soit {format_fr(change)} %."
    )
    diagnostic_lines.append(
        "Cette série historique porte sur les participants présents dans les "
        "codes Open, toutes nationalités confondues ; elle ne doit pas être "
        "confondue avec le vivier français EMS 2023-2025."
    )
    diagnostic_lines.append("")

    diagnostic_lines.append("2. ALIMENTATION U21 → OPEN")
    diagnostic_lines.append("-" * 88)
    for horizon in (1, 2, 3):
        converted, denominator, rate = u21_horizons[horizon]
        diagnostic_lines.append(
            f"Sous {horizon} an(s) : {converted}/{denominator} sorties U21 "
            f"retrouvées en Open ({format_fr(rate)} %)."
        )
    diagnostic_lines.append(
        f"À trois ans, {u21_h3[1] - u21_h3[0]}/{u21_h3[1]} ne sont pas "
        "retrouvées en Open au Championnat dans la fenêtre observable."
    )
    diagnostic_lines.append("")

    diagnostic_lines.append("3. PÉRENNITÉ APRÈS L'ENTRÉE EN OPEN")
    diagnostic_lines.append("-" * 88)
    for horizon in (1, 2, 3):
        values = persistence_global[horizon]
        diagnostic_lines.append(
            f"Horizon {horizon} an(s) : réapparition="
            f"{values['returned']}/{values['analyzable']} "
            f"({format_fr(values['return_rate'])} %) ; continuité annuelle="
            f"{values['continuous']}/{values['analyzable']} "
            f"({format_fr(values['continuous_rate'])} %)."
        )
    diagnostic_lines.append(
        "Le contraste entre réapparition et continuité montre une dynamique "
        "d'interruptions et de retours, plutôt qu'une présence annuelle stable."
    )
    diagnostic_lines.append("")

    diagnostic_lines.append("4. ORIGINE U21 ET PERSISTANCE OPEN")
    diagnostic_lines.append("-" * 88)
    diagnostic_lines.append(
        "Fenêtre complète 2020-2023 :"
    )
    diagnostic_lines.append(
        f"- U21 récent : "
        f"{strict_u21['OpenWithin3Years']}/"
        f"{strict_u21['FirstObservedOpenAthletes']} réapparaissent sous "
        f"trois ans ({format_fr(number(strict_u21['OpenWithin3YearsRatePercent']))} %) ; "
        f"continuité annuelle="
        f"{strict_u21['ContinuousThrough3Years']}/"
        f"{strict_u21['FirstObservedOpenAthletes']}."
    )
    diagnostic_lines.append(
        f"- Aucun U21 récent observé : "
        f"{strict_no_u21['OpenWithin3Years']}/"
        f"{strict_no_u21['FirstObservedOpenAthletes']} réapparaissent "
        f"({format_fr(number(strict_no_u21['OpenWithin3YearsRatePercent']))} %) ; "
        f"continuité annuelle="
        f"{strict_no_u21['ContinuousThrough3Years']}/"
        f"{strict_no_u21['FirstObservedOpenAthletes']}."
    )
    diagnostic_lines.append(
        "L'association avec la réapparition est forte mais repose sur six "
        "sportifs seulement dans le groupe U21 récent ; aucune causalité ne "
        "peut être déduite."
    )
    diagnostic_lines.append("")

    diagnostic_lines.append("5. FONCTION EFFECTIVE DU CALENDRIER")
    diagnostic_lines.append("-" * 88)
    for year in YEARS_EMS:
        rows = calendar_by_year[year]
        shallow = sum(
            (integer(row.get("OpenAthletes")) or 0) <= 4
            for row in rows
        )
        fragment = fragmentation_by_year[year]
        diagnostic_lines.append(
            f"{year} : {len(rows)} compétitions avec Open ; "
            f"{len(french_open_sets[year])} Open français distincts ; "
            f"champs de 1-4 Open={shallow}/{len(rows)} "
            f"({format_fr(percentage(shallow, len(rows)))} %) ; "
            f"paires sans participant commun="
            f"{fragment['PairsWithZeroOverlap']}/"
            f"{fragment['CompetitionPairs']} "
            f"({format_fr(number(fragment['ZeroOverlapSharePercent']))} %)."
        )
    diagnostic_lines.append(
        "Le calendrier est abondant mais peu profond et relationnellement "
        "fragmenté. Une grande composante demeure reliée par un noyau de "
        "sportifs multi-épreuves."
    )
    diagnostic_lines.append("")

    diagnostic_lines.append("6. CAPTATION DU CHAMPIONNAT DE FRANCE OPEN")
    diagnostic_lines.append("-" * 88)
    for year in YEARS_EMS:
        values = capture_summary[year]
        diagnostic_lines.append(
            f"{year} : {values['championship_french']}/"
            f"{values['total_french']} Open français au code précis "
            f"({format_fr(values['rate'])} %) ; "
            f"{values['championship_all']} participants toutes nationalités."
        )
    diagnostic_lines.append(
        "La captation est stable autour de 43 % en 2023-2024, puis tombe à "
        "28,6 % en 2025 malgré l'élargissement du vivier EMS."
    )
    diagnostic_lines.append("")

    diagnostic_lines.append("7. CONTINUITÉ AVAL VERS SENIOR")
    diagnostic_lines.append("-" * 88)
    for horizon in (1, 2, 3):
        transitioned, denominator, rate = senior_horizons[horizon]
        diagnostic_lines.append(
            f"Horizon {horizon} saison(s) observable(s) : "
            f"{transitioned}/{denominator} passages "
            f"({format_fr(rate)} %)."
        )
    diagnostic_lines.append(
        f"À un moment quelconque avant 2026 : "
        f"{eventual}/{len(any_followup)} transitions observées "
        f"({format_fr(percentage(eventual, len(any_followup)))} %)."
    )
    diagnostic_lines.append(
        f"Chevauchements Open/Senior : {len(overlap_athletes)} sportifs."
    )
    diagnostic_lines.append(
        "Senior est une population d'aval et de continuité ; elle ne mesure "
        "pas le renouvellement de la catégorie reine."
    )
    diagnostic_lines.append("")

    diagnostic_lines.append("8. CONCLUSION CONSOLIDÉE")
    diagnostic_lines.append("-" * 88)
    diagnostic_lines.append(
        "La filière compétitive nationale ne transforme qu'une partie des "
        "sorties U21 en présence Open et transforme rarement une première "
        "apparition Open en participation annuelle continue. Le calendrier "
        "offre de nombreuses occasions de performance, mais les répartit sur "
        "un vivier restreint, dans des champs le plus souvent faibles. Les "
        "données sont compatibles avec un circuit intensif de performances "
        "homologuées pour une population déjà intégrée, davantage qu'avec une "
        "filière démontrant sa capacité à élargir et stabiliser durablement "
        "la base Open."
    )
    diagnostic_lines.append("")
    diagnostic_lines.append("PRÉCAUTIONS")
    diagnostic_lines.append("- Les données EMS décrivent des inscriptions approuvées.")
    diagnostic_lines.append(
        "- Les données de Championnats et les données EMS n'ont pas toujours "
        "le même périmètre de nationalité ou de statut."
    )
    diagnostic_lines.append(
        "- Une absence au Championnat de France n'est pas un abandon sportif."
    )
    diagnostic_lines.append(
        "- Les associations entre fréquence, origine U21 et rétention ne "
        "démontrent pas de causalité."
    )
    diagnostic_lines.append("")
    diagnostic_lines.append("FIN DU DIAGNOSTIC")

    diagnostic_path = (
        exports / "diagnostic_consolide_filiere_open_2017_2026.txt"
    )
    diagnostic_path.parent.mkdir(parents=True, exist_ok=True)
    diagnostic_path.write_text(
        "\n".join(diagnostic_lines),
        encoding="utf-8",
    )

    # ------------------------------------------------------------------
    # 11. Rapport Markdown de travail.
    # ------------------------------------------------------------------
    report_lines: list[str] = []
    report_lines.append(
        "# Filière compétitive U21 → Open : diagnostic consolidé 2017-2026"
    )
    report_lines.append("")
    report_lines.append(
        "> Version de travail v1 — les Seniors sont traités comme population "
        "d’aval ; le centre du diagnostic est la capacité à alimenter et "
        "pérenniser Open."
    )
    report_lines.append("")
    report_lines.append("## Résumé exécutif")
    report_lines.append("")
    report_lines.append(
        f"La catégorie Open enregistrée aux Championnats passe de "
        f"**{first_count} participants en {first_year} à {last_count} en "
        f"{last_year}**, soit **{format_fr(change)} %**. Cette série historique "
        "inclut les nationalités présentes dans les codes Open."
    )
    report_lines.append("")
    report_lines.append(
        f"Parmi les sorties U21 disposant de trois années de recul, "
        f"**{u21_h3[0]} sur {u21_h3[1]}**, soit "
        f"**{format_fr(u21_h3[2])} %**, sont retrouvées en Open. "
        f"Après une première apparition Open, **"
        f"{pers_h3['returned']} sur {pers_h3['analyzable']}** réapparaissent "
        f"sous trois ans, mais seulement **"
        f"{pers_h3['continuous']} sur {pers_h3['analyzable']}** restent "
        "présents chaque année sans interruption."
    )
    report_lines.append("")
    report_lines.append(
        "Le calendrier EMS comporte **24 à 25 compétitions Open par saison** "
        "pour seulement **37 à 49 Open français distincts**. Entre **52 % et "
        "60 %** des compétitions réunissent au plus quatre Open, et entre "
        "**58 % et 67 %** des paires d’épreuves ne partagent aucun participant."
    )
    report_lines.append("")
    report_lines.append(
        "La captation du vivier français par le code précis du Championnat "
        "Open est de **43,9 % en 2023**, **43,2 % en 2024** et "
        "**28,6 % en 2025**."
    )
    report_lines.append("")
    report_lines.append("## 1. Objet et périmètres")
    report_lines.append("")
    report_lines.append(
        "L’objet central n’est pas le nombre total de compétiteurs toutes "
        "catégories confondues, mais la capacité de la filière à renouveler, "
        "alimenter et pérenniser la catégorie Open."
    )
    report_lines.append("")
    report_lines.append(
        "Trois périmètres sont distingués : les présences historiques aux "
        "Championnats, les inscriptions françaises approuvées dans l’EMS et "
        "les classements sportifs effectifs. Ils ne sont pas interchangeables."
    )
    report_lines.append("")
    report_lines.append("## 2. Évolution de la catégorie Open")
    report_lines.append("")
    report_lines.append("| Année | Open au Championnat |")
    report_lines.append("|---:|---:|")
    for year in sorted(annual_open_by_year):
        report_lines.append(
            f"| {year} | "
            f"{integer(annual_open_by_year[year].get('OpenAthletes')) or 0} |"
        )
    report_lines.append("")
    report_lines.append(
        "La série fait apparaître une contraction de long terme, malgré un "
        "rebond ponctuel en 2022."
    )
    report_lines.append("")
    report_lines.append("## 3. Alimentation U21 → Open")
    report_lines.append("")
    report_lines.append("| Horizon | Convertis | Cohorte observable | Taux |")
    report_lines.append("|---:|---:|---:|---:|")
    for horizon in (1, 2, 3):
        converted, denominator, rate = u21_horizons[horizon]
        report_lines.append(
            f"| {horizon} an(s) | {converted} | {denominator} | "
            f"{format_fr(rate)} % |"
        )
    report_lines.append("")
    report_lines.append(
        "Le passage existe, mais il n’est ni immédiat ni majoritaire."
    )
    report_lines.append("")
    report_lines.append("## 4. Pérennité après l’entrée en Open")
    report_lines.append("")
    report_lines.append(
        "| Horizon | Réapparition | Taux | Continuité annuelle | Taux |"
    )
    report_lines.append("|---:|---:|---:|---:|---:|")
    for horizon in (1, 2, 3):
        values = persistence_global[horizon]
        report_lines.append(
            f"| {horizon} an(s) | {values['returned']}/"
            f"{values['analyzable']} | "
            f"{format_fr(values['return_rate'])} % | "
            f"{values['continuous']}/{values['analyzable']} | "
            f"{format_fr(values['continuous_rate'])} % |"
        )
    report_lines.append("")
    report_lines.append(
        "La réapparition ponctuelle est nettement plus fréquente que la "
        "présence continue."
    )
    report_lines.append("")
    report_lines.append("## 5. Fonction du calendrier")
    report_lines.append("")
    report_lines.append(
        "| Année | Compétitions Open | Open français | Champs 1–4 | "
        "Paires sans recouvrement |"
    )
    report_lines.append("|---:|---:|---:|---:|---:|")
    for year in YEARS_EMS:
        rows = calendar_by_year[year]
        shallow = sum(
            (integer(row.get("OpenAthletes")) or 0) <= 4
            for row in rows
        )
        fragment = fragmentation_by_year[year]
        report_lines.append(
            f"| {year} | {len(rows)} | {len(french_open_sets[year])} | "
            f"{shallow}/{len(rows)} "
            f"({format_fr(percentage(shallow, len(rows)))} %) | "
            f"{fragment['PairsWithZeroOverlap']}/"
            f"{fragment['CompetitionPairs']} "
            f"({format_fr(number(fragment['ZeroOverlapSharePercent']))} %) |"
        )
    report_lines.append("")
    report_lines.append(
        "L’offre est abondante mais dispersée. L’essentiel du calendrier "
        "reste relié par un petit noyau multi-épreuves."
    )
    report_lines.append("")
    report_lines.append("## 6. Captation du Championnat Open")
    report_lines.append("")
    report_lines.append(
        "| Année | Vivier français EMS | Français au code précis | "
        "Captation | Tous participants |"
    )
    report_lines.append("|---:|---:|---:|---:|---:|")
    for year in YEARS_EMS:
        values = capture_summary[year]
        report_lines.append(
            f"| {year} | {values['total_french']} | "
            f"{values['championship_french']} | "
            f"{format_fr(values['rate'])} % | "
            f"{values['championship_all']} |"
        )
    report_lines.append("")
    report_lines.append(
        "Le rebond du vivier EMS en 2025 n’est pas capté par l’épreuve "
        "nationale centrale."
    )
    report_lines.append("")
    report_lines.append("## 7. Continuité aval vers Senior")
    report_lines.append("")
    report_lines.append(
        f"Parmi les anciens Open disposant d’au moins une saison observable, "
        f"**{eventual} sur {len(any_followup)}** sont retrouvés ultérieurement "
        f"en Senior. **{len(overlap_athletes)} sportifs** sont observés "
        "simultanément en Open et Senior une même saison."
    )
    report_lines.append("")
    report_lines.append(
        "Ces données renseignent la continuité de pratique ; elles ne mesurent "
        "pas la santé de la filière de performance."
    )
    report_lines.append("")
    report_lines.append("## 8. Conclusion")
    report_lines.append("")
    report_lines.append(
        "La filière ne manque pas d’épreuves. Elle manque principalement de "
        "profondeur, de conversion vers Open et de continuité annuelle après "
        "l’entrée dans la catégorie reine. Le calendrier paraît davantage "
        "optimisé pour permettre des performances homologuées à une population "
        "restreinte et déjà intégrée que pour élargir puis stabiliser le vivier."
    )
    report_lines.append("")
    report_lines.append("## Limites")
    report_lines.append("")
    report_lines.append(
        "Les données EMS sont des inscriptions approuvées, les données de "
        "Championnat peuvent inclure d’autres nationalités et une absence à "
        "l’épreuve nationale ne signifie pas un arrêt sportif. Les relations "
        "observées ne doivent pas être interprétées causalement."
    )

    report_path = reports / "rapport_filiere_open_2017_2026_v1.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        "\n".join(report_lines) + "\n",
        encoding="utf-8",
    )

    print("=" * 88)
    print("CONSOLIDATION DE LA FILIÈRE OPEN TERMINÉE")
    print("=" * 88)
    print(f"Indicateurs : {len(indicators)}")
    print(f"CSV         : {indicator_path}")
    print(f"Diagnostic  : {diagnostic_path}")
    print(f"Rapport MD  : {report_path}")
    print(f"Références périmées : {stale_path}")
    print("Aucun fichier d'analyse existant n'a été écrasé.")


if __name__ == "__main__":
    main()
