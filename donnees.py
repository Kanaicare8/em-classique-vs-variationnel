"""
================================================================================
DONNÉES : générateurs synthétiques et lecteurs écrits à la main (sans scikit-learn ni nltk)
================================================================================

  Synthétiques   gen_gauss(), gen_student(), centres_triangle(), centres_ligne()
  Iris           charger_iris()              data/iris.csv (Fisher 1936, UCI)
  Prix (PAM)     charger_prix()              data/prix/wfp_cmr_panier.csv (extrait HDX, CC BY-IGO), empreinte
                                             SHA-256 vérifiée ; écarts au niveau des 12 mois précédents
  Texte          charger_20newsgroups()      archive originale 20news-bydate.tar.gz (Lang 1995),
                                             lue avec tarfile ; en-têtes, citations et signatures
                                             retirés ; racinisation de Porter (1980) écrite ici ;
                                             mots vides définis par la fréquence documentaire
                                             (aucune liste externe).
"""

from __future__ import annotations

import csv
import hashlib
import math
import re
import tarfile
from collections import Counter
from datetime import date
from pathlib import Path

import torch

import algorithmes as A

RACINE = Path(__file__).parent
DATA = RACINE / "data"


# ==============================================================================
# SYNTHÉTIQUES
# ==============================================================================

def gen_gauss(n, centres, sigma, poids=None, graine=0):
    """Mélange de gaussiennes isotropes d'écart-type sigma. Retourne (X, y)."""
    g = A.generateur(graine)
    centres = torch.as_tensor(centres, dtype=torch.float64)
    K = centres.shape[0]
    p = torch.full((K,), 1.0 / K) if poids is None else torch.as_tensor(poids, dtype=torch.float64)
    y = torch.multinomial(p, n, replacement=True, generator=g)
    X = centres[y] + sigma * torch.randn(n, centres.shape[1], generator=g)
    return X, y


def gen_student(n, centres, sigma, nu, graine=0):
    """Composantes de Student (nu degrés de liberté) de variance sigma², mêmes centres : queues épaisses."""
    g = A.generateur(graine)
    centres = torch.as_tensor(centres, dtype=torch.float64)
    K, D = centres.shape
    y = torch.randint(K, (n,), generator=g)
    z = torch.randn(n, D, generator=g)
    with torch.random.fork_rng():
        torch.manual_seed(int(graine) % (2 ** 62))
        chi2 = torch.distributions.Gamma(torch.tensor(nu / 2.0), torch.tensor(0.5)).sample((n,))
    X = centres[y] + sigma * z * torch.sqrt(nu / chi2)[:, None] / (nu / (nu - 2.0)) ** 0.5
    return X, y


def centres_triangle(d_sigma, sigma=1.0, D=2):
    """Trois centres équidistants, distance d_sigma x sigma deux à deux (D >= 2)."""
    c = torch.zeros(3, D)
    c[1, 0] = d_sigma * sigma
    c[2, 0] = d_sigma * sigma / 2
    c[2, 1] = d_sigma * sigma * 3 ** 0.5 / 2
    return c


def centres_ligne(K, ecart, D=2):
    c = torch.zeros(K, D)
    c[:, 0] = torch.arange(K) * ecart
    return c


# ==============================================================================
# IRIS ET PRIX ALIMENTAIRES DU CAMEROUN
# ==============================================================================

def charger_iris():
    """Iris de Fisher (1936) : X (150, 4) en centimètres, y (150,) espèces 0, 1, 2."""
    lignes = list(csv.reader(open(DATA / "iris.csv", encoding="utf-8")))[1:]
    lignes = [l for l in lignes if l]
    X = torch.tensor([[float(v) for v in l[:4]] for l in lignes], dtype=torch.float64)
    especes = {e: i for i, e in enumerate(dict.fromkeys(l[4] for l in lignes))}
    return X, torch.tensor([especes[l[4]] for l in lignes])


PANIER_PRIX = ("Maize (white)", "Rice (long grain, imported)", "Beans (niebe)")
NOMS_PANIER = ("maïs blanc", "riz importé", "niébé")
SHA256_PRIX = "6b865e4068ad988faa80275ab0e228b5514a0836633f4991e2c18eae7d6b976f"   # extrait du 27/10/2026 (HDX du 04/10/2026)

