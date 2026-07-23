"""Exporte le rapport décennal principal v5 en PDF et crée ses aperçus.

Entrées
-------
reports/rapport_decennal_principal_2017_2026_v5.md
reports/figures/rapport_decennal_v5/*.png
reports/figures/filiere_open_v2/*.png

Sorties
-------
reports/rapport_decennal_principal_2017_2026_v5.pdf
reports/previews/rapport_decennal_v5_pdf/page_*.png
reports/previews/rapport_decennal_v5_pdf/contact_sheet.png

Contrôles
---------
- huit figures référencées et intègres ;
- absence des anciennes valeurs de captation ;
- tableaux Markdown convertis en vrais tableaux PDF ;
- PDF A4 paginé avec en-tête et pied de page ;
- texte extractible ;
- rendu de toutes les pages en PNG ;
- planche-contact automatique.
"""

from __future__ import annotations

import html
import re
import shutil
import subprocess
from pathlib import Path
from typing import Iterable

from PIL import Image as PILImage
from PIL import ImageDraw, ImageFont
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    KeepTogether,
    ListFlowable,
    ListItem,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


TITLE = (
    "Championnats de France de ski nautique classique : "
    "rapport décennal principal 2017-2026"
)
AUTHOR = "Observatoire FFSNW"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def find_font(candidates: Iterable[Path]) -> Path | None:
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def register_fonts() -> tuple[str, str]:
    regular = find_font(
        [
            Path(r"C:\Windows\Fonts\arial.ttf"),
            Path(r"C:\Windows\Fonts\calibri.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            Path(
                "/usr/share/fonts/truetype/liberation2/"
                "LiberationSans-Regular.ttf"
            ),
        ]
    )
    bold = find_font(
        [
            Path(r"C:\Windows\Fonts\arialbd.ttf"),
            Path(r"C:\Windows\Fonts\calibrib.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
            Path(
                "/usr/share/fonts/truetype/liberation2/"
                "LiberationSans-Bold.ttf"
            ),
        ]
    )

    if regular and bold:
        pdfmetrics.registerFont(TTFont("ReportSans", str(regular)))
        pdfmetrics.registerFont(TTFont("ReportSans-Bold", str(bold)))
        pdfmetrics.registerFontFamily(
            "ReportSans",
            normal="ReportSans",
            bold="ReportSans-Bold",
        )
        return "ReportSans", "ReportSans-Bold"

    return "Helvetica", "Helvetica-Bold"


def markdown_inline(text: str) -> str:
    escaped = html.escape(text, quote=False)
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", escaped)
    escaped = re.sub(
        r"(?<!\*)\*([^*]+?)\*(?!\*)",
        r"<i>\1</i>",
        escaped,
    )
    escaped = escaped.replace("→", "-&gt;")
    return escaped


class ReportDocTemplate(BaseDocTemplate):
    def __init__(
        self,
        filename: str,
        *,
        font_name: str,
        bold_font_name: str,
    ) -> None:
        super().__init__(
            filename,
            pagesize=A4,
            leftMargin=1.65 * cm,
            rightMargin=1.65 * cm,
            topMargin=1.85 * cm,
            bottomMargin=1.65 * cm,
            title=TITLE,
            author=AUTHOR,
            subject=(
                "Analyse décennale de la participation et de la filière "
                "U21-Open"
            ),
        )
        self.font_name = font_name
        self.bold_font_name = bold_font_name

        frame = Frame(
            self.leftMargin,
            self.bottomMargin,
            self.width,
            self.height,
            id="normal",
        )
        self.addPageTemplates(
            [
                PageTemplate(
                    id="report",
                    frames=[frame],
                    onPage=self.draw_header_footer,
                )
            ]
        )

    def draw_header_footer(self, canvas, doc) -> None:
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#B8BEC6"))
        canvas.setLineWidth(0.4)
        canvas.line(
            self.leftMargin,
            A4[1] - 1.25 * cm,
            A4[0] - self.rightMargin,
            A4[1] - 1.25 * cm,
        )

        canvas.setFont(self.font_name, 7.3)
        canvas.setFillColor(colors.HexColor("#5B6470"))
        canvas.drawString(
            self.leftMargin,
            A4[1] - 1.02 * cm,
            "Observatoire FFSNW - Rapport décennal 2017-2026",
        )
        canvas.drawRightString(
            A4[0] - self.rightMargin,
            0.75 * cm,
            f"Page {doc.page}",
        )
        canvas.restoreState()


def build_styles(font_name: str, bold_font_name: str):
    base = getSampleStyleSheet()

    return {
        "title": ParagraphStyle(
            "ReportTitle",
            parent=base["Title"],
            fontName=bold_font_name,
            fontSize=21,
            leading=25.5,
            alignment=TA_LEFT,
            textColor=colors.HexColor("#152238"),
            spaceAfter=15,
        ),
        "subtitle": ParagraphStyle(
            "ReportSubtitle",
            parent=base["Normal"],
            fontName=font_name,
            fontSize=10,
            leading=14.5,
            textColor=colors.HexColor("#4E5968"),
            backColor=colors.HexColor("#EEF1F5"),
            borderPadding=(8, 10, 8, 10),
            spaceAfter=16,
        ),
        "h2": ParagraphStyle(
            "Heading2Custom",
            parent=base["Heading2"],
            fontName=bold_font_name,
            fontSize=14.2,
            leading=18,
            textColor=colors.HexColor("#173B63"),
            spaceBefore=12,
            spaceAfter=7,
            keepWithNext=True,
        ),
        "body": ParagraphStyle(
            "BodyCustom",
            parent=base["BodyText"],
            fontName=font_name,
            fontSize=9.15,
            leading=13.5,
            alignment=TA_JUSTIFY,
            textColor=colors.HexColor("#20242A"),
            spaceAfter=7,
        ),
        "bullet": ParagraphStyle(
            "BulletCustom",
            parent=base["BodyText"],
            fontName=font_name,
            fontSize=8.9,
            leading=12.8,
            textColor=colors.HexColor("#20242A"),
        ),
        "caption": ParagraphStyle(
            "CaptionCustom",
            parent=base["BodyText"],
            fontName=font_name,
            fontSize=7.8,
            leading=10.5,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#5F6875"),
            spaceBefore=2,
            spaceAfter=7,
        ),
        "table_header": ParagraphStyle(
            "TableHeader",
            parent=base["BodyText"],
            fontName=bold_font_name,
            fontSize=7.2,
            leading=8.8,
            alignment=TA_CENTER,
            textColor=colors.white,
        ),
        "table_cell": ParagraphStyle(
            "TableCell",
            parent=base["BodyText"],
            fontName=font_name,
            fontSize=7.1,
            leading=8.8,
            alignment=TA_LEFT,
            textColor=colors.HexColor("#20242A"),
        ),
    }


def validate_markdown_and_images(
    markdown_path: Path,
) -> tuple[str, list[tuple[str, Path]]]:
    text = markdown_path.read_text(
        encoding="utf-8",
        errors="strict",
    )

    forbidden = {
        r"\b51[,.]2\s*%": "ancien taux de captation de 51,2 %",
        r"\b21\s*/\s*41\b": "ancien ratio de captation 21/41",
        r"capacité à absorber durablement les coûts":
            "ancienne inférence économique sur les Seniors",
    }
    for pattern, label in forbidden.items():
        if re.search(pattern, text, flags=re.IGNORECASE):
            raise RuntimeError(
                f"Le rapport contient encore : {label}."
            )

    required_phrases = [
        "poids numérique théorique du podium",
        "Open français distincts",
        "ressources économiques",
        "La participation aux Championnats se contracte fortement",
        "Le calendrier est abondant au regard",
    ]
    for phrase in required_phrases:
        if phrase not in text:
            raise RuntimeError(
                f"Formulation attendue absente : {phrase}"
            )

    image_refs = re.findall(
        r"!\[([^\]]*)\]\(([^)]+)\)",
        text,
    )
    if len(image_refs) != 8:
        raise RuntimeError(
            f"Huit figures attendues, {len(image_refs)} trouvée(s)."
        )

    validated: list[tuple[str, Path]] = []
    for alt, relative in image_refs:
        image_path = (markdown_path.parent / relative).resolve()
        if not image_path.exists():
            raise FileNotFoundError(image_path)

        with PILImage.open(image_path) as image:
            image.verify()

        with PILImage.open(image_path) as image:
            width, height = image.size

        if width < 700 or height < 350:
            raise RuntimeError(
                f"Figure trop petite : {image_path.name} "
                f"({width} x {height})."
            )

        validated.append((alt, image_path))

    return text, validated


def flush_paragraph(story: list, lines: list[str], style) -> None:
    if not lines:
        return

    text = " ".join(line.strip() for line in lines).strip()
    if text:
        story.append(Paragraph(markdown_inline(text), style))
    lines.clear()


def create_scaled_image(
    path: Path,
    max_width: float,
    max_height: float,
) -> Image:
    with PILImage.open(path) as source:
        width_px, height_px = source.size

    ratio = min(
        max_width / width_px,
        max_height / height_px,
    )

    return Image(
        str(path),
        width=width_px * ratio,
        height=height_px * ratio,
        hAlign="CENTER",
    )


def split_table_row(line: str) -> list[str]:
    content = line.strip().strip("|")
    return [cell.strip() for cell in content.split("|")]


def is_separator_row(cells: list[str]) -> bool:
    return all(
        bool(re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")))
        for cell in cells
    )


def make_table(
    rows: list[list[str]],
    styles,
    max_width: float,
) -> Table:
    if len(rows) < 2:
        raise RuntimeError("Tableau Markdown incomplet.")

    header = rows[0]
    body = rows[1:]

    paragraph_rows = [
        [
            Paragraph(
                markdown_inline(cell),
                styles["table_header"],
            )
            for cell in header
        ]
    ]
    for row in body:
        paragraph_rows.append(
            [
                Paragraph(
                    markdown_inline(cell),
                    styles["table_cell"],
                )
                for cell in row
            ]
        )

    columns = len(header)
    if columns == 3:
        widths = [
            max_width * 0.25,
            max_width * 0.38,
            max_width * 0.37,
        ]
    elif columns == 5:
        widths = [
            max_width * 0.10,
            max_width * 0.18,
            max_width * 0.18,
            max_width * 0.22,
            max_width * 0.32,
        ]
    else:
        widths = [max_width / columns] * columns

    table = Table(
        paragraph_rows,
        colWidths=widths,
        repeatRows=1,
        hAlign="CENTER",
    )
    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#315A7D"),
                ),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.4,
                    colors.HexColor("#B8BEC6"),
                ),
                (
                    "BACKGROUND",
                    (0, 1),
                    (-1, -1),
                    colors.HexColor("#F8F9FB"),
                ),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def markdown_to_story(
    markdown_text: str,
    markdown_path: Path,
    styles,
    max_width: float,
) -> list:
    story: list = []
    paragraph_lines: list[str] = []
    bullet_lines: list[str] = []

    lines = markdown_text.splitlines()
    index = 0
    first_title_seen = False

    def flush_bullets() -> None:
        nonlocal bullet_lines
        if not bullet_lines:
            return

        items = [
            ListItem(
                Paragraph(markdown_inline(item), styles["bullet"]),
                leftIndent=12,
            )
            for item in bullet_lines
        ]
        story.append(
            ListFlowable(
                items,
                bulletType="bullet",
                leftIndent=16,
                bulletFontName=styles["body"].fontName,
                bulletFontSize=7,
                spaceAfter=7,
            )
        )
        bullet_lines = []

    while index < len(lines):
        stripped = lines[index].strip()

        if stripped.startswith("|") and stripped.endswith("|"):
            flush_paragraph(story, paragraph_lines, styles["body"])
            flush_bullets()

            table_lines: list[str] = []
            while (
                index < len(lines)
                and lines[index].strip().startswith("|")
                and lines[index].strip().endswith("|")
            ):
                table_lines.append(lines[index].strip())
                index += 1

            parsed = [split_table_row(line) for line in table_lines]
            parsed = [
                row
                for row in parsed
                if not is_separator_row(row)
            ]
            story.append(make_table(parsed, styles, max_width))
            story.append(Spacer(1, 7))
            continue

        if stripped == "<!-- PAGEBREAK -->":
            flush_paragraph(story, paragraph_lines, styles["body"])
            flush_bullets()
            story.append(PageBreak())
            index += 1
            continue

        image_match = re.fullmatch(
            r"!\[([^\]]*)\]\(([^)]+)\)",
            stripped,
        )

        if image_match:
            flush_paragraph(story, paragraph_lines, styles["body"])
            flush_bullets()

            alt, relative = image_match.groups()
            image_path = (markdown_path.parent / relative).resolve()
            figure = create_scaled_image(
                image_path,
                max_width=max_width,
                max_height=12.9 * cm,
            )
            story.append(
                KeepTogether(
                    [
                        Spacer(1, 3),
                        figure,
                        Paragraph(
                            markdown_inline(alt),
                            styles["caption"],
                        ),
                    ]
                )
            )
            index += 1
            continue

        if not stripped:
            flush_paragraph(story, paragraph_lines, styles["body"])
            flush_bullets()
            index += 1
            continue

        if stripped.startswith("# "):
            flush_paragraph(story, paragraph_lines, styles["body"])
            flush_bullets()
            story.append(
                Paragraph(
                    markdown_inline(stripped[2:].strip()),
                    styles["title"],
                )
            )
            first_title_seen = True
            index += 1
            continue

        if stripped.startswith("## "):
            flush_paragraph(story, paragraph_lines, styles["body"])
            flush_bullets()

            heading = stripped[3:].strip()

            if heading == "14. Conclusion générale":
                story.append(PageBreak())

            story.append(
                Paragraph(
                    markdown_inline(heading),
                    styles["h2"],
                )
            )
            index += 1
            continue

        if stripped.startswith("> "):
            flush_paragraph(story, paragraph_lines, styles["body"])
            flush_bullets()
            story.append(
                Paragraph(
                    markdown_inline(stripped[2:].strip()),
                    styles["subtitle"],
                )
            )
            index += 1
            continue

        if stripped.startswith("- "):
            flush_paragraph(story, paragraph_lines, styles["body"])
            bullet_lines.append(stripped[2:].strip())
            index += 1
            continue

        if bullet_lines:
            flush_bullets()

        if (
            len(stripped) >= 2
            and stripped.startswith("*")
            and stripped.endswith("*")
            and not stripped.startswith("**")
        ):
            flush_paragraph(story, paragraph_lines, styles["body"])
            story.append(
                Paragraph(
                    markdown_inline(stripped),
                    styles["caption"],
                )
            )
            index += 1
            continue

        paragraph_lines.append(stripped)
        index += 1

    flush_paragraph(story, paragraph_lines, styles["body"])
    flush_bullets()
    return story


