"""Remplace la conclusion provisoire par la conclusion generale."""

from pathlib import Path


REPORT_FILE = Path(
    "reports/note_participation_2017_2026.md"
)

OLD_HEADING = "## Conclusion provisoire"

NEW_CONCLUSION = """## Conclusion générale

Les données étudiées ne montrent pas un effondrement uniforme de toutes les catégories. Elles décrivent toutefois un système compétitif national **structurellement étroit**, dont la contraction récente touche principalement les catégories Open et Seniors.

En 2026, les Championnats de France étudiés réunissent **69 participants différents**, contre **109 en 2023**. Sur cette période, la population Jeunes/U21 reste relativement stable, passant de **43 à 41 sportifs**. En revanche, l’Open passe de **21 à 12 participants**, et les catégories Seniors de **45 à 17**.

### Une continuité insuffisante vers l’Open

Le suivi individuel confirme que la faiblesse de l’Open ne constitue pas seulement une variation annuelle.

Parmi les **32 sportifs dont la dernière saison U17 est observée entre 2017 et 2020** :

- **19** sont ensuite retrouvés en U21 dans un délai maximal de trois ans ;
- **9 seulement** sont finalement retrouvés en Open après leur passage en U21.

Le parcours complet U17 → U21 → Open ne concerne donc que **9 sportifs sur 32** dans cette cohorte. Cette observation ne permet pas de conclure que les autres ont abandonné le ski nautique, mais elle montre qu’ils ne sont plus retrouvés dans le périmètre des Championnats de France étudiés.

### Une profondeur compétitive extrêmement limitée

La faiblesse des effectifs est accentuée par leur fragmentation entre les catégories et les disciplines.

Sur les **330 champs catégorie–discipline** étudiés entre 2017 et 2026 :

- **50** ne comptent aucun participant ;
- **103** ne réunissent qu’un à trois concurrents ;
- **153 sur 330** comptent donc au maximum trois participants, champs vides inclus ;
- parmi les **280 champs effectivement disputés**, **103** ne dépassent pas trois concurrents ;
- **279 sur 330** comptent moins de dix participants ;
- seuls **3 champs sur 330** atteignent vingt participants ou davantage.

Parmi les champs effectivement disputés, l’effectif médian n’est que de **8 participants en slalom**, de **4 en figures** et de **4 en saut**.

En 2026, l’Open ne compte que **10 concurrents en slalom**, **6 en figures** et **4 en saut**. Dans ce dernier cas, une seule personne représente un quart du champ.

### Un noyau durable très réduit

Entre 2017 et 2026, **289 personnes différentes** apparaissent au moins une fois dans les Championnats de France étudiés. Cette population cumulée ne correspond cependant pas à un vivier durable de même ampleur.

La médiane n’est que de **deux années de participation** par personne :

- **109 personnes** ne sont observées qu’une seule année ;
- **182 sur 289** apparaissent pendant trois années au maximum ;
- seules **39 personnes** sont présentes pendant au moins sept années ;
- **3 seulement** sont observées chacune des dix saisons.

Parmi les **103 participants recensés en 2017**, seuls **18** sont également présents en 2026, sans que cela implique nécessairement une participation continue entre ces deux dates.

### Portée générale des résultats

La participation aux Championnats de France étant libre, sans sélection préalable, les faibles effectifs observés ne peuvent pas être expliqués par des quotas d’accès à la compétition. Ils mesurent directement la faible profondeur du vivier compétitif national présent sur ces événements.

Ces résultats conduisent à distinguer deux dimensions :

- la valeur sportive individuelle d’une performance ou d’une médaille ;
- la solidité collective de la filière dans laquelle cette performance est obtenue.

Une médaille conserve naturellement sa valeur pour le sportif qui l’obtient. Elle ne suffit cependant pas, à elle seule, à démontrer la profondeur d’une catégorie, la continuité d’une filière ou l’efficacité structurelle du système compétitif.

L’évaluation de la politique sportive fédérale devrait donc intégrer systématiquement, en complément des résultats internationaux :

- les effectifs exacts et leurs dénominateurs ;
- la taille des champs par catégorie et par discipline ;
- la fidélisation d’une saison à l’autre ;
- les passages U17 → U21 → Open ;
- la durée réelle de présence des sportifs dans les compétitions nationales ;
- l’évolution différenciée des populations féminines et masculines.

Le constat principal est ainsi moins celui d’une disparition générale des jeunes que celui d’une **filière nationale très peu profonde, fortement fragmentée et insuffisamment capable de transformer durablement ses pratiquants jeunes en compétiteurs Open**.
"""


report = REPORT_FILE.read_text(
    encoding="utf-8"
)

if OLD_HEADING not in report:
    raise RuntimeError(
        "La conclusion provisoire est introuvable."
    )

before = report.split(
    OLD_HEADING,
    1,
)[0].rstrip()

report = (
    before
    + "\n\n"
    + NEW_CONCLUSION.strip()
    + "\n"
)

REPORT_FILE.write_text(
    report,
    encoding="utf-8",
)


print("=" * 82)
print("CONCLUSION GENERALE MISE A JOUR")
print("=" * 82)
print("Note :", REPORT_FILE)
print(
    "Derniere section :",
    "Conclusion generale",
)
print(
    "Nombre de lignes :",
    len(report.splitlines()),
)