# Épisodes datés par les bulletins (lecture qualitative, aucune décision n'en dépend). « marches » vide : toute la région.
# Le second épisode est une BAISSE : le régime de tension ne doit pas s'y allumer (contrôle négatif).
EPISODES_PRIX = (
    {"mois": "2023-08", "region": "Extrême-Nord", "marches": (), "sens": "hausse", "source": "pam2023bulletin",
     "texte": "août 2023 : maïs +24 % en un mois dans l'Extrême-Nord (PAM, 2023)"},
    {"mois": "2026-04", "region": "Extrême-Nord", "marches": ("Kousseri", "Mokolo", "Mora"), "sens": "baisse",
     "source": "fewsnet2026",
     "texte": "avril 2026 : maïs et sorgho 40 à 50 % moins chers qu'un an plus tôt à Kousseri, Mokolo, Mora "
              "(FEWS NET, 2026)"},
)


def prix_bruts(denree: str = PANIER_PRIX[0]) -> dict:
    """Prix de détail (XAF/kg) d'une denrée : {marché: {mois_index: prix}}, pics isolés écartés comme dans charger_prix."""
    import parametres as PARAM
    facteur = float(PARAM.valeur("prix_facteur_pic"))
    serie = {}
    for l in csv.DictReader(open(DATA / "prix" / "wfp_cmr_panier.csv", encoding="utf-8")):
        if l["commodity"] == denree:
            serie.setdefault(l["market"], {})[mois_index(l["date"])] = math.log(float(l["price"]))
    for s in serie.values():
        for t in pics_isoles(s, facteur):
            s.pop(t)
    return {m: {t: math.exp(v) for t, v in s.items()} for m, s in serie.items()}


def mois_index(aaaa_mm: str) -> int:
    """'2023-08' -> 2023 x 12 + 7 (mois consécutifs = entiers consécutifs)."""
    return int(aaaa_mm[:4]) * 12 + int(aaaa_mm[5:7]) - 1


def mois_texte(i: int) -> str:
    return f"{i // 12:04d}-{i % 12 + 1:02d}"


def pics_isoles(serie: dict, facteur: float) -> list[int]:
    """Mois t dont le log-prix diffère d'au moins ln(facteur), dans le même sens, des mois t - 1 et t + 1 (tous deux relevés)."""
    s = math.log(facteur)
    out = []
    for t, v in serie.items():
        if t - 1 in serie and t + 1 in serie:
            a, b = v - serie[t - 1], v - serie[t + 1]
            if min(abs(a), abs(b)) >= s and a * b > 0:
                out.append(t)
    return out


def charger_prix(fenetre: int | None = None, releves_min: int | None = None, facteur_pic: float | None = None) -> dict:
    """
    Panier de trois denrées de base (maïs blanc : céréale locale ; riz importé : céréale importée ; niébé :
    légumineuse), prix de détail en XAF par kg, extrait de la base de prix du PAM (empreinte SHA-256 vérifiée).

    Nettoyage (registre « prix_facteur_pic ») : les pics isolés d'un mois (pics_isoles) sont écartés AVANT le calcul
    des écarts ; ils sont rendus dans "ecartes" (marché, denrée, mois, prix).

    Variable de chaque denrée j, pour le marché m et le mois t : écart au niveau récent
        e_j(m, t) = ln p_j(m, t) - moyenne des ln p_j(m, u), u = t - fenetre .. t - 1 relevés,
    défini si au moins `releves_min` relevés existent dans la fenêtre. Elle est CAUSALE (aucune information
    postérieure à t), insensible aux mois manquants et retire la dérive lente des prix (inflation) ; un écart
    de +0,30 signifie un prix environ 35 % au-dessus de son niveau des douze derniers mois. Une observation
    (marché, mois) est retenue si les trois écarts sont définis.

    Retourne {"X" (N, 3), "marche" (N,), "mois" (N,), "marches", "regions", "lat", "lon", "variables", "panier"}.
    """
    import parametres as PARAM
    fenetre = int(PARAM.valeur("prix_fenetre_mois")) if fenetre is None else fenetre
    releves_min = int(PARAM.valeur("prix_releves_min")) if releves_min is None else releves_min
    facteur_pic = float(PARAM.valeur("prix_facteur_pic")) if facteur_pic is None else facteur_pic
    chemin = DATA / "prix" / "wfp_cmr_panier.csv"
    empreinte = hashlib.sha256(chemin.read_bytes()).hexdigest()
    if empreinte != SHA256_PRIX:
        raise RuntimeError(f"{chemin.name} : empreinte {empreinte[:12]}... différente de l'extrait du mémoire")
    serie, info = {}, {}
    for l in csv.DictReader(open(chemin, encoding="utf-8")):
        serie.setdefault((l["market"], l["commodity"]), {})[mois_index(l["date"])] = math.log(float(l["price"]))
        info[l["market"]] = (l["admin1"], float(l["latitude"]), float(l["longitude"]))
    ecartes = []
    for (m, c), s in serie.items():
        for t in pics_isoles(s, facteur_pic):
            ecartes.append({"marche": m, "denree": c, "mois": mois_texte(t), "prix": round(math.exp(s.pop(t)), 2)})
    marches = sorted(info)
    num = {m: i for i, m in enumerate(marches)}

    def ecart(m, c, t):
        s = serie.get((m, c), {})
        if t not in s:
            return None
        passe = [s[u] for u in range(t - fenetre, t) if u in s]
        return s[t] - sum(passe) / len(passe) if len(passe) >= releves_min else None
    obs = []
    for m in marches:
        for t in sorted(set().union(*(serie.get((m, c), {}).keys() for c in PANIER_PRIX))):
            x = [ecart(m, c, t) for c in PANIER_PRIX]
            if all(v is not None for v in x):
                obs.append((t, num[m], x))
    obs.sort(key=lambda o: (o[0], o[1]))
    return {"X": torch.tensor([o[2] for o in obs], dtype=torch.float64),
            "marche": torch.tensor([o[1] for o in obs]), "mois": torch.tensor([o[0] for o in obs]),
            "marches": marches, "regions": [info[m][0] for m in marches],
            "lat": torch.tensor([info[m][1] for m in marches], dtype=torch.float64),
            "lon": torch.tensor([info[m][2] for m in marches], dtype=torch.float64),
            "variables": [f"écart {n}" for n in NOMS_PANIER], "panier": list(PANIER_PRIX),
            "ecartes": sorted(ecartes, key=lambda e: (e["mois"], e["marche"], e["denree"]))}


