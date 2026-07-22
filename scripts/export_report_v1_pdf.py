"""Exporte le rapport V1 Markdown en PDF mis en page."""

from __future__ import annotations

import html
import re
from pathlib import Path

import reportlab
from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents


ROOT = Path(__file__).resolve().parents[1]

SOURCE_FILE = ROOT / (
    "reports/rapport_v1_participation_podiums_2017_2026.md"
)

OUTPUT_FILE = ROOT / (
    "reports/rapport_v1_participation_podiums_2017_2026.pdf"
)


TITLE = "Participation et profondeur des champs de compétition"

SUBTITLE = (
    "Championnats de France de ski nautique classique"
    " - 2017-2026"
)

REPORT_DATE = "Rapport V1 - juillet 2026"


def register_fonts() -> tuple[str, str, str, str]:
    reportlab_fonts = (
        Path(reportlab.__file__).resolve().parent / "fonts"
    )

    candidates = [
        (
            Path(r"C:\Windows\Fonts\arial.ttf"),
            Path(r"C:\Windows\Fonts\arialbd.ttf"),
            Path(r"C:\Windows\Fonts\ariali.ttf"),
            Path(r"C:\Windows\Fonts\arialbi.ttf"),
        ),
        (
            reportlab_fonts / "Vera.ttf",
            reportlab_fonts / "VeraBd.ttf",
            reportlab_fonts / "VeraIt.ttf",
            reportlab_fonts / "VeraBI.ttf",
        ),
    ]

    for regular, bold, italic, bold_italic in candidates:
        if all(
            path.exists()
            for path in (
                regular,
                bold,
                italic,
                bold_italic,
            )
        ):
            pdfmetrics.registerFont(
                TTFont(
                    "ObsRegular",
                    str(regular),
                )
            )
            pdfmetrics.registerFont(
                TTFont(
                    "ObsBold",
                    str(bold),
                )
            )
            pdfmetrics.registerFont(
                TTFont(
                    "ObsItalic",
                    str(italic),
                )
            )
            pdfmetrics.registerFont(
                TTFont(
                    "ObsBoldItalic",
                    str(bold_italic),
                )
            )

            pdfmetrics.registerFontFamily(
                "Obs",
                normal="ObsRegular",
                bold="ObsBold",
                italic="ObsItalic",
                boldItalic="ObsBoldItalic",
            )

            return (
                "ObsRegular",
                "ObsBold",
                "ObsItalic",
                "ObsBoldItalic",
            )

    raise RuntimeError(
        "Aucune famille de polices compatible n'a été trouvée."
    )


FONT_REGULAR, FONT_BOLD, FONT_ITALIC, FONT_BOLD_ITALIC = (
    register_fonts()
)


