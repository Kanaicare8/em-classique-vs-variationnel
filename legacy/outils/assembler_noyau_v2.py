"""Intègre le noyau v2 (statistiques suffisantes, registre des paramètres) dans algorithmes.py. À exécuter une fois."""
from pathlib import Path

R = Path(__file__).resolve().parent.parent
f = R / "algorithmes.py"
s = f.read_text(encoding="utf-8")
em = (R / "outils" / "bloc_noyau_v2_em.py").read_text(encoding="utf-8")
vb = (R / "outils" / "bloc_noyau_v2_vb.py").read_text(encoding="utf-8")


def remplacer(debut, fin, nouveau):
    global s
    i = s.index(debut)
    j = s.index(fin, i)
    s = s[:i] + nouveau + "\n\n" + s[j:]


remplacer("class EchecNumerique(RuntimeError):", "# ==============================================================================\n# VARIANTES DE L'EM CLASSIQUE", em)
remplacer("def _ln_B_ld(logdetW, nu, D):", "def svi_gmm(", vb)

# --- constantes -> registre --------------------------------------------------------------------------------
ancien = s[s.index("# Paramètres d'arrêt et de régularisation communs"):s.index("def entropie_affectation")]
s = s.replace(ancien, '''def a_converge(c_prec: float, c: float, tol: float | None = None) -> bool:
    """Test d'arrêt commun : variation relative du critère total (tolérance du registre par défaut)."""
    tol = float(PARAM.valeur("tol_rel")) if tol is None else tol
    return abs(c - c_prec) <= tol * max(abs(c_prec), 1.0)


''')
s = s.replace("import torch\nfrom torch import Tensor\n", "import torch\nfrom torch import Tensor\n\nimport parametres as PARAM\n", 1)
s = s.replace('''  * test : |c_t - c_(t-1)| <= TOL_REL * max(|c_(t-1)|, 1)  (tolérance relative) ;
  * plafond : N_ITER_MAX étapes M ;''', '''  * test : |c_t - c_(t-1)| <= tol_rel * max(|c_(t-1)|, 1)  (tolérance relative) ;
  * plafond : n_iter_max étapes M ;
  * tol_rel, n_iter_max, reg_covariance et toutes les autres valeurs méthodologiques viennent du
    registre `parametres.py`, où chacune est justifiée (source vérifiée, benchmark ou recherche).''')
s = s.replace('''Implémentation sans scikit-learn, sans SciPy et sans NumPy. Seules les opérations
élémentaires de PyTorch sont utilisées (algèbre linéaire, digamma, lgamma) ; les
modèles, les critères et les métriques sont écrits à la main.''', '''Implémentation sans scikit-learn, sans SciPy et sans NumPy. Seules les opérations
élémentaires de PyTorch sont utilisées (algèbre linéaire, digamma, lgamma) ; les
modèles, les critères et les métriques sont écrits à la main.

Calcul tensoriel par lots : les relances (B) et les composantes (K) d'un ajustement sont
traitées dans un seul tenseur ; la forme quadratique et les dispersions passent par les
statistiques suffisantes (x x^T vectorisés), sans tenseur (B, K, N, D). Les données sont centrées
en interne (sans effet sur la vraisemblance ni sur la partition). L'équivalence avec
l'implémentation séquentielle d'origine est vérifiée par tests/test_equivalence_lots.py.''')

