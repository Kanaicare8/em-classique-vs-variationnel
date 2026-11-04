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
DECISION = [("id", "Test", "t"), ("rh", "RH", "t"), ("test", "Type", "t"), ("n", "n", "i"), ("exclues", "Exclues", "i"),
            ("estimation", "Écart moyen A - B", "n"), ("ic_bas", "IC 95 % bas", "n"), ("ic_haut", "IC 95 % haut", "n"),
            ("marge", "Marge", "n"), ("p_holm", "p (Holm)", "n4"), ("attendu", "Attendu", "t"), ("decision", "Décision", "t")]
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
    T("S8_alpha0", "S8_resume", "Composantes actives du VB selon α₀ autour du seuil d/2, par type de covariance (S8)",
      [("cov", "Covariance", "t"), ("alpha0", "α₀", "n2"), ("n", "n", "i"), ("k_actif", "Actives (moy.)", "n2"),
       ("ARI", "ARI", "n"), ("converge", "Convergés", "p")])
    T("S10_seuil", "S10_resume", "Composantes actives selon le seuil d'activité (S10), moyennes sur les réplications",
      [("alpha0", "α₀", "n4"), ("n", "n", "i"), ("N_k_ge_1", "N_k ≥ 1", "n2"), ("pct_0.5", "≥ 0,5 %", "n2"),
       ("pct_1", "≥ 1 %", "n2"), ("pct_5", "≥ 5 %", "n2")])
    T("cout_selection", "chronometrage_pipeline", "Temps total jusqu'au modèle final : pipeline EM-BIC contre un VB (prix, D = 3)",
      [("N", "N", "i"), ("n_rep", "Répétitions", "i"), ("temps_em_bic_median", "EM-BIC (s)", "n2"),
       ("temps_vb_median", "VB (s)", "n2"), ("ratio_median", "Rapport médian", "n2"), ("ratio_ic_bas", "IC bas", "n2"),
       ("ratio_ic_haut", "IC haut", "n2")])
    # cas pratique : prix alimentaires du Cameroun
    T("prix_descriptif", "prix_descriptif", "Écarts des prix au niveau des douze mois précédents (log), par période",
      [("periode", "Période", "t"), ("observations", "Obs.", "i"), ("marches", "Marchés", "i"), ("regions", "Régions", "i"),
       ("debut", "Début", "t"), ("fin", "Fin", "t"), ("moyenne_maïs blanc", "Moy. maïs", "n"), ("ecart_type_maïs blanc", "É.-t. maïs", "n"),
       ("ecart_type_riz importé", "É.-t. riz", "n"), ("ecart_type_niébé", "É.-t. niébé", "n"),
       ("kurtosis_exc_maïs blanc", "Kurt. maïs", "n1"), ("kurtosis_exc_riz importé", "Kurt. riz", "n1"),
       ("kurtosis_exc_niébé", "Kurt. niébé", "n1")])
    T("prix_reference", "prix_reference", "Modèle de référence : BIC de l'EM selon K sur toute la période d'apprentissage",
      [("K", "K", "i"), ("BIC", "BIC", "n2"), ("retenu", "Retenu", "t")])
    T("prix_resume", "prix_resume", "Prix : moyennes par plan, effectif et bras",
      [("plan", "Plan", "t"), ("N", "N", "t"), ("bras", "Bras", "t"), ("n", "n", "i"), ("k_hat", "K̂", "n2"),
       ("erreur_k", "|K̂ - K_ref|", "n2"), ("ARI", "ARI", "n"), ("ll_test", "LL test", "n"),
       ("ll_test_predictive", "LL prédictive", "n"), ("degenere", "Dégénérés", "p")])
    T("decisions_prix", "prix_decisions", "Décisions, famille prix (Holm pour les tests ; intervalles pour HP4 à HP6)",
      DECISION)
    T("prix_complet", "prix_complet", "Ajustements sur toute la période d'apprentissage, évalués sur 2024-2026",
      [("bras", "Bras", "t"), ("k_hat", "K̂", "i"), ("poids_actifs", "Poids actifs", "l"), ("ll_apprentissage", "LL appr.", "n"),
       ("ll_test", "LL test", "n"), ("ll_test_predictive", "LL prédictive", "n"), ("temps_s", "Temps (s)", "n2")])
    T("prix_dm", "prix_diebold_mariano", "Comparaisons de prévision : Diebold-Mariano sur le log-score moyenné par mois (Holm)",
      [("id", "Id", "t"), ("A", "A", "t"), ("B", "B", "t"), ("ecart_logscore_moyen", "Écart moyen", "n4"), ("n_mois", "Mois", "i"),
       ("DM", "DM", "n2"), ("p_holm", "p (Holm)", "n4"), ("decision", "Décision", "t")])
    T("prix_alerte", "prix_alerte", "Régime de tension : probabilité d'alerte et largeur de son intervalle à 90 %",
      [("bras", "Bras", "t"), ("periode", "Période", "t"), ("k_hat", "K̂", "i"), ("poids_tension", "Poids", "n"),
       ("moyenne_maïs blanc", "Écart maïs", "n"), ("moyenne_riz importé", "Écart riz", "n"), ("moyenne_niébé", "Écart niébé", "n"),
       ("part_alerte", "Part p > 0,5", "p"), ("largeur_ic90_moyenne", "Largeur IC", "n"),
       ("part_ic_chevauche_0.5", "IC contient 0,5", "p")])
    T("prix_ecartes", "prix_releves_ecartes", "Relevés écartés comme pics isolés d'un mois (erreurs de saisie probables)",
      [("mois", "Mois", "t"), ("marche", "Marché", "t"), ("denree", "Denrée", "t"), ("prix", "Prix relevé (XAF/kg)", "n1")])
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
        ("Sélection de $K$ (prix)", "Erreur sur $K$ du VB et de EM-BIC (semi-synthétique)", ("prix_decisions", "HP1-"), REP, "§3.1"),
        ("Qualité prédictive (prix)", "Log-vraisemblance de test 2024-2026, VB contre EM-BIC", ("prix_decisions", "HP2-"), REP, "§3.1"),
        ("Singularités, petit $N$ (prix)", r"VB contre EM-Kmax, $N\leq120$", ("prix_decisions", "HP3-"), REP, "§3.1"),
        ("Coût de calcul", "Pipeline EM-BIC contre un VB, temps total", ("prix_decisions", "HP4-"), REP, "§2.3.20"),
        ("Sensibilité aux priors", r"Variance de $\hat K$ due aux priors contre due à l'initialisation", ("prix_decisions", "HP5"),
         "expérience répliquée (descriptive)", "§2.3.19"),
        ("Incertitude", r"Couverture des intervalles à 90 \% (VB et bootstrap EM)", ("prix_decisions", "HP6-"), REP, "§2.3.15"),
        ("Prévision (prix)", "Log-score des mélanges et de la gaussienne, 2024-2026 (Diebold-Mariano par mois, Holm)",
         ("prix_diebold_mariano", None), "expérience unique (une période de test)", "§3.1"),
        ("Surapprentissage (texte)", "Écart test/apprentissage de pLSA contre LDA", ("texte_decisions", "HT1-"), REP, "§3.2"),
        ("Seuil d'élagage", r"Seuil de $\alpha_0$ transféré au champ moyen", ("S8_alpha0", None), "expérience répliquée (descriptive)", "§1.7.4, §2.3.14"),
        ("Seuil d'activité", "Le nombre de composantes actives dépend du seuil", ("S10_seuil", None), "expérience répliquée (descriptive)", "§2.3.19"),
        ("Dépendance à $K_{\\max}$", "Résultat de l'élagage dépendant de $K_{\\max}$ (Iris)", ("illustrations_iris", None), "expérience unique", "§2.3.11"),
        ("Initialisation", "Composantes actives selon l'initialisation", ("illustrations_initialisation", None),
         "expérience répliquée (descriptive)", "§2.3.9"),
        ("Biais d'approximation", "Variance sous-estimée par le champ moyen", None, "théorème", "§1.5.4 (Bishop 2006) ; couverture : HP6"),
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
         ("$K$ inconnu", "EM-BIC/ICL ou VB : choix selon le coût total et le besoin d'incertitude", "expérience répliquée (HP1, HP4)"),
         ("Besoin d'une incertitude en aval (alerte)", "VB (approchée) ; vérifier la couverture ; bootstrap pour l'EM",
          "expérience répliquée (HP6)"),
         ("Petit effectif", "Comparer les taux de dégénérescence ; régulariser l'EM", "expérience répliquée (HS6, HP3)"),
         ("Grande dimension ($D>20$)", "Non testé", "non testé"),
         ("Très grand $N$", "EM online ou SVI pour les deux familles", "non testé (références)"),
         ("Sensibilité aux priors acceptable", "VB avec priors fixés avant les données ; plan factoriel",
          "expérience répliquée, descriptive (HP5, S9)")]
    ecrire("guide_decision", ["Situation", "Recommandation prudente", "Niveau de preuve"], [[a, b, esc(c)] for a, b, c in g],
           "Guide de décision avec niveau de preuve (aucune ligne n'est une recommandation absolue)", "tab:3_4", largeurs=[4.3, 7.2, 3.8])