class ReportDocTemplate(BaseDocTemplate):
    """Document avec sommaire, signets et pages portrait/paysage."""

    def __init__(self, filename: str):
        super().__init__(
            filename,
            pagesize=A4,
            leftMargin=17 * mm,
            rightMargin=17 * mm,
            topMargin=19 * mm,
            bottomMargin=17 * mm,
            title=TITLE,
            author="Observatoire FFSNW",
            subject=(
                "Participation aux Championnats de France "
                "de ski nautique classique"
            ),
        )

        self._heading_sequence = 0

        portrait_width, portrait_height = A4

        portrait_frame = Frame(
            17 * mm,
            17 * mm,
            portrait_width - 34 * mm,
            portrait_height - 36 * mm,
            id="portrait_frame",
        )

        title_frame = Frame(
            22 * mm,
            20 * mm,
            portrait_width - 44 * mm,
            portrait_height - 40 * mm,
            id="title_frame",
        )

        landscape_width, landscape_height = landscape(A4)

        landscape_frame = Frame(
            12 * mm,
            15 * mm,
            landscape_width - 24 * mm,
            landscape_height - 31 * mm,
            id="landscape_frame",
        )

        self.addPageTemplates(
            [
                PageTemplate(
                    id="Title",
                    pagesize=A4,
                    frames=[title_frame],
                    onPage=self.draw_title_page,
                ),
                PageTemplate(
                    id="Portrait",
                    pagesize=A4,
                    frames=[portrait_frame],
                    onPage=self.draw_body_page,
                ),
                PageTemplate(
                    id="Landscape",
                    pagesize=landscape(A4),
                    frames=[landscape_frame],
                    onPage=self.draw_body_page,
                ),
            ]
        )

    def draw_title_page(self, canvas, doc):
        canvas.saveState()

        width, _ = canvas._pagesize

        canvas.setStrokeColor(
            colors.HexColor("#1F4E79")
        )
        canvas.setLineWidth(2)
        canvas.line(
            22 * mm,
            18 * mm,
            width - 22 * mm,
            18 * mm,
        )

        canvas.setFont(
            FONT_REGULAR,
            8,
        )
        canvas.setFillColor(
            colors.HexColor("#5B6573")
        )
        canvas.drawString(
            22 * mm,
            12 * mm,
            "Observatoire FFSNW",
        )

        canvas.restoreState()

    def draw_body_page(self, canvas, doc):
        canvas.saveState()

        width, height = canvas._pagesize

        canvas.setStrokeColor(
            colors.HexColor("#D5DAE0")
        )
        canvas.setLineWidth(0.5)

        canvas.line(
            12 * mm,
            height - 12 * mm,
            width - 12 * mm,
            height - 12 * mm,
        )

        canvas.line(
            12 * mm,
            11 * mm,
            width - 12 * mm,
            11 * mm,
        )

        canvas.setFillColor(
            colors.HexColor("#5B6573")
        )
        canvas.setFont(
            FONT_REGULAR,
            7.5,
        )

        canvas.drawString(
            12 * mm,
            height - 9 * mm,
            "Observatoire FFSNW - Participation 2017-2026",
        )

        printed_page = max(
            1,
            canvas.getPageNumber() - 1,
        )

        canvas.drawRightString(
            width - 12 * mm,
            6.5 * mm,
            str(printed_page),
        )

        canvas.restoreState()

    def afterFlowable(self, flowable):
        if not isinstance(
            flowable,
            Paragraph,
        ):
            return

        style_name = flowable.style.name

        levels = {
            "ReportHeading1": 0,
            "ReportHeading2": 1,
        }

        if style_name not in levels:
            return

        level = levels[style_name]
        text = flowable.getPlainText()

        self._heading_sequence += 1

        key = (
            f"heading-{level}-"
            f"{self._heading_sequence}"
        )

        page_number = max(
            1,
            self.page - 1,
        )

        self.canv.bookmarkPage(key)

        self.canv.addOutlineEntry(
            text,
            key,
            level=level,
            closed=False,
        )

        self.notify(
            "TOCEntry",
            (
                level,
                text,
                page_number,
                key,
            ),
        )


styles = getSampleStyleSheet()


styles.add(
    ParagraphStyle(
        name="ReportTitle",
        parent=styles["Title"],
        fontName=FONT_BOLD,
        fontSize=25,
        leading=30,
        textColor=colors.HexColor("#17365D"),
        alignment=TA_LEFT,
        spaceAfter=8 * mm,
    )
)

styles.add(
    ParagraphStyle(
        name="ReportSubtitle",
        parent=styles["Normal"],
        fontName=FONT_REGULAR,
        fontSize=15,
        leading=20,
        textColor=colors.HexColor("#3F4A56"),
        alignment=TA_LEFT,
        spaceAfter=5 * mm,
    )
)

styles.add(
    ParagraphStyle(
        name="ReportDate",
        parent=styles["Normal"],
        fontName=FONT_ITALIC,
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#68717C"),
        spaceAfter=18 * mm,
    )
)