def render_previews(
    pdf_path: Path,
    preview_dir: Path,
) -> int:
    if preview_dir.exists():
        shutil.rmtree(preview_dir)
    preview_dir.mkdir(parents=True, exist_ok=True)

    try:
        import fitz  # type: ignore

        document = fitz.open(pdf_path)
        matrix = fitz.Matrix(1.45, 1.45)
        for page_index in range(document.page_count):
            page = document.load_page(page_index)
            pixmap = page.get_pixmap(
                matrix=matrix,
                alpha=False,
            )
            pixmap.save(
                preview_dir / f"page_{page_index + 1:02d}.png"
            )
        count = document.page_count
        document.close()
        return count

    except ImportError:
        pass

    executable = shutil.which("pdftoppm")
    if executable:
        prefix = preview_dir / "page"
        result = subprocess.run(
            [
                executable,
                "-png",
                "-r",
                "120",
                str(pdf_path),
                str(prefix),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(
                "Échec pdftoppm : " + result.stderr.strip()
            )
        return len(list(preview_dir.glob("page-*.png")))

    raise RuntimeError(
        "Aucun moteur de rendu disponible. "
        "Installer PyMuPDF : pip install pymupdf"
    )


def inspect_pdf(pdf_path: Path) -> tuple[int | None, int | None]:
    for module_name in ("pypdf", "PyPDF2"):
        try:
            module = __import__(module_name)
            reader = module.PdfReader(str(pdf_path))
            page_count = len(reader.pages)
            text_length = sum(
                len(page.extract_text() or "")
                for page in reader.pages
            )
            return page_count, text_length
        except ImportError:
            continue

    return None, None


def load_contact_font(size: int):
    candidates = [
        Path(r"C:\Windows\Fonts\arial.ttf"),
        Path(r"C:\Windows\Fonts\calibri.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default()


def create_contact_sheet(
    preview_dir: Path,
) -> Path:
    pages = sorted(preview_dir.glob("page_*.png"))
    if not pages:
        pages = sorted(preview_dir.glob("page-*.png"))
    if not pages:
        raise RuntimeError("Aucun aperçu à placer dans la planche-contact.")

    images = [PILImage.open(path).convert("RGB") for path in pages]

    columns = 2
    thumb_width = 700
    margin = 40
    label_height = 42
    rows = (len(images) + columns - 1) // columns

    thumbs: list[PILImage.Image] = []
    for image in images:
        ratio = thumb_width / image.width
        thumbs.append(
            image.resize(
                (thumb_width, round(image.height * ratio)),
                PILImage.Resampling.LANCZOS,
            )
        )

    cell_height = max(image.height for image in thumbs) + label_height
    sheet_width = columns * thumb_width + (columns + 1) * margin
    sheet_height = rows * cell_height + (rows + 1) * margin

    sheet = PILImage.new(
        "RGB",
        (sheet_width, sheet_height),
        "white",
    )
    draw = ImageDraw.Draw(sheet)
    font = load_contact_font(26)

    for index, image in enumerate(thumbs):
        row = index // columns
        column = index % columns
        x = margin + column * (thumb_width + margin)
        y = margin + row * (cell_height + margin)

        draw.text(
            (x, y),
            f"Page {index + 1}",
            fill="black",
            font=font,
        )
        sheet.paste(image, (x, y + label_height))

    output = preview_dir / "contact_sheet.png"
    sheet.save(output, quality=92)

    for image in images:
        image.close()

    return output


def main() -> None:
    root = repo_root()
    markdown_path = (
        root
        / "reports/rapport_decennal_principal_2017_2026_v5.md"
    )
    pdf_path = (
        root
        / "reports/rapport_decennal_principal_2017_2026_v5.pdf"
    )
    preview_dir = (
        root
        / "reports/previews/rapport_decennal_v5_pdf"
    )

    if not markdown_path.exists():
        raise FileNotFoundError(markdown_path)

    markdown_text, images = validate_markdown_and_images(
        markdown_path
    )

    font_name, bold_font_name = register_fonts()
    styles = build_styles(font_name, bold_font_name)

    document = ReportDocTemplate(
        str(pdf_path),
        font_name=font_name,
        bold_font_name=bold_font_name,
    )
    story = markdown_to_story(
        markdown_text,
        markdown_path,
        styles,
        max_width=document.width,
    )
    document.build(story)

    if not pdf_path.exists() or pdf_path.stat().st_size < 100_000:
        raise RuntimeError(
            "Le PDF n'a pas été généré correctement."
        )

    page_count, text_length = inspect_pdf(pdf_path)
    rendered_pages = render_previews(pdf_path, preview_dir)
    contact_sheet = create_contact_sheet(preview_dir)

    if page_count is not None and page_count != rendered_pages:
        raise RuntimeError(
            f"Nombre de pages incohérent : PDF={page_count}, "
            f"rendus={rendered_pages}."
        )

    print("=" * 88)
    print("RAPPORT DÉCENNAL PRINCIPAL V5 EXPORTÉ")
    print("=" * 88)
    print(f"Figures validées : {len(images)}")
    print(f"PDF              : {pdf_path}")
    print(f"Taille PDF       : {pdf_path.stat().st_size} octets")
    print(
        f"Pages            : "
        f"{page_count if page_count is not None else rendered_pages}"
    )
    print(
        f"Texte extrait    : "
        f"{text_length if text_length is not None else 'non vérifié'} "
        "caractères"
    )
    print(f"Aperçus          : {preview_dir}")
    print(f"Planche-contact  : {contact_sheet}")


if __name__ == "__main__":
    main()
