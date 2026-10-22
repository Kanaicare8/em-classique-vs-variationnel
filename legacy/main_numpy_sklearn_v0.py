"""
================================================================================
CODES DU MÉMOIRE — Comparaison entre l'EM Classique et l'EM Variationnel
Kana Tiodong Icare Brichel — Master 2 SDIA, ENSPD, Université de Douala
================================================================================

Ce fichier régroupe, dans l'ordre où ils apparaissent dans le mémoire,
TOUS les scripts Python utilisés pour produire :
  - les exemples numériques du Chapitre 1 (implémentations "from scratch")
  - les 12 expériences du Chapitre 2 (comparaisons avec scikit-learn)
  - la démonstration LDA du Chapitre 3

Chaque section est indépendante : tu peux copier-coller seulement la partie
qui t'intéresse, ou exécuter le fichier entier avec :

    python codes_memoire.py

Bibliothèques nécessaires (à installer une seule fois) :
    pip install numpy scipy scikit-learn matplotlib

================================================================================
"""

import numpy as np


# ==============================================================================
# PARTIE 1 — CHAPITRE 3, section 3.2.1
# EM CLASSIQUE "FROM SCRATCH" (sans bibliothèque spécialisée)
# ==============================================================================
#
# "From scratch" veut dire : on réécrit l'algorithme nous-mêmes, avec les
# formules mathématiques du chapitre 1, plutôt que d'utiliser une bibliothèque
# toute faite. C'est plus lent, mais ça permet de VOIR comment ça marche
# vraiment à l'intérieur.
#
# Analogie : c'est la différence entre acheter du pain tout fait (scikit-learn,
# partie 4 ci-dessous) et faire son pain soi-même en suivant la recette étape
# par étape (ici). Le résultat final est presque le même, mais on comprend
# beaucoup mieux ce qui se passe en le faisant soi-même.

from scipy.stats import multivariate_normal


def em_classique_gmm(X, K, n_iter=100, tol=1e-4, random_state=0):
    """
    EM classique pour un mélange de gaussiennes (GMM).

    Paramètres
    -
    X : tableau numpy de forme (N, D)
        Les données. N = nombre d'observations, D = nombre de dimensions
        (par exemple D=2 si chaque point a une coordonnée x et une coordonnée y).
    K : entier
        Le nombre de "groupes" (composantes gaussiennes) qu'on impose au modèle.
    n_iter : entier
        Nombre maximal d'allers-retours entre étape E et étape M.
    tol : float
        Seuil : si la vraisemblance ne progresse presque plus, on s'arrête.
    random_state : entier
        Graine aléatoire, pour que le résultat soit reproductible.

    Retourne
    --
    Un dictionnaire contenant :
        pi    : les poids de chaque groupe (leur "importance relative")
        mu    : les centres (moyennes) de chaque groupe
        sigma : les covariances (formes/tailles) de chaque groupe
        r     : les responsabilités finales (qui appartient à quel groupe)
    """
    rng = np.random.RandomState(random_state)
    N, D = X.shape

    #  Initialisation : on tire K points au hasard comme centres de départ 
    idx = rng.choice(N, K, replace=False)
    mu = X[idx].copy()
    sigma = np.array([np.cov(X.T) + 1e-6 * np.eye(D) for _ in range(K)])
    pi = np.ones(K) / K  # au début, tous les groupes ont le même poids

    log_lik_history = []

    for it in range(n_iter):
        # 
        # ÉTAPE E ("Espérance") : pour chaque point, on calcule la
        # probabilité qu'il appartienne à chaque groupe.
        # Analogie : on demande à chaque point "à quel groupe ressembles-tu
        # le plus ?" et on lui donne un pourcentage de confiance pour
        # chaque groupe (par exemple 80% groupe 1, 20% groupe 2).
        # 
        log_r = np.zeros((N, K))
        for k in range(K):
            log_r[:, k] = np.log(pi[k] + 1e-300) + multivariate_normal.logpdf(X, mu[k], sigma[k])

        # On travaille en "log" (logarithme) pour éviter que l'ordinateur
        # n'arrondisse des tout petits nombres à zéro (problème d'"underflow").
        log_norm = np.log(np.sum(np.exp(
            log_r - log_r.max(axis=1, keepdims=True)), axis=1, keepdims=True
        )) + log_r.max(axis=1, keepdims=True)
        r = np.exp(log_r - log_norm)  # r = les "responsabilités"

        # 
        # ÉTAPE M ("Maximisation") : maintenant qu'on sait qui appartient
        # à quel groupe (avec quel pourcentage), on recalcule les centres,
        # les formes et les poids de chaque groupe pour qu'ils collent
        # mieux aux points qui leur sont assignés.
        # Analogie : après le vote de confiance de l'étape E, chaque
        # groupe déménage son centre vers la moyenne des points qui
        # ont voté pour lui.
        # 
        Nk = r.sum(axis=0)          # nombre "effectif" de points par groupe
        pi = Nk / N                  # nouveau poids de chaque groupe
        mu = (r.T @ X) / Nk[:, None]  # nouveau centre de chaque groupe
        sigma = np.zeros((K, D, D))
        for k in range(K):
            diff = X - mu[k]
            sigma[k] = (r[:, k, None] * diff).T @ diff / Nk[k]
            sigma[k] += 1e-6 * np.eye(D)  # petite sécurité anti-erreur numérique

        # On vérifie si le modèle s'améliore encore
        log_lik_history.append(log_norm.sum())
        if it > 0 and abs(log_lik_history[-1] - log_lik_history[-2]) < tol:
            break  # ça ne bouge plus assez : on arrête

    return {"pi": pi, "mu": mu, "sigma": sigma, "r": r,
            "log_lik_history": log_lik_history, "n_iter": it + 1}


