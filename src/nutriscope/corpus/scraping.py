"""
Documents de référence du corpus du RAG (TP du 16/11, bloc 3).

Télécharge chaque source de ``SOURCES`` (miroir du tableau de ``docs/ia/corpus.md``), en extrait
le texte principal et écrit :

- ``data/documents/<id>.txt`` : le texte extrait (BeautifulSoup pour une page web, pypdf pour un PDF) ;
- ``data/documents/raw/<id>.html|.pdf`` : le fichier téléchargé, tel que reçu (traçabilité) ;
- ``data/documents/metadata.jsonl`` : une ligne JSON par document (URL, dates, licence, empreinte...).

Par défaut, seules les sources dont la licence est établie sont téléchargées. Les sources encore
« to_verify » demandent ``--include-unverified`` ; les sources « excluded » ne le sont jamais.

Utilisation ::

    python -m nutriscope.corpus.scraping
    python -m nutriscope.corpus.scraping --include-unverified
    python -m nutriscope.corpus.scraping --only viepub-ns
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import time
import urllib.robotparser
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader

from ..options import DATA_PATH

DEFAULT_OUTPUT = DATA_PATH / "documents"
METADATA_FILE = "metadata.jsonl"
USER_AGENT = "Mozilla/5.0 (compatible; NutriScope-corpus/0.1; educational project)"
TIMEOUT = 60
RETRIES = 4
PAUSE_S = 2.0  # délai de politesse entre deux requêtes au même site

AUTHORIZED, TO_VERIFY, EXCLUDED = "authorized", "to_verify", "excluded"


@dataclass(frozen=True)
class Source:
    id: str
    title: str
    publisher: str
    url: str
    kind: str      # "html" ou "pdf"
    license: str
    status: str    # AUTHORIZED, TO_VERIFY ou EXCLUDED
    used_for: str


# Mêmes id que docs/ia/corpus.md : mettre les deux à jour ensemble.
SOURCES = [
    Source("viepub-ns", "Le Nutri-Score en cinq questions", "Vie publique (DILA)",
           "https://www.vie-publique.fr/questions-reponses/286134-le-nutri-score-en-cinq-questions",
           "html", "Licence Ouverte 2.0 : citer « Vie publique » et la date ; ne pas modifier le contenu",
           AUTHORIZED, "fonctionnement du Nutri-Score"),
    Source("santefr-ns", "Ce qu'il faut savoir sur le nouveau Nutri-Score", "Santé.fr",
           "https://www.sante.fr/ce-quil-faut-savoir-sur-le-nouveau-nutri-score",
           "html", "CGU de Santé.fr à lire", TO_VERIFY,
           "nouveau calcul, boissons, caractère volontaire"),
    Source("spf-ns", "Nutri-Score", "Santé publique France",
           "https://www.santepubliquefrance.fr/determinants-de-sante/nutrition-et-activite-physique/articles/nutri-score",
           "html", "mentions légales de santepubliquefrance.fr à lire", TO_VERIFY, "composantes du score"),
    Source("pnns-adultes",
           "Recommandations relatives à l'alimentation, à l'activité physique et à la sédentarité pour les adultes",
           "Santé publique France",
           "https://www.santepubliquefrance.fr/sites/default/files/rdd/document/42466_spf00000619.pdf",
           "pdf", "mentions légales de santepubliquefrance.fr à lire", TO_VERIFY,
           "repères de consommation (fruits et légumes, légumes secs, charcuterie, produits laitiers)"),
    Source("hcsp-2017", "Avis relatif à la révision des repères alimentaires pour les adultes", "HCSP",
           "https://www.hcsp.fr/", "html",
           "« doit être diffusé dans sa totalité, sans ajout ni modification »", EXCLUDED,
           "lien seulement : le découper en morceaux serait le modifier"),
]

# Éléments qui ne font jamais partie du texte principal d'une page.
NOISE_TAGS = ["script", "style", "noscript", "template", "svg", "iframe", "form", "button",
              "nav", "header", "footer", "aside"]
NOISE_SELECTORS = ['[role="navigation"]', '[aria-hidden="true"]', ".breadcrumb", '[class*="share"]',
                   '[class*="social"]', '[class*="cookie"]', ".visually-hidden", ".sr-only"]
# Candidats pour le contenu principal, du plus précis au plus large.
MAIN_SELECTORS = ["main article", "article", "main", '[role="main"]', "#content", "body"]
BLOCK_TAGS = ["p", "li", "h1", "h2", "h3", "h4", "h5", "h6", "td", "th", "dt", "dd", "blockquote",
              "figcaption", "br", "div", "section", "tr"]

FRENCH_MONTHS = {"janvier": 1, "février": 2, "fevrier": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6,
                 "juillet": 7, "août": 8, "aout": 8, "septembre": 9, "octobre": 10, "novembre": 11,
                 "décembre": 12, "decembre": 12}
UPDATE_PATTERN = re.compile(
    r"(?:mis à jour le|mise à jour\s*:?|dernière modification\s*:?)\s*"
    r"(\d{1,2}/\d{1,2}/\d{4}|\d{1,2}(?:er)?\s+[a-zéû]+\s+\d{4})", re.IGNORECASE)


# ============================================================================
# TÉLÉCHARGEMENT
# ============================================================================

def new_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "fr-FR,fr;q=0.9"})
    return session


def get(session: requests.Session, url: str, attempts: int = RETRIES) -> requests.Response:
    """GET avec relances : le téléchargement d'un gros PDF peut être coupé en route (IncompleteRead)."""
    for attempt in range(1, attempts + 1):
        try:
            response = session.get(url, timeout=TIMEOUT)
            response.raise_for_status()
            return response
        except (requests.ConnectionError, requests.Timeout) as error:  # y compris ChunkedEncodingError
            if attempt == attempts:
                raise
            print(f"  attempt {attempt} failed ({type(error).__name__}), retrying")
            time.sleep(PAUSE_S * attempt)
    raise AssertionError("unreachable")


