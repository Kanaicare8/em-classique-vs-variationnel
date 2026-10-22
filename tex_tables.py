"""
================================================================================
TABLEAUX LaTeX : produits depuis resultats/tables/*.csv (aucun nombre saisi à la main)
================================================================================

python tex_tables.py [--rapide]

Écrit tables/<nom>.tex, inclus dans le texte par \\tableauGenere{nom}. Un tableau dont le CSV source est absent
n'est pas écrit (le macro affiche alors « à générer ») et il est listé en fin d'exécution.
Chaque tableau est décrit par une spécification : CSV source, filtre de lignes, colonnes (colonne, en-tête, format).
Formats : n nombre (3 décimales), n1/n2/n4 nombre à 1, 2 ou 4 décimales, i entier, p pourcentage, t texte, l liste.
"""

from __future__ import annotations

import csv
import math
import re
import sys
from pathlib import Path

import etapes as E
import parametres as PARAM

RACINE = Path(__file__).parent
OUT = RACINE / "tables"          # tables_rapide pour les essais (--rapide)
ECRITS, ABSENTS = [], []


def esc(t) -> str:
    t = str(t)
    for a, b in (("\\", r"\textbackslash{}"), ("&", r"\&"), ("%", r"\%"), ("#", r"\#"), ("_", r"\_"), ("^", r"\^{}")):
        t = t.replace(a, b)
    return t.replace("K̂", r"$\hat K$")


def num(x, nd=3) -> str:
    try:
        x = float(x)
    except (TypeError, ValueError):
        return esc(x) if x not in (None, "") else "n/d"
    if math.isnan(x):
        return "n/d"
    if math.isinf(x):
        return r"$-\infty$" if x < 0 else r"$+\infty$"
    if abs(x) >= 1e5 or (0 < abs(x) < 10 ** (-nd)):
        m, e = f"{x:.2e}".split("e")
        return rf"${m.replace('.', '{,}')} \times 10^{{{int(e)}}}$"
    return f"{x:.{nd}f}".replace(".", ",")


def cellule(v, fmt):
    if fmt == "t":
        return esc(v)
    if fmt == "i":
        return num(v, 0)
    if fmt == "p":
        try:
            return num(100 * float(v), 1) + r"\,\%"
        except (TypeError, ValueError):
            return "n/d"
    if fmt == "l":
        return esc(str(v).replace(" ; ", " ; "))
    nd = int(fmt[1:]) if len(fmt) > 1 else 3
    return num(v, nd)


def lire(nom, rapide):
    f = E.dossier_tables(rapide) / f"{nom}.csv"
    if not f.exists():
        return None
    with open(f, encoding="utf-8") as h:
        return list(csv.DictReader(h))


def ecrire(nom, entetes, lignes, legende, label, note=None, taille="scriptsize", largeurs=None):
    OUT.mkdir(exist_ok=True)
    pc = lambda t: re.sub(r"(?<!\\)%", r"\\%", str(t))
    n = len(entetes)
    largeurs = largeurs or [15.3 / n] * n
    cols = "".join(rf">{{\raggedright\arraybackslash}}p{{{w:.2f}cm}}" for w in largeurs)
    tete = " & ".join(rf"\textbf{{{pc(h)}}}" for h in entetes) + r" \\"
    s = [rf"{{\{taille}", r"\setlength{\tabcolsep}{3pt}", rf"\begin{{longtable}}{{{cols}}}",
         rf"\caption{{{pc(legende)}}}\label{{{label}}}\\", r"\toprule", tete, r"\midrule", r"\endfirsthead",
         r"\toprule", tete, r"\midrule", r"\endhead", r"\bottomrule", r"\endfoot"]
    s += [" & ".join(c for c in l) + r" \\" for l in lignes]
    s.append(r"\end{longtable}")
    if note:
        s.append(rf"\par\noindent{{\footnotesize {pc(note)}}}")
    s.append("}")
    (OUT / f"{nom}.tex").write_text("\n".join(s) + "\n", encoding="utf-8")
    ECRITS.append(nom)


