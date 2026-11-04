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
EPISODES = [("2023-08", "août 2023 : maïs +24 % en un mois dans l'Extrême-Nord (PAM, 2023)"),
            ("2026-04", "avril 2026 : maïs et sorgho 40 à 50 % moins chers qu'un an plus tôt à Kousseri, Mokolo, Mora "
                        "(FEWS NET, 2026)")]

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
           {"id": "HP5", "axe": "Hyperparamètres", "test": "descriptif",
            "enonce": "Variance de K̂ du VB sur le domaine plausible des priors contre variance de K̂ de l'EM-BIC entre graines"},
           {"id": "HP6", "axe": "Incertitude", "test": "intervalle",
            "enonce": "Couverture à 90 % des intervalles (VB : crédibilité ; EM : bootstrap), inconditionnelle"}]
    hs += [{"id": f"HPP{i}", "axe": "Prévision", "test": "Diebold-Mariano (Holm)", "enonce": f"Log-score : {a} contre {b}"}
           for i, (a, b) in enumerate(EP.DM_DECLARES, start=1)]
    return hs


def non_calibres() -> list[str]:
    return PARAM.non_calibres()
