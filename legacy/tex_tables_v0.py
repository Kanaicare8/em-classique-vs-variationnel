"""
================================================================================
PRODUCTION DES TABLEAUX LaTeX DU MÉMOIRE À PARTIR DES FICHIERS DE RÉSULTATS
================================================================================

Usage : python tex_tables.py

Lit resultats/*.csv (produits par main.py, scenarios.py, cas_pratique*.py, texte_plsa_lda.py)
et écrit tables/*.tex, inclus dans body.tex par \\tableauGenere{nom}. Aucun nombre n'est saisi à
la main : un tableau dont le fichier source est absent est signalé par un encadré « à générer »
(le tableau n'est alors pas écrit et le macro \\tableauGenere affiche le message).
"""

from __future__ import annotations

import ast
import math
import re
from pathlib import Path

import pandas as pd

RACINE = Path(__file__).parent
RES = RACINE / "resultats"
OUT = RACINE / "tables"
OUT.mkdir(exist_ok=True)
ECRITS, ABSENTS = [], []


# ------------------------------------------------------------------ mise en forme
def esc(t) -> str:
    t = str(t)
    for a, b in (("\\", r"\textbackslash{}"), ("&", r"\&"), ("%", r"\%"), ("#", r"\#"), ("_", r"\_")):
        t = t.replace(a, b)
    t = t.replace("K̂", r"$\hat K$")      # K avec accent circonflexe combinant : non géré par LaTeX
    return t


def num(x, nd=3) -> str:
    """Nombre au format français (virgule), vide si absent."""
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "n/d"
    if isinstance(x, bool):
        return "oui" if x else "non"
    if isinstance(x, int) or (isinstance(x, float) and float(x).is_integer() and abs(x) < 1e6 and nd == 0):
        return str(int(x))
    if isinstance(x, float):
        return f"{x:.{nd}f}".replace(".", ",").replace("-", "-")
    return esc(x)


def liste(x, nd=3) -> str:
    """Convertit une chaîne '[0.1, 0.2]' en '0,1 ; 0,2'."""
    try:
        v = ast.literal_eval(x) if isinstance(x, str) else x
        return " ; ".join(num(float(t), nd) for t in v)
    except Exception:
        return esc(x)


def lire(nom):
    p = RES / nom
    if not p.exists():
        ABSENTS.append(nom)
        return None
    return pd.read_csv(p)


def pct(t) -> str:
    """Échappe les % non échappés (le % ouvre un commentaire LaTeX)."""
    bs = chr(92)
    return re.sub("(?<!" + re.escape(bs) + ")%", lambda m: bs + "%", str(t))


def ecrire(nom, entetes, lignes, legende, label, largeurs=None, note=None, taille="scriptsize"):
    """Écrit tables/nom.tex (longtable) ; `largeurs` en cm."""
    entetes = [pct(h) for h in entetes]
    legende = pct(legende)
    note = pct(note) if note else note
    lignes = [[pct(c) for c in l] for l in lignes]
    n = len(entetes)
    largeurs = largeurs or [15.3 / n] * n
    cols = "".join(rf">{{\raggedright\arraybackslash}}p{{{w:.2f}cm}}" for w in largeurs)
    s = [rf"{{\{taille}", rf"\setlength{{\tabcolsep}}{{3pt}}", rf"\begin{{longtable}}{{{cols}}}",
         rf"\caption{{{legende}}}\label{{{label}}}\\", r"\toprule",
         " & ".join(rf"\textbf{{{h}}}" for h in entetes) + r" \\", r"\midrule", r"\endfirsthead",
         r"\toprule", " & ".join(rf"\textbf{{{h}}}" for h in entetes) + r" \\", r"\midrule", r"\endhead",
         r"\bottomrule", r"\endfoot"]
    for l in lignes:
        s.append(" & ".join(str(c) for c in l) + r" \\")
    s.append(r"\end{longtable}")
    if note:
        s.append(rf"\par\noindent{{\footnotesize {note}}}")
    s.append("}")
    (OUT / f"{nom}.tex").write_text("\n".join(s) + "\n", encoding="utf-8")
    ECRITS.append(nom)


def generique(nom, csv, legende, label, colonnes, note=None, nd=3):
    """colonnes : liste (colonne csv, en-tête, type) avec type 'n' nombre, 't' texte, 'l' liste, 'p' pourcentage, 'i' entier."""
    df = lire(csv)
    if df is None:
        return None
    ent = [c[1] for c in colonnes]
    lignes = []
    for _, r in df.iterrows():
        ligne = []
        for col, _, typ in colonnes:
            v = r.get(col)
            if typ == "n":
                ligne.append(num(float(v), nd) if pd.notna(v) else "n/d")
            elif typ == "i":
                ligne.append(str(int(v)) if pd.notna(v) else "n/d")
            elif typ == "l":
                ligne.append(liste(v, nd))
            elif typ == "p":
                ligne.append(num(100.0 * float(v), 1) + r"\,\%" if pd.notna(v) else "n/d")
            elif typ == "b":
                ligne.append("oui" if bool(v) else "non")
            else:
                ligne.append(esc(v))
        lignes.append(ligne)
    ecrire(nom, ent, lignes, legende, label, note=note)
    return df