# ==============================================================================
# PARTIE 2 — CHAPITRE 3, section 3.3.1
# EM VARIATIONNEL "FROM SCRATCH"
# ==============================================================================
#
# Différence avec la partie 1 : au lieu de chercher UN SEUL centre et UNE
# SEULE forme par groupe (des nombres précis), on cherche une DISTRIBUTION
# de probabilité sur ces centres et ces formes (une fourchette de valeurs
# plausibles, avec plus ou moins de confiance).
#
# Analogie : l'EM classique te donne "le centre du groupe 1 est exactement
# au point (5, 3)". L'EM variationnel te donne "le centre du groupe 1 est
# probablement autour de (5, 3), mais il pourrait être entre (4.5, 2.8) et
# (5.5, 3.2)" — il garde une trace de l'incertitude.
#
# Le "bonus" de cette version : elle peut automatiquement "éteindre" les
# groupes en trop si on en demande plus que nécessaire (voir alpha_k dans
# le code : quand un groupe ne sert à rien, son poids s'effondre tout seul).

from scipy.special import digamma


def em_variationnel_gmm(X, Kmax, alpha0=None, n_iter=200, tol=1e-4, random_state=0):
    """
    EM variationnel (bayésien) pour un mélange de gaussiennes.

    Paramètres
    -
    X : tableau numpy (N, D)
        Les données.
    Kmax : entier
        Le nombre MAXIMUM de groupes autorisés (l'algorithme peut en
        "éteindre" certains tout seul s'ils ne servent à rien).
    alpha0 : float ou None
        Réglage de la "sévérité" avec laquelle on élague les groupes en trop.
        Petit alpha0 (ex: 1/Kmax) = élagage agressif.
        Grand alpha0 (ex: 10) = presque pas d'élagage.
    n_iter, tol, random_state : comme dans la fonction précédente.

    Retourne
    --
    Un dictionnaire avec :
        pi    : poids finaux de chaque groupe (les groupes inutiles ont
                un poids proche de 0)
        m     : centres estimés
        alpha : paramètres bruts du modèle de Dirichlet (plus alpha_k est
                grand par rapport à alpha0, plus le groupe k est "actif")
        r     : responsabilités finales
    """
    rng = np.random.RandomState(random_state)
    N, D = X.shape
    K = Kmax
    alpha0 = alpha0 if alpha0 is not None else 1.0 / K

    #  Réglages "a priori" (nos croyances de départ, avant d'avoir vu les données) 
    m0 = X.mean(axis=0)
    beta0 = 1e-3
    W0 = np.eye(D)
    nu0 = D

    #  Initialisation des paramètres 
    idx = rng.choice(N, K, replace=False)
    m = X[idx].copy()
    beta = np.full(K, beta0 + N / K)
    nu = np.full(K, nu0 + N / K)
    W = np.array([W0.copy() for _ in range(K)])
    alpha = np.full(K, alpha0 + N / K)

    for it in range(n_iter):
        # 
        # ÉTAPE E variationnelle : même idée que l'étape E classique
        # (calculer à qui appartient chaque point), mais en tenant compte
        # de l'incertitude sur les paramètres, via la fonction digamma.
        # 
        E_log_pi = digamma(alpha) - digamma(alpha.sum())
        log_rho = np.zeros((N, K))
        for k in range(K):
            E_log_det_lambda = sum(digamma((nu[k] + 1 - j) / 2) for j in range(1, D + 1)) \
                + D * np.log(2) + np.log(np.linalg.det(W[k]))
            diff = X - m[k]
            quad = D / beta[k] + nu[k] * np.einsum("ni,ij,nj->n", diff, W[k], diff)
            log_rho[:, k] = E_log_pi[k] + 0.5 * E_log_det_lambda - 0.5 * D * np.log(2 * np.pi) - 0.5 * quad
        log_norm = np.log(np.sum(np.exp(
            log_rho - log_rho.max(axis=1, keepdims=True)), axis=1, keepdims=True
        )) + log_rho.max(axis=1, keepdims=True)
        r = np.exp(log_rho - log_norm)

        # 
        # ÉTAPE M variationnelle : on met à jour nos croyances sur les
        # centres ET sur notre incertitude, en mélangeant ce qu'on
        # croyait au départ (le "prior") avec ce que les données nous
        # apprennent.
        # 
        Nk = r.sum(axis=0) + 1e-10
        xk = (r.T @ X) / Nk[:, None]
        Sk = np.zeros((K, D, D))
        for k in range(K):
            diff = X - xk[k]
            Sk[k] = (r[:, k, None] * diff).T @ diff / Nk[k]

        alpha = alpha0 + Nk  # <-- c'est ICI que se joue l'élagage automatique
        beta_new = beta0 + Nk
        m_new = (beta0 * m0 + Nk[:, None] * xk) / beta_new[:, None]
        nu_new = nu0 + Nk
        W_new = np.zeros((K, D, D))
        for k in range(K):
            d0 = xk[k] - m0
            W_new[k] = np.linalg.inv(
                np.linalg.inv(W0) + Nk[k] * Sk[k]
                + (beta0 * Nk[k] / (beta0 + Nk[k])) * np.outer(d0, d0)
            )
        beta, m, nu, W = beta_new, m_new, nu_new, W_new

    pi_final = alpha / alpha.sum()
    return {"pi": pi_final, "m": m, "alpha": alpha, "r": r, "n_iter": it + 1}


