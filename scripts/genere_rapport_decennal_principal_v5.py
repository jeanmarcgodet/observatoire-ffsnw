"""Génère le rapport décennal principal intégré, version 5.

Le rapport articule :
- le cadrage longitudinal global 2017-2026 ;
- la contraction de la catégorie Open ;
- l'alimentation U21 -> Open ;
- la persistance après l'entrée en Open ;
- la fonction effective du calendrier EMS ;
- la captation du Championnat de France Open ;
- la continuité aval vers Senior ;
- un tableau de bord institutionnel proposé.

Entrées
-------
reports/rapport_longitudinal_participation_2017_2026_v4.md
reports/rapport_filiere_open_2017_2026_v2.md
data/processed/indicateurs_consolides_filiere_open_2017_2026.csv
reports/figures/filiere_open_v2/*.png

Sorties
-------
reports/rapport_decennal_principal_2017_2026_v5.md
reports/figures/rapport_decennal_v5/01_contraction_globale.png
reports/figures/rapport_decennal_v5/02_structure_2026.png

Le rapport v4 et le rapport Open v2 ne sont pas modifiés.
"""

from __future__ import annotations

import csv
import math
from pathlib import Path

import matplotlib.pyplot as plt


GLOBAL = {
    "participants_2017": 103,
    "participants_2026": 69,
    "participations_champs_2017": 256,
    "participations_champs_2026": 141,
    "fields_2026": 52,
    "fields_1_3_2026": 36,
    "podium_weight_2026": 79.4,
    "analytical_grid_fields": 104,
}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle, delimiter=";"))


def number(value: object) -> float | None:
    text = str(value or "").strip().replace(",", ".")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def integer(value: object) -> int | None:
    value_number = number(value)
    return int(value_number) if value_number is not None else None


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


def percent_change(start: int, end: int) -> float:
    return round(100 * (end - start) / start, 1)


def lookup_indicators(
    rows: list[dict[str, str]],
) -> dict[tuple[str, str], dict[str, str]]:
    return {
        (row["IndicatorCode"], row["Period"]): row
        for row in rows
    }


def require(
    lookup: dict[tuple[str, str], dict[str, str]],
    code: str,
    period: str,
) -> dict[str, str]:
    key = (code, period)
    if key not in lookup:
        raise KeyError(f"Indicateur absent : {code} / {period}")
    return lookup[key]