# ------------------------------------------------------------------ chapitre 1 : exemples numériques
def chap1():
    df = lire("00_tableau_1_2_em_8_points.csv")
    if df is not None:
        lig = [[str(int(r.iteration)), num(r.mu1), num(r.mu2), num(r.sigma1), num(r.sigma2), num(r.pi1), num(r.pi2),
                num(r.loglik) if pd.notna(r.loglik) else "non rapportée"] for r in df.itertuples()]
        ecrire("t1_2", ["Itération", r"$\mu_1$", r"$\mu_2$", r"$\sigma_1$", r"$\sigma_2$", r"$\pi_1$", r"$\pi_2$", "Log-vraisemblance"],
               lig, "Convergence de l'algorithme EM sur l'exemple numérique à $K=2$ composantes (8 observations)", "tab:1_2")
    df = lire("00_tableau_1_4_forward_backward.csv")
    if df is not None:
        obs = ["NPa", "Pa", "Pa"]
        lig = [[str(int(r.t)), obs[int(r.t) - 1] if int(r.t) <= len(obs) else "", num(r.alpha_B), num(r.alpha_P), num(r.beta_B),
                num(r.beta_P), num(r.gamma_B), num(r.gamma_P)] for r in df.itertuples()]
        ecrire("t1_4", ["$t$", "Observation $o_t$", r"$\alpha_t$(B)", r"$\alpha_t$(P)", r"$\beta_t$(B)", r"$\beta_t$(P)", r"$\gamma_t$(B)", r"$\gamma_t$(P)"],
               lig, r"Calcul détaillé des quantités forward, backward et a posteriori pour $O=($NPa, Pa, Pa$)$", "tab:1_4",
               largeurs=[0.9, 2.6, 1.9, 1.9, 1.9, 1.9, 1.9, 1.9])
    generique("t1_5", "00_tableau_1_5_vb_8_points.csv",
              r"Résultat de l'EM variationnel sur l'exemple à 8 observations ($K_{\max}=3$) selon l'initialisation et la graine", "tab:1_5",
              [("init", "Init.", "t"), ("graine", "Graine", "i"), ("iterations", "Itérations", "i"), ("alpha", r"$\alpha_k$", "l"),
               ("m", r"$m_k$", "l"), ("actives", "Actives", "i")])


