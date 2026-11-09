"""
Jeu de photos pour le classifieur de rayon : N images valides par rayon du périmètre.

Lit l'export brut Open Food Facts, garde les produits du périmètre (`docs/cadrage/parties/
perimetre.md`) : commercialisés en France, avec un nom, au moins deux des trois nutriments
clés (énergie, sucres, sel), une `image_url`, et un `pnns_groups_1` rattaché à l'un des
huit rayons métier (`RAYONS`). Les candidats de chaque rayon sont mélangés avec la graine
du projet, puis téléchargés dans cet ordre jusqu'à obtenir `--per-rayon` images valides.

Une image est valide si :

- le serveur répond 200 avec un `Content-Type` image ;
- Pillow l'ouvre, la vérifie puis la décode entièrement (un fichier tronqué échoue ici) ;
- son plus petit côté fait au moins `MIN_SIDE` pixels ;
- elle n'est pas quasi uniforme (écart-type des niveaux de gris ≥ `MIN_STD`) : écarte les
  images vides ou les fonds unis ;
- son contenu n'a pas déjà été retenu (SHA-256) : une même photo partagée par plusieurs
  fiches ne compte qu'une fois.

Chaque image retenue est réduite dans un carré `IMAGE_SIZE` × `IMAGE_SIZE` sans déformation
(complétée en blanc) et réencodée en JPEG.

Sortie : `<output>/<rayon>/<code>.jpg` et `<output>/manifest.csv` (une ligne par tentative :
code, rayon, groupe PNNS, URL, statut, détail, dimensions, SHA-256). Le manifeste permet la
reprise : relancer le script saute les codes déjà tentés et repart des compteurs existants.

Le serveur d'Open Food Facts est un service associatif : peu de requêtes en parallèle
(`--workers`, 16 par défaut, soit 128 requêtes avec `--parallel`), un User-Agent identifiable et deux nouvelles tentatives
espacées sur erreur réseau ou 5xx.

Avec `--parallel`, le script lit les candidats une seule fois, les écrit dans
`<output>/candidates_<rayon>.csv`, puis ouvre une console par rayon qui relance le script
avec `--rayon` (donc `--workers` requêtes simultanées *par rayon*). Chaque console écrit son
propre `manifest_<rayon>.csv` ; la reprise et `--verify` lisent tous les manifestes. Les
doublons entre rayons apparus pendant ce téléchargement ne sont repérés que par `--verify`.

Avec `--shards K`, chaque rayon est réparti sur K consoles : la console `i` prend un candidat
sur K (à partir du i-ème), vise sa part de `--per-rayon` et écrit `manifest_<rayon>_<i>.csv`.
Les parts sont disjointes ; seules les photos identiques partagées par deux fiches de parts
différentes passent en double, ce que `--verify --delete` nettoie. Garder le même K pour
reprendre un téléchargement interrompu.

    python -m nutriscope.download_images
    python -m nutriscope.download_images --per-rayon 3000 -o ~/Desktop/data/image
    python -m nutriscope.download_images --parallel          # une console par rayon
    python -m nutriscope.download_images --parallel --shards 4 -w 4   # 32 consoles
    python -m nutriscope.download_images --verify            # revalide le disque
    python -m nutriscope.download_images --verify --delete   # puis relancer pour compléter

Données : © Open Food Facts contributors — ODbL.
"""

import argparse
import csv
import hashlib
import io
import subprocess
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageStat

from .options import DATA_PATH, RANDOM_SEED

SOURCE = DATA_PATH / "en.openfoodfacts.org.products.csv"
DEFAULT_OUTPUT = Path.home() / "Desktop" / "data" / "image"
PER_RAYON = 6000
IMAGE_SIZE = 128        # px, côté du carré enregistré
JPEG_QUALITY = 90