# ==============================================================================
# PARTIE 3 — CHAPITRE 3, Annexe B
# CALCUL DE L'ELBO (fonctions auxiliaires)
# ==============================================================================
#
# L'ELBO, c'est le "score" que l'EM variationnel essaie de maximiser à
# chaque itération (un peu comme la vraisemblance pour l'EM classique).
# Ces trois petites fonctions calculent des "espérances" (moyennes
# théoriques) nécessaires à ce calcul.

from scipy.special import gammaln


def esperance_log_pi(alpha):
    """E[log(pi_k)] sous une loi de Dirichlet(alpha)."""
    return digamma(alpha) - digamma(np.sum(alpha))


def esperance_log_det_lambda(W, nu, D):
    """E[log|Lambda_k|] sous une loi de Wishart(W, nu)."""
    j = np.arange(1, D + 1)
    return np.sum(digamma((nu + 1 - j) / 2)) + D * np.log(2) + np.log(np.linalg.det(W))


def esperance_forme_quadratique(x, m, W, beta, nu):
    """E[(x - mu_k)^T Lambda_k (x - mu_k)]."""
    D = len(x)
    diff = x - m
    return D / beta + nu * diff.T @ W @ diff


# ==============================================================================
# PARTIE 4 — CHAPITRE 3, sections 3.2.2 / 3.3.2
# LES MÊMES ALGORITHMES, MAIS AVEC SCIKIT-LEARN (bibliothèque "prête à l'emploi")
# ==============================================================================
#
# Ici on n'écrit plus les formules nous-mêmes : on utilise une bibliothèque
# (scikit-learn) qui fait tout ça pour nous, en beaucoup plus rapide et
# plus robuste. C'est cette version qui a servi à produire TOUS les
# résultats chiffrés du chapitre 2.
#
# GaussianMixture        = EM classique
# BayesianGaussianMixture = EM variationnel

