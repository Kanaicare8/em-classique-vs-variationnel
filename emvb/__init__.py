"""
emvb : comparaison de l'EM classique et de l'EM variationnel pour les modèles de mélange.

Code du mémoire de KANA TIODONG Icare Brichel (ENSPD, Université de Douala, 2025-2026).

  algorithmes, risque        EM, EM variationnel, MAP-EM, pLSA, LDA, gestion du risque
  comparaison, scenarios     protocole de comparaison et scénarios synthétiques S1 à S10
  hypotheses, statistique    hypothèses déclarées et tests (TOST, Wilcoxon, Holm, Diebold-Mariano)
  parametres, calibrage      registre des paramètres et calibrage écrit à l'avance
  donnees                    jeux de données (synthétique, Iris, prix du PAM, texte)
  etapes, etape_*, cli       étapes du calcul et orchestrateur reprenable (python run.py)
  persistance, progression   magasin d'artefacts, journal, barre de progression
  figures, tex_tables        figures et tableaux du mémoire, produits depuis les résultats
"""

__version__ = "1.1"