# rayon métier (perimetre.md §5) → groupes PNNS de niveau 1
RAYONS = {
    "petit_dejeuner": ("Cereals and potatoes",),
    "boissons": ("Beverages",),
    "snacks": ("Sugary snacks", "Salty snacks"),
    "produits_laitiers": ("Milk and dairy products",),
    "fruits_legumes": ("Fruits and vegetables",),
    "viandes_substituts": ("Fish Meat Eggs",),
    "plats_prepares": ("Composite foods",),
    "condiments_huiles": ("Fat and sauces",),
}

MIN_SIDE = 100          # px, plus petit côté accepté
MIN_STD = 5.0           # écart-type des niveaux de gris en dessous duquel l'image est vide
TIMEOUT = 20            # s par requête
RETRIES = 2             # nouvelles tentatives sur erreur réseau ou 5xx
USER_AGENT = "NutriScope-TP/1.0 (projet pedagogique, classifieur de rayon)"
MANIFEST_FIELDS = ("code", "rayon", "pnns", "url", "status", "detail", "width", "height", "sha256")


@dataclass
class Result:
    code: str
    rayon: str
    pnns: str
    url: str
    status: str             # ok | http | invalid | small | blank | duplicate
    detail: str = ""
    width: int = 0
    height: int = 0
    sha256: str = ""
    content: bytes = b""


def load_candidates(source: Path) -> dict[str, list[tuple[str, str, str]]]:
    """Candidats (code, pnns, url) par rayon, filtrés sur le périmètre, mélangés avec la graine."""
    # imports locaux : numpy réserve ~500 Mo par processus (tampons OpenBLAS), inutiles aux
    # consoles de `--parallel` qui lisent `candidates_<rayon>.csv`
    import duckdb
    import numpy as np

    to_rayon = {pnns: rayon for rayon, groups in RAYONS.items() for pnns in groups}
    groups = ", ".join(f"'{pnns}'" for pnns in to_rayon)
    query = f"""
        SELECT DISTINCT ON (code) code, pnns_groups_1 AS pnns, image_url AS url
        FROM read_csv('{source.as_posix()}', delim='\t', header=true, quote='',
                      all_varchar=true, ignore_errors=true, strict_mode=false)
        WHERE countries_tags LIKE '%en:france%'
          AND coalesce(image_url, '') <> ''
          AND trim(coalesce(product_name, '')) <> ''
          AND (coalesce(energy_100g, '') <> '')::int + (coalesce(sugars_100g, '') <> '')::int
              + (coalesce(salt_100g, '') <> '')::int >= 2
          AND pnns_groups_1 IN ({groups})
        ORDER BY code
    """
    rows = duckdb.sql(query).fetchall()
    candidates = {rayon: [] for rayon in RAYONS}
    for code, pnns, url in rows:
        candidates[to_rayon[pnns]].append((code, pnns, url))
    rng = np.random.default_rng(RANDOM_SEED)
    for rayon, items in candidates.items():
        candidates[rayon] = [items[i] for i in rng.permutation(len(items))]
    return candidates


def candidates_path(output: Path, rayon: str) -> Path:
    return output / f"candidates_{rayon}.csv"


def save_candidates(output: Path, candidates: dict[str, list[tuple[str, str, str]]]) -> None:
    output.mkdir(parents=True, exist_ok=True)
    for rayon, items in candidates.items():
        with candidates_path(output, rayon).open("w", newline="", encoding="utf-8") as file:
            csv.writer(file).writerows(items)


def read_candidates(output: Path, rayon: str) -> list[tuple[str, str, str]]:
    with candidates_path(output, rayon).open(newline="", encoding="utf-8") as file:
        return [tuple(row) for row in csv.reader(file)]