styles.add(
    ParagraphStyle(
        name="ReportHeading1",
        parent=styles["Heading1"],
        fontName=FONT_BOLD,
        fontSize=16,
        leading=20,
        textColor=colors.HexColor("#17365D"),
        spaceBefore=7 * mm,
        spaceAfter=3.5 * mm,
        keepWithNext=True,
    )
)

styles.add(
    ParagraphStyle(
        name="ReportHeading2",
        parent=styles["Heading2"],
        fontName=FONT_BOLD,
        fontSize=12,
        leading=15,
        textColor=colors.HexColor("#2E5D86"),
        spaceBefore=5 * mm,
        spaceAfter=2.5 * mm,
        keepWithNext=True,
    )
)

styles.add(
    ParagraphStyle(
        name="ReportBody",
        parent=styles["BodyText"],
        fontName=FONT_REGULAR,
        fontSize=9.5,
        leading=14,
        alignment=TA_JUSTIFY,
        textColor=colors.HexColor("#20252B"),
        spaceAfter=2.8 * mm,
    )
)

styles.add(
    ParagraphStyle(
        name="ReportBullet",
        parent=styles["BodyText"],
        fontName=FONT_REGULAR,
        fontSize=9.3,
        leading=13,
        leftIndent=5 * mm,
        firstLineIndent=-3.5 * mm,
        spaceAfter=1.8 * mm,
    )
)

styles.add(
    ParagraphStyle(
        name="ReportCaption",
        parent=styles["Normal"],
        fontName=FONT_ITALIC,
        fontSize=8,
        leading=11,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#5B6573"),
        spaceBefore=1.5 * mm,
        spaceAfter=4 * mm,
    )
)

styles.add(
    ParagraphStyle(
        name="ReportTableCell",
        parent=styles["Normal"],
        fontName=FONT_REGULAR,
        fontSize=7.3,
        leading=8.8,
        alignment=TA_CENTER,
    )
)

styles.add(
    ParagraphStyle(
        name="ReportTableHeader",
        parent=styles["Normal"],
        fontName=FONT_BOLD,
        fontSize=7.2,
        leading=8.5,
        alignment=TA_CENTER,
        textColor=colors.white,
    )
)

styles.add(
    ParagraphStyle(
        name="WideTableCell",
        parent=styles["Normal"],
        fontName=FONT_REGULAR,
        fontSize=6.2,
        leading=7.3,
        alignment=TA_CENTER,
    )
)

styles.add(
    ParagraphStyle(
        name="WideTableHeader",
        parent=styles["Normal"],
        fontName=FONT_BOLD,
        fontSize=6.1,
        leading=7.1,
        alignment=TA_CENTER,
        textColor=colors.white,
    )
)

styles.add(
    ParagraphStyle(
        name="KeyNumber",
        parent=styles["Normal"],
        fontName=FONT_BOLD,
        fontSize=22,
        leading=25,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#17365D"),
        spaceAfter=2 * mm,
    )
)

styles.add(
    ParagraphStyle(
        name="KeyLabel",
        parent=styles["Normal"],
        fontName=FONT_REGULAR,
        fontSize=8.5,
        leading=11,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#414A54"),
    )
)

styles.add(
    ParagraphStyle(
        name="TocTitle",
        parent=styles["Heading1"],
        fontName=FONT_BOLD,
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#17365D"),
        spaceAfter=7 * mm,
    )
)


def inline_markup(text: str) -> str:
    protected: list[str] = []

    def protect_code(match):
        index = len(protected)

        protected.append(
            "<font name='Courier'>"
            + html.escape(match.group(1))
            + "</font>"
        )

        return f"@@CODE{index}@@"

    text = re.sub(
        r"`([^`]+)`",
        protect_code,
        text,
    )

    text = html.escape(
        text,
        quote=False,
    )

    text = re.sub(
        r"\*\*(.+?)\*\*",
        r"<b>\1</b>",
        text,
    )

    for index, value in enumerate(protected):
        text = text.replace(
            f"@@CODE{index}@@",
            value,
        )

    return text