def save_figure(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(path, dpi=180, bbox_inches="tight")
    plt.close()


def figure_global_contraction(path: Path) -> None:
    labels = [
        "Participants distincts",
        "Participations aux champs",
    ]
    values_2017 = [
        GLOBAL["participants_2017"],
        GLOBAL["participations_champs_2017"],
    ]
    values_2026 = [
        GLOBAL["participants_2026"],
        GLOBAL["participations_champs_2026"],
    ]

    x = list(range(len(labels)))
    width = 0.36

    plt.figure(figsize=(9.2, 5.4))
    ax = plt.gca()

    bars_2017 = ax.bar(
        [position - width / 2 for position in x],
        values_2017,
        width,
        label="2017",
    )
    bars_2026 = ax.bar(
        [position + width / 2 for position in x],
        values_2026,
        width,
        label="2026",
    )

    ax.bar_label(bars_2017, padding=3)
    ax.bar_label(bars_2026, padding=3)
    ax.set_xticks(x, labels)
    ax.set_ylabel("Nombre")
    ax.set_title("Contraction globale des Championnats, 2017-2026")
    ax.legend()
    ax.grid(axis="y", alpha=0.25)

    save_figure(path)


def figure_structure_2026(path: Path) -> None:
    low_depth_rate = round(
        100
        * GLOBAL["fields_1_3_2026"]
        / GLOBAL["fields_2026"],
        1,
    )
    labels = [
        "Champs à 1–3 participants",
        "Poids numérique du podium",
    ]
    values = [
        low_depth_rate,
        GLOBAL["podium_weight_2026"],
    ]

    plt.figure(figsize=(8.8, 5.2))
    ax = plt.gca()
    bars = ax.bar(labels, values)
    ax.bar_label(
        bars,
        labels=[f"{format_fr(value)} %" for value in values],
        padding=4,
    )
    ax.set_ylim(0, 100)
    ax.set_ylabel("Part (%)")
    ax.set_title("Structure quantitative des Championnats en 2026")
    ax.grid(axis="y", alpha=0.25)

    save_figure(path)


def build_report(
    report_path: Path,
    figure_dir: Path,
    indicators: dict[tuple[str, str], dict[str, str]],
) -> None:
    participants_change = percent_change(
        GLOBAL["participants_2017"],
        GLOBAL["participants_2026"],
    )
    participations_change = percent_change(
        GLOBAL["participations_champs_2017"],
        GLOBAL["participations_champs_2026"],
    )
    shallow_rate = round(
        100
        * GLOBAL["fields_1_3_2026"]
        / GLOBAL["fields_2026"],
        1,
    )

    open_2017 = require(
        indicators,
        "OPEN_CHAMP_TOTAL",
        "2017",
    )
    open_2026 = require(
        indicators,
        "OPEN_CHAMP_TOTAL",
        "2026",
    )
    open_change = require(
        indicators,
        "OPEN_CHAMP_EVOLUTION",
        "2017-2026",
    )

    u21_h1 = require(
        indicators,
        "U21_OPEN_H1",
        "horizon_1_an",
    )
    u21_h2 = require(
        indicators,
        "U21_OPEN_H2",
        "horizon_2_an",
    )
    u21_h3 = require(
        indicators,
        "U21_OPEN_H3",
        "horizon_3_an",
    )

    reapp_h3 = require(
        indicators,
        "OPEN_REAPPARITION_H3",
        "horizon_3_an",
    )
    continuity_h3 = require(
        indicators,
        "OPEN_CONTINUITE_H3",
        "horizon_3_an",
    )

    recent_u21 = require(
        indicators,
        "OPEN_ORIGINE_U21_RECENTE_REAPPARITION_H3",
        "cohortes_open_2020_2023",
    )
    no_recent_u21 = require(
        indicators,
        "OPEN_SANS_U21_RECENTE_REAPPARITION_H3",
        "cohortes_open_2020_2023",
    )

    captures = {
        year: require(
            indicators,
            "CHAMP_OPEN_CAPTURE_FR",
            str(year),
        )
        for year in (2023, 2024, 2025)
    }

    calendar = {
        year: {
            "competitions": require(
                indicators,
                "CAL_OPEN_COMPETITIONS",
                str(year),
            ),
            "shallow": require(
                indicators,
                "CAL_OPEN_CHAMPS_1_4",
                str(year),
            ),
            "zero_overlap": require(
                indicators,
                "CAL_ZERO_OVERLAP",
                str(year),
            ),
        }
        for year in (2023, 2024, 2025)
    }

    senior_eventual = require(
        indicators,
        "OPEN_SENIOR_EVENTUEL",
        "jusqu_a_2026",
    )
    senior_overlap = require(
        indicators,
        "OPEN_SENIOR_CHEVAUCHEMENT",
        "2017-2026",
    )

    relative_global_figures = figure_dir.relative_to(
        report_path.parent
    ).as_posix()
    relative_open_figures = "figures/filiere_open_v2"

    lines: list[str] = []

    lines.append(
        "# Championnats de France de ski nautique classique : "
        "rapport décennal principal 2017-2026"
    )
    lines.append("")
    lines.append(
        "> Version 5 — synthèse intégrée du rapport longitudinal global et "
        "de l’analyse de la filière U21 → Open."
    )
    lines.append("")

    lines.append("## Résumé exécutif")
    lines.append("")
    lines.append(
        f"Entre 2017 et 2026, le nombre de participants distincts "
        f"enregistrés aux Championnats passe de "
        f"**{GLOBAL['participants_2017']} à "
        f"{GLOBAL['participants_2026']}**, soit "
        f"**{format_fr(participants_change)} %**. Dans le même temps, les "
        f"participations aux champs diminuent de "
        f"**{GLOBAL['participations_champs_2017']} à "
        f"{GLOBAL['participations_champs_2026']}**, soit "
        f"**{format_fr(participations_change)} %**."
    )
    lines.append("")
    lines.append(
        f"En 2026, **{GLOBAL['fields_1_3_2026']} des "
        f"{GLOBAL['fields_2026']} champs effectivement disputés**, soit "
        f"**{format_fr(shallow_rate)} %**, ne réunissent que un à trois "
        "participants. Le poids numérique théorique du podium atteint "
        f"**{format_fr(GLOBAL['podium_weight_2026'])} %**."
    )
    lines.append("")
    lines.append(
        f"La catégorie Open, centrale dans la trajectoire compétitive, passe "
        f"de **{open_2017['Value']} participants au Championnat en 2017 à "
        f"{open_2026['Value']} en 2026**, soit "
        f"**{format_fr(number(open_change['Value']))} %**. Parmi les sorties "
        f"U21 disposant de trois années de recul, "
        f"**{u21_h3['Numerator']} sur {u21_h3['Denominator']}** sont "
        "retrouvées en Open. Après une première apparition Open, seulement "
        f"**{continuity_h3['Numerator']} sur "
        f"{continuity_h3['Denominator']}** restent présents chaque année "
        "pendant les trois années suivantes."
    )
    lines.append("")
    lines.append(
        "**Conclusion centrale.** La difficulté principale ne réside pas "
        "dans l’absence d’épreuves, mais dans la réduction du vivier, la "
        "faible profondeur des champs, la conversion incomplète vers Open "
        "et la rareté d’une présence annuelle durable dans la catégorie "
        "centrale."
    )
    lines.append("")

    lines.append("## 1. Objet du rapport")
    lines.append("")
    lines.append(
        "Le rapport global v4 établissait la contraction générale de la "
        "participation et la multiplication des champs à très faible effectif. "
        "La présente version conserve ce cadrage, mais déplace le centre de "
        "l’analyse vers la trajectoire compétitive : "
        "**Relève/U17 → U21 → Open → Senior**."
    )
    lines.append("")
    lines.append(
        "La santé de la filière n’est donc pas appréciée uniquement au nombre "
        "total de compétiteurs toutes catégories confondues. Elle est examinée "
        "à travers sa capacité à renouveler, alimenter et pérenniser la "
        "catégorie Open. Les Seniors renseignent la continuité ou l’héritage "
        "de la pratique ; ils ne peuvent pas, seuls, servir d’indicateur de "
        "développement ou d’accès au haut niveau."
    )
    lines.append("")

    lines.append("## 2. Méthode et périmètres")
    lines.append("")
    lines.append(
        "L’analyse combine les codes nationaux explicitement validés des "
        "Championnats de France, les inscriptions approuvées dans l’EMS et "
        "les résultats classés. Ces sources décrivent des objets différents "
        "et ne sont jamais fusionnées sans contrôle de périmètre."
    )
    lines.append("")
    lines.append(
        f"La grille de **{GLOBAL['analytical_grid_fields']} champs** utilisée "
        "dans le rapport global constitue une grille analytique de référence. "
        "Elle ne doit pas être présentée comme le programme réglementaire "
        "effectivement disputé chaque année."
    )
    lines.append("")
    lines.append(
        "Le **poids numérique théorique du podium** rapporte le nombre maximal "
        "de places de podium attribuables dans les champs effectivement "
        "disputés au nombre total de participations classées. Il mesure la "
        "sélectivité quantitative des champs ; il ne mesure pas la valeur "
        "sportive des médailles."
    )
    lines.append("")
    lines.append(
        "L’année 2020 constitue une rupture statistique dans un contexte "
        "sanitaire exceptionnel. Les données permettent d’en constater "
        "l’existence, mais pas d’attribuer mécaniquement l’ensemble des "
        "évolutions ultérieures à cette seule cause."
    )
    lines.append("")

    lines.append("<!-- PAGEBREAK -->")
    lines.append("")
    lines.append("## 3. Une contraction globale et une sélectivité quantitative affaiblie")
    lines.append("")
    lines.append(
        f"![Contraction globale]("
        f"{relative_global_figures}/01_contraction_globale.png)"
    )
    lines.append("")
    lines.append(
        "*Source : rapport longitudinal global v4. Les deux indicateurs "
        "mesurent respectivement les personnes distinctes et les présences "
        "dans les champs de classement.*"
    )
    lines.append("")
    lines.append(
        "La baisse des participations aux champs est plus forte que celle des "
        "participants distincts. Cette divergence est compatible avec une "
        "réduction de la multidisciplinarité ou du nombre de participations "
        "par sportif, sans permettre d’en établir seule la cause."
    )
    lines.append("")
    lines.append(
        f"![Structure 2026]("
        f"{relative_global_figures}/02_structure_2026.png)"
    )
    lines.append("")
    lines.append(
        "La valeur sportive d’une médaille ne peut pas être réduite à son "
        "poids numérique. Les données établissent toutefois un "
        "**affaiblissement de la sélectivité quantitative** : dans une part "
        "croissante des champs, l’accès au podium dépend d’un nombre très "
        "faible de concurrents."
    )
    lines.append("")

    lines.append("## 4. Open devient le point critique de la filière")
    lines.append("")
    lines.append(
        f"![Effectifs Open au Championnat]("
        f"{relative_open_figures}/01_effectifs_open_championnat.png)"
    )
    lines.append("")
    lines.append(
        f"Le nombre de participants au Championnat Open passe de "
        f"**{open_2017['Value']} à {open_2026['Value']}**. La hausse observée "
        "en 2022 ne renverse pas la contraction enregistrée depuis 2023."
    )
    lines.append("")
    lines.append(
        "Cette série historique comprend toutes les nationalités présentes "
        "dans les codes Open. Elle ne doit pas être confondue avec le vivier "
        "français EMS utilisé pour l’analyse du calendrier à partir de 2023."
    )
    lines.append("")

    lines.append("<!-- PAGEBREAK -->")
    lines.append("")
    lines.append("## 5. Le passage U21 → Open reste minoritaire à trois ans")
    lines.append("")
    lines.append(
        f"![Conversion U21 vers Open]("
        f"{relative_open_figures}/02_conversion_u21_open.png)"
    )
    lines.append("")
    lines.append(
        f"Les taux observés sont de "
        f"**{format_fr(number(u21_h1['Value']))} % sous un an**, "
        f"**{format_fr(number(u21_h2['Value']))} % sous deux ans** et "
        f"**{format_fr(number(u21_h3['Value']))} % sous trois ans**. "
        "Les dénominateurs diminuent avec l’horizon, car seules les cohortes "
        "disposant d’un recul suffisant sont conservées."
    )
    lines.append("")
    lines.append(
        f"À trois ans, **{integer(u21_h3['Denominator']) - integer(u21_h3['Numerator'])} "
        f"sorties U21 sur {u21_h3['Denominator']}** ne sont pas retrouvées "
        "en Open au Championnat dans la fenêtre observable. Cela ne signifie "
        "pas qu’elles ont cessé toute pratique sportive."
    )
    lines.append("")

    lines.append("<!-- PAGEBREAK -->")
    lines.append("")
    lines.append("## 6. L’entrée en Open débouche rarement sur une présence continue")
    lines.append("")
    lines.append(
        f"![Persistance Open]("
        f"{relative_open_figures}/03_persistance_open.png)"
    )
    lines.append("")
    lines.append(
        f"Sous trois ans, **{reapp_h3['Numerator']} sur "
        f"{reapp_h3['Denominator']}**, soit "
        f"**{format_fr(number(reapp_h3['Value']))} %**, réapparaissent au "
        "moins une fois. Mais seulement "
        f"**{continuity_h3['Numerator']} sur "
        f"{continuity_h3['Denominator']}**, soit "
        f"**{format_fr(number(continuity_h3['Value']))} %**, sont présents "
        "chaque année sans interruption."
    )
    lines.append("")
    lines.append(
        "Le principal enjeu n’est donc pas uniquement l’accès ponctuel à Open, "
        "mais l’intégration durable dans la catégorie."
    )
    lines.append("")

    lines.append("<!-- PAGEBREAK -->")
    lines.append("")
    lines.append("## 7. Un parcours U21 récent est associé à davantage de réapparitions")
    lines.append("")
    lines.append(
        f"![Origine U21 et persistance]("
        f"{relative_open_figures}/04_origine_u21_persistance.png)"
    )
    lines.append("")
    lines.append(
        f"Parmi les premières apparitions Open précédées d’un parcours U21 "
        f"récent, **{recent_u21['Numerator']} sur "
        f"{recent_u21['Denominator']}** réapparaissent sous trois ans, contre "
        f"**{no_recent_u21['Numerator']} sur "
        f"{no_recent_u21['Denominator']}** lorsqu’aucun U21 récent n’est "
        "observé."
    )
    lines.append("")
    lines.append(
        "L’effectif du groupe U21 récent n’est que de six sportifs. Le résultat "
        "décrit une association forte, mais ne permet pas d’établir une "
        "causalité."
    )
    lines.append("")

    lines.append("## 8. Un calendrier abondant, mais dispersé sur un vivier réduit")
    lines.append("")
    lines.append(
        f"![Profondeur et fragmentation du calendrier]("
        f"{relative_open_figures}/05_calendrier_profondeur_fragmentation.png)"
    )
    lines.append("")
    lines.append("| Année | Compétitions avec Open | Open français distincts | Champs à 1–4 Open | Paires sans participant commun |")
    lines.append("|---:|---:|---:|---:|---:|")
    open_distincts = {2023: 41, 2024: 37, 2025: 49}
    for year in (2023, 2024, 2025):
        values = calendar[year]
        lines.append(
            f"| {year} | {values['competitions']['Value']} | "
            f"{open_distincts[year]} | "
            f"{values['shallow']['Numerator']}/"
            f"{values['shallow']['Denominator']} "
            f"({format_fr(number(values['shallow']['Value']))} %) | "
            f"{values['zero_overlap']['Numerator']}/"
            f"{values['zero_overlap']['Denominator']} "
            f"({format_fr(number(values['zero_overlap']['Value']))} %) |"
        )
    lines.append("")
    lines.append(
        "Le calendrier n’est pas constitué de circuits entièrement étanches : "
        "une grande composante relie l’essentiel des épreuves à travers un "
        "petit noyau de compétiteurs multi-épreuves. Il apparaît toutefois "
        "davantage comme un réseau faiblement connecté offrant de nombreuses "
        "occasions de performances homologuées à une population restreinte "
        "que comme un dispositif élargissant durablement la base Open."
    )
    lines.append("")

    lines.append("<!-- PAGEBREAK -->")
    lines.append("")
    lines.append("## 9. Le Championnat Open rassemble une part décroissante du vivier français")
    lines.append("")
    lines.append(
        f"![Captation du Championnat Open]("
        f"{relative_open_figures}/06_captation_championnat_open.png)"
    )
    lines.append("")
    lines.append(
        f"La captation du vivier français EMS est de "
        f"**{format_fr(number(captures[2023]['Value']))} % en 2023**, "
        f"**{format_fr(number(captures[2024]['Value']))} % en 2024** et "
        f"**{format_fr(number(captures[2025]['Value']))} % en 2025**."
    )
    lines.append("")
    lines.append(
        "L’augmentation du nombre d’Open français actifs en 2025 ne se traduit "
        "donc pas par un renforcement de l’épreuve nationale centrale. "
        "Comme le Championnat Open ne repose pas sur une qualification "
        "nationale préalable, cette faible captation interroge directement "
        "la capacité fédératrice et l’attractivité compétitive du dispositif."
    )
    lines.append("")

    lines.append("## 10. Senior : une population d’aval qui ne compense pas la faiblesse d’Open")
    lines.append("")
    lines.append(
        f"Parmi les anciens Open disposant d’au moins une saison observable, "
        f"**{senior_eventual['Numerator']} sur "
        f"{senior_eventual['Denominator']}**, soit "
        f"**{format_fr(number(senior_eventual['Value']))} %**, sont retrouvés "
        "ultérieurement en Senior. "
        f"**{senior_overlap['Value']} sportifs** sont observés simultanément "
        "en Open et Senior une même saison."
    )
    lines.append("")
    lines.append(
        "La population Senior peut témoigner d’une continuité ou d’une reprise "
        "de la pratique. Les données ne permettent pas de caractériser les "
        "ressources économiques des participants ni les conditions ayant rendu "
        "cette continuité possible. Elle ne peut pas masquer un faible "
        "renouvellement U21, une catégorie Open réduite ou une faible présence "
        "annuelle continue."
    )
    lines.append("")

    lines.append("## 11. Ce que les données permettent d’affirmer")
    lines.append("")
    lines.append(
        "- La participation aux Championnats se contracte fortement sur la décennie."
    )
    lines.append(
        "- La profondeur des champs diminue et le poids numérique du podium augmente."
    )
    lines.append(
        "- Moins de la moitié des sorties U21 observables sont retrouvées en Open sous trois ans."
    )
    lines.append(
        "- Une première apparition Open conduit plus souvent à une réapparition intermittente qu’à une présence annuelle continue."
    )
    lines.append(
        "- Le calendrier est abondant au regard du faible nombre d’Open concernés."
    )
    lines.append(
        "- Le Championnat Open capte une part minoritaire et décroissante du vivier français EMS."
    )
    lines.append(
        "- Senior renseigne l’aval de la pratique, mais pas la capacité de renouvellement de la catégorie reine."
    )
    lines.append("")

    lines.append("## 12. Ce que les données ne permettent pas d’affirmer seules")
    lines.append("")
    lines.append(
        "- Elles n’établissent pas les causes individuelles de l’absence ou de l’arrêt."
    )
    lines.append(
        "- Elles ne démontrent pas une désertion sociale ou économique sans données complémentaires."
    )
    lines.append(
        "- Elles ne permettent pas d’attribuer mécaniquement les évolutions à 2020."
    )
    lines.append(
        "- Elles ne prouvent pas que la fréquence de compétition cause la fidélisation."
    )
    lines.append(
        "- Elles ne permettent pas de réduire la valeur sportive d’une médaille à la seule taille du champ."
    )
    lines.append("")

    lines.append("## 13. Tableau de bord annuel recommandé")
    lines.append("")
    lines.append("| Indicateur | Définition | Fonction |")
    lines.append("|---|---|---|")
    lines.append(
        "| Conversion U21 → Open à 1, 2 et 3 ans | Part des dernières présences U21 retrouvées en Open | Mesurer l’alimentation de la catégorie centrale |"
    )
    lines.append(
        "| Continuité Open à 1, 2 et 3 ans | Présence Open chaque année sans interruption | Mesurer l’intégration durable |"
    )
    lines.append(
        "| Captation du Championnat Open | Open français du code précis / vivier Open français EMS | Mesurer la capacité fédératrice de l’épreuve nationale |"
    )
    lines.append(
        "| Profondeur des champs | Distribution des champs par taille | Mesurer la sélectivité quantitative |"
    )
    lines.append(
        "| Concentration du calendrier | Part des participations portée par le noyau le plus actif | Identifier la dépendance à un petit groupe |"
    )
    lines.append(
        "| Passage Open → Senior | Anciens Open retrouvés en Senior | Décrire la continuité aval sans la confondre avec le développement |"
    )
    lines.append("")

    lines.append("## 14. Conclusion générale")
    lines.append("")
    lines.append(
        "Le diagnostic décennal ne décrit pas simplement une baisse de "
        "participation. Il met en évidence une architecture compétitive dont "
        "la catégorie centrale se contracte, dont l’alimentation par U21 reste "
        "partielle et dont la présence annuelle continue est rare."
    )
    lines.append("")
    lines.append(
        "Le calendrier français propose de nombreuses occasions de produire "
        "des performances homologuées, mais cette abondance ne suffit pas à "
        "démontrer l’existence d’une filière capable d’élargir et de stabiliser "
        "durablement le vivier Open. L’enjeu institutionnel devient donc moins "
        "la multiplication des épreuves que la définition d’une trajectoire "
        "mesurable : entrée en Open, accompagnement, fidélisation et rôle "
        "fédérateur du Championnat de France."
    )
    lines.append("")

    lines.append("## Limites")
    lines.append("")
    lines.append(
        "- Les données EMS décrivent des inscriptions approuvées, pas nécessairement des départs ou des classements."
    )
    lines.append(
        "- Les périmètres de nationalité et de statut diffèrent entre certaines séries historiques et l’EMS."
    )
    lines.append(
        "- Le bloc U21/Open 2025 est incomplet dans les résultats classés ; les analyses centrales 2025 reposent donc sur l’EMS lorsque nécessaire."
    )
    lines.append(
        "- Une absence au Championnat de France ne signifie pas un arrêt de toute pratique compétitive."
    )
    lines.append(
        "- Les associations observées ne démontrent pas de causalité."
    )

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    root = repo_root()

    global_v4 = (
        root
        / "reports/rapport_longitudinal_participation_2017_2026_v4.md"
    )
    open_v2 = (
        root
        / "reports/rapport_filiere_open_2017_2026_v2.md"
    )
    indicator_path = (
        root
        / "data/processed/indicateurs_consolides_filiere_open_2017_2026.csv"
    )
    report_path = (
        root
        / "reports/rapport_decennal_principal_2017_2026_v5.md"
    )
    figure_dir = (
        root
        / "reports/figures/rapport_decennal_v5"
    )

    for required_path in (global_v4, open_v2, indicator_path):
        if not required_path.exists():
            raise FileNotFoundError(required_path)

    open_figures = root / "reports/figures/filiere_open_v2"
    required_figures = [
        "01_effectifs_open_championnat.png",
        "02_conversion_u21_open.png",
        "03_persistance_open.png",
        "04_origine_u21_persistance.png",
        "05_calendrier_profondeur_fragmentation.png",
        "06_captation_championnat_open.png",
    ]
    for filename in required_figures:
        path = open_figures / filename
        if not path.exists():
            raise FileNotFoundError(path)

    rows = read_csv(indicator_path)
    indicators = lookup_indicators(rows)

    figure_global_contraction(
        figure_dir / "01_contraction_globale.png"
    )
    figure_structure_2026(
        figure_dir / "02_structure_2026.png"
    )
    build_report(
        report_path,
        figure_dir,
        indicators,
    )

    print("=" * 88)
    print("RAPPORT DÉCENNAL PRINCIPAL V5 GÉNÉRÉ")
    print("=" * 88)
    print(f"Rapport : {report_path}")
    print(f"Figures nouvelles : {figure_dir}")
    print("Figures Open réutilisées : 6")
    print("Aucun rapport antérieur n'a été modifié.")


if __name__ == "__main__":
    main()