def fetch(url: str) -> bytes:
    """Télécharge `url` ; relance sur erreur réseau ou 5xx, lève `urllib.error.HTTPError` sinon."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(RETRIES + 1):
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
                content_type = response.headers.get("Content-Type", "")
                if not content_type.startswith("image/"):
                    raise ValueError(f"Content-Type {content_type!r}")
                return response.read()
        except urllib.error.HTTPError as error:
            if error.code < 500 or attempt == RETRIES:
                raise
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            if attempt == RETRIES:
                raise
        time.sleep(2 ** attempt)
    raise AssertionError("inatteignable")


def validate(content: bytes, result: Result) -> Result:
    """Contrôle le contenu d'une image (décodage, taille, uniformité) et complète `result`."""
    try:
        Image.open(io.BytesIO(content)).verify()
        image = Image.open(io.BytesIO(content))
        image.load()
    except Exception as error:
        result.status, result.detail = "invalid", str(error)[:200]
        return result
    result.width, result.height = image.size
    if min(image.size) < MIN_SIDE:
        result.status = "small"
        return result
    std = ImageStat.Stat(image.convert("L")).stddev[0]
    if std < MIN_STD:
        result.status, result.detail = "blank", f"std={std:.1f}"
        return result
    result.sha256 = hashlib.sha256(content).hexdigest()
    result.content = content
    return result