from sklearn.datasets import make_blobs
from sklearn.mixture import GaussianMixture, BayesianGaussianMixture
from sklearn.metrics import adjusted_rand_score, silhouette_score
import time


def generer_donnees(random_state=42):
    """
    Crée un petit jeu de données artificiel : 300 points, répartis en
    3 groupes bien séparés (comme 3 nuages de points sur un graphique).
    C'est le jeu de données utilisé dans TOUT le chapitre 2.
    """
    X, y_true = make_blobs(
        n_samples=300,
        centers=[[0, 0], [5, 5], [0, 5]],
        cluster_std=0.7,
        random_state=random_state,
    )
    return X, y_true


def ajuster_em_classique(X, n_components=6, random_state=42):
    """Ajuste un EM classique avec un nombre de composantes donné."""
    modele = GaussianMixture(
        n_components=n_components,
        covariance_type="full",
        tol=1e-3,
        max_iter=200,
        n_init=10,       # on relance 10 fois avec des départs différents
        random_state=random_state,
    )
    modele.fit(X)
    return modele


def ajuster_em_variationnel(X, n_components=6, alpha0=None, random_state=42):
    """Ajuste un EM variationnel avec un nombre maximum de composantes donné."""
    alpha0 = alpha0 if alpha0 is not None else 1 / n_components
    modele = BayesianGaussianMixture(
        n_components=n_components,
        covariance_type="full",
        weight_concentration_prior_type="dirichlet_distribution",
        weight_concentration_prior=alpha0,
        tol=1e-3,
        max_iter=200,
        n_init=10,
        random_state=random_state,
    )
    modele.fit(X)
    return modele


def evaluer(modele, X, y_true, nom):
    """
    Calcule des "notes de qualité" pour un modèle déjà ajusté :
      - ARI : est-ce que les groupes trouvés correspondent aux vrais
        groupes ? (1.0 = parfait, 0 = au hasard)
      - silhouette : est-ce que les groupes sont bien séparés et
        compacts ? (plus c'est proche de 1, mieux c'est)
    """
    t0 = time.time()
    modele.fit(X)
    duree = time.time() - t0
    affectations = modele.predict(X)
    ari = adjusted_rand_score(y_true, affectations)
    sil = silhouette_score(X, affectations)
    n_eff = np.sum(modele.weights_ * len(X) >= 1)
    print(f" {nom} ")
    print(f"Poids           : {np.round(modele.weights_, 3)}")
    print(f"Composantes actives : {n_eff}")
    print(f"ARI = {ari:.3f} | silhouette = {sil:.3f} | temps = {duree:.3f}s")
    return affectations


