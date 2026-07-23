"""Crée une planche-contact des aperçus du rapport Open v2.

Entrée
------
reports/previews/filiere_open_v2_pdf/page_*.png

Sortie
------
reports/previews/filiere_open_v2_pdf/contact_sheet.png
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_font(size: int):
    candidates = [
        Path(r"C:\Windows\Fonts\arial.ttf"),
        Path(r"C:\Windows\Fonts\calibri.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default()


def main() -> None:
    root = repo_root()
    preview_dir = root / "reports/previews/filiere_open_v2_pdf"
    pages = sorted(preview_dir.glob("page_*.png"))

    if len(pages) != 6:
        raise RuntimeError(
            f"Six aperçus attendus, {len(pages)} trouvés dans {preview_dir}"
        )

    images = [Image.open(path).convert("RGB") for path in pages]

    thumb_width = 700
    margin = 40
    label_height = 42
    columns = 2
    rows = 3

    thumbs = []
    for image in images:
        ratio = thumb_width / image.width
        thumb_height = round(image.height * ratio)
        thumbs.append(
            image.resize(
                (thumb_width, thumb_height),
                Image.Resampling.LANCZOS,
            )
        )

    cell_height = max(image.height for image in thumbs) + label_height
    sheet_width = columns * thumb_width + (columns + 1) * margin
    sheet_height = rows * cell_height + (rows + 1) * margin

    sheet = Image.new("RGB", (sheet_width, sheet_height), "white")
    draw = ImageDraw.Draw(sheet)
    font = load_font(26)

    for index, (path, image) in enumerate(zip(pages, thumbs)):
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

    print("=" * 80)
    print("PLANCHE-CONTACT CRÉÉE")
    print("=" * 80)
    print(f"Pages : {len(pages)}")
    print(f"Fichier : {output}")
    print(f"Dimensions : {sheet.width} x {sheet.height}")


if __name__ == "__main__":
    main()
