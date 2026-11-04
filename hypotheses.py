"""
================================================================================
HYPOTHÈSES : hypothèses de recherche (RH) et tests déclarés qui les opérationnalisent
================================================================================

La thèse du mémoire est : « le VB ne bat pas l'EM ; il déplace la sélection de K vers les hyperparamètres (et Kmax),
apporte une incertitude approchée, au prix d'un coût et d'une sensibilité aux priors ». Elle est décomposée en cinq
hypothèses de recherche RH1 à RH5 (RECHERCHE ci-dessous). Chacune est mise à l'épreuve par des TESTS DÉCLARÉS :

  * tests appariés (H) : identifiant préfixé (HS scénarios, HP prix alimentaires, HT texte), une famille (la correction
    de Holm porte sur la famille), UN test ('equivalence' par TOST à la marge calibrée, ou 'difference' par Wilcoxon
    exact), une métrique, deux bras A et B (différences appariées A - B, réplication par réplication), l'hypothèse de
    recherche rattachée (rh) et le résultat attendu si elle est vraie (attendu : « équivalent », « A > B », « A < B »,
    ou None quand la thèse ne prédit pas de sens) ;
  * décisions par intervalle (AUTRES) : coût (HP4), couverture (HP6) et comparaisons de prévision (HPP1 à HPP6,
    Diebold-Mariano, famille « prix_prevision »), avec le même rattachement.

Écarts au protocole (déclarés dans le chapitre de méthodologie) :
  1. les tests des scénarios ont été formalisés (un seul par hypothèse) après une première exécution exploratoire ;
  2. les tests HP du cas pratique ont été déclarés le 27 octobre 2026, après la seule description de la couverture des
     données et avant tout ajustement de modèle ;
  3. le même jour, APRÈS un essai technique de la chaîne (mode rapide : 2 réplications, paramètres provisoires), le
     rattachement aux hypothèses de recherche a été ajouté, HP5 est passée d'un constat descriptif à un test apparié,
     et HP7 a été ajoutée pour isoler l'effet des priors (MAP-EM). Les valeurs de l'essai technique ne sont pas des
     résultats et ne sont rapportées nulle part.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# ------------------------------------------------------------------------------ hypothèses de recherche
RECHERCHE = {
    "RH1": ("Absence de supériorité générale",
            "Quand la structure est identifiable (groupes séparés, effectif suffisant), le VB et l'EM avec K choisi par BIC "
            "donnent des résultats équivalents ; quand ils diffèrent, le sens de l'écart dépend du contexte."),
    "RH2": ("Déplacement de la sélection de K",
            "Le nombre de composantes retenu par le VB dépend de ses hyperparamètres (et de Kmax) au moins autant que celui "
            "de l'EM dépend de ses propres choix (critère d'information et initialisation)."),
    "RH3": ("Incertitude approchée",
            "Les intervalles de crédibilité du VB en champ moyen sont trop étroits : leur couverture est inférieure au "
            "niveau nominal, alors que le bootstrap de l'EM en est plus proche."),
    "RH4": ("Régularisation par les priors",
            "À petit effectif, le VB produit moins d'ajustements dégénérés que l'EM de même capacité, et cet effet est "
            "celui des priors : le MAP-EM, qui porte les mêmes priors sans loi sur les paramètres, l'obtient aussi."),
    "RH5": ("Coût",
            "Un ajustement VB coûte plus qu'un ajustement EM, mais le pipeline EM-BIC complet (balayage de K) coûte plus "
            "qu'un ajustement VB en temps total jusqu'au modèle final."),
}


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
    rh: str = ""              # hypothèse de recherche rattachée
    attendu: str | None = None  # résultat attendu si l'hypothèse de recherche est vraie


H: list[Hypothese] = []


def _h(*a, **k):
    h = Hypothese(*a, **k)
    assert h.rh in RECHERCHE, h.id
    if h.test == "equivalence":
        h = Hypothese(**{**h.__dict__, "attendu": "équivalent"})
    H.append(h)


# ------------------------------------------------------------------------------ scénarios synthétiques
for d in (4, 5):
    _h(f"HS1-sep{d}", "scenarios", "Chevauchement", f"Groupes séparés de {d} écarts-types : ARI du VB (priors empiriques) "
       "équivalent à celui de l'EM-BIC", "equivalence", "ARI", "VB-emp", "EM-BIC", {"scenario": "S1", "parametre": str(d)}, "ARI",
       rh="RH1")
for d in (1, 2, 3):
    _h(f"HS1-sep{d}", "scenarios", "Chevauchement", f"Groupes séparés de {d} écart(s)-type(s) : l'ARI du VB diffère de celui "
       "de l'EM-BIC", "difference", "ARI", "VB-emp", "EM-BIC", {"scenario": "S1", "parametre": str(d)}, rh="RH1")
_h("HS2", "scenarios", "Poids déséquilibrés", "Poids 80/15/5 : le VB perd la composante minoritaire (K̂ < 3) à une "
   "fréquence différente de l'EM-BIC", "difference", "minoritaire_perdue", "VB-emp", "EM-BIC", {"scenario": "S2"}, rh="RH1")
for kv in (4, 5, 6):
    _h(f"HS3-K{kv}", "scenarios", "Sous-estimation de K", f"K vrai = {kv}, K choisi = 3 : ARI du VB à Kmax = 3 équivalent "
       "à celui de l'EM à K = 3 (aucun ne peut corriger l'erreur)", "equivalence", "ARI", "VB-Kmax=K", "EM-K",
       {"scenario": "S3", "parametre": f"Kvrai={kv}"}, "ARI", rh="RH2")
_h("HS4", "scenarios", "Queues épaisses", "Composantes de Student (nu = 3) : l'ARI du VB diffère de celui de l'EM-BIC",
   "difference", "ARI", "VB-emp", "EM-BIC", {"scenario": "S4"}, rh="RH1")
for D in (2, 5, 10, 20):
    _h(f"HS5-D{D}", "scenarios", "Dimension", f"D = {D} : l'ARI du VB diffère de celui de l'EM-BIC", "difference", "ARI",
       "VB-emp", "EM-BIC", {"scenario": "S5", "parametre": str(D)}, rh="RH1")
for n in (30, 60, 120, 300, 1000):
    _h(f"HS6-N{n}", "scenarios", "Petit effectif", f"N = {n} : la fréquence d'ajustements dégénérés du VB diffère de "
       "celle de l'EM à Kmax", "difference", "degenere", "VB-emp", "EM-Kmax", {"scenario": "S6", "parametre": str(n)},
       rh="RH4", attendu="A < B")
for prop in ("0.01", "0.05", "0.1"):
    for amp in ("5.0", "10.0", "20.0"):
        _h(f"HS7-p{prop}-a{amp}", "scenarios", "Aberrations", f"Aberrations (proportion {prop}, amplitude {amp}) : ARI hors "
           "aberrations du VB équivalent à celui de l'EM-BIC", "equivalence", "ARI", "VB-emp", "EM-BIC",
           {"scenario": "S7", "parametre": f"prop={prop};amp={amp}"}, "ARI", rh="RH1")

# ------------------------------------------------------------------------------ prix alimentaires du Cameroun
for n in (30, 60, 120, 250, 500):
    _h(f"HP1-N{n}", "prix", "Sélection de K", f"Semi-synthétique, N = {n} : |K̂ - K_ref| du VB équivalent à celui de "
       "l'EM-BIC (marge d'une demi-composante)", "equivalence", "erreur_k", "VB-emp", "EM-BIC", {"plan": "semi", "N": str(n)}, "K",
       rh="RH1")
_h("HP2-LL", "prix", "Qualité prédictive", "N = 250, validation temporelle (test 2024-2026) : log-vraisemblance de test "
   "du VB équivalente à celle de l'EM-BIC", "equivalence", "ll_test", "VB-emp", "EM-BIC", {"plan": "sous", "N": "250"}, "LL",
   rh="RH1")
for n in (30, 60, 120):
    _h(f"HP3-N{n}", "prix", "Petit N", f"N = {n} : la fréquence d'ajustements dégénérés du VB diffère de celle de l'EM "
       "à Kmax", "difference", "degenere", "VB-emp", "EM-Kmax", {"plan": "sous", "N": str(n)}, rh="RH4", attendu="A < B")
_h("HP5", "prix", "Hyperparamètres", "Sur un même sous-échantillon (N = 250), la variance de K̂ du VB entre configurations "
   "de priors plausibles diffère de la variance de K̂ de l'EM entre ses propres choix (BIC ou ICL, trois graines)",
   "difference", "var_k", "VB-priors", "EM-choix", {"plan": "sensibilite"}, rh="RH2", attendu="A > B")
for n in (30, 60, 120):
    _h(f"HP7-N{n}", "prix", "Effet des priors", f"N = {n} : la fréquence d'ajustements dégénérés du MAP-EM (mêmes priors que "
       "le VB, sans loi sur les paramètres) diffère de celle de l'EM à Kmax", "difference", "degenere", "MAP-EM", "EM-Kmax",
       {"plan": "sous", "N": str(n)}, rh="RH4", attendu="A < B")

# ------------------------------------------------------------------------------ texte
for n in (50, 200, 1000):
    _h(f"HT1-N{n}", "texte", "Surapprentissage", f"N = {n} documents : l'écart relatif de perplexité (test / apprentissage) "
       "du pLSA diffère de celui de la LDA", "difference", "ecart_relatif", "pLSA", "LDA", {"N": str(n)}, rh="RH4",
       attendu="A > B")

# ------------------------------------------------------------------------------ décisions par intervalle et prévision
# (préfixe de l'identifiant, hypothèse de recherche, résultat attendu, test)
AUTRES = [
    ("HP4", "RH5", "ratio > 1", "Rapport des temps médians pipeline EM-BIC / VB, IC bootstrap de la médiane"),
    ("HP6-VB", "RH3", "< 90 %", "Couverture à 90 % des intervalles de crédibilité du VB, IC bootstrap par grappes"),
    ("HP6-bootstrap EM", "RH3", "compatible avec 90 %", "Couverture à 90 % du bootstrap de l'EM, IC bootstrap par grappes"),
    ("HPP1", "RH1", None, "Log-score de test, EM-BIC contre gaussienne unique (Diebold-Mariano par mois)"),
    ("HPP2", "RH1", None, "Log-score de test, VB-emp (prédictive) contre gaussienne unique"),
    ("HPP3", "RH1", None, "Log-score de test, VB-emp (prédictive) contre EM-BIC"),
    ("HPP4", "RH3", None, "Log-score de test, VB-emp prédictive contre VB-emp plug-in (apport de la loi sur les paramètres)"),
    ("HPP5", "RH2", None, "Log-score de test, VB-cal contre VB-emp (effet du choix des priors)"),
    ("HPP6", "RH4", None, "Log-score de test, MAP-EM contre EM-BIC (effet des priors sans loi sur les paramètres)"),
]


def rattachement(ident: str):
    """(hypothèse de recherche, résultat attendu) d'un identifiant de décision (test apparié ou décision par intervalle)."""
    for h in H:
        if h.id == ident:
            return h.rh, h.attendu
    for pre, rh, att, _ in AUTRES:
        if ident.startswith(pre):
            return rh, att
    return "", None


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


def exclusions(h: Hypothese, lignes: list[dict], cle_rep: str = "rep") -> int:
    """Réplications du point de l'hypothèse écartées des différences appariées (bras en échec ou métrique absente)."""
    def garde(l):
        return all(str(l.get(k)) == v for k, v in h.filtre.items())
    reps = {l[cle_rep] for l in lignes if garde(l) and l.get("bras") in (h.bras_a, h.bras_b)}
    return len(reps) - len(diffs(h, lignes, cle_rep))


def marge(h: Hypothese):
    import parametres as PARAM
    if h.marge is None:
        return None
    if h.marge == "K":
        return float(PARAM.valeur("marge_k"))
    return float(PARAM.valeur("marges_equivalence")[h.marge])