# ==============================================================================
# PARTIE 5 — CHAPITRE 2, sections 2.3.5 à 2.3.10
# LES EXPÉRIENCES DE SENSIBILITÉ (alpha0, scalabilité, covariance...)
# ==============================================================================

def experience_sensibilite_alpha(X):
    """
    Teste plusieurs valeurs de alpha0 (le réglage de sévérité de
    l'élagage) et regarde combien de groupes restent "actifs" à la fin.
    Résultat attendu : alpha0 petit -> peu de groupes ; alpha0 grand ->
    beaucoup de groupes (l'élagage ne fonctionne presque plus).
    """
    for alpha0 in [0.001, 0.01, 0.1, 1.0, 10.0]:
        modele = ajuster_em_variationnel(X, n_components=6, alpha0=alpha0)
        n_actives = int(np.sum(modele.weights_ * len(X) >= 1))
        print(f"alpha0={alpha0:<8} composantes actives={n_actives} "
              f"poids={np.round(modele.weights_, 3)}")


def experience_scalabilite(n_samples, n_features):
    """
    Mesure le temps que prend chaque algorithme selon la taille des
    données (nombre de points N et nombre de dimensions D).
    Sert à répondre à la question : "est-ce que l'EM variationnel
    devient trop lent sur de grosses données ?"
    """
    centers = np.random.RandomState(0).uniform(-5, 5, size=(3, n_features))
    X, _ = make_blobs(n_samples=n_samples, centers=centers, cluster_std=0.8, random_state=42)

    t0 = time.time()
    ajuster_em_classique(X, n_components=6)
    tc = time.time() - t0

    t0 = time.time()
    ajuster_em_variationnel(X, n_components=6)
    tv = time.time() - t0

    return tc, tv


def experience_selection_modele(X):
    """
    Calcule le BIC et l'AIC (deux "notes de complexité") de l'EM
    classique pour K allant de 1 à 8, afin de trouver quel K est le
    "meilleur" selon ces critères statistiques classiques.
    """
    bics, aics = [], []
    for K in range(1, 9):
        gm = ajuster_em_classique(X, n_components=K)
        bics.append(gm.bic(X))
        aics.append(gm.aic(X))
        print(f"K={K}  BIC={gm.bic(X):.2f}  AIC={gm.aic(X):.2f}")
    print("K* selon BIC :", np.argmin(bics) + 1)
    print("K* selon AIC :", np.argmin(aics) + 1)


def experience_type_covariance(X, y_true):
    """
    Teste 4 façons différentes de contraindre la "forme" des groupes
    (covariance) : full, tied, diag, spherical. Vérifie que l'élagage
    automatique fonctionne quelle que soit la forme choisie.
    """
    for cov_type in ["full", "tied", "diag", "spherical"]:
        gc = GaussianMixture(n_components=6, covariance_type=cov_type, n_init=10, random_state=42).fit(X)
        gv = BayesianGaussianMixture(
            n_components=6, covariance_type=cov_type,
            weight_concentration_prior_type="dirichlet_distribution",
            weight_concentration_prior=1 / 6, n_init=10, random_state=42,
        ).fit(X)
        ari_c = adjusted_rand_score(y_true, gc.predict(X))
        ari_v = adjusted_rand_score(y_true, gv.predict(X))
        print(f"{cov_type:<10} ARI classique={ari_c:.3f}  ARI variationnel={ari_v:.3f}")


