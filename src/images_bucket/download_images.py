"""Download the TP 17 photos from the public Open Food Facts bucket.

    python src/images_bucket/download_images.py --list
    python src/images_bucket/download_images.py --aisles sodas biscuits chocolats eaux fromages jus

Writes data/images/<aisle>/<code>.jpg (400 px version). Running the script again only
downloads what is missing. Photos: CC BY-SA, Open Food Facts contributors.
"""

import argparse
import csv
import http.client
import sys
import time
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]  # src/images_bucket/ -> repository root
BUCKET_URL = "https://openfoodfacts-images.s3.eu-west-3.amazonaws.com/"
MAX_ATTEMPTS = 5
TIMEOUT_S = 60

# Column names of manifest_bucket.csv (provided file, kept as is)
COL_AISLE = "rayon"
COL_CODE = "code"
COL_S3_KEY = "cle_s3"

ALREADY_THERE = "already there"
DOWNLOADED = "downloaded"
FAILED = "failed"


def image_path(row: dict, dest: Path) -> Path:
    """Local path of a manifest row: <dest>/<aisle>/<code>.jpg."""
    return dest / row[COL_AISLE] / f"{row[COL_CODE]}.jpg"


def download(row: dict, dest: Path) -> str:
    """Download one photo with exponential backoff; atomic write through a .tmp file."""
    path = image_path(row, dest)
    if path.exists():
        return ALREADY_THERE
    for attempt in range(MAX_ATTEMPTS):
        try:
            with urllib.request.urlopen(BUCKET_URL + row[COL_S3_KEY], timeout=TIMEOUT_S) as response:
                content = response.read()
            break
        except (OSError, http.client.HTTPException):
            time.sleep(2**attempt)
    else:
        return FAILED
    tmp_path = path.with_suffix(".tmp")
    tmp_path.write_bytes(content)
    tmp_path.replace(path)
    return DOWNLOADED


def read_manifest(manifest: Path) -> list[dict]:
    with manifest.open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--aisles", nargs="+", help="5 to 8 aisles from your scope")
    parser.add_argument("--list", action="store_true", help="show the available aisles")
    parser.add_argument("--dest", type=Path, default=ROOT / "data" / "images")
    parser.add_argument("--manifest", type=Path, default=HERE / "manifest_bucket.csv")
    parser.add_argument("--workers", type=int, default=8, help="parallel downloads")
    return parser.parse_args(argv)


def main(argv=None) -> None:
    args = parse_args(argv)
    rows = read_manifest(args.manifest)
    available = Counter(row[COL_AISLE] for row in rows)

    if args.list or not args.aisles:
        for aisle, count in sorted(available.items()):
            print(f"{aisle:15s} {count}")
        return
    unknown = set(args.aisles) - set(available)
    if unknown:
        sys.exit(f"Unknown aisles: {sorted(unknown)}. See --list.")

    selected = [row for row in rows if row[COL_AISLE] in args.aisles]
    for aisle in args.aisles:
        (args.dest / aisle).mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(args.workers) as pool:
        summary = Counter(pool.map(lambda row: download(row, args.dest), selected))
    print(dict(summary))
    if summary[FAILED]:
        print("Some photos failed: run the same command again.")


if __name__ == "__main__":
    main()