def tableau(nom, source, legende, colonnes, rapide, filtre=None, note=None, label=None):
    L = lire(source, rapide)
    if L is None:
        ABSENTS.append(f"{nom} ({source}.csv)")
        return
    if filtre:
        L = [l for l in L if all(str(l.get(k)) == str(v) for k, v in filtre.items())]
    ecrire(nom, [c[1] for c in colonnes], [[cellule(l.get(c[0]), c[2]) for c in colonnes] for l in L], legende,
           label or f"tab:{nom}", note)


# ------------------------------------------------------------------------------ spécifications
DECISION = [("id", "Hypothèse", "t"), ("test", "Test", "t"), ("n", "n", "i"), ("estimation", "Écart moyen A - B", "n"),
            ("ic_bas", "IC 95 % bas", "n"), ("ic_haut", "IC 95 % haut", "n"), ("marge", "Marge", "n"),
            ("p_holm", "p (Holm)", "n4"), ("decision", "Décision", "t")]
RESUME_BRAS = [("bras", "Bras", "t"), ("n", "n", "i"), ("k_hat", "K̂ moyen", "n2"), ("erreur_k", "|K̂ - K|", "n2"),
               ("ARI", "ARI", "n"), ("ll_test", "LL test", "n"), ("ll_test_predictive", "LL prédictive", "n"),
               ("degenere", "Dégénérés", "p"), ("converge", "Convergés", "p")]