# ------------------------------------------------------------------ chapitre 2
def chap2():
    d = lire("01_comparaison_k6.csv")
    if d is not None:
        for nom, motif, label, leg in (("poids_em", "EM classique", "tab:2_5", r"Poids de mélange $\pi_k$ obtenus par l'EM classique ($K=6$)"),
                                       ("poids_vb", "variationnel", "tab:2_6", r"Poids de mélange $\mathbb{E}[\pi_k]$ obtenus par l'EM variationnel ($K_{\max}=6$)")):
            sous = d[d.modele.str.contains(motif)]
            ecrire(nom, ["Modèle", "Poids"], [[esc(r.modele), liste(r.poids)] for r in sous.itertuples()], leg, label, largeurs=[7.0, 8.3])
        cols = [("modele", "Modèle", "t"), ("composantes_actives", "Actives", "i"), ("ARI", "ARI", "n"), ("silhouette", "Silh.", "n"),
                ("iterations", "Itér.", "i")]
        if "converge" in d.columns:
            cols += [("converge", "Convergé", "b"), ("degenere", "Dégénéré", "b")]
        cols += [("temps_s", "Temps (s)", "n")]
        note = r"Critère d'arrêt commun (tolérance relative $10^{-6}$ sur le critère total, plafond de 500 étapes M) ; « convergé : non » signale un plafond atteint."
        generique("t2_7", "01_comparaison_k6.csv", r"Métriques de qualité de partition ($K=6$ imposé), critère d'arrêt commun", "tab:2_7", cols, note=note)
        generique("init_priors", "01_comparaison_k6.csv", r"Effet de l'initialisation et des priors (jeu de référence, $K=6$)", "tab:init_priors", cols, note=note)
    generique("t2_8", "02_sensibilite_alpha0.csv", r"Composantes actives ($N_k\geq1$) et ARI selon la concentration $\alpha_0$", "tab:2_8",
              [("alpha0", r"$\alpha_0$", "n"), ("priors", "Priors", "t"), ("composantes_actives", "Actives", "i"), ("ARI", "ARI", "n"),
               ("poids", "Poids", "l"), ("iterations", "Itér.", "i")], nd=3)
    colonnes9 = [("parametre", "Paramètre", "t"), ("valeur", "Valeur", "i"), ("n_rep", "Rép.", "i"), ("classique_s", "EM (s)", "n"),
                 ("variationnel_s", "VB (s)", "n"), ("ratio", "Ratio", "n")]
    d9 = lire("03_scalabilite.csv")
    if d9 is not None and "iter_classique" in d9.columns:
        colonnes9 += [("iter_classique", "Itér. EM", "n"), ("iter_variationnel", "Itér. VB", "n"), ("ratio_cout_iter", "Ratio coût/itér.", "n")]
    generique("t2_9", "03_scalabilite.csv", "Temps d'exécution selon $N$ et $D$ (médiane de répétitions ; critère d'arrêt commun)", "tab:2_9", colonnes9,
              note="Le ratio global (temps jusqu'au modèle final) mélange coût par itération et nombre d'itérations ; le ratio coût/itération les sépare. Tableau et figure sortent du même run.", nd=4)
    generique("t2_10", "04_k3.csv", r"Résultats de référence avec le nombre de composantes correctement spécifié ($K=3$)", "tab:2_10",
              [("modele", "Modèle", "t"), ("composantes_actives", "Actives", "i"), ("ARI", "ARI", "n"), ("silhouette", "Silh.", "n"),
               ("iterations", "Itér.", "i"), ("temps_s", "Temps (s)", "n"), ("poids", "Poids", "l")])
    d11 = lire("06_initialisation.csv")
    if d11 is not None:
        cols = list(d11.columns)
        ecrire("t2_11", [esc(c) for c in cols],
               [[esc(r[c]) for c in cols] for _, r in d11.iterrows()],
               "Nombre de composantes actives sur 20 initialisations indépendantes", "tab:2_11")
    generique("t2_12", "07_covariance.csv", r"ARI et nombre de composantes actives selon le type de covariance ($K=6$ imposé)", "tab:2_12",
              [("covariance", "Covariance", "t"), ("ARI_classique", "ARI EM", "n"), ("ARI_variationnel", "ARI VB", "n"),
               ("actives_variationnel", "Actives VB", "i"), ("BIC_classique", "BIC EM", "n")],
              note=r"Pour tied, diag et spherical le critère du VB est une approximation (ELBO sans le terme KL sur $\theta$), non l'ELBO.", nd=2)
    generique("t2_13", "08_iris.csv", r"Résultats sur le jeu réel Iris ($N=150$, $D=4$)", "tab:2_13",
              [("modele", "Modèle", "t"), ("composantes_actives", "Actives", "i"), ("ARI", "ARI", "n"), ("silhouette", "Silh.", "n"),
               ("iterations", "Itér.", "i"), ("temps_s", "Temps (s)", "n"), ("poids", "Poids", "l")])
    generique("t2_14", "09_aberrantes.csv", "Comportement en présence de 10 valeurs aberrantes ajoutées (tirage unique, graine 7 : illustration, non test de robustesse)", "tab:2_14",
              [("modele", "Modèle", "t"), ("ARI_hors_aberrantes", "ARI hors aberrations", "n"), ("composantes_actives", "Actives", "i"),
               ("trace_covariance_max", "Trace max.", "n"), ("poids_plus_petit", "Plus petit poids", "n")])
    d15 = lire("12_replication_resume.csv")
    if d15 is not None:
        ecrire("t2_15", ["Modèle", "R", "ARI moyen [IC 95 %]", "Silh. moy.", r"Part de jeux à $\hat K=3$ [IC de Wilson]", "Itér. moy.", "Temps (s)"],
               [[esc(r.modele), str(int(r.R)), num(r.ARI_moyen) + " " + esc(r.ARI_IC95), num(r.silhouette_moyenne),
                 num(100 * r.part_exactement_3_actives, 0) + r"\,\% " + esc(r.part_IC95_Wilson), num(r.iterations_moyennes, 1), num(r.temps_moyen_s, 2)]
                for r in d15.itertuples()],
               "Résultats moyens sur 30 jeux de données d'un même générateur ($K=6$ imposé)", "tab:2_15")
    generique("t2_16", "12_replication_differences.csv", "Différences appariées d'ARI entre EM variationnel et EM classique", "tab:2_16",
              [("comparaison", "Comparaison", "t"), ("difference_moyenne", "Différence moyenne", "n"), ("IC95_bootstrap", "IC 95 % (bootstrap)", "t"),
               ("jeux_ou_variationnel_meilleur", "Jeux favorables au VB", "t")])