def parse_table_row(line: str) -> list[str]:
    return [
        cell.strip()
        for cell in line.strip().strip("|").split("|")
    ]


def is_separator_row(line: str) -> bool:
    cells = parse_table_row(line)

    return bool(cells) and all(
        re.fullmatch(
            r":?-{3,}:?",
            cell,
        )
        for cell in cells
    )


def normalized_widths(
    total_width: float,
    weights: list[float],
) -> list[float]:
    total = sum(weights)

    return [
        total_width * weight / total
        for weight in weights
    ]


def build_table(
    raw_rows: list[list[str]],
) -> tuple[list, bool]:
    column_count = len(raw_rows[0])
    wide = column_count >= 8

    header_style = (
        styles["WideTableHeader"]
        if wide
        else styles["ReportTableHeader"]
    )

    body_style = (
        styles["WideTableCell"]
        if wide
        else styles["ReportTableCell"]
    )

    table_data = []

    for row_index, raw_row in enumerate(raw_rows):
        style = (
            header_style
            if row_index == 0
            else body_style
        )

        table_data.append(
            [
                Paragraph(
                    inline_markup(cell),
                    style,
                )
                for cell in raw_row
            ]
        )

    if column_count == 2:
        available_width = A4[0] - 34 * mm
        weights = [1.0, 1.0]

    elif column_count == 6:
        available_width = A4[0] - 34 * mm
        weights = [
            0.9,
            0.7,
            1.15,
            1.15,
            1.0,
            1.15,
        ]

    elif column_count == 10:
        available_width = landscape(A4)[0] - 24 * mm
        weights = [
            1.25,
            0.55,
            0.9,
            1.0,
            0.95,
            0.95,
            1.05,
            1.35,
            1.05,
            1.05,
        ]

    else:
        available_width = (
            landscape(A4)[0] - 24 * mm
            if wide
            else A4[0] - 34 * mm
        )

        weights = [
            1.0
            for _ in range(column_count)
        ]

    table = Table(
        table_data,
        colWidths=normalized_widths(
            available_width,
            weights,
        ),
        repeatRows=1,
        splitByRow=True,
        hAlign="CENTER",
    )

    table_style = [
        (
            "BACKGROUND",
            (0, 0),
            (-1, 0),
            colors.HexColor("#1F4E79"),
        ),
        (
            "TEXTCOLOR",
            (0, 0),
            (-1, 0),
            colors.white,
        ),
        (
            "GRID",
            (0, 0),
            (-1, -1),
            0.35,
            colors.HexColor("#B8C0C8"),
        ),
        (
            "VALIGN",
            (0, 0),
            (-1, -1),
            "MIDDLE",
        ),
        (
            "LEFTPADDING",
            (0, 0),
            (-1, -1),
            2.5,
        ),
        (
            "RIGHTPADDING",
            (0, 0),
            (-1, -1),
            2.5,
        ),
        (
            "TOPPADDING",
            (0, 0),
            (-1, -1),
            3.2,
        ),
        (
            "BOTTOMPADDING",
            (0, 0),
            (-1, -1),
            3.2,
        ),
    ]

    for row_index in range(
        1,
        len(table_data),
    ):
        if row_index % 2 == 0:
            table_style.append(
                (
                    "BACKGROUND",
                    (0, row_index),
                    (-1, row_index),
                    colors.HexColor("#F2F5F8"),
                )
            )

    table.setStyle(
        TableStyle(table_style)
    )

    return [table, Spacer(1, 4 * mm)], wide


def scaled_image(path: Path) -> Image:
    image = Image(
        str(path)
    )

    max_width = A4[0] - 38 * mm
    max_height = 125 * mm

    scale = min(
        max_width / image.imageWidth,
        max_height / image.imageHeight,
        1,
    )

    image.drawWidth = (
        image.imageWidth * scale
    )

    image.drawHeight = (
        image.imageHeight * scale
    )

    image.hAlign = "CENTER"

    return image


