"""Exporte le rapport illustré de la filière Open v2 en PDF.

Entrées
-------
reports/rapport_filiere_open_2017_2026_v2.md
reports/figures/filiere_open_v2/*.png

Sorties
-------
reports/rapport_filiere_open_2017_2026_v2.pdf
reports/previews/filiere_open_v2_pdf/page_*.png   (si PyMuPDF est disponible)

Contrôles
---------
- vérifie toutes les images référencées par le Markdown ;
- contrôle leurs dimensions et leur intégrité ;
- refuse les anciennes valeurs de captation 2023 ;
- génère un PDF A4 avec en-tête, pied de page et pagination ;
- relit le PDF et tente de le rendre en PNG pour contrôle visuel.
"""

from __future__ import annotations

import html
import re
import shutil
import subprocess
from pathlib import Path
from typing import Iterable

from PIL import Image as PILImage
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
)


TITLE = "Filière compétitive U21 -> Open : diagnostic principal 2017-2026"
AUTHOR = "Observatoire FFSNW"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def find_font(candidates: Iterable[Path]) -> Path | None:
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def register_fonts() -> tuple[str, str]:
    regular_candidates = [
        Path(r"C:\Windows\Fonts\arial.ttf"),
        Path(r"C:\Windows\Fonts\calibri.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"),
    ]
    bold_candidates = [
        Path(r"C:\Windows\Fonts\arialbd.ttf"),
        Path(r"C:\Windows\Fonts\calibrib.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"),
    ]

    regular = find_font(regular_candidates)
    bold = find_font(bold_candidates)

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

    # Gras Markdown.
    escaped = re.sub(
        r"\*\*(.+?)\*\*",
        r"<b>\1</b>",
        escaped,
    )

    # Italique Markdown simple.
    escaped = re.sub(
        r"(?<!\*)\*([^*]+?)\*(?!\*)",
        r"<i>\1</i>",
        escaped,
    )

    # Conserver la flèche avec les polices Unicode ; la remplacer sinon ne
    # serait nécessaire qu'avec Helvetica. ReportLab gère le glyphe si la
    # police enregistrée le contient.
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
            leftMargin=1.8 * cm,
            rightMargin=1.8 * cm,
            topMargin=1.9 * cm,
            bottomMargin=1.8 * cm,
            title=TITLE,
            author=AUTHOR,
            subject="Analyse longitudinale de la filière compétitive U21-Open",
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
            A4[1] - 1.28 * cm,
            A4[0] - self.rightMargin,
            A4[1] - 1.28 * cm,
        )

        canvas.setFont(self.font_name, 7.5)
        canvas.setFillColor(colors.HexColor("#5B6470"))
        canvas.drawString(
            self.leftMargin,
            A4[1] - 1.05 * cm,
            "Observatoire FFSNW - Filière U21 -> Open",
        )
        canvas.drawRightString(
            A4[0] - self.rightMargin,
            0.82 * cm,
            f"Page {doc.page}",
        )

        canvas.restoreState()