# ------------------------------------------------------------------ scénarios synthétiques
def scenarios():
    cols = [("parametre", "Paramètre", "t"), ("bras", "Bras", "t"), ("k_hat_moy", r"$\hat K$ moy.", "n"), ("erreur_k", r"$\lvert\hat K-K\rvert$", "n"),
            ("ARI", "ARI", "n"), ("loglik_test", "LL test", "n"), ("degenere", "Dégénérés", "p"), ("non_converge", "Non convergés", "p"),
            ("temps_med", "Temps méd. (s)", "n"), ("n", "Rép.", "i")]
    titres = {"S1_chevauchement": ("Chevauchement croissant (S1)", "tab:S1"), "S2_desequilibre": ("Poids déséquilibrés 80/15/5 (S2)", "tab:S2"),
              "S3_sous_estimation": (r"Sous-estimation de $K$ : $K$ choisi $=3<K$ vrai (S3)", "tab:S3"),
              "S4_queues_epaisses": ("Queues épaisses : composantes de Student, $\\nu=3$ (S4)", "tab:S4"),
              "S5_dimension": ("Dimension croissante (S5)", "tab:S5"), "S6_petit_N": ("Petit effectif $N$ (S6)", "tab:S6"),
              "S7_aberrations": ("Aberrations : proportion et amplitude variées (S7)", "tab:S7")}
    for fich, (t, lab) in titres.items():
        generique(fich, f"{fich}.csv", t + " : moyennes sur les réplications (au moins 30)", lab, cols,
                  note="Mêmes critère d'arrêt et graines pour tous les bras ; LL test : log-vraisemblance moyenne par observation sur un jeu indépendant. Tests appariés : grille du tableau récapitulatif.")
    d = lire("S8_alpha0.csv")
    if d is not None:
        ecrire("S8_alpha0", ["Covariance", r"$\alpha_0$", r"$\bar K$ actif (1 %)", "Écart-type", "ARI", "Non convergés"],
               [[esc(r.cov), num(r.alpha0, 2), num(r.k_moy, 2), num(r.k_sd, 2), num(r.ARI), num(100 * r.non_converge, 0) + r"\,\%"] for r in d.itertuples()],
               r"Nombre de composantes actives du VB selon $\alpha_0$ et le type de covariance ($K_{\max}=6$)", "tab:S8",
               note=r"Seuils théoriques de Rousseau et Mengersen (2011) en $D=2$ : $d/2=2{,}5$ (pleine), $2$ (diagonale), $1{,}5$ (sphérique) ; hypothèse à tester, la théorie portant sur le posterior exact. Covariances tied/diag/spherical : critère approché.")
    generique("S9_decomposition_variance", "S9_decomposition_variance.csv", r"Part de variance du nombre de composantes actives expliquée par chaque facteur du plan factoriel", "tab:S9",
              [("facteur", "Facteur", "t"), ("part_variance_Khat", "Part de variance", "p")], note="Effets principaux ; le résidu contient les interactions.")
    generique("S10_seuil_activite", "S10_seuil_activite.csv", r"Nombre moyen de composantes actives du VB selon le seuil d'activité", "tab:S10",
              [("alpha0", r"$\alpha_0$", "n"), ("N_k_ge_1", r"$N_k\geq1$", "n"), ("pct_0.5", "0,5 % de $N$", "n"), ("pct_1", "1 % de $N$", "n"), ("pct_5", "5 % de $N$", "n")], nd=2)