# --- LDA corrigée : constante comptée D fois, boucle alignée sur le critère commun ----------------------
i = s.index("def lda_variationnel(")
j = s.index("# ==============================================================================\n# pLSA PAR EM")
s = s[:i] + '''def lda_variationnel(comptes: Tensor, K: int, alpha=None, lissage=None, n_iter=None, tol=None, graine=0):
    """
    LDA de Blei, Ng et Jordan (2003) par EM variationnel (theta_d aléatoire, beta ponctuel).

    comptes : (D, V) nombres d'occurrences de chaque mot dans chaque document.
    Étape E (par document) : point fixe phi_{vk} prop. à beta_{kv} exp(E[log theta_k])   (éq. 3.2)
                             gamma_k = alpha + sum_v comptes_v phi_{vk},
                             jusqu'à variation relative max de gamma <= tol (même tolérance que le critère commun).
    Critère : borne L(gamma, phi ; alpha, beta) + lissage * somme log beta, c'est-à-dire l'objectif exact
              maximisé quand l'étape M ajoute le pseudo-compte `lissage` (mode a posteriori de beta sous un
              Dirichlet(1 + lissage)) : il est donc croissant. Le terme ln Gamma(K alpha) - K ln Gamma(alpha)
              de E[log p(theta_d | alpha)] est compté une fois PAR DOCUMENT.
    Étape M : beta_{kv} proportionnel à sum_d comptes_{dv} phi_{dvk} + lissage.
    Boucle : étape E, critère, test d'arrêt commun, étape M ; n_iter compte les étapes M.
    """
    hyp = PARAM.valeur("lda_hyper")
    alpha = float(hyp["alpha"]) if alpha is None else alpha
    lissage = float(hyp["lissage"]) if lissage is None else lissage
    tol, n_iter, _ = _defauts(tol, n_iter, 0.0)
    g = generateur(graine)
    Dn, V = comptes.shape
    beta = torch.rand(K, V, generator=g) + 1.0
    beta = beta / beta.sum(1, keepdim=True)
    Nd = comptes.sum(1)
    gamma = alpha + Nd[:, None] / K
    digam = torch.special.digamma
    c = comptes[:, :, None]
    bornes, converge, n_m = [], False, 0
    const_doc = math.lgamma(K * alpha) - K * math.lgamma(alpha)
    while True:
        logbeta = torch.log(beta)
        for _ in range(n_iter):
            Elog = digam(gamma) - digam(gamma.sum(1, keepdim=True))                # (D,K)
            phi = torch.softmax(Elog[:, None, :] + logbeta.T[None, :, :], dim=2)   # (D,V,K)
            gamma_new = alpha + (c * phi).sum(1)
            fini = ((gamma_new - gamma).abs() <= tol * gamma.abs().clamp(min=1.0)).all()
            gamma = gamma_new
            if bool(fini):
                break
        Elog = digam(gamma) - digam(gamma.sum(1, keepdim=True))
        phi = torch.softmax(Elog[:, None, :] + logbeta.T[None, :, :], dim=2)
        L = (Dn * const_doc
             + ((alpha - 1) * Elog).sum()
             + (c * phi * Elog[:, None, :]).sum()
             + (c * phi * logbeta.T[None]).sum()
             - (torch.lgamma(gamma.sum(1)) - torch.lgamma(gamma).sum(1)).sum()
             - ((gamma - 1) * Elog).sum()
             - (c * torch.xlogy(phi, phi)).sum()
             + lissage * logbeta.sum())
        bornes.append(float(L))
        if len(bornes) > 1 and a_converge(bornes[-2], bornes[-1], tol):
            converge = True
            break
        if n_m >= n_iter:
            break
        beta = (c * phi).sum(0).T + lissage
        beta = beta / beta.sum(1, keepdim=True)
        n_m += 1
    theta = gamma / gamma.sum(1, keepdim=True)
    return {"beta": beta, "gamma": gamma, "theta": theta, "bornes": bornes, "n_iter": n_m,
            "converge": converge, "alpha": alpha, "lissage": lissage}


''' + s[j:]

# --- pLSA : valeurs par défaut du registre -------------------------------------------------------------
s = s.replace("def plsa_em(comptes: Tensor, K: int, n_iter=N_ITER_MAX, tol=TOL_REL, graine=0, tempering=1.0):",
              "def plsa_em(comptes: Tensor, K: int, n_iter=None, tol=None, graine=0, tempering=1.0):")