# ==============================================================================
# PARTIE 6 — CHAPITRE 3, section 3.1.1
# DÉMONSTRATION LDA (application au texte — modélisation de "thèmes")
# ==============================================================================
#
# LDA (Latent Dirichlet Allocation) applique la MÊME logique d'EM
# variationnel que le GMM, mais à des textes au lieu de points sur un
# graphique. Chaque "thème" (topic) découvert est un peu comme un groupe
# du GMM, sauf qu'au lieu d'être un nuage de points, c'est une liste de
# mots qui vont souvent ensemble.

from sklearn.feature_extraction.text import CountVectorizer
from sklearn.decomposition import LatentDirichletAllocation


def demo_lda():
    """
    Petit exemple : on donne 12 phrases courtes (sur les animaux, la
    finance et le football) à l'algorithme, sans lui dire de quoi elles
    parlent, et on regarde s'il retrouve tout seul les 3 thématiques.
    """
    corpus = [
        "le chat mange des croquettes et dort sur le canape",
        "le chien joue dans le jardin avec la balle",
        "le chat et le chien dorment ensemble le soir",
        "la bourse chute apres l annonce des taux d interet",
        "les actions technologiques progressent sur le marche financier",
        "la banque centrale releve son taux directeur cette semaine",
        "l equipe de football remporte le match a l exterieur",
        "le joueur marque un but decisif en fin de rencontre",
        "le championnat de football reprend ce week end",
        "le chat observe les oiseaux depuis la fenetre du salon",
        "les investisseurs surveillent la reaction des marches financiers",
        "l entraineur felicite ses joueurs apres la victoire",
    ]
    stop = ["le", "la", "les", "de", "des", "et", "en", "du", "un", "une", "ce",
            "cette", "son", "ses", "a", "sur", "dans", "avec", "depuis", "apres", "d", "l"]

    vec = CountVectorizer(stop_words=stop)
    Xc = vec.fit_transform(corpus)

    lda = LatentDirichletAllocation(n_components=3, random_state=42, max_iter=100)
    lda.fit(Xc)

    vocab = np.array(vec.get_feature_names_out())
    for k, topic in enumerate(lda.components_):
        top_mots = vocab[np.argsort(topic)[::-1][:6]]
        print(f"Thème {k} :", ", ".join(top_mots))


# ==============================================================================
# EXÉCUTION : si tu lances ce fichier directement, voici ce qui se passe
# ==============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("1. EM classique 'from scratch' (chapitre 1, exemple numérique)")
    print("=" * 70)
    X, y_true = generer_donnees()
    res_scratch = em_classique_gmm(X, K=6, random_state=42)
    print("Poids finaux :", np.round(res_scratch["pi"], 3))
    print("Itérations   :", res_scratch["n_iter"])

    print("\n" + "=" * 70)
    print("2. EM variationnel 'from scratch'")
    print("=" * 70)
    res_scratch_v = em_variationnel_gmm(X, Kmax=6, alpha0=1/6, random_state=42)
    print("Poids finaux :", np.round(res_scratch_v["pi"], 3))

    print("\n" + "=" * 70)
    print("3. Comparaison avec scikit-learn (chapitre 2, expérience principale)")
    print("=" * 70)
    gmm_classique = ajuster_em_classique(X)
    gmm_variationnel = ajuster_em_variationnel(X)
    evaluer(gmm_classique, X, y_true, "EM classique (K=6)")
    evaluer(gmm_variationnel, X, y_true, "EM variationnel (Kmax=6)")

    print("\n" + "=" * 70)
    print("4. Sensibilité à alpha0")
    print("=" * 70)
    experience_sensibilite_alpha(X)

    print("\n" + "=" * 70)
    print("5. Sélection de modèle par BIC/AIC")
    print("=" * 70)
    experience_selection_modele(X)

    print("\n" + "=" * 70)
    print("6. Sensibilité au type de covariance")
    print("=" * 70)
    experience_type_covariance(X, y_true)

    print("\n" + "=" * 70)
    print("7. Démonstration LDA (texte)")
    print("=" * 70)
    demo_lda()