# ------------------------------------------------------------------ climat
def climat():
    d = lire("climat/couverture.csv")
    if d is not None:
        lig = []
        for (meth, par), s in d.groupby(["methode", "param"]):
            n = len(s)
            p = float(s.couvert.mean())
            z = 1.959963984540054
            dd = 1 + z * z / n
            c = (p + z * z / (2 * n)) / dd
            h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / dd
            lig.append([esc(meth), esc(par), str(n), num(100 * p, 1) + r"\,\%", f"[{num(100 * max(0, c - h), 1)} ; {num(100 * min(1, c + h), 1)}]"])
        ecrire("climat_couverture", ["Méthode", "Paramètre", "Cas", "Couverture empirique", "IC de Wilson 95 %"], lig,
               "Couverture empirique des intervalles à 90 % sur le jeu semi-synthétique (cas climatique)", "tab:climat_couverture",
               note="Nominal : 90 %. Intervalle de crédibilité (VB) et intervalle de confiance bootstrap (EM) : objets différents, comparaison de calibration.")
    generique("climat_grille", "climat/grille_hypotheses_climat.csv", "Grille de décision des hypothèses H1 à H8 (cas climatique)", "tab:climat_grille",
              [("id", "N°", "t"), ("axe", "Axe", "t"), ("enonce", "Énoncé", "t"), ("decision", "Décision", "t"), ("intervalle", "Intervalle", "t"),
               ("p_holm", "$p$ (Holm)", "n"), ("niveau_preuve", "Niveau de preuve", "t")])
    d = lire("climat/sous_echantillons_D5.csv")
    if d is not None:
        d = d.assign(N=d.N.astype(str))
        ordre = {"30": 0, "60": 1, "120": 2, "500": 3, "2000": 4, "complet": 5}
        lig = []
        for (N, bras), s in sorted(d.groupby(["N", "bras"]), key=lambda t: (ordre.get(t[0][0], 9), t[0][1])):
            ok = s[~s.echec.astype(bool)]
            ari = ok["ARI_koppen"].mean() if "ARI_koppen" in ok.columns else float("nan")
            lig.append([esc(N), esc(bras), num(float(ok.k_hat.mean()), 1), num(float(ari), 3), num(float(ok.loglik_plugin.median()), 2),
                        num(float(ok.loglik_predictive.median()), 2) if ok.loglik_predictive.notna().any() else "n/d",
                        num(100 * float(ok.degenere.astype(float).mean()), 0) + r"\,\%", num(float(ok.temps_s.median()), 2), str(len(s))])
        ecrire("climat_sous", [r"$N$", "Bras", r"$\hat K$ moy.", "ARI Köppen", "LL hors bloc (méd.)", "LL prédictive VB (méd.)", "Dégénérés", "Temps méd. (s)", "Rép."], lig,
               r"Cas climatique, sous-échantillons espacés ($D=5$, référence Köppen--Geiger seule) : moyennes sur les réplications", "tab:climat_sous",
               largeurs=[1.1, 1.8, 1.3, 1.6, 2.3, 2.3, 1.7, 1.7, 1.0],
               note=r"LL : log-vraisemblance moyenne par observation sur des blocs de 100 km sans point d'apprentissage ; $\hat K$ des bras MAP-EM et VB : composantes avec $N_k/N\geq1\,\%$. Une seule exécution à $N$ complet.")
    d = lire("climat/semi_synthetique.csv")
    if d is not None:
        d = d.assign(N=d.N.astype(str))
        lig = []
        for (N, bras), s in sorted(d.groupby(["N", "bras"]), key=lambda t: (int(t[0][0]), t[0][1])):
            lig.append([esc(N), esc(bras), num(float(s.k_hat.mean()), 2), num(float(s.erreur_k.mean()), 2), num(float(s.ARI.mean()), 3),
                        num(100 * float(s.degenere.astype(float).mean()), 0) + r"\,\%", str(len(s))])
        ecrire("climat_semi", [r"$N$", "Bras", r"$\hat K$ moy.", r"$\lvert\hat K-5\rvert$", "ARI vérité", "Dégénérés", "Jeux"], lig,
               r"Jeu semi-synthétique ($K_{\text{réf}}=5$, modèle ajusté à $N$ complet) : sélection de $K$ et qualité de partition", "tab:climat_semi")
    d = lire("climat/sous_echantillons_D5.csv")
    if d is not None:
        lig = []
        for N, s in d.groupby("N", sort=False):
            a, b = s[s.bras == "EM-BIC"].temps_s, s[s.bras == "VB-emp"].temps_s
            if len(a) and len(b):
                lig.append([esc(N), num(float(a.median()), 3), num(float(b.median()), 3), num(float(a.median() / b.median()), 2)])
        ecrire("cout_selection", [r"$N$", "EM-BIC, balayage complet (s)", "VB, un ajustement (s)", "Ratio"], lig,
               "Temps total jusqu'au modèle final : pipeline EM-BIC ($K$ de 1 à 10, 10 initialisations) contre un VB à 10 initialisations (médianes)", "tab:cout_selection",
               note="Ratio supérieur à 1 : le pipeline EM-BIC coûte plus. Même machine, même critère d'arrêt.")


def climat_d20():
    d = lire("climat/sous_echantillons_D20.csv")
    if d is None:
        return
    d = d.assign(N=d.N.astype(str))
    lig = []
    for (N, bras), s in sorted(d.groupby(["N", "bras"]), key=lambda t: (int(t[0][0]), t[0][1])):
        ok = s[~s.echec.astype(bool)]
        lig.append([esc(N), esc(bras), num(float(ok.k_hat.mean()), 1) if len(ok) else "n/d",
                    num(float(ok["ARI_koppen"].mean()), 3) if len(ok) else "n/d",
                    num(100 * float(s.echec.astype(float).mean()), 0) + r"\,\%",
                    num(100 * float(s.apply(lambda r: True if bool(r.echec) else bool(r.degenere), axis=1).mean()), 0) + r"\,\%", str(len(s))])
    ecrire("climat_sous20", [r"$N$", "Bras", r"$\hat K$ moy.", "ARI Köppen", "Échecs numériques", "Dégénérés (échecs inclus)", "Rép."], lig,
           r"Cas climatique, extension à $D=20$ (19 variables bioclimatiques et l'altitude) : sous-échantillons espacés", "tab:climat_sous20",
           note=r"Un échec numérique (covariance non définie positive) est compté comme ajustement dégénéré ; moyennes calculées sur les ajustements qui ont abouti.")


