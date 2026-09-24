"""
Pipeline complet de nettoyage — TP 9
Exécution end-to-end : lecture → nettoyage → rapport → export
"""

import pandas as pd
import sys
from pathlib import Path
from cleaning import nettoyer, STRATEGIE_PAR_DEFAUT
from report import generer_rapport


def main(
    chemin_entree: str = "data/echantillon_france.csv",
    chemin_sortie: str = "data/echantillon_france_propre.csv",
    chemin_rapport: str = "docs/data/rapport_nettoyage.md"
):
    """
    Pipeline complet de nettoyage.

    Args:
        chemin_entree : CSV brut
        chemin_sortie : CSV nettoyé
        chemin_rapport : Rapport Markdown
    """

    print("=" * 80)
    print("PIPELINE NETTOYAGE — NutriScope TP 9")
    print("=" * 80)

    # Étape 1 : Lecture
    print(f"\n[1/4] Lecture de {chemin_entree}...")
    try:
        df_brut = pd.read_csv(chemin_entree)
        print(f"  ✓ {len(df_brut):,} lignes chargées")
        print(f"  ✓ {len(df_brut.columns)} colonnes")
    except FileNotFoundError:
        print(f"  ✗ Fichier introuvable: {chemin_entree}")
        return 1
    except Exception as e:
        print(f"  ✗ Erreur: {e}")
        return 1

    # Étape 2 : Nettoyage
    print("\n[2/4] Nettoyage appliqué...")
    try:
        df_propre, rapports = nettoyer(df_brut, STRATEGIE_PAR_DEFAUT)
        print(f"  ✓ Pipeline exécuté: {len(rapports)} règles appliquées")

        for rapport in rapports:
            status = "✓" if rapport.lignes_touchees == 0 else "○"
            print(f"    {status} {rapport.regle}: {rapport.lignes_touchees} lignes touchées")

        print(f"  ✓ Résultat: {len(df_propre):,} lignes ({len(df_propre)/len(df_brut)*100:.1f}%)")
    except Exception as e:
        print(f"  ✗ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Étape 3 : Rapport
    print("\n[3/4] Génération du rapport...")
    try:
        rapport_text = generer_rapport(df_brut, df_propre, rapports, chemin_rapport)
        print(f"  ✓ Rapport généré ({len(rapport_text)} caractères)")
    except Exception as e:
        print(f"  ✗ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Étape 4 : Export
    print("\n[4/4] Export des données et rapport...")
    try:
        # CSV nettoyé
        df_propre.to_csv(chemin_sortie, index=False)
        print(f"  ✓ CSV exporté: {chemin_sortie}")

        # Rapport
        Path(chemin_rapport).parent.mkdir(parents=True, exist_ok=True)
        with open(chemin_rapport, "w", encoding="utf-8") as f:
            f.write(rapport_text)
        print(f"  ✓ Rapport exporté: {chemin_rapport}")
    except Exception as e:
        print(f"  ✗ Erreur: {e}")
        return 1

    # Résumé final
    print("\n" + "=" * 80)
    print("✅ PIPELINE COMPLÉTÉ AVEC SUCCÈS")
    print("=" * 80)
    print(f"  • Données brutes: {len(df_brut):,} lignes")
    print(f"  • Données nettoyées: {len(df_propre):,} lignes ({len(df_propre)/len(df_brut)*100:.1f}%)")
    print(f"  • Colonnes: {len(df_brut.columns)} → {len(df_propre.columns)}")
    print(f"\n  Fichiers générés:")
    print(f"    - {chemin_sortie}")
    print(f"    - {chemin_rapport}")
    print("\nCommandes de test:")
    print(f"  $ head {chemin_sortie}")
    print(f"  $ cat {chemin_rapport}")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    # Utilisation
    # python pipeline.py [chemin_entree] [chemin_sortie] [chemin_rapport]

    if len(sys.argv) > 1:
        chemin_entree = sys.argv[1]
        chemin_sortie = sys.argv[2] if len(sys.argv) > 2 else "data/echantillon_france_propre.csv"
        chemin_rapport = sys.argv[3] if len(sys.argv) > 3 else "docs/data/rapport_nettoyage.md"
        sys.exit(main(chemin_entree, chemin_sortie, chemin_rapport))
    else:
        # Valeurs par défaut
        sys.exit(main())
