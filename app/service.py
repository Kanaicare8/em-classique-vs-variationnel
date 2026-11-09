"""
================================================================================
SERVICE DE L'APPLICATION : données, précalcul et magasin confirmatoire, en lecture seule
================================================================================

Aucun ajustement n'est lancé ici. Trois sources :
  données           etape_prix.donnees() (écarts standardisés par l'apprentissage) et l'extrait PAM brut ;
  précalcul         resultats/app/ (app/precalcul.py) : unités « reference » et « alerte », résumé des régimes ;
  confirmatoire     resultats/magasin/ et resultats/tables/, lus par figures.py ; jamais écrits ni « réparés »
                    (Magasin.complete() déplacerait un fichier tronqué : on n'utilise que existe() et lire()).
"""

from __future__ import annotations

import csv
import math
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

import torch  # noqa: E402  (import long : une à deux minutes sur le poste du mémoire)

import donnees as DO  # noqa: E402
import etape_prix as EP  # noqa: E402
import figures as FG  # noqa: E402
import hypotheses as HY  # noqa: E402
import parametres as PARAM  # noqa: E402
import persistance as PE  # noqa: E402

DOSSIER_APP = RACINE / "resultats" / "app"
NOMS = list(DO.NOMS_PANIER)
PANIER = list(DO.PANIER_PRIX)
BRAS = list(EP.BRAS_ALERTE)
FIN_APP = DO.mois_index(str(PARAM.valeur("prix_fin_apprentissage")))
EPISODES = [(e["mois"], e["texte"]) for e in DO.EPISODES_PRIX]     # source unique : donnees.EPISODES_PRIX

# ------------------------------------------------------------------------------ données
_, _, D = EP.donnees()
MARCHES = D["marches"]
REGIONS = D["regions"]
LAT, LON = D["lat"].tolist(), D["lon"].tolist()
X = D["X"]                                         # écarts du log-prix au niveau des 12 mois précédents, (N, 3)
MOIS = D["mois"].tolist()
MARCHE = D["marche"].tolist()
APP = D["app"].tolist()
N_APP = torch.bincount(D["marche"][D["app"]], minlength=len(MARCHES)).tolist()
N_TEST = torch.bincount(D["marche"][~D["app"]], minlength=len(MARCHES)).tolist()
MOIS_TOUS = sorted(set(MOIS))
REGIONS_ORDRE = sorted(set(REGIONS), key=lambda r: (-sum(N_APP[i] + N_TEST[i] for i, x in enumerate(REGIONS) if x == r), r))
COULEUR_REGION = dict(zip(REGIONS_ORDRE, FG.SERIES + [FG.ENCRE_2]))
COULEUR_DENREE = dict(zip(NOMS, (FG.SERIES[3], FG.SERIES[0], FG.SERIES[2])))
ECARTES = D["ecartes"]
DESCRIPTIF = EP._descriptif()


def _prix_bruts() -> dict:
    """{(marché, denrée) : [(aaaa-mm, prix XAF/kg), ...]} : extrait PAM tel quel, relevés écartés compris."""
    s = {}
    with open(DO.DATA / "prix" / "wfp_cmr_panier.csv", encoding="utf-8") as f:
        for l in csv.DictReader(f):
            s.setdefault((l["market"], l["commodity"]), []).append((l["date"][:7], float(l["price"])))
    return {k: sorted(v) for k, v in s.items()}


PRIX = _prix_bruts()
MARCHES_AVEC_PRIX = sorted({m for m, _ in PRIX})
PRIX_NETS = {c: DO.prix_bruts(c) for c in PANIER}   # {denrée : {marché : {mois : prix}}}, pics isolés écartés (mémoire)


def mois_date(t: int) -> str:
    """Indice de mois -> date du milieu du mois, lisible par Plotly."""
    return DO.mois_texte(int(t)) + "-15"


def marche_par_defaut() -> int:
    return max(range(len(MARCHES)), key=lambda i: (N_TEST[i], N_APP[i]))


def observations(marche: int) -> list[int]:
    return [i for i, m in enumerate(MARCHE) if m == marche]


# ------------------------------------------------------------------------------ précalcul (resultats/app/)
_cache = {"cle": None, "valeur": None}


def precalcul():
    """Précalcul le plus complet disponible (complet, sinon rapide), relu si les fichiers ont changé ; None sinon."""
    for rapide in (False, True):
        reg = DOSSIER_APP / ("regimes_rapide.pt" if rapide else "regimes.pt")
        mag = PE.Magasin("prix", DOSSIER_APP / ("magasin_rapide" if rapide else "magasin"))
        if reg.exists() and mag.existe("alerte"):
            cle = (rapide, reg.stat().st_mtime, mag.chemin("alerte").stat().st_mtime)
            if _cache["cle"] != cle:
                al = mag.lire("alerte")
                if al is None:
                    continue
                _cache.update(cle=cle, valeur={"regimes": PE.charger(reg), "alerte": al["artefacts"],
                                               "lignes_alerte": al["lignes"], "rapide": rapide})
            return _cache["valeur"]
    return None


COULEURS_REGIMES = ["#2a78d6", "#1baf7a", "#eda100", "#6250d6", "#e87ba4", "#008300", "#eb6834"]
COULEUR_TENSION = "#e34948"