def to_square(content: bytes) -> bytes:
    """Réduit l'image dans un carré `IMAGE_SIZE` sans la déformer, complété en blanc, en JPEG."""
    image = Image.open(io.BytesIO(content)).convert("RGB")
    image.thumbnail((IMAGE_SIZE, IMAGE_SIZE), Image.Resampling.LANCZOS)
    square = Image.new("RGB", (IMAGE_SIZE, IMAGE_SIZE), "white")
    square.paste(image, ((IMAGE_SIZE - image.width) // 2, (IMAGE_SIZE - image.height) // 2))
    buffer = io.BytesIO()
    square.save(buffer, "JPEG", quality=JPEG_QUALITY)
    return buffer.getvalue()


def check(code: str, rayon: str, pnns: str, url: str) -> Result:
    """
    Télécharge et valide une image ; le statut dit pourquoi elle est rejetée.

    Les contrôles portent sur l'original (dimensions et SHA-256 du manifeste aussi) ;
    `content` contient la version carrée à enregistrer.
    """
    result = Result(code, rayon, pnns, url, "ok")
    try:
        content = fetch(url)
    except Exception as error:
        result.status, result.detail = "http", str(error)[:200]
        return result
    result = validate(content, result)
    if result.status == "ok":
        result.content = to_square(content)
    return result


def verify(output: Path, delete: bool) -> dict[str, int]:
    """
    Revalide les images déjà sur disque ; renvoie le nombre d'images valides par rayon.

    Une image invalide ou en double est signalée, et supprimée avec `delete` : elle est
    alors marquée `removed` dans le manifeste, et relancer le téléchargement complète le
    rayon avec de nouveaux candidats.
    """
    manifests = {path: read_manifest(path) for path in manifest_paths(output)}
    rows = [row for path_rows in manifests.values() for row in path_rows]
    hashes: set[str] = set()
    counts = {rayon: 0 for rayon in RAYONS}
    bad = 0
    for rayon in RAYONS:
        for path in sorted((output / rayon).glob("*.jpg")):
            result = validate(path.read_bytes(), Result(path.stem, rayon, "", "", "ok"))
            if result.status == "ok" and result.sha256 in hashes:
                result.status = "duplicate"
            if result.status == "ok":
                hashes.add(result.sha256)
                counts[rayon] += 1
                continue
            bad += 1
            print(f"  {rayon}/{path.name} : {result.status} {result.detail}", flush=True)
            if delete:
                path.unlink()
                for row in rows:
                    if row["code"] == path.stem and row["status"] == "ok":
                        row["status"], row["detail"] = "removed", f"verify: {result.status}"
        print(f"{rayon} : {counts[rayon]} valides", flush=True)
    if delete and bad:
        for path, path_rows in manifests.items():
            with path.open("w", newline="", encoding="utf-8") as file:
                writer = csv.DictWriter(file, fieldnames=MANIFEST_FIELDS)
                writer.writeheader()
                writer.writerows(path_rows)
    print(f"\n{bad} image(s) en défaut" + (" supprimée(s)" if delete and bad else ""))
    return counts


def manifest_paths(output: Path) -> list[Path]:
    """Manifeste commun (mode séquentiel) puis manifestes par rayon (mode `--parallel`)."""
    paths = [output / "manifest.csv", *sorted(output.glob("manifest_*.csv"))]
    return [path for path in paths if path.exists()]


def read_manifest(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def count_ok(output: Path) -> dict[str, int]:
    counts = {rayon: 0 for rayon in RAYONS}
    for path in manifest_paths(output):
        for row in read_manifest(path):
            if row["status"] == "ok":
                counts[row["rayon"]] += 1
    return counts


def download(output: Path, per_rayon: int, workers: int, source: Path,
             rayon: str | None = None, shard: int = 0, shards: int = 1) -> dict[str, int]:
    """
    Remplit `output/<rayon>/` jusqu'à `per_rayon` images valides ; renvoie le compte par rayon.

    Avec `rayon`, ne traite que ce rayon, écrit dans `manifest_<rayon>.csv` et reprend les
    candidats de `candidates_<rayon>.csv` s'il existe (écrit par `parallel`). Avec `shards`
    > 1, ne garde qu'un candidat sur `shards` à partir de `shard`, écrit dans
    `manifest_<rayon>_<shard>.csv` et ne compte que ses propres images.
    """
    if rayon is None:
        manifest_path = output / "manifest.csv"
    elif shards == 1:
        manifest_path = output / f"manifest_{rayon}.csv"
    else:
        manifest_path = output / f"manifest_{rayon}_{shard}.csv"
    previous = [row for path in manifest_paths(output) for row in read_manifest(path)]
    tried = {row["code"] for row in previous}
    hashes = {row["sha256"] for row in previous if row["status"] == "ok"}
    counts = {rayon: 0 for rayon in RAYONS}
    for row in previous if shards == 1 else read_manifest(manifest_path):
        if row["status"] == "ok":
            counts[row["rayon"]] += 1

    if rayon is not None and candidates_path(output, rayon).exists():
        candidates = {rayon: read_candidates(output, rayon)}
    else:
        print(f"Lecture des candidats dans {source.name}…", flush=True)
        candidates = load_candidates(source)
        if rayon is not None:
            candidates = {rayon: candidates[rayon]}
    if rayon is not None:
        candidates[rayon] = candidates[rayon][shard::shards]

    output.mkdir(parents=True, exist_ok=True)
    # un manifeste vide vient d'un processus tué avant d'avoir écrit son en-tête
    new_file = not manifest_path.exists() or manifest_path.stat().st_size == 0
    with manifest_path.open("a", newline="", encoding="utf-8") as file, \
            ThreadPoolExecutor(max_workers=workers) as pool:
        writer = csv.DictWriter(file, fieldnames=MANIFEST_FIELDS, extrasaction="ignore")
        if new_file:
            writer.writeheader()
        for rayon, items in candidates.items():
            folder = output / rayon
            folder.mkdir(exist_ok=True)
            queue = [item for item in items if item[0] not in tried]
            print(f"{rayon} : {counts[rayon]}/{per_rayon} déjà présentes, "
                  f"{len(queue)} candidats restants", flush=True)
            while counts[rayon] < per_rayon and queue:
                # un peu plus que le manque, pour absorber les rejets sans dépasser de beaucoup
                need = per_rayon - counts[rayon]
                batch, queue = queue[:need + need // 10 + workers], queue[need + need // 10 + workers:]
                for result in pool.map(lambda item: check(item[0], rayon, item[1], item[2]), batch):
                    if result.status == "ok":
                        if result.sha256 in hashes:
                            result.status = "duplicate"
                        elif counts[rayon] >= per_rayon:
                            continue        # surplus du dernier lot : ni gardé ni marqué tenté
                        else:
                            (folder / f"{result.code}.jpg").write_bytes(result.content)
                            hashes.add(result.sha256)
                            counts[rayon] += 1
                    writer.writerow(vars(result))
                    file.flush()            # manifeste à jour même si le script est tué
                print(f"  {rayon} : {counts[rayon]}/{per_rayon}", flush=True)
            if counts[rayon] < per_rayon:
                print(f"  {rayon} : candidats épuisés à {counts[rayon]} images", flush=True)
    return counts


def parallel(output: Path, per_rayon: int, workers: int, source: Path,
             shards: int = 1, consoles: int | None = None) -> dict[str, int]:
    """
    Lit les candidats une fois puis lance `shards` consoles par rayon ; attend qu'elles finissent.

    Avec `consoles`, au plus `consoles` tournent en même temps : chaque console terminée laisse
    la place à la part suivante. Les parts sont lancées rayon par rayon en alternance, pour que
    tous les rayons avancent ensemble.
    """
    print(f"Lecture des candidats dans {source.name}…", flush=True)
    save_candidates(output, load_candidates(source))
    start = time.perf_counter()
    pending = []
    for shard in range(shards):
        for rayon in RAYONS:
            # les premières parts prennent le reste de la division
            target = per_rayon // shards + (shard < per_rayon % shards)
            command = [sys.executable, "-m", "nutriscope.download_images", "--rayon", rayon,
                       "-o", str(output), "-n", str(target), "-w", str(workers)]
            if shards > 1:
                command += ["--shards", str(shards), "--shard", str(shard)]
            pending.append((rayon if shards == 1 else f"{rayon}[{shard}]", command))
    limit = consoles or len(pending)
    running: dict[str, subprocess.Popen] = {}
    while pending or running:
        while pending and len(running) < limit:
            name, command = pending.pop(0)
            running[name] = subprocess.Popen(
                command, creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0))
            print(f"  {name} : console lancée (PID {running[name].pid})", flush=True)
        for name, process in list(running.items()):
            if process.poll() is not None:
                del running[name]
                print(f"  {name} : terminé (code {process.returncode}) à "
                      f"{time.perf_counter() - start:.0f} s", flush=True)
        time.sleep(0.5)
    print(f"\nDurée totale : {time.perf_counter() - start:.0f} s")
    return count_ok(output)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0].strip())
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_OUTPUT,
                        help=f"dossier de sortie (défaut : {DEFAULT_OUTPUT})")
    parser.add_argument("-n", "--per-rayon", type=int, default=PER_RAYON,
                        help=f"images valides par rayon (défaut : {PER_RAYON})")
    parser.add_argument("-w", "--workers", type=int, default=16,
                        help="téléchargements en parallèle, par rayon avec --parallel (défaut : 16)")
    parser.add_argument("-s", "--source", type=Path, default=SOURCE,
                        help="export CSV Open Food Facts")
    parser.add_argument("--parallel", action="store_true",
                        help="une console par rayon, lancées en parallèle")
    parser.add_argument("--rayon", choices=RAYONS,
                        help="ne traiter que ce rayon (utilisé par --parallel)")
    parser.add_argument("--consoles", type=int,
                        help="avec --parallel : consoles simultanées au plus (défaut : toutes)")
    parser.add_argument("--shards", type=int, default=1,
                        help="consoles par rayon avec --parallel (défaut : 1)")
    parser.add_argument("--shard", type=int, default=0,
                        help="avec --rayon et --shards : numéro de la part (utilisé par --parallel)")
    parser.add_argument("--verify", action="store_true",
                        help="revalider les images déjà téléchargées, sans rien télécharger")
    parser.add_argument("--delete", action="store_true",
                        help="avec --verify : supprimer les images en défaut")
    args = parser.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")

    if args.verify:
        counts = verify(args.output, args.delete)
    elif args.parallel:
        counts = parallel(args.output, args.per_rayon, args.workers, args.source, args.shards,
                          args.consoles)
    else:
        start = time.perf_counter()
        counts = download(args.output, args.per_rayon, args.workers, args.source, args.rayon,
                          args.shard, args.shards)
        print(f"\nDurée : {time.perf_counter() - start:.0f} s")
        if args.rayon:
            counts = {args.rayon: counts[args.rayon]}
    print("\nImages valides par rayon :")
    for rayon, count in counts.items():
        print(f"  {rayon:<20} {count}")
    return 0 if all(count >= args.per_rayon for count in counts.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