def fetch(session: requests.Session, url: str) -> requests.Response:
    """GET qui suit aussi la redirection cookie + JavaScript que certains sites (vie-publique.fr)
    placent devant leurs pages : un navigateur la suivrait, et le cookie est déjà dans la session."""
    response = get(session, url)
    if "text/html" in response.headers.get("Content-Type", "") and len(response.content) < 2000:
        match = re.search(r"window\.location\.href\s*=\s*'([^']+)'", response.text)
        if match:
            response = get(session, urljoin(response.url, match.group(1)))
    return response


def allowed_by_robots(session: requests.Session, url: str) -> bool:
    """Lit le robots.txt du site (par la même session) ; fichier illisible -> autorisé."""
    parts = urlsplit(url)
    robots_url = f"{parts.scheme}://{parts.netloc}/robots.txt"
    try:
        text = fetch(session, robots_url).text
    except requests.RequestException:
        return True
    parser = urllib.robotparser.RobotFileParser()
    parser.parse(text.splitlines())
    return parser.can_fetch(USER_AGENT, url)


# ============================================================================
# EXTRACTION DU TEXTE
# ============================================================================

def clean_lines(text: str) -> str:
    """Réduit les espaces dans les lignes, supprime les lignes vides et les doublons consécutifs."""
    lines, previous = [], None
    for line in text.splitlines():
        line = re.sub(r"\s+", " ", line).strip()
        if line and line != previous:
            lines.append(line)
        previous = line or previous
    return "\n".join(lines)


def html_main_text(html: str) -> str:
    """Texte principal d'une page web : bruit retiré, candidat le plus fourni, un bloc par ligne."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(NOISE_TAGS):
        tag.decompose()
    for selector in NOISE_SELECTORS:
        for tag in soup.select(selector):
            tag.decompose()

    candidates = [element for selector in MAIN_SELECTORS for element in soup.select(selector)]
    if not candidates:
        return ""
    # « main article » peut être une simple vignette : on garde le candidat le plus précis qui
    # contient l'essentiel du texte.
    longest = max(len(element.get_text(" ", strip=True)) for element in candidates)
    main = next(element for element in candidates if len(element.get_text(" ", strip=True)) >= 0.6 * longest)

    for tag in main.find_all(BLOCK_TAGS):
        tag.insert_before("\n")
        tag.insert_after("\n")
    return clean_lines(main.get_text())


def pdf_text(content: bytes) -> tuple[str, int]:
    """Texte d'un PDF page par page, avec un repère de page pour que les réponses citent la page."""
    reader = PdfReader(io.BytesIO(content))
    pages = []
    for number, page in enumerate(reader.pages, start=1):
        text = clean_lines(page.extract_text() or "")
        if text:
            pages.append(f"[page {number}]\n{text}")
    return "\n\n".join(pages), len(reader.pages)


def parse_french_date(text: str) -> str | None:
    text = text.strip().lower()
    if match := re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", text):
        day, month, year = map(int, match.groups())
    elif match := re.fullmatch(r"(\d{1,2})(?:er)?\s+([a-zéû]+)\s+(\d{4})", text):
        day, month, year = int(match.group(1)), FRENCH_MONTHS.get(match.group(2)), int(match.group(3))
        if month is None:
            return None
    else:
        return None
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return None