def regimes(nom: str) -> list[dict]:
    """Composantes actives d'un bras, ordonnées par écart moyen croissant (unités d'origine) ; la dernière règle est
    celle du mémoire : le régime de tension est la composante active d'écart moyen le plus élevé."""
    b = precalcul()["regimes"]["bras"][nom]
    aff = b["affectation"]
    app = D["app"]
    ks = sorted((int(k) for k in torch.nonzero(b["actives"]).flatten()), key=lambda k: float(b["mu"][k].mean()))
    out = []
    autres = iter(COULEURS_REGIMES)
    for rang, k in enumerate(ks, start=1):
        tension = k == int(b["k_tension"])
        out.append({"k": k, "nom": f"R{rang}", "tension": tension, "poids": float(b["pi"][k]),
                    "mu": b["mu"][k].tolist(), "cov": b["cov"][k],
                    "n_app": int(((aff == k) & app).sum()), "n_test": int(((aff == k) & ~app).sum()),
                    "couleur": COULEUR_TENSION if tension else next(autres)})
    return out


# ------------------------------------------------------------------------------ nouveau relevé (page « Nouveau relevé »)
FENETRE = int(PARAM.valeur("prix_fenetre_mois"))
RELEVES_MIN = int(PARAM.valeur("prix_releves_min"))
_cache_tir = {"cle": None, "valeur": None}


def tirages():
    """Tirages de l'unité « alerte » écrits par app/precalcul.py (resultats/app/releve.pt) ; None s'ils manquent."""
    for nom in ("releve.pt", "releve_rapide.pt"):
        f = DOSSIER_APP / nom
        if f.exists():
            if _cache_tir["cle"] != (nom, f.stat().st_mtime):
                _cache_tir.update(cle=(nom, f.stat().st_mtime), valeur=PE.charger(f))
            return _cache_tir["valeur"]
    return None


def niveau_12_mois(marche: int, denree: str, t: int):
    """(niveau en XAF/kg, nombre de relevés) des `FENETRE` mois avant t, comme donnees.charger_prix ; niveau = exp(moyenne
    des log-prix) ; None si moins de `RELEVES_MIN` relevés."""
    s = PRIX_NETS[denree].get(MARCHES[marche], {})
    passe = [math.log(s[u]) for u in range(t - FENETRE, t) if u in s]
    return (math.exp(sum(passe) / len(passe)), len(passe)) if len(passe) >= RELEVES_MIN else (None, len(passe))


def evaluer_releve(marche: int, t: int, prix: dict):
    """Écarts d'un relevé saisi ({denrée : XAF/kg}) et, pour chaque bras, P(tension) et intervalle à 90 % ; même définition
    que le mémoire (écart = ln p - moyenne des ln p des 12 mois précédents ; P plug-in pour EM-BIC, moyenne sous q pour le
    VB ; intervalle = quantiles 5 % et 95 % des tirages). Rend (écarts, niveaux, résultats par bras ou None)."""
    niveaux = {c: niveau_12_mois(marche, c, t) for c in PANIER}
    ecarts = [math.log(prix[c]) - math.log(niveaux[c][0]) if prix.get(c) and niveaux[c][0] else None for c in PANIER]
    tir = tirages()
    if tir is None or any(e is None for e in ecarts):
        return ecarts, niveaux, None
    z = ((torch.tensor(ecarts, dtype=torch.float64) - tir["centre"]) / tir["echelle"])[None]
    out = {}
    for nom, b in tir["bras"].items():
        ps = torch.stack([EP._proba_composante(z, b["pi"][i][None], b["mu"][i][None], b["cov"][i][None],
                                               int(b["k_tirage"][i]))[0, 0] for i in range(len(b["pi"]))])
        pl = b["plugin"]
        p = float(ps.mean()) if b["moyenne_des_tirages"] else \
            float(EP._proba_composante(z, pl["pi"][None], pl["mu"][None], pl["cov"][None], b["k"])[0, 0])
        q = torch.quantile(ps, torch.tensor([0.05, 0.95], dtype=torch.float64))
        out[nom] = {"p": p, "bas": float(q[0]), "haut": float(q[1]), "n_tirages": len(ps)}
    return ecarts, niveaux, out


# ------------------------------------------------------------------------------ calcul confirmatoire (lecture seule)
def magasin_officiel(rapide: bool) -> PE.Magasin:
    return PE.Magasin("prix", RACINE / "resultats" / ("magasin_rapide" if rapide else "magasin"))


def avancement(rapide: bool) -> tuple[int, int]:
    faites = set(magasin_officiel(rapide).cles())
    prevues = [u.cle for u in EP.unites(rapide)]
    return sum(c in faites for c in prevues), len(prevues)


def figure_officielle(nom: str, rapide: bool):
    """Figure du mémoire produite par figures.py depuis le magasin ; (None, message) si l'étape n'est pas faite."""
    try:
        return FG.FIGURES[nom](rapide), None
    except (LookupError, KeyError, TypeError) as ex:
        return None, f"{type(ex).__name__} : {ex}"


def table_officielle(nom: str, rapide: bool):
    return FG.lire_csv(nom, rapide)


def hypotheses_declarees() -> list[dict]:
    hs = [{"id": h.id, "axe": h.axe, "enonce": h.enonce, "test": h.test} for h in HY.famille("prix")]
    hs += [{"id": "HP4", "axe": "Coût", "test": "intervalle",
            "enonce": "Temps du pipeline EM-BIC divisé par le temps d'un VB (étape chronometrage)"},
           {"id": "HP6", "axe": "Incertitude", "test": "intervalle",
            "enonce": "Couverture à 90 % des intervalles (VB : crédibilité ; EM : bootstrap), inconditionnelle"}]
    hs += [{"id": f"HPP{i}", "axe": "Prévision", "test": "Diebold-Mariano (Holm)", "enonce": f"Log-score : {a} contre {b}"}
           for i, (a, b) in enumerate(EP.DM_DECLARES, start=1)]
    return hs


def non_calibres() -> list[str]:
    return PARAM.non_calibres()
