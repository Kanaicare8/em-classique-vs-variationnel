"""
================================================================================
HYPOTHÈSES CONFIRMATOIRES DÉCLARÉES (une seule source pour le calibrage et les agrégations)
================================================================================

Chaque hypothèse a un identifiant préfixé (HS scénarios, HC climat, HF finance, HT texte), une famille
(la correction de Holm porte sur toute la famille), UN test déclaré ('equivalence' par TOST à la marge
calibrée, ou 'difference' par Wilcoxon exact), une métrique et deux bras A et B : les différences
appariées sont A - B, réplication par réplication.

Écarts au plan d'origine (déclarés dans le chapitre de méthodologie) : les tests ont été formalisés
(un seul par hypothèse) après une première exécution, à la suite de la relecture du code ; leur liste
ci-dessous est figée avant la réexécution complète.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Hypothese:
    id: str
    famille: str
    axe: str
    enonce: str
    test: str                 # "equivalence" | "difference"
    metrique: str             # colonne des lignes d'unités
    bras_a: str
    bras_b: str
    filtre: dict = field(default_factory=dict)   # sélection des lignes (point du plan d'expérience)
    marge: str | None = None  # clé de la marge dans le registre (marges_equivalence ou marge_k)


H: list[Hypothese] = []


def _h(*a, **k):
    H.append(Hypothese(*a, **k))


# ------------------------------------------------------------------------------ scénarios synthétiques
for d in (4, 5):
    _h(f"HS1-sep{d}", "scenarios", "Chevauchement", f"Groupes séparés de {d} écarts-types : ARI du VB (priors empiriques) "
       "équivalent à celui de l'EM-BIC", "equivalence", "ARI", "VB-emp", "EM-BIC", {"scenario": "S1", "parametre": str(d)}, "ARI")
for d in (1, 2, 3):
    _h(f"HS1-sep{d}", "scenarios", "Chevauchement", f"Groupes séparés de {d} écart(s)-type(s) : l'ARI du VB diffère de celui "
       "de l'EM-BIC", "difference", "ARI", "VB-emp", "EM-BIC", {"scenario": "S1", "parametre": str(d)})
_h("HS2", "scenarios", "Poids déséquilibrés", "Poids 80/15/5 : le VB perd la composante minoritaire (K̂ < 3) à une "
   "fréquence différente de l'EM-BIC", "difference", "minoritaire_perdue", "VB-emp", "EM-BIC", {"scenario": "S2"})
for kv in (4, 5, 6):
    _h(f"HS3-K{kv}", "scenarios", "Sous-estimation de K", f"K vrai = {kv}, K choisi = 3 : ARI du VB à Kmax = 3 équivalent "
       "à celui de l'EM à K = 3 (aucun ne peut corriger l'erreur)", "equivalence", "ARI", "VB-Kmax=K", "EM-K",
       {"scenario": "S3", "parametre": f"Kvrai={kv}"}, "ARI")
_h("HS4", "scenarios", "Queues épaisses", "Composantes de Student (nu = 3) : l'ARI du VB diffère de celui de l'EM-BIC",
   "difference", "ARI", "VB-emp", "EM-BIC", {"scenario": "S4"})
for D in (2, 5, 10, 20):
    _h(f"HS5-D{D}", "scenarios", "Dimension", f"D = {D} : l'ARI du VB diffère de celui de l'EM-BIC", "difference", "ARI",
       "VB-emp", "EM-BIC", {"scenario": "S5", "parametre": str(D)})
for n in (30, 60, 120, 300, 1000):
    _h(f"HS6-N{n}", "scenarios", "Petit effectif", f"N = {n} : la fréquence d'ajustements dégénérés du VB diffère de "
       "celle de l'EM à Kmax", "difference", "degenere", "VB-emp", "EM-Kmax", {"scenario": "S6", "parametre": str(n)})
for prop in ("0.01", "0.05", "0.1"):
    for amp in ("5.0", "10.0", "20.0"):
        _h(f"HS7-p{prop}-a{amp}", "scenarios", "Aberrations", f"Aberrations (proportion {prop}, amplitude {amp}) : ARI hors "
           "aberrations du VB équivalent à celui de l'EM-BIC", "equivalence", "ARI", "VB-emp", "EM-BIC",
           {"scenario": "S7", "parametre": f"prop={prop};amp={amp}"}, "ARI")

# ------------------------------------------------------------------------------ climat
for n in (30, 60, 120, 500, 2000):
    _h(f"HC1-N{n}", "climat", "Sélection de K", f"Semi-synthétique, N = {n} : |K̂ - 5| du VB équivalent à celui de l'EM-BIC "
       "(marge d'une demi-composante)", "equivalence", "erreur_k", "VB-emp", "EM-BIC", {"plan": "semi", "N": str(n)}, "K")
_h("HC2-ARI", "climat", "Qualité à grand N", "N = 2000, validation par blocs : ARI contre Köppen-Geiger du VB équivalent "
   "à celui de l'EM-BIC", "equivalence", "ARI_koppen", "VB-emp", "EM-BIC", {"plan": "sous", "N": "2000"}, "ARI")
_h("HC2-LL", "climat", "Qualité à grand N", "N = 2000, validation par blocs : log-vraisemblance hors bloc du VB "
   "équivalente à celle de l'EM-BIC", "equivalence", "ll_test", "VB-emp", "EM-BIC", {"plan": "sous", "N": "2000"}, "LL")
for n in (30, 60, 120):
    _h(f"HC3-N{n}", "climat", "Petit N", f"N = {n} : la fréquence d'ajustements dégénérés du VB diffère de celle de l'EM "
       "à Kmax", "difference", "degenere", "VB-emp", "EM-Kmax", {"plan": "sous", "N": str(n)})
for n in (2000,):
    _h(f"HC7-N{n}", "climat", "Chevauchement", f"Semi-synthétique, N = {n} : le nombre de composantes retenues par le VB "
       "diffère de celui de l'EM-BIC (fusion de zones voisines)", "difference", "k_hat", "VB-emp", "EM-BIC",
       {"plan": "semi", "N": str(n)})
for n in (120, 500, 2000):
    _h(f"HC8-N{n}", "climat", "Dimension", f"D = 20, N = {n} : la fréquence d'ajustements dégénérés du VB diffère de celle "
       "de l'EM à Kmax", "difference", "degenere", "VB-emp", "EM-Kmax", {"plan": "d20", "N": str(n)})
# HC4 (coût), HC5 (hyperparamètres) et HC6 (couverture) sont décidées par intervalles (voir etape_climat.agreger).

# ------------------------------------------------------------------------------ texte
for n in (50, 200, 1000):
    _h(f"HT1-N{n}", "texte", "Surapprentissage", f"N = {n} documents : l'écart relatif de perplexité (test / apprentissage) "
       "du pLSA diffère de celui de la LDA", "difference", "ecart_relatif", "pLSA", "LDA", {"N": str(n)})


def famille(nom: str) -> list[Hypothese]:
    return [h for h in H if h.famille == nom]


def diffs(h: Hypothese, lignes: list[dict], cle_rep: str = "rep") -> list[float]:
    """Différences appariées A - B (par réplication) pour l'hypothèse h, à partir des lignes d'unités."""
    def garde(l):
        return all(str(l.get(k)) == v for k, v in h.filtre.items())
    a = {l[cle_rep]: l.get(h.metrique) for l in lignes if garde(l) and l.get("bras") == h.bras_a and not l.get("echec")}
    b = {l[cle_rep]: l.get(h.metrique) for l in lignes if garde(l) and l.get("bras") == h.bras_b and not l.get("echec")}
    out = []
    for r in sorted(set(a) & set(b)):
        va, vb = a[r], b[r]
        if va is None or vb is None or va != va or vb != vb:
            continue
        out.append(float(va) - float(vb))
    return out


def marge(h: Hypothese):
    import parametres as PARAM
    if h.marge is None:
        return None
    if h.marge == "K":
        return float(PARAM.valeur("marge_k"))
    return float(PARAM.valeur("marges_equivalence")[h.marge])
