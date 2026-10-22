"""
================================================================================
REGISTRE DES PARAMÈTRES : aucune valeur méthodologique sans justification
================================================================================

Chaque paramètre utilisé par le code est déclaré ici avec :
  * statut :
      mathematique  conséquence d'un fait mathématique, démontré ou cité ;
      source        valeur prescrite par une référence vérifiée (clé de la bibliographie) ;
      plan          choix de conception du protocole (plan de recherche), déclaré avant l'analyse ;
      benchmark     valeur fixée par une étude de calibrage (étape `calibrage`) selon une règle écrite ici ;
      recherche     valeur fixée par une recherche heuristique sur un grand espace (validation croisée,
                    jamais sur les données de test) ;
      donnees       valeur estimée sur les données selon une règle écrite ici ;
      performance   réglage d'exécution sans effet sur les résultats (vérifié par test d'équivalence).
  * justification : la règle ou le raisonnement, en clair ;
  * references : clés bibliographiques vérifiées (titre, revue, pages contrôlés en ligne) ;
  * calibrage : identifiant de l'étude qui fixe la valeur (resultats/calibrage/<id>.json).

Tant qu'une valeur de statut benchmark, recherche ou donnees n'a pas été calibrée, `valeur()`
renvoie la valeur provisoire et l'enregistre dans `provisoires()` : l'orchestrateur `run.py`
refuse alors de lancer les étapes confirmatoires (sauf option explicite --autoriser-provisoire,
réservée aux essais).
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

RACINE = Path(__file__).parent


def dossier_calibrage() -> Path:
    """resultats/calibrage (exécution complète) ou resultats/calibrage_rapide (essais : run.py --rapide)."""
    return RACINE / "resultats" / ("calibrage_rapide" if os.environ.get("ICARE_RAPIDE") == "1" else "calibrage")

STATUTS = ("mathematique", "source", "plan", "benchmark", "recherche", "donnees", "performance")


@dataclass(frozen=True)
class Parametre:
    nom: str
    provisoire: object
    statut: str
    justification: str
    references: tuple = ()
    calibrage: str | None = None
    cle: str | None = None            # clé dans le fichier de calibrage (par défaut : nom)


R: dict[str, Parametre] = {}

# Références citées par le registre : vérifiées (éditeur, JSTOR, DOI ou copie locale), voir references/SOURCES.md.
REFERENCES = {
    "bergstra2012": "J. Bergstra, Y. Bengio, Random search for hyper-parameter optimization, JMLR 13, 281-305, 2012",
    "biernacki2003": "C. Biernacki, G. Celeux, G. Govaert, Choosing starting values for the EM algorithm for getting the highest "
                     "likelihood in multivariate Gaussian mixture models, Comput. Stat. Data Anal. 41(3-4), 561-575, 2003",
    "bishop2006": "C. M. Bishop, Pattern Recognition and Machine Learning, Springer, 2006",
    "blei2003": "D. M. Blei, A. Y. Ng, M. I. Jordan, Latent Dirichlet Allocation, JMLR 3, 993-1022, 2003",
    "cappe2009": "O. Cappé, E. Moulines, On-line expectation-maximization algorithm for latent data models, JRSS B 71(3), 593-613, 2009",
    "cohen1988": "J. Cohen, Statistical Power Analysis for the Behavioral Sciences, 2e éd., Lawrence Erlbaum, 1988",
    "hoffman2013": "M. D. Hoffman, D. M. Blei, C. Wang, J. Paisley, Stochastic variational inference, JMLR 14, 1303-1347, 2013",
    "holm1979": "S. Holm, A simple sequentially rejective multiple test procedure, Scand. J. Statist. 6(2), 65-70, 1979",
    "jamieson2016": "K. Jamieson, A. Talwalkar, Non-stochastic best arm identification and hyperparameter optimization, "
                    "AISTATS, PMLR 51, 240-248, 2016",
    "lakens2017": "D. Lakens, Equivalence tests: a practical primer for t tests, correlations, and meta-analyses, "
                  "Soc. Psychol. Personal. Sci. 8(4), 355-362, 2017",
    "pedregosa2011": "F. Pedregosa et al., Scikit-learn: Machine learning in Python, JMLR 12, 2825-2830, 2011",
    "porter1980": "M. F. Porter, An algorithm for suffix stripping, Program 14(3), 130-137, 1980",
    "robbins1951": "H. Robbins, S. Monro, A stochastic approximation method, Ann. Math. Statist. 22(3), 400-407, 1951",
    "roberts2017": "D. R. Roberts et al., Cross-validation strategies for data with temporal, spatial, hierarchical, or "
                   "phylogenetic structure, Ecography 40(8), 913-929, 2017",
    "schuirmann1987": "D. J. Schuirmann, A comparison of the two one-sided tests procedure and the power approach for assessing "
                      "the equivalence of average bioavailability, J. Pharmacokinet. Biopharm. 15(6), 657-680, 1987",
    "schwarz1978": "G. Schwarz, Estimating the dimension of a model, Ann. Statist. 6(2), 461-464, 1978",
}


def _p(*a, **k):
    p = Parametre(*a, **k)
    assert p.statut in STATUTS, p.statut
    assert all(r in REFERENCES for r in p.references), f"{p.nom} : référence non vérifiée {p.references}"
    assert p.statut not in ("benchmark", "recherche", "donnees") or p.calibrage, f"{p.nom} : étude de calibrage requise"
    R[p.nom] = p


# ------------------------------------------------------------------------------ critère d'arrêt et régularisation
_p("tol_rel", 1e-6, "benchmark",
   "Plus grande tolérance relative pour laquelle les résultats (critère final, K̂, ARI) ne diffèrent pas de ceux obtenus "
   "avec une tolérance 100 fois plus stricte, au-delà de l'écart observé entre deux relances convergeant vers le même optimum. "
   "Grille 1e-3 à 1e-10 sur les jeux du protocole.", calibrage="tolerance")
_p("n_iter_max", 500, "benchmark",
   "Plafond d'étapes M tel que, avec tol_rel calibrée, moins de 1 % des ajustements du pilote l'atteignent ; "
   "les ajustements plafonnés sont marqués non convergés.", calibrage="tolerance")
_p("reg_covariance", 1e-6, "recherche",
   "Régularisation + reg I des covariances (EM, MAP-EM). Choisie sur une grille logarithmique 0 et 1e-10 à 1e-1 "
   "en maximisant la log-vraisemblance moyenne hors échantillon (validation croisée sur les jeux d'apprentissage).",
   calibrage="regularisation")
_p("kmeans_n_iter_max", 100, "benchmark",
   "Plafond des itérations de Lloyd pour l'initialisation : la part des initialisations qui l'atteignent est mesurée sur "
   "les jeux du protocole ; le plafond est relevé (par pas de 100) tant qu'elle dépasse 1 %.", calibrage="kmeans")

# ------------------------------------------------------------------------------ relances
_p("n_init", {"synthetique": 10, "iris": 10, "sp500": 10, "climat": 10, "texte": 10}, "benchmark",
   "Par famille de données : nombre de relances tel que la probabilité qu'au moins une relance atteigne le meilleur "
   "optimum (à 10 fois la tolérance d'arrêt près) soit au moins 0,99, soit ceil(ln 0,01 / ln(1 - p)) où p est estimé "
   "par 200 relances pilotes, pour le plus difficile des algorithmes comparés ; plafonné à la taille du pilote (200), "
   "la probabilité résiduelle étant alors rapportée.", references=("biernacki2003",), calibrage="n_init")

# ------------------------------------------------------------------------------ composantes actives, dégénérescence
_p("seuil_actif", 0.01, "plan",
   "Composante active si N_k / N >= 1 % (plan de recherche) ; sensibilité aux seuils 0,5 %, 5 % et N_k >= 1 rapportée (scénario S10).")
_p("k_max", {"synthetique": 6, "climat": 10, "sp500": 6}, "plan",
   "Nombre maximal de composantes du plan (au moins deux fois le K de référence) ; la dépendance à Kmax est un objet "
   "d'étude (Iris, sections 2.3.11), non un réglage.")

# ------------------------------------------------------------------------------ priors
_p("alpha0_map", 1.0, "mathematique",
   "MAP-EM : plus petite concentration de Dirichlet pour laquelle le mode existe à l'intérieur du simplexe "
   "(alpha0 >= 1) ; alpha0 = 1 n'ajoute aucun pseudo-compte, le mode en pi coïncide avec l'estimateur du maximum de vraisemblance.")
_p("priors_reference", "emp,diff", "source",
   "Deux jeux de référence comparés tels quels : « empiriques » (beta0 = 1, nu0 = D, W0^-1 = covariance empirique, "
   "m0 = moyenne, alpha0 = 1/Kmax : valeurs par défaut documentées de BayesianGaussianMixture) et « diffus » "
   "(beta0 = 1e-3, W0 = I, nu0 = D). Ils ne sont pas présentés comme optimaux : le bras calibré est VB-cal.",
   references=("pedregosa2011",))
_p("espace_priors", {"alpha0": (1e-3, 10.0), "beta0": (1e-4, 1e2), "nu0_plus": (0.0, 50.0), "echelle_w0": (1e-2, 1e2)},
   "plan",
   "Espace de recherche des hyperparamètres Normal-Wishart et Dirichlet (bornes, échelle logarithmique sauf nu0 - D) : il "
   "contient les deux jeux de référence (alpha0 = 1/Kmax, beta0 = 1e-3 ou 1, nu0 = D, W0 = I ou covariance empirique) et "
   "s'étend de deux ordres de grandeur au moins de part et d'autre ; nu0 > D - 1 garantit une loi de Wishart propre "
   "(Bishop 2006, section 2.3.6). Les illustrations de sensibilité parcourent les mêmes bornes.", references=("bishop2006",))
_p("priors_vb_calibres", {f: {"alpha0": 0.1, "beta0": 1.0, "nu0_plus": 0.0, "echelle_w0": 1.0}
                          for f in ("synthetique", "climat", "sp500")}, "recherche",
   "Bras VB-cal et MAP-cal : hyperparamètres choisis par recherche aléatoire puis divisions successives (successive halving) "
   "sur l'espace « espace_priors », en maximisant la log-vraisemblance prédictive moyenne en validation croisée sur les données d'apprentissage, "
   "séparément pour chaque famille de données (plis spatiaux par blocs pour le climat). Toutes les évaluations sont conservées "
   "pour l'analyse de sensibilité (configurations plausibles).",
   references=("bergstra2012", "jamieson2016"), calibrage="priors")

# ------------------------------------------------------------------------------ inférence statistique
_p("alpha_test", 0.05, "plan", "Niveau des tests, déclaré dans le plan ; contrôle du risque familial par la procédure de Holm.",
   references=("holm1979",))
_p("marges_equivalence", {"ARI": 0.03, "LL": 0.02}, "donnees",
   "Plus petite différence d'intérêt (Lakens 2017) : quantile à 95 % de l'écart absolu entre deux ajustements de la MÊME "
   "méthode avec des graines différentes sur les mêmes données (plancher de bruit d'optimisation), avec un plancher de 0,001 ; "
   "un écart inférieur n'est pas attribuable à la méthode.", references=("lakens2017", "schuirmann1987"), calibrage="marges")
_p("marge_k", 0.5, "mathematique",
   "Marge d'équivalence sur l'erreur moyenne de K : K est entier, un écart moyen inférieur à 0,5 signifie que la "
   "majorité des réplications ne diffèrent pas d'une composante entière.")
_p("n_bootstrap_ic", 2000, "benchmark",
   "Nombre de rééchantillonnages des intervalles bootstrap : erreur Monte Carlo des bornes inférieure à la moitié de la "
   "dernière décimale affichée (3 décimales), estimée par répétition du bootstrap.", calibrage="monte_carlo")
_p("n_bootstrap_modele", 1000, "benchmark",
   "Nombre de réplicats bootstrap des intervalles de paramètres et de VaR : même règle de précision Monte Carlo.",
   calibrage="monte_carlo")
_p("n_tirages_posterieur", 4000, "benchmark",
   "Tirages a posteriori pour les intervalles de crédibilité : même règle de précision Monte Carlo.", calibrage="monte_carlo")
_p("n_simulation_var", 200000, "benchmark",
   "Tirages Monte Carlo de la VaR et de l'ES prédictives : même règle de précision Monte Carlo.", calibrage="monte_carlo")
_p("effet_standardise", 0.5, "source",
   "Hypothèses de différence sans marge naturelle (taux d'ajustements dégénérés, écart relatif de perplexité) : la puissance "
   "est calculée pour un écart vrai égal à 0,5 écart-type des différences appariées du pilote (effet « moyen » de Cohen) ; "
   "pour les métriques munies d'une marge (ARI, log-vraisemblance, K), l'écart vrai est la marge.", references=("cohen1988",))
_p("taille_pilote", 10, "plan",
   "Réplications pilotes servant à estimer la variance des différences appariées avant le calcul de puissance ; "
   "les données du pilote ne sont pas réutilisées dans les tests confirmatoires (graines disjointes).",
   references=("lakens2017",))
_p("replications", {"scenarios": 30, "climat_sous": 40, "climat_semi": 60, "climat_d20": 40, "climat_sensibilite": 20,
                    "texte": 10}, "benchmark",
   "Nombre de réplications : puissance d'au moins 0,8 du test déclaré (TOST à la marge calibrée, ou Wilcoxon pour un écart "
   "égal à la marge) au niveau corrigé, d'après la variance des différences observée dans le pilote (Lakens 2017).",
   references=("lakens2017",), calibrage="puissance")

_p("repetitions_chronometrage", 20, "plan",
   "Répétitions de chaque mesure de temps (un seul processus, un seul fil) : avec 20 mesures, l'intervalle entre les 6e et "
   "15e statistiques d'ordre contient la médiane avec une probabilité 1 - 2 P(Bin(20 ; 0,5) <= 5) = 0,959, sans hypothèse "
   "de loi ; l'intervalle bootstrap de la médiane du rapport des temps est rapporté.")

# ------------------------------------------------------------------------------ cas climatique
_p("taille_bloc_km", 100.0, "donnees",
   "Côté des blocs de la validation croisée spatiale : au moins la portée de l'autocorrélation spatiale (Roberts et al. 2017). "
   "Portée pratique = plus petite distance où le variogramme empirique exhaustif des variables standardisées atteint 95 % de "
   "son palier ; pour des variables réduites, E||x_i - x_j||² / (2D) = 1 pour deux points indépendants, le palier vaut donc 1.",
   references=("roberts2017",), calibrage="spatial")
_p("n_plis", 5, "plan", "Nombre de plis de la validation croisée par blocs (plan) ; l'affectation des blocs aux plis est tirée au hasard.")

# ------------------------------------------------------------------------------ texte
_p("espace_lda", {"alpha": (1e-3, 10.0), "lissage": (1e-4, 1.0)}, "plan",
   "Espace de recherche de la LDA (échelle logarithmique) : concentration de Dirichlet sur theta_d sur les mêmes bornes que "
   "alpha0 (« espace_priors ») ; lissage des distributions de mots d'un pseudo-compte négligeable (1e-4) à un pseudo-compte "
   "par mot et par thème (1).", references=("blei2003",))
_p("lda_hyper", {"alpha": 0.1, "lissage": 1e-3}, "recherche",
   "Hyperparamètres de la LDA : recherche aléatoire puis divisions successives sur « espace_lda », en minimisant la perplexité "
   "par complétion de documents de validation tirés du réservoir d'apprentissage (jamais des documents de test).",
   references=("bergstra2012", "jamieson2016"), calibrage="texte")
_p("vocabulaire", {"taille": 1500, "df_min": 5, "df_max": 0.5, "longueur_min_mot": 3, "longueur_min_doc": 20,
                   "sensibilite": (500, 3000)}, "plan",
   "Prétraitement fixé avant l'analyse et identique pour pLSA et LDA : mots présents dans au moins 5 documents et au plus "
   "la moitié d'entre eux (les mots vides sont écartés par cette fréquence documentaire, sans liste externe), mots d'au moins "
   "3 lettres après racinisation de Porter (1980), documents d'au moins 20 mots retenus. Ce n'est pas un réglage optimisé : "
   "la sensibilité des conclusions à la taille du vocabulaire (500 et 3000 mots) est mesurée.", references=("porter1980",))

# ------------------------------------------------------------------------------ variantes et finance
_p("espace_variantes", {"kappa": (0.5, 1.0), "t0": (1.0, 1000.0), "lot": (10, 150), "epoques": (1, 50),
                        "sem_n_iter": (50, 1000), "sem_part_burn": (0.0, 0.9), "tau": (1.0, 1000.0)}, "plan",
   "Espace de recherche des variantes stochastiques : kappa dans ]0,5 ; 1] (conditions de Robbins et Monro sur les pas) ; "
   "décalages t0 et tau, tailles de lot (de 10 à la moitié du jeu de 300 points) et nombres d'époques en échelle logarithmique ; "
   "SEM : nombre d'itérations et part de chauffe.", references=("robbins1951", "cappe2009", "hoffman2013"))
_p("variantes_stochastiques", {"sem_burn": 50, "sem_n_iter": 150, "online_kappa": 0.6, "online_t0": 10.0, "online_lot": 30,
                               "svi_kappa": 0.7, "svi_tau": 1.0, "svi_lot": 30, "epoques": 15}, "recherche",
   "Pas et tailles de lot de la SVI et de l'EM online, burn-in du SEM : recherche sur la log-vraisemblance de validation, "
   "kappa contraint à ]0,5 ; 1] (conditions de Robbins et Monro).", references=("robbins1951", "cappe2009", "hoffman2013"),
   calibrage="variantes")
_p("hmm_etats", 2, "benchmark", "Nombre d'états du HMM choisi par BIC sur la période d'apprentissage (S de 1 à 5).",
   references=("schwarz1978",), calibrage="hmm")
_p("niveaux_var", (0.05, 0.01), "plan", "Niveaux de VaR du plan (1 % et 5 %).")

# ------------------------------------------------------------------------------ exécution
_p("elements_lot_max", 30_000_000, "performance",
   "Taille maximale d'un tenseur (b, K, N) traité d'un coup : borne mémoire, sans effet sur les résultats (tests d'équivalence).")


# ==============================================================================
_PROVISOIRES: set[str] = set()


def _lire_calibrage(p: Parametre):
    f = dossier_calibrage() / f"{p.calibrage}.json"
    if not f.exists():
        return None
    d = json.loads(f.read_text(encoding="utf-8"))
    return d.get("valeurs", {}).get(p.cle or p.nom)


def valeur(nom: str):
    p = R[nom]
    if p.statut in ("benchmark", "recherche", "donnees"):
        v = _lire_calibrage(p)
        if v is not None:
            return tuple(v) if isinstance(p.provisoire, tuple) else v
        _PROVISOIRES.add(nom)
    return p.provisoire


def provisoires() -> list[str]:
    """Paramètres utilisés avec leur valeur provisoire (non calibrée) dans ce processus."""
    return sorted(_PROVISOIRES)


def non_calibres() -> list[str]:
    """Paramètres dont l'étude de calibrage n'a pas encore produit de valeur."""
    return sorted(n for n, p in R.items() if p.statut in ("benchmark", "recherche", "donnees") and _lire_calibrage(p) is None)


def tableau() -> list[dict]:
    """Registre complet pour l'annexe du mémoire."""
    return [{"nom": p.nom, "valeur": valeur(p.nom), "statut": p.statut, "justification": p.justification,
             "references": ", ".join(p.references), "calibrage": p.calibrage or ""} for p in R.values()]
