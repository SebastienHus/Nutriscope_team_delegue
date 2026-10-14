"""
Étape 2 — `nettoyer` : brut figé → `data/clean/produits_propres_<AAAAMMJJ>.parquet`
+ `rapport_nettoyage_<AAAAMMJJ>.md` + `regles_<AAAAMMJJ>.json` + manifeste.

- Les règles sont celles du TP 9 (`cleaning.clean`, stratégie `DEFAULT_STRATEGY`), importées, pas recopiées.
- Nettoyage en N lots (défaut 8, `NUTRISCOPE_BATCHES`) : le lot i contient les lignes dont
  `hash(trim(code)) % N = i`. Un même code est donc toujours dans le même lot : la déduplication reste juste.
  Banc d'essai du 14/10 : 8 lots → 2,5 Go de pic au lieu de 14,1 Go, même résultat (996 637 lignes),
  identique ligne à ligne sur 300 000 lignes.
- Sortie en Parquet (un CSV perdrait les types : entiers nullables, dates, booléens).
- Sortie triée par code : deux exécutions produisent le même fichier.

Données : © Open Food Facts contributors — ODbL.
"""

from __future__ import annotations

from nutriscope.duck import connect, count, sql_str
from nutriscope.files import StepError, find_input, manifest, publish, rel, sha256_file, write_json
from nutriscope.reporting import markdown, merge_reports
from nutriscope.steps.base import StepResult
from nutriscope.steps.charger import PREFIX as RAW_PREFIX

PREFIX = "produits_propres_"


def output_path(settings):
    return settings.clean_dir / f"{PREFIX}{settings.stamp}.parquet"


def batch_query(raw, batches: int, index: int, columns: list[str]) -> str:
    order = ", ".join(f'"{c}" NULLS LAST' for c in ("code", "last_modified_t", "product_name") if c in columns)
    where = f" WHERE hash(trim(coalesce(\"code\", ''))) % {int(batches)} = {int(index)}" if batches > 1 else ""
    return f"SELECT * FROM read_parquet({sql_str(raw)}){where} ORDER BY {order}"


def run(settings, force: bool = False) -> StepResult:
    import pandas as pd

    from nutriscope import legacy  # noqa: F401
    import schema
    from cleaning import DEFAULT_STRATEGY, clean

    raw = find_input(settings.raw_dir, RAW_PREFIX, ".parquet", settings.stamp, producer="charger",
                     what="brut figé (produits_bruts_<date>.parquet)")
    batches = max(1, int(settings.batches))
    con = connect(settings)
    try:
        raw_rows = count(con, f"read_parquet({sql_str(raw)})")
        columns = [r[0] for r in con.execute(f"DESCRIBE SELECT * FROM read_parquet({sql_str(raw)})").fetchall()]
        cleaned_parts, all_reports, per_batch = [], [], []
        for index in range(batches):
            df = con.execute(batch_query(raw, batches, index, columns)).df()
            if df.empty:
                per_batch.append({"batch": index, "rows_in": 0, "rows_out": 0})
                continue
            try:
                cleaned, reports = clean(df, DEFAULT_STRATEGY)
            except ValueError as error:   # validate_output du TP 9 : contrat de sortie non respecté
                raise StepError(f"Le nettoyage du lot {index + 1}/{batches} viole le schéma de sortie : {error}") from error
            per_batch.append({"batch": index, "rows_in": len(df), "rows_out": len(cleaned)})
            cleaned_parts.append(cleaned)
            all_reports.append(reports)
            del df
    finally:
        con.close()

    if not cleaned_parts:
        raise StepError("Le nettoyage n'a produit aucune ligne : vérifiez la source et l'étape charger.")
    clean_df = pd.concat(cleaned_parts, ignore_index=True)
    del cleaned_parts
    if clean_df["code"].duplicated().any():
        raise StepError("Codes-barres en double après nettoyage par lots : la répartition par hachage a échoué.")
    clean_df = clean_df.sort_values("code", kind="stable").reset_index(drop=True)

    out = output_path(settings)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(out.name + ".tmp")
    clean_df.to_parquet(tmp, index=False, compression="zstd")
    publish(tmp, out, settings.data_dir)

    rules = merge_reports(all_reports)
    report_path = settings.clean_dir / f"rapport_nettoyage_{settings.stamp}.md"
    report_path.write_text(markdown(settings, raw.name, raw_rows, clean_df, rules, list(schema.KEY_NUTRIENTS)),
                           encoding="utf-8")
    rules_path = write_json(settings.clean_dir / f"regles_{settings.stamp}.json",
                            {"rules": rules, "batches": per_batch, "license": "© Open Food Facts contributors — ODbL"})
    manifest_path = write_json(out.with_name(out.stem + ".manifest.json"), manifest("nettoyer", settings, {
        "file": rel(out), "rows": len(clean_df), "sha256": sha256_file(out), "bytes": out.stat().st_size,
    }, {
        "input": {"file": rel(raw), "rows": raw_rows},
        "batches": batches,
        "batch_rule": "hash(trim(code)) % N" if batches > 1 else "un seul bloc",
        "rules_source": "src/cleaning.py (TP 9), DEFAULT_STRATEGY",
    }))
    return StepResult("nettoyer", rows=len(clean_df),
                      outputs=[rel(out), rel(report_path), rel(rules_path), rel(manifest_path)],
                      message=f"{raw_rows} -> {len(clean_df)} lignes, {batches} lot(s)")