def markdown_to_flowables(
    markdown_text: str,
) -> list:
    lines = markdown_text.splitlines()

    start_index = 0

    for index, line in enumerate(lines):
        if line.startswith("## 1."):
            start_index = index
            break

    lines = lines[start_index:]

    story = []
    paragraph_buffer: list[str] = []

    def flush_paragraph():
        nonlocal paragraph_buffer

        if not paragraph_buffer:
            return

        text = " ".join(
            part.strip()
            for part in paragraph_buffer
        )

        story.append(
            Paragraph(
                inline_markup(text),
                styles["ReportBody"],
            )
        )

        paragraph_buffer = []

    index = 0

    while index < len(lines):
        line = lines[index].rstrip()

        if not line.strip():
            flush_paragraph()
            index += 1
            continue

        image_match = re.fullmatch(
            r"!\[(.*?)\]\((.*?)\)",
            line.strip(),
        )

        if image_match:
            flush_paragraph()

            alt_text = image_match.group(1)
            relative_path = image_match.group(2)

            image_path = (
                SOURCE_FILE.parent / relative_path
            ).resolve()

            if image_path.exists():
                story.append(
                    Spacer(
                        1,
                        2 * mm,
                    )
                )

                story.append(
                    scaled_image(image_path)
                )

                story.append(
                    Paragraph(
                        inline_markup(alt_text),
                        styles["ReportCaption"],
                    )
                )

            else:
                story.append(
                    Paragraph(
                        (
                            "<i>Illustration introuvable : "
                            + html.escape(relative_path)
                            + "</i>"
                        ),
                        styles["ReportBody"],
                    )
                )

            index += 1
            continue

        if line.startswith("### "):
            flush_paragraph()

            story.append(
                Paragraph(
                    inline_markup(line[4:].strip()),
                    styles["ReportHeading2"],
                )
            )

            index += 1
            continue

        if line.startswith("## "):
            flush_paragraph()

            story.append(
                Paragraph(
                    inline_markup(line[3:].strip()),
                    styles["ReportHeading1"],
                )
            )

            index += 1
            continue

        if (
            line.strip().startswith("|")
            and index + 1 < len(lines)
            and is_separator_row(
                lines[index + 1]
            )
        ):
            flush_paragraph()

            raw_rows = [
                parse_table_row(line)
            ]

            index += 2

            while (
                index < len(lines)
                and lines[index].strip().startswith("|")
            ):
                raw_rows.append(
                    parse_table_row(
                        lines[index]
                    )
                )

                index += 1

            table_flowables, wide = build_table(
                raw_rows
            )

            if wide:
                story.extend(
                    [
                        NextPageTemplate(
                            "Landscape"
                        ),
                        PageBreak(),
                    ]
                )

                story.extend(
                    table_flowables
                )

                story.extend(
                    [
                        NextPageTemplate(
                            "Portrait"
                        ),
                        PageBreak(),
                    ]
                )

            else:
                story.extend(
                    table_flowables
                )

            continue

        if line.startswith("- "):
            flush_paragraph()

            story.append(
                Paragraph(
                    "• "
                    + inline_markup(
                        line[2:].strip()
                    ),
                    styles["ReportBullet"],
                )
            )

            index += 1
            continue

        paragraph_buffer.append(
            line.strip()
        )

        index += 1

    flush_paragraph()

    return story


if not SOURCE_FILE.exists():
    raise FileNotFoundError(
        SOURCE_FILE
    )


markdown_text = SOURCE_FILE.read_text(
    encoding="utf-8"
)