def build_styles(font_name: str, bold_font_name: str):
    base = getSampleStyleSheet()

    styles = {
        "title": ParagraphStyle(
            "ReportTitle",
            parent=base["Title"],
            fontName=bold_font_name,
            fontSize=22,
            leading=27,
            alignment=TA_LEFT,
            textColor=colors.HexColor("#152238"),
            spaceAfter=16,
        ),
        "subtitle": ParagraphStyle(
            "ReportSubtitle",
            parent=base["Normal"],
            fontName=font_name,
            fontSize=10.5,
            leading=15,
            textColor=colors.HexColor("#4E5968"),
            backColor=colors.HexColor("#EEF1F5"),
            borderPadding=(8, 10, 8, 10),
            spaceAfter=18,
        ),
        "h2": ParagraphStyle(
            "Heading2Custom",
            parent=base["Heading2"],
            fontName=bold_font_name,
            fontSize=15,
            leading=19,
            textColor=colors.HexColor("#173B63"),
            spaceBefore=14,
            spaceAfter=8,
            keepWithNext=True,
        ),
        "body": ParagraphStyle(
            "BodyCustom",
            parent=base["BodyText"],
            fontName=font_name,
            fontSize=9.5,
            leading=14.2,
            alignment=TA_JUSTIFY,
            textColor=colors.HexColor("#20242A"),
            spaceAfter=8,
        ),
        "bullet": ParagraphStyle(
            "BulletCustom",
            parent=base["BodyText"],
            fontName=font_name,
            fontSize=9.3,
            leading=13.5,
            leftIndent=0,
            firstLineIndent=0,
            textColor=colors.HexColor("#20242A"),
        ),
        "caption": ParagraphStyle(
            "CaptionCustom",
            parent=base["BodyText"],
            fontName=font_name,
            fontSize=8.2,
            leading=11.5,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#5F6875"),
            spaceBefore=3,
            spaceAfter=8,
        ),
        "callout": ParagraphStyle(
            "CalloutCustom",
            parent=base["BodyText"],
            fontName=font_name,
            fontSize=10,
            leading=14.5,
            textColor=colors.HexColor("#233142"),
            backColor=colors.HexColor("#F4F6F8"),
            borderColor=colors.HexColor("#BBC5D0"),
            borderWidth=0.6,
            borderPadding=(8, 10, 8, 10),
            spaceBefore=4,
            spaceAfter=10,
        ),
    }

    return styles


def validate_markdown_and_images(
    markdown_path: Path,
) -> tuple[str, list[tuple[str, Path]]]:
    text = markdown_path.read_text(
        encoding="utf-8",
        errors="strict",
    )

    forbidden_patterns = {
        r"\b51[,.]2\s*%": "ancien taux 2023 de 51,2 %",
        r"\b21\s*/\s*41\b": "ancien ratio 2023 de 21/41",
    }
    for pattern, label in forbidden_patterns.items():
        if re.search(pattern, text):
            raise RuntimeError(
                f"Le rapport contient encore {label}."
            )

    image_refs = re.findall(
        r"!\[([^\]]*)\]\(([^)]+)\)",
        text,
    )
    if len(image_refs) != 6:
        raise RuntimeError(
            f"Six figures attendues, {len(image_refs)} trouvée(s)."
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

        if width < 800 or height < 400:
            raise RuntimeError(
                f"Figure trop petite : {image_path.name} "
                f"({width} x {height})."
            )

        validated.append((alt, image_path))

    return text, validated


def flush_paragraph(
    story: list,
    lines: list[str],
    style,
) -> None:
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
    width = width_px * ratio
    height = height_px * ratio

    return Image(
        str(path),
        width=width,
        height=height,
        hAlign="CENTER",
    )


def markdown_to_story(
    markdown_text: str,
    markdown_path: Path,
    styles,
    max_width: float,
) -> list:
    story: list = []
    paragraph_lines: list[str] = []
    bullet_lines: list[str] = []

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
                spaceAfter=8,
            )
        )
        bullet_lines = []

    lines = markdown_text.splitlines()
    first_title_seen = False

    for line in lines:
        stripped = line.strip()

        if stripped == "<!-- PAGEBREAK -->":
            flush_paragraph(story, paragraph_lines, styles["body"])
            flush_bullets()
            story.append(PageBreak())
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
                max_height=13.8 * cm,
            )
            figure_block = [
                Spacer(1, 4),
                figure,
                Paragraph(
                    markdown_inline(alt),
                    styles["caption"],
                ),
            ]
            story.append(KeepTogether(figure_block))
            continue

        if not stripped:
            flush_paragraph(story, paragraph_lines, styles["body"])
            flush_bullets()
            continue

        if stripped.startswith("# "):
            flush_paragraph(story, paragraph_lines, styles["body"])
            flush_bullets()

            title = stripped[2:].strip()
            story.append(
                Paragraph(markdown_inline(title), styles["title"])
            )
            first_title_seen = True
            continue

        if stripped.startswith("## "):
            flush_paragraph(story, paragraph_lines, styles["body"])
            flush_bullets()

            heading = stripped[3:].strip()
            story.append(
                Paragraph(markdown_inline(heading), styles["h2"])
            )
            continue

        if stripped.startswith("> "):
            flush_paragraph(story, paragraph_lines, styles["body"])
            flush_bullets()

            story.append(
                Paragraph(
                    markdown_inline(stripped[2:].strip()),
                    styles["subtitle"] if first_title_seen else styles["callout"],
                )
            )
            continue

        if stripped.startswith("- "):
            flush_paragraph(story, paragraph_lines, styles["body"])
            bullet_lines.append(stripped[2:].strip())
            continue

        if bullet_lines:
            flush_bullets()

        # Les lignes uniquement en italique sont traitées comme légendes/source.
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
            continue

        paragraph_lines.append(stripped)

    flush_paragraph(story, paragraph_lines, styles["body"])
    flush_bullets()
    return story