# ------------------------------------------------------------------------------ hypothèses (méthodologie, sans résultats)
def plan_hypotheses():
    """Hypothèses de recherche et tests déclarés qui les opérationnalisent : produits depuis hypotheses.py, avant tout résultat."""
    import hypotheses as HY
    lig = []
    for rh, (titre, enonce) in HY.RECHERCHE.items():
        ids = [h.id for h in HY.H if h.rh == rh] + [p for p, r, _, _ in HY.AUTRES if r == rh]
        prefixes = list(dict.fromkeys(i.split("-")[0] if not i.startswith("HP6") else "HP6" for i in ids))
        lig.append([esc(rh), esc(titre), esc(enonce), esc(", ".join(prefixes))])
    ecrire("hypotheses_recherche", ["RH", "Intitulé", "Hypothèse de recherche", "Tests rattachés"], lig,
           "Hypothèses de recherche issues de la thèse et tests qui les mettent à l'épreuve", "tab:hypotheses_recherche",
           largeurs=[1.0, 3.0, 8.3, 3.0])
    att = {"équivalent": "équivalence", "A > B": "A > B", "A < B": "A < B", None: "non orienté"}
    lig = [[esc(h.id), esc(h.rh), esc(h.enonce), esc(f"{h.bras_a} - {h.bras_b}"), esc(h.metrique),
            "TOST" if h.test == "equivalence" else "Wilcoxon exact", esc(att.get(h.attendu, h.attendu))] for h in HY.H]
    lig += [[esc(p + ("*" if p.startswith("HP") and not p.startswith("HPP") else "")), esc(r), esc(t), "", "",
             "intervalle" if not p.startswith("HPP") else "Diebold-Mariano", esc(a or "non orienté")] for p, r, a, t in HY.AUTRES]
    ecrire("plan_tests", ["Test", "RH", "Énoncé", "Bras (A - B)", "Métrique", "Test déclaré", "Attendu si RH vraie"], lig,
           "Plan des tests déclarés (familles de Holm : scénarios, prix, prévision, texte)", "tab:plan_tests",
           largeurs=[1.7, 0.8, 6.2, 2.2, 1.6, 1.5, 1.6], taille="tiny",
           note="* : décision par intervalle (pas de correction de Holm). « Non orienté » : la thèse ne prédit pas le sens "
                "de l'écart ; une différence démontrée est alors rapportée sans être comptée pour ni contre l'hypothèse.")


