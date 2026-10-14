"""
Étape 5 — `exports` : Parquet par rayon → export d'entraînement figé
`data/exports/features_nutriscore_<AAAAMMJJ>.parquet` (+ colonne `split`) et son contrat
`features_nutriscore_<AAAAMMJJ>.schema.json`.

Reprend l'export du TP 12 (`src/storage/export_features.py`) en important sa requête (`features_query`),
ses colonnes (`FEATURES`) et ses filtres (`FILTERS`), et ajoute ce que demande le TP 13 :

- **split train / test stratifié sur `nutriscore_grade`, graine 42, 20 % de test par grade.**
  Méthode : dans chaque grade, les produits sont rangés par `md5('42:' || code)` (puis par code) ; les
  `round(0,20 × effectif du grade)` premiers sont `test`, les autres `train`. L'affectation d'un produit ne
  dépend que de son code et de la graine : ni de l'ordre des lignes, ni d'une version de numpy ou scikit-learn.
  Le grade est respecté exactement (même part de test dans chaque grade, à un produit près par arrondi).
- **export figé** : refuse de réécrire un export existant sans `--force` (dans `all`, il est simplement sauté) ;
- **reproductible** : tri par code, un seul thread → même SHA-256 à chaque réécriture ;
- **commit Git** lu dans `NUTRISCOPE_GIT_COMMIT` si défini (conteneur sans `.git`), sinon avec `git`.

Données : © Open Food Facts contributors — ODbL.
"""

from __future__ import annotations

from nutriscope.duck import connect, count, ident, sql_str
from nutriscope.files import StepError, find_input, manifest, publish, rel, sha256_file, write_json
from nutriscope.steps.base import StepResult
from nutriscope.steps.parquet import DATASET, PREFIX as PARQUET_PREFIX

PREFIX = "features_nutriscore_"
SPLIT = "split"
USAGE_RULES = [
    "fit sur le train seulement ; le test n'est regardé qu'une fois, à la fin ;",
    "la validation croisée se fait à l'intérieur du train ;",
    "ne jamais recalculer le split : utiliser la colonne `split` telle quelle ;",
    "ne pas utiliser `nutriscore_score` pour prédire `nutriscore_grade` (le grade en est dérivé : fuite de cible) ;",
    "ne pas utiliser `code` comme feature (identifiant).",
]


def output_paths(settings):
    parquet = settings.exports_dir / f"{PREFIX}{settings.stamp}.parquet"
    return parquet, parquet.with_suffix(".schema.json")


def split_query(base_query: str, target: str, seed: int, fraction: float) -> str:
    """Ajoute la colonne `split` (stratifiée par grade, ordre défini par md5(graine:code)) à la requête du TP 12."""
    t, code = ident(target), ident("code")
    return f"""
SELECT f.*,
       CASE WHEN row_number() OVER (PARTITION BY f.{t} ORDER BY md5('{int(seed)}:' || f.{code}), f.{code})
                 <= round({float(fraction)!r} * count(*) OVER (PARTITION BY f.{t}))
            THEN 'test' ELSE 'train' END AS {SPLIT}
FROM ({base_query}) AS f
ORDER BY f.{code}
"""