def specifications(rapide):
    T = lambda *a, **k: tableau(*a, rapide=rapide, **k)
    # chapitre 1
    T("t1_2", "validation_tableau_1_2", "EM classique sur les huit observations (K = 2)",
      [("iteration", "t", "i"), ("mu1", "μ₁", "n"), ("mu2", "μ₂", "n"), ("sigma1", "σ₁", "n"), ("sigma2", "σ₂", "n"),
       ("pi1", "π₁", "n"), ("pi2", "π₂", "n"), ("loglik", "log-vraisemblance", "n")])
    T("t1_4", "validation_tableau_1_4", "Forward-backward sur l'exemple du texte",
      [("t", "t", "i"), ("alpha_B", "α(B)", "n"), ("alpha_P", "α(P)", "n"), ("beta_B", "β(B)", "n"), ("beta_P", "β(P)", "n"),
       ("gamma_B", "γ(B)", "n"), ("gamma_P", "γ(P)", "n")])
    T("t1_5", "validation_tableau_1_5", "EM variationnel sur les huit observations (Kmax = 3, α₀ = 1/3)",
      [("init", "Initialisation", "t"), ("graine", "Graine", "i"), ("iterations", "Itérations", "i"),
       ("alpha", "α (tri décroissant)", "l"), ("m", "m", "l"), ("actives", "Actives", "i")])
    T("validation_proprietes", "validation_resume", "Propriétés théoriques vérifiées numériquement",
      [("mesure", "Mesure", "t"), ("valeur", "Valeur", "n4")])
    # illustrations
    ILL = [("modele", "Modèle", "t"), ("composantes_actives", "Actives", "i"), ("ARI", "ARI", "n"), ("silhouette", "Silhouette", "n"),
           ("iterations", "Itérations", "i"), ("converge", "Convergé", "i"), ("temps_s", "Temps (s)", "n")]
    T("ill_k6", "illustrations_k6", "Jeu de référence, K = Kmax", ILL)
    T("ill_k3", "illustrations_k3", "Jeu de référence, K = 3", ILL)
    T("ill_iris", "illustrations_iris", "Iris", ILL)
    T("ill_alpha0", "illustrations_alpha0", "Composantes actives du VB selon α₀",
      [("priors", "Priors", "t"), ("alpha0", "α₀", "n4"), ("composantes_actives", "Actives", "i"), ("ARI", "ARI", "n")])
    T("ill_covariance", "illustrations_covariance", "Contraintes de covariance",
      [("covariance", "Covariance", "t"), ("modele", "Modèle", "t"), ("ARI", "ARI", "n"), ("composantes_actives", "Actives", "i")])
    T("ill_bic_aic", "illustrations_bic_aic", "Critères d'information de l'EM selon K",
      [("K", "K", "i"), ("loglik", "log-vraisemblance", "n2"), ("BIC", "BIC", "n2"), ("AIC", "AIC", "n2"), ("ICL", "ICL", "n2")])
    T("ill_aberrantes", "illustrations_aberrantes", "Jeu de référence et points aberrants",
      [("modele", "Modèle", "t"), ("ARI_hors_aberrantes", "ARI (hors aberrants)", "n"), ("composantes_actives", "Actives", "i"),
       ("trace_covariance_max", "Trace max.", "n2"), ("poids_plus_petit_actif", "Plus petit poids actif", "n4")])
    T("ill_variantes", "illustrations_variantes", "Variantes de l'EM et du VB",
      [("methode", "Méthode", "t"), ("loglik", "log-vraisemblance", "n2"), ("ARI", "ARI", "n"), ("temps_s", "Temps (s)", "n"),
       ("actives", "Actives", "i"), ("baisses_loglik", "Baisses", "i")])
    T("ill_initialisation", "illustrations_initialisation", "Composantes actives selon l'initialisation (une relance par graine)",
      [("initialisation", "Initialisation", "t"), ("modele", "Modèle", "t"), ("n", "n", "i")] +
      [(f"actives_{k}", f"{k} actives", "i") for k in range(1, int(PARAM.valeur("k_max")["synthetique"]) + 1)])
    T("chronometrage", "chronometrage_scalabilite", "Temps médians (un seul processus, un seul fil)",
      [("N", "N", "i"), ("D", "D", "i"), ("n_rep", "Répétitions", "i"), ("temps_em", "EM (s)", "n4"), ("temps_vb", "VB (s)", "n4"),
       ("ratio_temps", "Rapport", "n2"), ("iter_em", "Itér. EM", "i"), ("iter_vb", "Itér. VB", "i"),
       ("ratio_cout_iter", "Rapport par itération", "n2")])
    # scénarios
    for sc, titre in (("S1", "chevauchement"), ("S2", "poids déséquilibrés"), ("S3", "sous-estimation de K"),
                      ("S4", "queues épaisses"), ("S5", "dimension"), ("S6", "petit effectif"), ("S7", "aberrations")):
        T(f"scenario_{sc}", "scenarios_resume", f"Scénario {sc} ({titre}) : moyennes par bras",
          [("parametre", "Paramètre", "t")] + RESUME_BRAS, filtre={"scenario": sc})
    T("decisions_scenarios", "scenarios_decisions", "Décisions confirmatoires, famille des scénarios (Holm)", DECISION)
    T("S9_variance", "S9_decomposition_variance", "Part de variance de K̂ expliquée par chaque hyperparamètre (S9)",
      [("facteur", "Facteur", "t"), ("part_variance", "Part", "p")])
    # climat
    T("climat_resume", "climat_resume", "Climat : moyennes par plan, effectif et bras",
      [("plan", "Plan", "t"), ("N", "N", "t"), ("bras", "Bras", "t"), ("n", "n", "i"), ("k_hat", "K̂", "n2"),
       ("ARI_koppen", "ARI Köppen", "n"), ("ll_test", "LL hors bloc", "n"), ("degenere", "Dégénérés", "p")])
    T("decisions_climat", "climat_decisions", "Décisions, famille climat (Holm pour les tests ; intervalles pour HC4 à HC6)",
      DECISION)
    T("climat_cartes", "climat_cartes_k", "Grille complète : nombre de composantes retenues",
      [("bras", "Bras", "t"), ("k_hat", "K̂", "i"), ("k_ajuste", "K ajusté", "i")])
    # S&P 500
    T("sp500_descriptif", "sp500_descriptif", "Rendements quotidiens du S&P 500",
      [("periode", "Période", "t"), ("observations", "Obs.", "i"), ("moyenne_pct", "Moyenne (%)", "n"),
       ("ecart_type_pct", "Écart-type (%)", "n"), ("asymetrie", "Asymétrie", "n"), ("kurtosis_excedentaire", "Kurtosis exc.", "n"),
       ("minimum_pct", "Min. (%)", "n"), ("maximum_pct", "Max. (%)", "n")])
    T("sp500_backtests", "sp500_backtests", "Validation rétrospective de la VaR et de l'ES",
      [("modele", "Modèle", "t"), ("niveau", "Niveau", "p"), ("exceptions", "Exceptions", "i"), ("attendues", "Attendues", "n1"),
       ("Kupiec_p", "p Kupiec", "n4"), ("Christoffersen_cc_p", "p Christoffersen", "n4"), ("AS_Z2", "Z₂", "n"),
       ("logscore_moyen", "Log-score", "n")])
    T("sp500_dm", "sp500_diebold_mariano", "Tests de Diebold-Mariano sur le log-score (Holm)",
      [("A", "A", "t"), ("B", "B", "t"), ("ecart_logscore_moyen", "Écart moyen", "n4"), ("DM", "DM", "n2"),
       ("p_holm", "p (Holm)", "n4"), ("decision", "Décision", "t")])
    T("sp500_intervalles", "sp500_intervalles", "Incertitude de la VaR : bootstrap (EM) et crédibilité (VB)",
      [("niveau", "Niveau", "p"), ("IC95_bootstrap_bas", "Bootstrap bas", "n"), ("IC95_bootstrap_haut", "Bootstrap haut", "n"),
       ("IC95_credible_bas", "Crédible bas", "n"), ("IC95_credible_haut", "Crédible haut", "n")])
    # texte
    T("texte_resume", "texte_resume", "pLSA et LDA : moyennes par vocabulaire, effectif et modèle",
      [("V", "V", "t"), ("N", "N", "t"), ("bras", "Modèle", "t"), ("n", "n", "i"), ("perplexite_test", "Perplexité test", "n1"),
       ("ecart_relatif", "Écart relatif", "n"), ("part_mots_nuls", "Mots nuls", "p"), ("NPMI", "NPMI", "n"), ("purete", "Pureté", "n")])
    T("decisions_texte", "texte_decisions", "Décisions, famille texte (Holm)", DECISION)