s = s.replace('''    g = generateur(graine)
    Dn, V = comptes.shape
    theta = torch.rand(Dn, K, generator=g) + 1.0''', '''    tol, n_iter, _ = _defauts(tol, n_iter, 0.0)
    g = generateur(graine)
    Dn, V = comptes.shape
    theta = torch.rand(Dn, K, generator=g) + 1.0''')

# --- Baum-Welch : critère d'arrêt commun ----------------------------------------------------------------
s = s.replace("def baum_welch(sequences, S, emission=\"discrete\", V=None, n_iter=100, tol=1e-6, graine=0):",
              "def baum_welch(sequences, S, emission=\"discrete\", V=None, n_iter=None, tol=None, graine=0):")
s = s.replace('''    Étape M : A_ij = sum xi / sum gamma, B_i(v) = sum_{o_t = v} gamma / sum gamma (discret),
              mu_i, sigma_i^2 = moyennes pondérées par gamma (gaussien).
    """
    g = generateur(graine)''', '''    Étape M : A_ij = sum xi / sum gamma, B_i(v) = sum_{o_t = v} gamma / sum gamma (discret),
              mu_i, sigma_i^2 = moyennes pondérées par gamma (gaussien), variance planchée à reg_covariance
              (même garde-fou que l'EM du mélange).
    Critère d'arrêt commun (tolérance relative sur la log-vraisemblance totale, plafond d'étapes M).
    """
    tol, n_iter, reg = _defauts(tol, n_iter, None)
    g = generateur(graine)''')
s = s.replace('''    hist = []
    for it in range(n_iter):
        gam_l, xi_l, ll = [], [], 0.0''', '''    hist, n_m, converge = [], 0, False
    while True:
        gam_l, xi_l, ll = [], [], 0.0''')
s = s.replace('''        hist.append(ll)
        if it > 0 and abs(hist[-1] - hist[-2]) < tol:
            break
        pi0 = torch.stack''', '''        hist.append(ll)
        if len(hist) > 1 and a_converge(hist[-2], hist[-1], tol):
            converge = True
            break
        if n_m >= n_iter:
            break
        n_m += 1
        pi0 = torch.stack''')
s = s.replace('''                      for o, g_ in zip(sequences, gam_l)) / tot + 1e-9
    out = {"A": A, "pi0": pi0, "loglik": hist[-1], "ll_hist": hist, "n_iter": len(hist)}''', '''                      for o, g_ in zip(sequences, gam_l)) / tot + reg
    out = {"A": A, "pi0": pi0, "loglik": hist[-1], "ll_hist": hist, "n_iter": n_m, "converge": converge}''')

# --- variantes stochastiques : régularisation du registre -------------------------------------------------
s = s.replace("def em_stochastique(X, K, n_iter=200, reg=1e-6, graine=0, burn=50):",
              "def em_stochastique(X, K, n_iter=150, reg=None, graine=0, burn=50):")
s = s.replace('''    g = generateur(graine)
    N, D = X.shape
    pi, mu, cov = _init_em(X, K, "full", "kmeans", graine, reg)
    hist, accum = [], []''', '''    reg = float(PARAM.valeur("reg_covariance")) if reg is None else reg
    g = generateur(graine)
    N, D = X.shape
    pi, mu, cov = _init_em(X, K, "full", "kmeans", graine, reg)
    hist, accum = [], []''')
s = s.replace("def em_online(X, K, taille_lot=50, n_epoques=5, kappa=0.6, t0=10.0, reg=1e-6, graine=0):",
              "def em_online(X, K, taille_lot=50, n_epoques=5, kappa=0.6, t0=10.0, reg=None, graine=0):")
s = s.replace('''    g = generateur(graine)
    N, D = X.shape
    sous = X[torch.randperm''', '''    reg = float(PARAM.valeur("reg_covariance")) if reg is None else reg
    g = generateur(graine)
    N, D = X.shape
    sous = X[torch.randperm''')
f.write_text(s, encoding="utf-8")
import ast
ast.parse(s)
print("noyau v2 intégré")