# ------------------------------------------------------------------------------ lectures générées depuis les résultats
def _phrase_decision(l):
    est, lo, hi = num(l.get("estimation")), num(l.get("ic_bas")), num(l.get("ic_haut"))
    if l.get("test") == "intervalle":
        return f"{esc(l['id'])} : estimation {est}, IC à 95 \\% [{lo} ; {hi}], décision « {esc(l['decision'])} »"
    if str(l.get("id", "")).startswith("HPP"):
        return (f"{esc(l['id'])} ({esc(l['A'])} contre {esc(l['B'])}) : écart moyen de log-score {num(l.get('estimation'), 4)} "
                f"sur {num(l.get('n_mois'), 0)} mois, statistique DM {num(l.get('DM'), 2)}, p de Holm {num(l.get('p_holm'), 4)}, "
                f"décision « {esc(l['decision'])} »")
    p = num(l.get("p_holm"), 4)
    return (f"{esc(l['id'])} : écart moyen A $-$ B de {est} (IC à 95 \\% [{lo} ; {hi}], n = {num(l.get('n'), 0)}, "
            f"p de Holm {p}), décision « {esc(l['decision'])} »")


def _verdict(attendu, decision):
    """conforme, contraire, non tranché ou différence non orientée."""
    d = str(decision)
    if attendu in (None, "", "None"):
        return "différence non orientée" if d in ("A > B", "A < B") else "non tranché"
    if attendu == "équivalent":
        return "conforme" if d == "équivalent" else "non tranché"
    if attendu in ("A > B", "A < B"):
        return "conforme" if d == attendu else ("contraire" if d in ("A > B", "A < B") else "non tranché")
    if attendu == "ratio > 1":
        return "conforme" if d == "ratio > 1" else ("contraire" if d == "ratio < 1" else "non tranché")
    if attendu == "< 90 %":
        return "conforme" if d == "< 90 %" else ("contraire" if d == ">= 90 %" else "non tranché")
    if attendu == "compatible avec 90 %":
        return "conforme" if d in ("compatible avec 90 %", ">= 90 %") else "contraire"
    return "non tranché"