# ==============================================================================
# RACINISATION DE PORTER (1980), écrite d'après l'article original
# ==============================================================================

_VOY = set("aeiou")


def _consonne(m: str, i: int) -> bool:
    c = m[i]
    if c in _VOY:
        return False
    if c == "y":
        return i == 0 or not _consonne(m, i - 1)
    return True


def _mesure(m: str) -> int:
    """m dans [C](VC)^m[V]."""
    n, i, L = 0, 0, len(m)
    while i < L and _consonne(m, i):
        i += 1
    while i < L:
        while i < L and not _consonne(m, i):
            i += 1
        if i >= L:
            break
        while i < L and _consonne(m, i):
            i += 1
        n += 1
    return n


def _a_voyelle(m: str) -> bool:
    return any(not _consonne(m, i) for i in range(len(m)))


def _double_consonne(m: str) -> bool:
    return len(m) >= 2 and m[-1] == m[-2] and _consonne(m, len(m) - 1)


def _cvc(m: str) -> bool:
    """*o : consonne-voyelle-consonne finale, la dernière n'étant ni w, ni x, ni y."""
    if len(m) < 3:
        return False
    return (_consonne(m, len(m) - 3) and not _consonne(m, len(m) - 2) and _consonne(m, len(m) - 1)
            and m[-1] not in "wxy")


def _remplacer(mot: str, regles, condition) -> str:
    """Applique la règle au suffixe le plus long ; si sa condition échoue, aucune autre règle de l'étape."""
    for suf, rep in sorted(regles, key=lambda t: -len(t[0])):
        if mot.endswith(suf):
            radical = mot[: len(mot) - len(suf)]
            return radical + rep if condition(radical, suf) else mot
    return mot


_ETAPE2 = [("ational", "ate"), ("tional", "tion"), ("enci", "ence"), ("anci", "ance"), ("izer", "ize"),
           ("abli", "able"), ("alli", "al"), ("entli", "ent"), ("eli", "e"), ("ousli", "ous"), ("ization", "ize"),
           ("ation", "ate"), ("ator", "ate"), ("alism", "al"), ("iveness", "ive"), ("fulness", "ful"),
           ("ousness", "ous"), ("aliti", "al"), ("iviti", "ive"), ("biliti", "ble")]
_ETAPE3 = [("icate", "ic"), ("ative", ""), ("alize", "al"), ("iciti", "ic"), ("ical", "ic"), ("ful", ""), ("ness", "")]
_ETAPE4 = ["al", "ance", "ence", "er", "ic", "able", "ible", "ant", "ement", "ment", "ent", "ion", "ou", "ism",
           "ate", "iti", "ous", "ive", "ize"]