# ------------------------------------------------------------------ S&P 500
def sp500():
    generique("sp500_descriptif", "cas_pratique_descriptif.csv", "Statistiques descriptives des rendements journaliers (%) : apprentissage et évaluation", "tab:3_cas_desc",
              [("periode", "Période", "t"), ("observations", "Obs.", "i"), ("moyenne_pct", "Moyenne", "n"), ("ecart_type_pct", "Écart-type", "n"),
               ("asymetrie", "Asymétrie", "n"), ("kurtosis_excedentaire", "Kurtosis exc.", "n"), ("minimum_pct", "Min.", "n"), ("maximum_pct", "Max.", "n")])
    generique("sp500_backtests", "sp500_backtests.csv", "Backtests de la VaR et de l'ES (période d'évaluation)", "tab:sp500_backtests",
              [("modele", "Modèle", "t"), ("niveau", "Niv.", "n"), ("exceptions", "Exc.", "i"), ("attendues", "Att.", "n"), ("Kupiec_p", "Kupiec $p$", "n"),
               ("Christoffersen_ind_p", "Chr. ind. $p$", "n"), ("Christoffersen_cc_p", "Chr. cc $p$", "n"), ("AS_Z1", "$Z_1$", "n"), ("AS_Z2", "$Z_2$", "n"),
               ("logscore_moyen", "Log-score", "n")],
              note=r"Exc. : exceptions observées, Att. : attendues. $Z_1$, $Z_2$ d'Acerbi et Székely (2014) : valeurs positives = risque sous-estimé. Les écarts d'une exception entre mélanges EM et VB ne sont pas une différence d'algorithme.", nd=3)
    generique("sp500_diebold_mariano", "sp500_diebold_mariano.csv", "Tests de Diebold--Mariano sur les log-scores quotidiens (correction de Harvey)", "tab:sp500_dm",
              [("A", "Modèle A", "t"), ("B", "Modèle B", "t"), ("ecart_logscore_moyen", "Écart moyen (nat/jour)", "n"), ("DM", "DM", "n"), ("p", "$p$", "n"), ("p_holm", "$p$ (Holm)", "n")])
    generique("sp500_intervalles", "sp500_intervalles.csv", "Intervalles à 95 % de la VaR : bootstrap de l'EM contre crédibilité du VB", "tab:sp500_int",
              [("niveau", "Niv.", "n"), ("B", "$B$", "i"), ("IC95_bootstrap_EM", "Bootstrap EM", "t"), ("largeur_bootstrap", "Largeur", "n"),
               ("IC95_credible_VB", "Crédibilité VB", "t"), ("largeur_VB", "Largeur", "n")],
              note="Objets différents (variabilité d'estimateur contre crédibilité a posteriori) : la comparaison des largeurs n'est pas une comparaison de fiabilité.")


# ------------------------------------------------------------------ texte
def texte():
    generique("texte_plsa_lda", "texte_plsa_lda.csv", "pLSA contre LDA sur 20 Newsgroups (4 groupes) selon le nombre de documents $N$ d'apprentissage", "tab:texte",
              [("N", "$N$", "i"), ("modele", "Modèle", "t"), ("ppl_test", "Perplexité test", "n"), ("ecart_rel", "Écart relatif test/appr.", "n"),
               ("planchers", "Mots planchés", "p"), ("NPMI", "NPMI", "n"), ("purete", "Pureté", "n"), ("non_converge", "Non convergés", "p")],
              note="Écart relatif : perplexité hors échantillon / perplexité d'apprentissage - 1. Moyennes sur les réplications.")
    generique("texte_grille", "texte_grille.csv", "Test apparié du surapprentissage (pLSA moins LDA, écart relatif de perplexité)", "tab:texte_grille",
              [("id", "N°", "t"), ("decision", "Décision", "t"), ("estimation", "Estimation", "n"), ("intervalle", "IC bootstrap 95 %", "t"), ("n", "Rép.", "i")])


# ------------------------------------------------------------------ grille « axe x preuve »
def decisions(csv, prefixe):
    d = lire(csv) if (RES / csv).exists() else None
    if d is None or "id" not in d.columns:
        return None
    s = d[d["id"].astype(str).str.startswith(prefixe)]
    if not len(s):
        return None
    return "; ".join(f"{esc(r.id)} : {esc(r.decision)}" for r in s.itertuples())