def _decisions_toutes(rapide):
    import hypotheses as HY
    out = []
    for src in ("scenarios_decisions", "prix_decisions", "prix_diebold_mariano", "texte_decisions"):
        for l in lire(src, rapide) or []:
            rh, att = HY.rattachement(l["id"])
            if l["id"].startswith("HPP"):
                l = dict(l, estimation=l["ecart_logscore_moyen"], ic_bas="", ic_haut="", test="difference")
            out.append(dict(l, rh=rh, attendu=att, source=src))
    return out


def _ecrire_lecture(nom, paragraphes):
    OUT.mkdir(exist_ok=True)
    (OUT / f"lecture_{nom}.tex").write_text("\n\n".join(paragraphes) + "\n", encoding="utf-8")
    ECRITS.append(f"lecture_{nom}")


def lectures(rapide):
    """
    Lectures factuelles écrites dans tables/lecture_<nom>.tex, uniquement à partir des fichiers de résultats : pour chaque
    décision, l'estimation, l'intervalle, la p-valeur de Holm et la décision, puis le verdict au regard de l'hypothèse de
    recherche rattachée (conforme, contraire, non tranché). Aucune phrase n'est écrite pour un résultat absent.
    """
    import hypotheses as HY
    toutes = _decisions_toutes(rapide)
    for nom, srcs in (("scenarios", ("scenarios_decisions",)), ("prix", ("prix_decisions", "prix_diebold_mariano")),
                      ("texte", ("texte_decisions",))):
        dec = [l for l in toutes if l["source"] in srcs]
        if not dec:
            continue
        par = []
        for rh, (titre, _) in HY.RECHERCHE.items():
            d = [l for l in dec if l["rh"] == rh]
            if not d:
                continue
            v = [_verdict(l["attendu"], l["decision"]) for l in d]
            bilan = (f"{v.count('conforme')} conforme(s) à l'hypothèse, {v.count('contraire')} contraire(s), "
                     f"{v.count('non tranché')} non tranchée(s)"
                     + (f", {v.count('différence non orientée')} différence(s) démontrée(s) sans sens prédit"
                        if "différence non orientée" in v else ""))
            par.append(f"\\textbf{{{rh} ({esc(titre)}).}} Sur {len(d)} décision(s) : {bilan}. "
                       + " ; ".join(f"{_phrase_decision(l)} [{v_}]" for l, v_ in zip(d, v)) + ".")
        _ecrire_lecture(nom, par)
    _lecture_prix_cas(rapide)
    _lecture_recherche(toutes)