def html_updated_date(html: str) -> str | None:
    """Dernière mise à jour affichée : mention visible d'abord, puis balises meta, puis <time>."""
    soup = BeautifulSoup(html, "html.parser")
    if match := UPDATE_PATTERN.search(soup.get_text(" ")):
        if parsed := parse_french_date(match.group(1)):
            return parsed
    for key in ("article:modified_time", "og:updated_time", "dateModified", "article:published_time"):
        meta = soup.find("meta", attrs={"property": key}) or soup.find("meta", attrs={"name": key})
        if meta and meta.get("content"):
            return meta["content"][:10]
    time_tag = soup.find("time", attrs={"datetime": True})
    return time_tag["datetime"][:10] if time_tag else None


def pdf_updated_date(content: bytes) -> str | None:
    """Date de modification du PDF (sinon de création), lue dans ses métadonnées."""
    try:
        info = PdfReader(io.BytesIO(content)).metadata
    except Exception:
        return None
    if not info:
        return None
    value = info.modification_date or info.creation_date
    return value.date().isoformat() if value else None


# ============================================================================
# CORPUS
# ============================================================================

def download_source(session: requests.Session, source: Source, output_dir: Path,
                    check_robots: bool = True) -> dict:
    """Télécharge une source, écrit son fichier brut et son texte, renvoie sa ligne de métadonnées."""
    if check_robots and not allowed_by_robots(session, source.url):
        raise PermissionError(f"robots.txt forbids {source.url}")
    response = fetch(session, source.url)
    content_type = response.headers.get("Content-Type", "")
    is_pdf = source.kind == "pdf"
    if is_pdf and "pdf" not in content_type and not response.content.startswith(b"%PDF"):
        raise ValueError(f"expected a PDF, got {content_type} from {response.url} (link moved?)")

    raw_dir = output_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    (raw_dir / f"{source.id}.{'pdf' if is_pdf else 'html'}").write_bytes(response.content)

    if is_pdf:
        text, pages = pdf_text(response.content)
        updated = pdf_updated_date(response.content)
    else:
        html = response.text
        text, pages = html_main_text(html), None
        updated = html_updated_date(html)
    if len(text) < 500:
        raise ValueError(f"only {len(text)} characters extracted from {response.url}: check the selectors")

    (output_dir / f"{source.id}.txt").write_text(text + "\n", encoding="utf-8")
    return {
        **asdict(source),
        "final_url": response.url,
        "updated": updated,
        "fetched": datetime.now().astimezone().isoformat(timespec="seconds"),
        "pages": pages,
        "characters": len(text),
        "sha256": hashlib.sha256(response.content).hexdigest(),
    }


def select_sources(only: list[str] | None, include_unverified: bool) -> list[Source]:
    if only:
        unknown = set(only) - {source.id for source in SOURCES}
        if unknown:
            raise SystemExit(f"Unknown source id(s): {', '.join(sorted(unknown))}")
    selected = []
    for source in SOURCES:
        if only and source.id not in only:
            continue
        if source.status == EXCLUDED:
            print(f"- {source.id}: excluded ({source.used_for})")
        elif source.status == TO_VERIFY and not include_unverified:
            print(f"- {source.id}: licence to verify, skipped (--include-unverified to download it)")
        else:
            selected.append(source)
    return selected


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Télécharge les documents de référence du corpus du RAG.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="dossier des documents")
    parser.add_argument("--include-unverified", action="store_true",
                        help="télécharge aussi les sources dont la licence reste à vérifier")
    parser.add_argument("--only", nargs="+", metavar="ID", help="seulement ces id de sources")
    parser.add_argument("--no-robots", action="store_true", help="ne lit pas robots.txt")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    sources = select_sources(args.only, args.include_unverified)
    args.output.mkdir(parents=True, exist_ok=True)
    metadata_path = args.output / METADATA_FILE

    # Garde les métadonnées des documents non téléchargés cette fois-ci (par exemple avec --only).
    records = {}
    if metadata_path.is_file():
        for line in metadata_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                record = json.loads(line)
                records[record["id"]] = record

    session, failures = new_session(), 0
    for index, source in enumerate(sources):
        if index:
            time.sleep(PAUSE_S)
        try:
            record = download_source(session, source, args.output, check_robots=not args.no_robots)
        except (requests.RequestException, ValueError, PermissionError) as error:
            failures += 1
            print(f"x {source.id}: {error}")
            continue
        records[source.id] = record
        print(f"+ {source.id}: {record['characters']:,} characters, updated {record['updated'] or '?'}")

    with open(metadata_path, "w", encoding="utf-8") as handle:
        for source in SOURCES:  # ordre stable, le même que docs/ia/corpus.md
            if source.id in records:
                handle.write(json.dumps(records[source.id], ensure_ascii=False) + "\n")
    print(f"{len(sources) - failures}/{len(sources)} document(s) written to {args.output}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
