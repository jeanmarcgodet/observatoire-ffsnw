import ssl
from pathlib import Path
from urllib.request import Request, urlopen

import certifi


URL = "https://www.iwwfed-ea.org/classic/26FRA021/"
OUTPUT_FILE = Path("data/raw/iwwf/26FRA021.html")


def main() -> None:
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    request = Request(
        URL,
        headers={"User-Agent": "Mozilla/5.0 observatoire-ffsnw/0.1"},
    )

    ssl_context = ssl.create_default_context(cafile=certifi.where())

    with urlopen(request, timeout=30, context=ssl_context) as response:
        html = response.read().decode("utf-8", errors="replace")

    OUTPUT_FILE.write_text(html, encoding="utf-8")

    print(f"Page enregistrée : {OUTPUT_FILE}")
    print(f"Taille : {len(html)} caractères")
    print("\nPremiers caractères reçus :\n")
    print(html[:2000])


if __name__ == "__main__":
    main()