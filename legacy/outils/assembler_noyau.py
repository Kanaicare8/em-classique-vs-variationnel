"""Assemble le nouveau noyau par lots dans algorithmes.py à partir de la référence figée (tests/algorithmes_reference.py).
À exécuter une seule fois (historique de la refonte)."""
from pathlib import Path

R = Path(__file__).resolve().parent.parent
ref = (R / "tests" / "algorithmes_reference.py").read_text(encoding="utf-8").split("\n")
ref = ref[1:]                                                     # retire la ligne de marquage de la copie figée
em_lot = (R / "outils" / "bloc_em_lot.py").read_text(encoding="utf-8")
vb_lot = (R / "outils" / "bloc_vb_lot.py").read_text(encoding="utf-8")


def idx(prefixe, depart=0):
    return next(i for i in range(depart, len(ref)) if ref[i].startswith(prefixe))


i_kmeans = idx("def kmeans(")
i_nbpar = idx("def nb_parametres(")
i_em = idx("# EM CLASSIQUE POUR LE GMM") - 1                      # ligne « # ==== » qui précède le titre
i_var = idx("# VARIANTES DE L'EM CLASSIQUE") - 1
i_vb_titre = idx("# EM VARIATIONNEL POUR LE GMM BAYÉSIEN") - 1
i_prior = idx("@dataclass")
i_ln_b = idx("def _ln_B(")
i_svi = idx("def svi_gmm(")

haut = ref[:i_kmeans]                                             # en-tête, outils, jeux de données
milieu1 = ref[i_nbpar:i_em]                                       # nb_parametres, bic, aic, log_gauss, métriques
variantes = ref[i_var:i_vb_titre]                                 # SEM, EM online
titre_vb = ref[i_vb_titre:i_prior]                                # titre de section VB
priors = ref[i_prior:i_ln_b]                                      # PrioriNW, priori_diffus, priori_empirique
fin = ref[i_svi:]                                                 # SVI, HMM, LDA, pLSA

# PrioriNW doit être défini avant le bloc EM (priori_plat l'utilise à l'exécution seulement, mais on garde l'ordre lisible)
nouveau = (haut + ["# kmeans_lot / kmeans : voir le noyau par lots ci-dessous", ""] + milieu1
           + ["# ==============================================================================",
              "# DISTRIBUTIONS A PRIORI (hyperparamètres du GMM bayésien)",
              "# =============================================================================="] + priors
           + em_lot.split("\n") + [""] + variantes + titre_vb[:3] + vb_lot.split("\n") + [""] + fin)
texte = "\n".join(nouveau)
(R / "algorithmes.py").write_text(texte, encoding="utf-8")
import ast
ast.parse(texte)
print("algorithmes.py assemblé :", len(nouveau), "lignes")