def render_previews(pdf_path: Path, preview_dir: Path) -> str:
    if preview_dir.exists():
        shutil.rmtree(preview_dir)
    preview_dir.mkdir(parents=True, exist_ok=True)

    # Méthode privilégiée : PyMuPDF.
    try:
        import fitz  # type: ignore

        document = fitz.open(pdf_path)
        matrix = fitz.Matrix(1.6, 1.6)

        for page_index in range(document.page_count):
            page = document.load_page(page_index)
            pixmap = page.get_pixmap(
                matrix=matrix,
                alpha=False,
            )
            pixmap.save(
                preview_dir / f"page_{page_index + 1:02d}.png"
            )

        page_count = document.page_count
        document.close()
        return f"PyMuPDF : {page_count} page(s) rendue(s)"

    except ImportError:
        pass

    # Second choix : pdftoppm si installé.
    executable = shutil.which("pdftoppm")
    if executable:
        prefix = preview_dir / "page"
        result = subprocess.run(
            [
                executable,
                "-png",
                "-r",
                "130",
                str(pdf_path),
                str(prefix),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            generated = list(preview_dir.glob("page-*.png"))
            return f"pdftoppm : {len(generated)} page(s) rendue(s)"

        return (
            "pdftoppm présent mais échec du rendu : "
            + result.stderr.strip()
        )

    return (
        "Aucun moteur de rendu disponible. "
        "Installer PyMuPDF avec : pip install pymupdf"
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


def main() -> None:
    root = repo_root()
    markdown_path = (
        root / "reports/rapport_filiere_open_2017_2026_v2.md"
    )
    pdf_path = (
        root / "reports/rapport_filiere_open_2017_2026_v2.pdf"
    )
    preview_dir = (
        root / "reports/previews/filiere_open_v2_pdf"
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

    if not pdf_path.exists() or pdf_path.stat().st_size < 50_000:
        raise RuntimeError(
            "Le PDF n'a pas été généré correctement "
            f"({pdf_path.stat().st_size if pdf_path.exists() else 0} octets)."
        )

    page_count, text_length = inspect_pdf(pdf_path)
    render_status = render_previews(pdf_path, preview_dir)

    print("=" * 88)
    print("RAPPORT V2 EXPORTÉ ET CONTRÔLÉ")
    print("=" * 88)
    print(f"Figures validées : {len(images)}")
    print(f"PDF              : {pdf_path}")
    print(f"Taille PDF       : {pdf_path.stat().st_size} octets")
    print(
        f"Pages            : "
        f"{page_count if page_count is not None else 'non vérifié'}"
    )
    print(
        f"Texte extrait    : "
        f"{text_length if text_length is not None else 'non vérifié'} caractères"
    )
    print(f"Rendu de contrôle: {render_status}")
    print(f"Aperçus          : {preview_dir}")


if __name__ == "__main__":
    main()