def _lecture_prix_cas(rapide):
    """Lecture descriptive du cas pratique : modèle de référence, régime de tension, alertes, prévision."""
    ref, alerte, comp = lire("prix_reference", rapide), lire("prix_alerte", rapide), lire("prix_complet", rapide)
    par = []
    if ref:
        k = next((l for l in ref if l["retenu"] == "True"), None)
        if k:
            par.append(f"\\textbf{{Nombre de régimes.}} Sur toute la période d'apprentissage, le BIC de l'EM est minimal à "
                       f"$K = {k['K']}$ (BIC = {num(k['BIC'], 1)}, tableau~\\ref{{tab:prix_reference}}) ; ce $K$ sert de "
                       "$K_{\\text{réf}}$ et de modèle générateur du jeu semi-synthétique.")
    if comp:
        s = " ; ".join(f"{esc(l['bras'])} : $\\hat K$ = {num(l.get('k_hat'), 0)}, log-vraisemblance de test {num(l.get('ll_test'))}"
                       + (f" (prédictive {num(l.get('ll_test_predictive'))})" if l.get("ll_test_predictive") not in ("", "nan") else "")
                       for l in comp if l.get("echec") == "False")
        par.append(f"\\textbf{{Ajustements sur toute la période d'apprentissage}} (tableau~\\ref{{tab:prix_complet}}). {s}.")
    if alerte:
        d = []
        for l in alerte:
            if l["bras"].startswith("accord"):
                d.append(f"les deux méthodes classent de la même façon (probabilité supérieure ou non à 0,5) "
                         f"{cellule(l['part_alerte'], 'p')} des observations")
                continue
            d.append(f"{esc(l['bras'])}, {esc(l['periode'])} : régime de tension de poids {num(l['poids_tension'])}, d'écarts "
                     f"moyens {num(l['moyenne_maïs blanc'])} (maïs), {num(l['moyenne_riz importé'])} (riz), "
                     f"{num(l['moyenne_niébé'])} (niébé) ; {cellule(l['part_alerte'], 'p')} des observations en alerte ; "
                     f"largeur moyenne de l'intervalle à 90 \\% de la probabilité d'alerte {num(l['largeur_ic90_moyenne'])}")
        par.append("\\textbf{Régime de tension et alertes} (tableau~\\ref{tab:prix_alerte}). " + " ; ".join(d) + ".")
    if par:
        _ecrire_lecture("prix_cas", par)


def _lecture_recherche(toutes):
    """Bilan transversal : pour chaque hypothèse de recherche, décisions conformes, contraires et non tranchées, toutes familles."""
    import hypotheses as HY
    if not toutes:
        return
    lig, par = [], []
    for rh, (titre, enonce) in HY.RECHERCHE.items():
        d = [l for l in toutes if l["rh"] == rh]
        v = [_verdict(l["attendu"], l["decision"]) for l in d]
        n = {k: v.count(k) for k in ("conforme", "contraire", "non tranché", "différence non orientée")}
        lig.append([esc(rh), esc(titre), num(len(d), 0), num(n["conforme"], 0), num(n["contraire"], 0), num(n["non tranché"], 0),
                    num(n["différence non orientée"], 0)])
        if d:
            ids = lambda k: ", ".join(esc(l["id"]) for l, x in zip(d, v) if x == k) or "aucune"
            par.append(f"\\textbf{{{rh} ({esc(titre)}).}} {esc(enonce)} Décisions conformes : {ids('conforme')}. "
                       f"Contraires : {ids('contraire')}. Non tranchées : {ids('non tranché')}.")
    ecrire("bilan_recherche", ["RH", "Intitulé", "Décisions", "Conformes", "Contraires", "Non tranchées", "Différences non orientées"],
           lig, "Bilan des hypothèses de recherche sur l'ensemble des tests déclarés", "tab:bilan_recherche",
           largeurs=[1.0, 4.0, 1.9, 1.9, 1.9, 2.1, 2.5])
    _ecrire_lecture("recherche", par)


def main(rapide=False):
    global OUT
    if rapide:
        OUT = RACINE / "tables_rapide"
    specifications(rapide)
    plan_hypotheses()
    lectures(rapide)
    grille(rapide)
    registre()
    print(f"{len(ECRITS)} tableaux écrits dans tables/")
    if ABSENTS:
        print("à générer (CSV absent) :\n  " + "\n  ".join(ABSENTS))


if __name__ == "__main__":
    main("--rapide" in sys.argv)