def porter(mot: str) -> str:
    """Racine de Porter (1980) d'un mot anglais en minuscules."""
    m = mot
    if len(m) <= 2:
        return m
    # étape 1a
    if m.endswith("sses"):
        m = m[:-2]
    elif m.endswith("ies"):
        m = m[:-2]
    elif m.endswith("ss"):
        pass
    elif m.endswith("s"):
        m = m[:-1]
    # étape 1b
    suite = False
    if m.endswith("eed"):
        if _mesure(m[:-3]) > 0:
            m = m[:-1]
    elif m.endswith("ed") and _a_voyelle(m[:-2]):
        m, suite = m[:-2], True
    elif m.endswith("ing") and _a_voyelle(m[:-3]):
        m, suite = m[:-3], True
    if suite:
        if m.endswith(("at", "bl", "iz")):
            m += "e"
        elif _double_consonne(m) and m[-1] not in "lsz":
            m = m[:-1]
        elif _mesure(m) == 1 and _cvc(m):
            m += "e"
    # étape 1c
    if m.endswith("y") and _a_voyelle(m[:-1]):
        m = m[:-1] + "i"
    # étapes 2 et 3
    m = _remplacer(m, _ETAPE2, lambda r, s: _mesure(r) > 0)
    m = _remplacer(m, _ETAPE3, lambda r, s: _mesure(r) > 0)
    # étape 4
    m = _remplacer(m, [(s, "") for s in _ETAPE4],
                   lambda r, s: _mesure(r) > 1 and (s != "ion" or (len(r) > 0 and r[-1] in "st")))
    # étape 5a
    if m.endswith("e"):
        r = m[:-1]
        if _mesure(r) > 1 or (_mesure(r) == 1 and not _cvc(r)):
            m = r
    # étape 5b
    if _mesure(m) > 1 and _double_consonne(m) and m.endswith("l"):
        m = m[:-1]
    return m


# ==============================================================================
# 20 NEWSGROUPS
# ==============================================================================

_CITATION = re.compile(r"(writes in|writes:|wrote:|says:|said:|^In article|^Quoted from|^\||^>)")


def _nettoyer_message(texte: str) -> str:
    """Retire l'en-tête (jusqu'à la première ligne vide), les lignes de citation et la signature (après « -- »)."""
    _, _, corps = texte.partition("\n\n")
    lignes = [l for l in corps.split("\n") if not _CITATION.search(l)]
    lignes = "\n".join(lignes).strip().split("\n")
    for i in range(len(lignes) - 1, -1, -1):
        if lignes[i].strip().strip("-") == "" and lignes[i].strip().startswith("--"):
            lignes = lignes[:i]
            break
    return "\n".join(lignes)


def charger_20newsgroups(categories, archive: Path = DATA / "texte" / "20news-bydate.tar.gz"):
    """
    Documents bruts des catégories demandées (parties train et test de « bydate » réunies, l'échantillonnage
    étant refait par le protocole). Retourne (textes nettoyés, étiquettes).
    """
    if not Path(archive).exists():
        raise FileNotFoundError(f"{archive} absent : télécharger http://qwone.com/~jason/20Newsgroups/20news-bydate.tar.gz "
                                f"(14 Mo) dans {Path(archive).parent}")
    textes, etiq = [], []
    ordre = {c: i for i, c in enumerate(categories)}
    with tarfile.open(archive, "r:gz") as t:
        for m in t:
            if not m.isfile():
                continue
            parties = m.name.split("/")
            if len(parties) < 3 or parties[-2] not in ordre:
                continue
            brut = t.extractfile(m).read().decode("latin-1")
            textes.append(_nettoyer_message(brut))
            etiq.append(ordre[parties[-2]])
    return textes, torch.tensor(etiq)


def tokeniser(texte: str, longueur_min_mot: int) -> list[str]:
    return [porter(w) for w in re.findall(r"[a-z]+", texte.lower()) if len(w) >= longueur_min_mot]


def matrice_documents(textes, vocab_taille: int, df_min: int, df_max: float, longueur_min_mot: int,
                      longueur_min_doc: int):
    """
    Matrice documents x mots. Vocabulaire : racines présentes dans au moins df_min documents et dans au plus
    une fraction df_max des documents (les mots grammaticaux, présents partout, sont écartés par ce seul
    critère de fréquence documentaire), puis les vocab_taille plus fréquentes. Documents d'au moins
    longueur_min_doc occurrences retenus. Retourne (comptes (D,V), indices des documents retenus, vocabulaire).
    """
    docs = [tokeniser(t, longueur_min_mot) for t in textes]
    df = Counter(w for d in docs for w in set(d))
    freq = Counter(w for d in docs for w in d)
    n = len(docs)
    vocab = [w for w, _ in freq.most_common() if df_min <= df[w] <= df_max * n][:vocab_taille]
    idx = {w: i for i, w in enumerate(vocab)}
    lignes, garde = [], []
    for j, d in enumerate(docs):
        c = Counter(idx[w] for w in d if w in idx)
        if sum(c.values()) >= longueur_min_doc:
            v = torch.zeros(len(vocab), dtype=torch.float64)
            for i, k in c.items():
                v[i] = k
            lignes.append(v)
            garde.append(j)
    return torch.stack(lignes), torch.tensor(garde), vocab