def grille_scenarios():
    generique("grille_scenarios", "grille_scenarios.csv", "Décisions des tests appariés des scénarios (VB à priors empiriques contre EM-BIC, sauf S3 : VB à $K_{\max}=K$ contre EM à $K$ ; S6 : taux de dégénérescence contre EM à $K_{\max}$)", "tab:grille_scenarios",
              [("id", "N°", "t"), ("decision", "Décision", "t"), ("estimation", "Différence moyenne", "n"), ("intervalle", "IC bootstrap 95 %", "t"), ("p_holm", "$p$ (Holm)", "n"), ("n", "Rép.", "i")],
              note="Équivalence par TOST (marge $\pm0{,}03$ en ARI, $\pm0{,}5$ en $\hat K$, $\pm0{,}1$ en taux de dégénérescence) ; sinon test des rangs signés de Wilcoxon ; « A > B » : le premier bras est supérieur. Correction de Holm sur l'ensemble des tests de la grille.", nd=3)


def grille():
    ABS_MSG = r"\emph{non encore généré}"
    lignes_def = [
        # (axe, affirmation, source, niveau si source présente, niveau sinon, sections)
        ("Sélection de $K$", "VB comparé à EM-BIC/ICL, dans l'intervalle de $\\pm0{,}5$ composante", ("grille_scenarios.csv", "S1"), "expérience répliquée", "§2.3.16"),
        ("Composante minoritaire", "Le VB perd la composante à 5 \\% plus souvent que EM-BIC", ("grille_scenarios.csv", "S2"), "expérience répliquée", "§2.3.16"),
        ("Sous-estimation de $K$", "Avec $K_{\\max}=K$ choisi $<K$ vrai, le VB ne corrige pas l'erreur", ("grille_scenarios.csv", "S3"), "expérience répliquée", "§2.3.16"),
        ("Queues épaisses", "Composantes de Student : VB comparé à EM-BIC", ("grille_scenarios.csv", "S4"), "expérience répliquée", "§2.3.17"),
        ("Dimension", "Dimension croissante $D\\in\\{2,5,10,20\\}$", ("grille_scenarios.csv", "S5"), "expérience répliquée", "§2.3.17"),
        ("Singularités, petit $N$", "Taux d'ajustements dégénérés selon $N$ (EM régularisé par $\\varepsilon I$)", ("grille_scenarios.csv", "S6"), "expérience répliquée", "§2.3.17"),
        ("Valeurs aberrantes", "Proportion et amplitude variées", ("grille_scenarios.csv", "S7"), "expérience répliquée", "§2.3.18"),
        ("Coût de calcul", "Pipeline EM-BIC contre un VB, temps total", ("climat/grille_hypotheses_climat.csv", "H4"), "expérience répliquée", "§2.3.20"),
        ("Sensibilité aux priors", "Variance de $\\hat K$ due aux priors contre due à l'initialisation", ("climat/grille_hypotheses_climat.csv", "H5"), "expérience unique", "§2.3.19"),
        ("Incertitude", "Couverture des intervalles de crédibilité à 90 \\% du VB", ("climat/grille_hypotheses_climat.csv", "H6"), "expérience répliquée", "§2.3.15"),
        ("Chevauchement", "Le VB fusionne plus de zones voisines que EM-BIC", ("climat/grille_hypotheses_climat.csv", "H7"), "expérience répliquée", "§3.1.1"),
        ("Singularités (climat)", "VB contre EM-10, $N\\leq120$", ("climat/grille_hypotheses_climat.csv", "H3"), "expérience répliquée", "§3.1.1"),
        ("Surapprentissage (texte)", "pLSA sur-apprend davantage que LDA quand $N$ est petit", ("texte_grille.csv", "H-texte"), "expérience répliquée", "§3.1.2"),
        ("Seuil d'élagage", "Seuil $d/2$ de $\\alpha_0$ transféré au champ moyen", ("S8_alpha0.csv", None), "expérience répliquée", "§1.7.4, §2.3.14"),
        ("Seuil d'activité", "Le nombre de composantes actives dépend du seuil", ("S10_seuil_activite.csv", None), "expérience répliquée", "§2.3.19"),
        ("Gestion du risque", "Intervalles de VaR : bootstrap EM contre crédibilité VB", ("sp500_intervalles.csv", None), "expérience unique", "§3.1.3"),
        ("Dépendance à $K_{\\max}$", "Résultat de l'élagage dépendant de $K_{\\max}$ (Iris, $K_{\\max}=6$ contre 3)", ("08_iris.csv", None), "expérience unique", "§2.3.11"),
        ("Biais d'approximation", "Variance sous-estimée par le champ moyen", None, "théorème", "§1.5.4 (cas général, Bishop 2006) ; couverture dans le GMM : voir H6"),
        ("Monotonie du critère", "Croissance de la log-vraisemblance (EM) et de l'ELBO (VB, covariance pleine)", None, "théorème", "§1.6.3, §1.7.6 ; tests unitaires"),
        ("Convergence de l'EM pour le GMM", "Le théorème de Wu (1983) ne s'applique pas tel quel (vraisemblance non bornée)", None, "théorème", "§1.6.3 ; régularisation $\\varepsilon I$"),
        ("Initialisation", "Sensibilité du nombre de composantes actives à l'initialisation (20 graines)", ("06_initialisation.csv", None), "expérience unique", "§2.3.9"),
        ("Consistance de la sélection de $K$", "Garantie de consistance du champ moyen pour $K$", None, "non testé", "§1.7.9 ; théorie sur le posterior exact seulement"),
        ("Taux de l'EM en sur-spécification", "Convergence lente, précision $(d/n)^{1/4}$ dans le cas équilibré (Dwivedi et al., 2020)", None, "non testé", "§1.6.3.d ; théorème hors du cadre des covariances libres"),
        ("Cible de l'EM en sous-spécification", "Convergence vers la projection de Kullback-Leibler (Dwivedi et al., 2018)", None, "non testé", "§1.6.3.d ; lecture des cas S4 et du chapitre 3"),
        ("Consistance des paramètres du VB", "Moyenne variationnelle consistante, covariance trop petite (Wang et Titterington, cités)", None, "non testé", "§1.7.9 ; H6 cohérente, sans vérification"),
        ("Optima locaux de l'ELBO", "Fréquence des optima locaux du VB", None, "non testé", "—"),
        ("Irréversibilité de l'élagage", "Une composante éteinte ne revient pas", None, "non testé", "§1.7.4"),
        ("Double usage des données", "Effet des priors empiriques sur l'ELBO et les intervalles", None, "non testé", "§2.3.1"),
        ("Vitesse de VAE, flux normalisants, gradient naturel", "Affirmations de vitesse des variantes avancées", None, "non testé", "§1.7.7"),
        ("Vision, bio-informatique, recommandation", "Choix d'algorithme par domaine", None, "non testé", "§3.1.3, revue"),
    ]
    lig = []
    for axe, aff, src, niv, sec in lignes_def:
        if src is None:
            preuve, niveau = ("référence théorique" if niv == "théorème" else "aucune"), niv
        else:
            csv, pref = src
            fichier = RES / csv
            if fichier.exists():
                if pref:
                    dec = decisions(csv, pref)
                    preuve = dec if dec else ABS_MSG
                else:
                    preuve = r"voir " + esc(csv)
                niveau = niv if (pref is None or dec) else "non testé (résultats non générés)"
            else:
                preuve, niveau = ABS_MSG, "non testé (résultats non générés)"
        lig.append([axe, aff, preuve, esc(niveau), sec])
    ecrire("grille_axe_preuve", ["Axe", "Affirmation (avantage ou inconvénient)", "Preuve (décision lue dans le fichier de résultats)", "Niveau de preuve", "Section"],
           lig, r"Grille « axe $\times$ preuve » : chaque affirmation renvoie à un théorème, une expérience ou la mention « non testé »", "tab:2_17",
           largeurs=[2.4, 4.2, 4.6, 2.2, 1.9],
           note="Niveaux : théorème ; expérience répliquée (au moins 30 réplications) ; expérience unique ; non testé. Aucune ligne n'autorise à parler de supériorité d'un algorithme.")
    g = [
        ("$K$ connu avec confiance", "EM classique ou VB peuvent convenir ; confirmer l'équivalence", "expérience répliquée (S1, S3)"),
        ("$K$ inconnu", "EM-BIC/ICL ou VB : choix selon le coût total et le besoin d'incertitude", "expérience répliquée (H1, H4)"),
        ("Besoin d'une incertitude en aval", "VB (approchée) ; vérifier la couverture ; bootstrap pour l'EM", "expérience répliquée (H6)"),
        ("Petit effectif", "Comparer les taux de dégénérescence ; régulariser l'EM", "expérience répliquée (S6, H3)"),
        ("Grande dimension ($D>20$)", "Non testé dans ce mémoire", "non testé"),
        ("Très grand $N$", "EM online ou SVI pour les deux familles", "non testé (références)"),
        ("Sensibilité aux priors acceptable", "VB avec priors fixés avant les données ; plan factoriel", "expérience unique (H5, S9)"),
    ]
    ecrire("guide_decision", ["Situation", "Recommandation prudente", "Niveau de preuve"], [[a, b, esc(c)] for a, b, c in g],
           "Guide de décision avec niveau de preuve (aucune ligne n'est une recommandation absolue)", "tab:3_4", largeurs=[4.3, 7.2, 3.8])


def main():
    for f in (chap1, chap2, scenarios, grille_scenarios, climat, climat_d20, sp500, texte, grille):
        f()
    print("Tableaux écrits :", len(ECRITS))
    manquants = sorted(set(ABSENTS))
    if manquants:
        print("Fichiers de résultats absents (tableaux correspondants non écrits) :")
        for m in manquants:
            print("  -", m)


if __name__ == "__main__":
    main()