story = [
    Spacer(
        1,
        35 * mm,
    ),
    Paragraph(
        TITLE,
        styles["ReportTitle"],
    ),
    Paragraph(
        SUBTITLE,
        styles["ReportSubtitle"],
    ),
    Paragraph(
        REPORT_DATE,
        styles["ReportDate"],
    ),
]


key_figures = [
    [
        [
            Paragraph(
                "69",
                styles["KeyNumber"],
            ),
            Paragraph(
                "participants distincts en 2026",
                styles["KeyLabel"],
            ),
        ],
        [
            Paragraph(
                "52 / 104",
                styles["KeyNumber"],
            ),
            Paragraph(
                "champs effectivement disputés",
                styles["KeyLabel"],
            ),
        ],
    ],
    [
        [
            Paragraph(
                "36 / 52",
                styles["KeyNumber"],
            ),
            Paragraph(
                "champs comptant de 1 à 3 participants",
                styles["KeyLabel"],
            ),
        ],
        [
            Paragraph(
                "79,4 %",
                styles["KeyNumber"],
            ),
            Paragraph(
                "des participations couvertes par les podiums",
                styles["KeyLabel"],
            ),
        ],
    ],
]


key_table = Table(
    key_figures,
    colWidths=[
        72 * mm,
        72 * mm,
    ],
    rowHeights=[
        34 * mm,
        34 * mm,
    ],
    hAlign="LEFT",
)


key_table.setStyle(
    TableStyle(
        [
            (
                "BOX",
                (0, 0),
                (-1, -1),
                0.6,
                colors.HexColor("#BFC7D0"),
            ),
            (
                "INNERGRID",
                (0, 0),
                (-1, -1),
                0.4,
                colors.HexColor("#D5DAE0"),
            ),
            (
                "BACKGROUND",
                (0, 0),
                (-1, -1),
                colors.HexColor("#F4F7FA"),
            ),
            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "MIDDLE",
            ),
            (
                "LEFTPADDING",
                (0, 0),
                (-1, -1),
                5 * mm,
            ),
            (
                "RIGHTPADDING",
                (0, 0),
                (-1, -1),
                5 * mm,
            ),
            (
                "TOPPADDING",
                (0, 0),
                (-1, -1),
                4 * mm,
            ),
            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                4 * mm,
            ),
        ]
    )
)


story.extend(
    [
        key_table,
        Spacer(
            1,
            22 * mm,
        ),
        Paragraph(
            (
                "Analyse longitudinale des effectifs, "
                "de la profondeur des champs et du poids "
                "théorique des podiums."
            ),
            styles["ReportBody"],
        ),
        NextPageTemplate(
            "Portrait"
        ),
        PageBreak(),
        Paragraph(
            "Sommaire",
            styles["TocTitle"],
        ),
    ]
)


toc_entries = [
    "1. Objet et perimetre",
    "2. Evolution de la participation annuelle",
    "3. Profondeur des champs et poids des podiums",
    "4. Tableau detaille par categorie, sexe et epreuve - 2026",
    "5. Tableau regroupe par population - 2026",
    "6. Principaux constats",
    "7. Interpretation institutionnelle",
    "8. Limites",
    "9. Conclusion",
    "Sources de donnees",
]

for entry in toc_entries:
    story.append(
        Paragraph(
            entry,
            styles["ReportBody"],
        )
    )

story.append(
    PageBreak()
)

story.extend(
    markdown_to_flowables(
        markdown_text
    )
)


OUTPUT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True,
)


document = ReportDocTemplate(
    str(OUTPUT_FILE)
)

document.build(
    story
)


reader = PdfReader(
    str(OUTPUT_FILE)
)


print("=" * 88)
print("PDF V1 GENERE")
print("=" * 88)
print("Source :", SOURCE_FILE)
print("PDF    :", OUTPUT_FILE)
print("Pages  :", len(reader.pages))
print("Taille :", OUTPUT_FILE.stat().st_size, "octets")
print()
print("Le PDF n'est pas encore ajoute a Git.")