def run(settings, force: bool = False) -> StepResult:
    from nutriscope import legacy  # noqa: F401
    from storage.convert_parquet import LICENSE, open_products
    from storage.export_features import (FEATURES, FILTERS, ID_COLUMN, INTENDED_USE, TARGET, TARGET_GRADES,
                                         features_query, git_commit)

    source_dir = find_input(settings.parquet_dir, PARQUET_PREFIX, "", settings.stamp, producer="parquet",
                            what="jeu Parquet complet (dossier produits_<date> avec _SUCCESS)", need_success=True)
    dataset = source_dir / DATASET
    out, schema_path = output_paths(settings)
    if out.exists() and not force:
        return StepResult("exports", "skipped", outputs=[rel(out)],
                          message="export du jour déjà figé : il n'est pas réécrit (--force pour le réécrire)")

    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(out.name + ".tmp")
    tmp.unlink(missing_ok=True)
    con = connect(settings, threads=1)                   # écriture déterministe : même SHA-256
    try:
        open_products(con, dataset)
        query = split_query(features_query(), TARGET, settings.seed, settings.test_fraction)
        con.execute(f"COPY ({query}) TO {sql_str(tmp)} (FORMAT PARQUET, COMPRESSION ZSTD)")
        relation = f"read_parquet({sql_str(tmp)})"
        described = con.execute(f"DESCRIBE SELECT * FROM {relation}").fetchall()
        names = [row[0] for row in described]
        expected = [feature.name for feature in FEATURES] + [SPLIT]
        if names != expected:
            raise StepError(f"Colonnes écrites {names} différentes des colonnes déclarées {expected}")
        rows = count(con, relation)
        present = con.execute("SELECT " + ", ".join(f"count({ident(n)})" for n in names) + f" FROM {relation}").fetchone()
        by_grade = con.execute(f"SELECT {ident(TARGET)}, {SPLIT}, count(*) FROM {relation} "
                               f"GROUP BY 1, 2 ORDER BY 1, 2").fetchall()
    finally:
        con.close()
    if rows == 0:
        raise StepError("Export vide : aucun produit ne passe les filtres de l'export.")
    publish(tmp, out, settings.data_dir)

    counts: dict = {grade: {"train": 0, "test": 0} for grade in TARGET_GRADES}
    for grade, split, n in by_grade:
        counts.setdefault(grade, {"train": 0, "test": 0})[split] = int(n)
    for grade, c in counts.items():
        total = c["train"] + c["test"]
        c["total"] = total
        c["test_pct"] = round(100 * c["test"] / total, 2) if total else 0.0

    pct = lambda n: round(100 * (rows - n) / rows, 2)  # noqa: E731  (part de manquants)
    columns = [{"name": f.name, "type": t, "unit": f.unit, "description": f.description,
                "missing_pct": pct(n), "missing_policy": f.missing_policy}
               for f, (_, t, *_), n in zip(FEATURES, described, present)]
    columns.append({"name": SPLIT, "type": described[-1][1], "unit": None,
                    "description": "Jeu d'appartenance figé : 'train' ou 'test' (voir `split`).",
                    "missing_pct": pct(present[-1]), "missing_policy": "Aucun manquant."})

    contract = {
        "name": out.name,
        "freeze_date": settings.run_date.isoformat(),
        "source": f"{rel(dataset)}",
        "git_commit": settings.git_commit or git_commit(),
        "row_count": rows,
        "sha256": sha256_file(out),
        "target": TARGET,
        "identifier": ID_COLUMN,
        "filters": list(FILTERS),
        "split": {
            "column": SPLIT,
            "method": ("stratifié sur nutriscore_grade ; dans chaque grade, produits rangés par "
                       f"md5('{settings.seed}:' || code) puis code ; les round({settings.test_fraction} × effectif) "
                       "premiers sont 'test', les autres 'train'"),
            "seed": settings.seed,
            "test_fraction": settings.test_fraction,
            "counts_by_grade": counts,
            "train_total": sum(c["train"] for c in counts.values()),
            "test_total": sum(c["test"] for c in counts.values()),
        },
        "usage_rules": USAGE_RULES,
        "forbidden_features": ["code", "product_name", "brands", "nutriscore_score (pour prédire le grade)"],
        "columns": columns,
        "license": LICENSE,
        "intended_use": INTENDED_USE,
    }
    write_json(schema_path, contract)
    manifest_path = write_json(out.with_name(out.stem + ".manifest.json"), manifest("exports", settings, {
        "file": rel(out), "schema": rel(schema_path), "rows": rows, "sha256": contract["sha256"],
    }, {"input": {"directory": rel(source_dir)}, "forced": force}))
    return StepResult("exports", rows=rows, outputs=[rel(out), rel(schema_path), rel(manifest_path)],
                      message=f"train {contract['split']['train_total']} / test {contract['split']['test_total']}")