def registre():
    """Annexe : registre complet des paramètres, avec leur statut et leur justification."""
    lignes = []
    for r in PARAM.tableau():
        v = r["valeur"]
        lignes.append([esc(r["nom"]), esc(v if not isinstance(v, float) else num(v, 6)), esc(r["statut"]),
                       esc(r["justification"]), esc(r["references"]), esc(r["calibrage"])])
    ecrire("registre_parametres", ["Paramètre", "Valeur", "Statut", "Justification", "Références", "Calibrage"], lignes,
           "Registre des paramètres", "tab:registre_parametres", taille="tiny")


def _decisions(source, prefixe, rapide):
    L = lire(source, rapide)
    if L is None:
        return None
    d = [l for l in L if str(l.get("id", "")).startswith(prefixe)]
    return " ; ".join(f"{esc(l['id'])} : {esc(l['decision'])}" for l in d) or None


def grille(rapide):
    """Grille « axe × preuve » : chaque affirmation renvoie à une décision lue dans un fichier, à un théorème ou à « non testé »."""
    A_GEN = r"\emph{non encore généré}"
    REP = "expérience répliquée"
    lignes_def = [
        ("Sélection de $K$", "VB comparé à EM-BIC sur des groupes séparés", ("scenarios_decisions", "HS1-"), REP, "§2.3.16"),
        ("Composante minoritaire", r"Le VB perd la composante à 5 \% à une fréquence différente de EM-BIC", ("scenarios_decisions", "HS2"), REP, "§2.3.16"),
        ("Sous-estimation de $K$", r"Avec $K_{\max}=K$ choisi $<K$ vrai, le VB ne corrige pas l'erreur", ("scenarios_decisions", "HS3-"), REP, "§2.3.16"),
        ("Queues épaisses", "Composantes de Student : VB comparé à EM-BIC", ("scenarios_decisions", "HS4"), REP, "§2.3.17"),
        ("Dimension", r"Dimension croissante $D\in\{2,5,10,20\}$", ("scenarios_decisions", "HS5-"), REP, "§2.3.17"),
        ("Singularités, petit $N$", "Taux d'ajustements dégénérés selon $N$", ("scenarios_decisions", "HS6-"), REP, "§2.3.17"),
        ("Valeurs aberrantes", "Proportion et amplitude variées", ("scenarios_decisions", "HS7-"), REP, "§2.3.18"),
        ("Sélection de $K$ (climat)", "Erreur sur $K$ du VB et de EM-BIC (semi-synthétique)", ("climat_decisions", "HC1-"), REP, "§3.1.1"),
        ("Qualité à grand $N$ (climat)", "ARI et log-vraisemblance hors bloc", ("climat_decisions", "HC2-"), REP, "§3.1.1"),
        ("Singularités (climat)", r"VB contre EM-Kmax, $N\leq120$", ("climat_decisions", "HC3-"), REP, "§3.1.1"),
        ("Coût de calcul", "Pipeline EM-BIC contre un VB, temps total", ("climat_decisions", "HC4-"), REP, "§2.3.20"),
        ("Sensibilité aux priors", r"Variance de $\hat K$ due aux priors contre due à l'initialisation", ("climat_decisions", "HC5"),
         "expérience répliquée (descriptive)", "§2.3.19"),
        ("Incertitude", r"Couverture des intervalles à 90 \% (VB et bootstrap EM)", ("climat_decisions", "HC6-"), REP, "§2.3.15"),
        ("Chevauchement", "Le VB fusionne des zones voisines plus que EM-BIC", ("climat_decisions", "HC7-"), REP, "§3.1.1"),
        ("Dimension (climat)", "$D = 20$ : dégénérescence du VB contre EM-Kmax", ("climat_decisions", "HC8-"), REP, "§3.1.1"),
        ("Surapprentissage (texte)", "Écart test/apprentissage de pLSA contre LDA", ("texte_decisions", "HT1-"), REP, "§3.1.2"),
        ("Gestion du risque", "Log-score des modèles de VaR (Diebold-Mariano, Holm)", ("sp500_diebold_mariano", None),
         "expérience unique (une série)", "§3.1.3"),
        ("Seuil d'élagage", r"Seuil de $\alpha_0$ transféré au champ moyen", ("S8_alpha0", None), "expérience répliquée (descriptive)", "§1.7.4, §2.3.14"),
        ("Seuil d'activité", "Le nombre de composantes actives dépend du seuil", ("S10_seuil", None), "expérience répliquée (descriptive)", "§2.3.19"),
        ("Dépendance à $K_{\\max}$", "Résultat de l'élagage dépendant de $K_{\\max}$ (Iris)", ("illustrations_iris", None), "expérience unique", "§2.3.11"),
        ("Initialisation", "Composantes actives selon l'initialisation", ("illustrations_initialisation", None),
         "expérience répliquée (descriptive)", "§2.3.9"),
        ("Biais d'approximation", "Variance sous-estimée par le champ moyen", None, "théorème", "§1.5.4 (Bishop 2006) ; couverture : HC6"),
        ("Monotonie du critère", "Croissance de la log-vraisemblance (EM) et de l'ELBO (VB, covariance pleine)", None, "théorème",
         "§1.6.3, §1.7.6 ; vérification numérique (validation)"),
        ("Convergence de l'EM pour le GMM", "Le théorème de Wu (1983) ne s'applique pas tel quel (vraisemblance non bornée)", None,
         "théorème", r"§1.6.3 ; régularisation $\varepsilon I$"),
        ("Consistance de la sélection de $K$", "Garantie de consistance du champ moyen pour $K$", None, "non testé", "§1.7.9"),
        ("Taux de l'EM en sur-spécification", "Précision $(d/n)^{1/4}$ dans le cas équilibré (Dwivedi et al., 2020)", None, "non testé", "§1.6.3.d"),
        ("Cible de l'EM en sous-spécification", "Convergence vers la projection de Kullback-Leibler (Dwivedi et al., 2018)", None,
         "non testé", "§1.6.3.d"),
        ("Consistance des paramètres du VB", "Moyenne variationnelle consistante, covariance trop petite (Wang et Titterington, cités)",
         None, "non testé", "§1.7.9"),
        ("Optima locaux de l'ELBO", "Fréquence des optima locaux du VB", None, "mesuré au calibrage", r"annexe (calibrage n\_init)"),
        ("Irréversibilité de l'élagage", "Une composante éteinte ne revient pas", None, "non testé", "§1.7.4"),
        ("Double usage des données", "Effet des priors empiriques sur l'ELBO et les intervalles", None, "non testé", "§2.3.1"),
        ("Vitesse de VAE, flux normalisants, gradient naturel", "Affirmations de vitesse des variantes avancées", None, "non testé", "§1.7.7"),
        ("Vision, bio-informatique, recommandation", "Choix d'algorithme par domaine", None, "non testé", "revue"),
    ]
    lig = []
    for axe, aff, src, niv, sec in lignes_def:
        if src is None:
            preuve = "référence théorique" if niv == "théorème" else ("voir l'annexe" if "calibrage" in niv else "aucune")
            niveau = niv
        elif lire(src[0], rapide) is None:
            preuve, niveau = A_GEN, "non testé (résultats non générés)"
        elif src[1]:
            preuve = _decisions(src[0], src[1], rapide) or A_GEN
            niveau = niv if preuve != A_GEN else "non testé (résultats non générés)"
        else:
            preuve, niveau = "voir " + esc(src[0]), niv
        lig.append([axe, aff, preuve, esc(niveau), sec])
    ecrire("grille_axe_preuve", ["Axe", "Affirmation", "Preuve (décision lue dans le fichier de résultats)", "Niveau de preuve", "Section"],
           lig, r"Grille « axe $\times$ preuve » : chaque affirmation renvoie à un théorème, une expérience ou la mention « non testé »",
           "tab:2_17", largeurs=[2.4, 4.2, 4.6, 2.2, 1.9],
           note="Niveaux : théorème ; expérience répliquée (nombre de réplications fixé par le calcul de puissance) ; expérience "
                "unique ; non testé. Aucune ligne n'autorise à parler de supériorité d'un algorithme.")
    g = [("$K$ connu avec confiance", "EM classique ou VB peuvent convenir ; confirmer l'équivalence", "expérience répliquée (HS1, HS3)"),
         ("$K$ inconnu", "EM-BIC/ICL ou VB : choix selon le coût total et le besoin d'incertitude", "expérience répliquée (HC1, HC4)"),
         ("Besoin d'une incertitude en aval", "VB (approchée) ; vérifier la couverture ; bootstrap pour l'EM", "expérience répliquée (HC6)"),
         ("Petit effectif", "Comparer les taux de dégénérescence ; régulariser l'EM", "expérience répliquée (HS6, HC3)"),
         ("Grande dimension ($D>20$)", "Non testé", "non testé"),
         ("Très grand $N$", "EM online ou SVI pour les deux familles", "non testé (références)"),
         ("Sensibilité aux priors acceptable", "VB avec priors fixés avant les données ; plan factoriel",
          "expérience répliquée, descriptive (HC5, S9)")]
    ecrire("guide_decision", ["Situation", "Recommandation prudente", "Niveau de preuve"], [[a, b, esc(c)] for a, b, c in g],
           "Guide de décision avec niveau de preuve (aucune ligne n'est une recommandation absolue)", "tab:3_4", largeurs=[4.3, 7.2, 3.8])


def main(rapide=False):
    global OUT
    if rapide:
        OUT = RACINE / "tables_rapide"
    specifications(rapide)
    grille(rapide)
    registre()
    print(f"{len(ECRITS)} tableaux écrits dans tables/")
    if ABSENTS:
        print("à générer (CSV absent) :\n  " + "\n  ".join(ABSENTS))


if __name__ == "__main__":
    main("--rapide" in sys.argv)
